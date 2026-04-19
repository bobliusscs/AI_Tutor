"""
模型配置管理模块 - 管理多模型API配置和模块-模型映射
配置存储在 backend/model_config.json 中
"""
import json
import os
import uuid
import threading
from typing import Optional, Dict, Any, List

from app.services.tts_provider import TTS_PROVIDER_DEFINITIONS


# 配置文件路径（backend/model_config.json）
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONFIG_PATH = os.path.join(_BACKEND_DIR, "model_config.json")

# 功能模块定义
MODULE_DEFINITIONS = [
    {"id": "knowledge_graph", "name": "知识图谱生成", "description": "分析学习资料并生成知识图谱"},
    {"id": "learning_plan", "name": "学习计划生成", "description": "基于知识图谱生成个性化学习计划"},
    {"id": "lesson_ppt", "name": "课件生成", "description": "为知识点生成教学课件PPT"},
    {"id": "exercise", "name": "习题生成", "description": "根据知识点生成练习题和测评"},
    {"id": "agent", "name": "Agent 交互", "description": "AI对话助手的交互模型"},
]

# 线程安全锁（使用RLock支持重入，避免load_model_config调用save_model_config时死锁）
_config_lock = threading.RLock()

# 内存缓存
_config_cache: Optional[Dict[str, Any]] = None


def _generate_id() -> str:
    """生成唯一的模型API ID"""
    return f"model_{uuid.uuid4().hex[:8]}"


def _migrate_from_env() -> Dict[str, Any]:
    """
    从 .env 文件迁移现有配置到新格式
    """
    config = {
        "model_apis": [],
        "module_models": {},
        "tavily_api_key": "",
        "dashscope_api_key": "",
        "tts_apis": [],
        "tts_model": "",
    }

    # 读取 .env 文件
    env_path = os.path.join(_BACKEND_DIR, ".env")
    env_values = {}
    if os.path.exists(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        env_values[key.strip()] = value.strip()
        except Exception as e:
            print(f"[ModelConfig] 读取 .env 文件出错: {e}")

    current_provider = env_values.get("CURRENT_PROVIDER", "ollama")

    # 迁移 Ollama 配置
    ollama_base_url = env_values.get("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_model = env_values.get("OLLAMA_MODEL", "qwen3.5:9B")
    if ollama_model:
        ollama_id = _generate_id()
        config["model_apis"].append({
            "id": ollama_id,
            "name": "本地 Ollama",
            "type": "ollama",
            "base_url": ollama_base_url,
            "model": ollama_model,
            "api_key": "",
            "supports_thinking": True,
        })
        # 如果当前使用 ollama，设置所有模块使用 ollama
        if current_provider == "ollama":
            for mod in MODULE_DEFINITIONS:
                config["module_models"][mod["id"]] = ollama_id

    # 迁移 Custom API 配置
    custom_api_key = env_values.get("CUSTOM_API_KEY", "")
    custom_base_url = env_values.get("CUSTOM_API_BASE_URL", "")
    custom_model = env_values.get("CUSTOM_MODEL", "")
    custom_thinking = env_values.get("CUSTOM_SUPPORTS_THINKING", "false").lower() == "true"

    if custom_model and custom_base_url:
        custom_id = _generate_id()
        config["model_apis"].append({
            "id": custom_id,
            "name": "云端 API",
            "type": "custom",
            "base_url": custom_base_url,
            "model": custom_model,
            "api_key": custom_api_key,
            "supports_thinking": custom_thinking,
        })
        # 如果当前使用 custom，设置所有模块使用 custom
        if current_provider == "custom":
            for mod in MODULE_DEFINITIONS:
                config["module_models"][mod["id"]] = custom_id

    # 迁移 Tavily 和 DashScope 配置
    config["tavily_api_key"] = env_values.get("TAVILY_API_KEY", "")
    dashscope_key = env_values.get("DASHSCOPE_API_KEY", "")
    config["dashscope_api_key"] = dashscope_key

    # 迁移 DashScope TTS 到新的 tts_apis 格式
    if dashscope_key:
        tts_id = _generate_id()
        config["tts_apis"].append({
            "id": tts_id,
            "name": "阿里云百炼 TTS",
            "provider": "dashscope",
            "base_url": "https://dashscope.aliyuncs.com/api/v1",
            "model": "qwen3-tts-flash",
            "api_key": dashscope_key,
            "voice": "Cherry",
        })
        config["tts_model"] = tts_id

    # 确保 module_models 中每个模块都有值（默认用第一个可用模型）
    for mod in MODULE_DEFINITIONS:
        if mod["id"] not in config["module_models"] or not config["module_models"][mod["id"]]:
            if config["model_apis"]:
                config["module_models"][mod["id"]] = config["model_apis"][0]["id"]
            else:
                config["module_models"][mod["id"]] = ""

    return config


def load_model_config() -> Dict[str, Any]:
    """
    读取模型配置，不存在则从 .env 迁移创建
    """
    global _config_cache

    if _config_cache is not None:
        return _config_cache

    with _config_lock:
        if _config_cache is not None:
            return _config_cache

        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    config = json.load(f)
                _config_cache = config
                return config
            except Exception as e:
                print(f"[ModelConfig] 读取 model_config.json 出错: {e}")

        # 文件不存在，从 .env 迁移
        print("[ModelConfig] model_config.json 不存在，从 .env 迁移配置...")
        config = _migrate_from_env()
        save_model_config(config)
        _config_cache = config
        return config


def save_model_config(config: Dict[str, Any]) -> None:
    """
    写入模型配置到文件
    """
    global _config_cache

    with _config_lock:
        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            _config_cache = config
        except Exception as e:
            print(f"[ModelConfig] 写入 model_config.json 出错: {e}")
            raise


def get_module_model_config(module_name: str) -> Optional[Dict[str, Any]]:
    """
    获取指定功能模块的模型配置

    Args:
        module_name: 模块名称，如 "knowledge_graph", "agent" 等

    Returns:
        模型配置字典，包含 type, base_url, model, api_key 等字段；
        如果模块未配置模型，返回 None
    """
    config = load_model_config()
    model_id = config.get("module_models", {}).get(module_name, "")

    if not model_id:
        return None

    # 查找对应的模型API配置
    for api in config.get("model_apis", []):
        if api["id"] == model_id:
            return api

    return None


def get_module_provider_config(module_name: str) -> Optional[Dict[str, Any]]:
    """
    获取指定功能模块的 Provider 构建参数

    Returns:
        {"provider_name": "ollama"/"custom", "config": {...}}
        如果模块未配置模型，返回 None
    """
    api_config = get_module_model_config(module_name)
    if not api_config:
        return None

    provider_name = api_config.get("type", "ollama")

    # 构建与 AIModelProvider 兼容的 config 字典
    if provider_name == "ollama":
        config = {
            "CURRENT_PROVIDER": "ollama",
            "OLLAMA_BASE_URL": api_config.get("base_url", "http://localhost:11434"),
            "OLLAMA_MODEL": api_config.get("model", "qwen3.5:9B"),
            "SUPPORTS_VISION": api_config.get("supports_vision", False),
            "SUPPORTS_VIDEO": api_config.get("supports_video", False),
            "SUPPORTS_AUDIO": api_config.get("supports_audio", False),
        }
    else:
        config = {
            "CURRENT_PROVIDER": "custom",
            "CUSTOM_API_KEY": api_config.get("api_key", ""),
            "CUSTOM_API_BASE_URL": api_config.get("base_url", ""),
            "CUSTOM_MODEL": api_config.get("model", ""),
            "CUSTOM_SUPPORTS_THINKING": api_config.get("supports_thinking", False),
            "SUPPORTS_VISION": api_config.get("supports_vision", False),
            "SUPPORTS_VIDEO": api_config.get("supports_video", False),
            "SUPPORTS_AUDIO": api_config.get("supports_audio", False),
        }

    return {"provider_name": provider_name, "config": config}


def clear_config_cache():
    """清除配置缓存（设置更新时调用）"""
    global _config_cache
    with _config_lock:
        _config_cache = None


def get_tts_model_config() -> Optional[Dict[str, Any]]:
    """
    获取当前选中的 TTS 模型配置

    Returns:
        TTS API 配置字典，包含 provider, base_url, model, api_key, voice 等字段；
        如果未配置 TTS，返回 None
    """
    config = load_model_config()
    tts_apis = config.get("tts_apis", [])
    tts_model_id = config.get("tts_model", "")

    if not tts_apis:
        # 兼容旧配置：如果有 dashscope_api_key，返回兼容配置
        dashscope_key = config.get("dashscope_api_key", "")
        if dashscope_key:
            return {
                "provider": "dashscope",
                "base_url": "https://dashscope.aliyuncs.com/api/v1",
                "model": "qwen3-tts-flash",
                "api_key": dashscope_key,
                "voice": "Cherry",
            }
        return None

    # 查找选中的 TTS API
    for api in tts_apis:
        if api.get("id") == tts_model_id:
            return api

    # 如果没有选中，返回第一个
    if tts_apis:
        return tts_apis[0]

    return None
