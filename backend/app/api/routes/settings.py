"""
设置 API 路由 - 管理多模型API配置和模块-模型映射
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from app.schemas import Response
from app.core.model_config import (
    load_model_config,
    save_model_config,
    clear_config_cache,
    MODULE_DEFINITIONS,
    get_tts_model_config,
)
from app.services.tts_provider import (
    TTS_PROVIDER_DEFINITIONS,
    TTS_VOICES,
    create_tts_provider,
    reset_tts_provider_cache,
)


router = APIRouter()


# ========== 请求/响应模型 ==========

class ModelApiItem(BaseModel):
    """单个模型API配置"""
    id: Optional[str] = None  # 新增时为None，由后端生成
    name: str = ""
    type: str = "ollama"  # ollama / custom
    base_url: str = ""
    model: str = ""
    api_key: Optional[str] = ""
    supports_thinking: bool = False
    supports_vision: bool = False
    supports_video: bool = False
    supports_audio: bool = False


class TtsApiItem(BaseModel):
    """单个TTS API配置"""
    id: Optional[str] = None
    name: str = ""
    provider: str = "dashscope"  # dashscope / openai / edge
    base_url: str = ""
    model: str = ""
    api_key: Optional[str] = ""
    voice: str = ""


class ModelConfigRequest(BaseModel):
    """保存模型配置请求"""
    model_apis: List[ModelApiItem] = []
    module_models: Dict[str, str] = {}  # module_id -> model_api_id
    tavily_api_key: Optional[str] = None
    dashscope_api_key: Optional[str] = None
    tts_apis: List[TtsApiItem] = []
    tts_model: Optional[str] = None  # 选中的TTS API ID


# ========== API 接口 ==========

@router.get("/model-config", response_model=Response)
async def get_model_config():
    """
    获取完整的模型配置
    包括：模型API列表、模块-模型映射、Tavily/DashScope Key、模块定义
    """
    config = load_model_config()

    # 对 API Key 进行掩码处理
    masked_apis = []
    for api in config.get("model_apis", []):
        masked_api = {**api}
        if masked_api.get("api_key") and len(masked_api["api_key"]) > 8:
            key = masked_api["api_key"]
            masked_api["api_key"] = key[:4] + "****" + key[-4:]
            masked_api["api_key_configured"] = True
        elif masked_api.get("api_key"):
            masked_api["api_key_configured"] = True
        else:
            masked_api["api_key_configured"] = False
        masked_apis.append(masked_api)

    # Tavily Key 掩码
    tavily_key = config.get("tavily_api_key", "")
    tavily_configured = bool(tavily_key)
    masked_tavily = ""
    if tavily_key:
        if len(tavily_key) > 8:
            masked_tavily = tavily_key[:4] + "****" + tavily_key[-4:]
        else:
            masked_tavily = "****"

    # DashScope Key 掩码
    dashscope_key = config.get("dashscope_api_key", "")
    dashscope_configured = bool(dashscope_key)
    masked_dashscope = ""
    if dashscope_key:
        if len(dashscope_key) > 8:
            masked_dashscope = dashscope_key[:4] + "****" + dashscope_key[-4:]
        else:
            masked_dashscope = "****"

    # TTS APIs 掩码
    masked_tts_apis = []
    for api in config.get("tts_apis", []):
        masked_api = {**api}
        if masked_api.get("api_key") and len(masked_api["api_key"]) > 8:
            key = masked_api["api_key"]
            masked_api["api_key"] = key[:4] + "****" + key[-4:]
            masked_api["api_key_configured"] = True
        elif masked_api.get("api_key"):
            masked_api["api_key_configured"] = True
        else:
            masked_api["api_key_configured"] = False
        masked_tts_apis.append(masked_api)

    return Response(
        success=True,
        message="获取配置成功",
        data={
            "model_apis": masked_apis,
            "module_models": config.get("module_models", {}),
            "module_definitions": MODULE_DEFINITIONS,
            "tavily_api_key": masked_tavily,
            "tavily_configured": tavily_configured,
            "dashscope_api_key": masked_dashscope,
            "dashscope_configured": dashscope_configured,
            "tts_apis": masked_tts_apis,
            "tts_model": config.get("tts_model", ""),
            "tts_provider_definitions": TTS_PROVIDER_DEFINITIONS,
            "tts_voices": TTS_VOICES,
        }
    )


@router.post("/model-config", response_model=Response)
async def update_model_config(request: ModelConfigRequest):
    """
    保存完整的模型配置
    """
    import uuid

    try:
        # 读取当前配置（获取未掩码的 API Key）
        current_config = load_model_config()
        current_apis_map = {api["id"]: api for api in current_config.get("model_apis", [])}

        # 处理模型API列表 - 保留未修改的API Key
        processed_apis = []
        for item in request.model_apis:
            api_dict = item.model_dump()

            # 如果是新增模型，生成ID
            if not api_dict.get("id"):
                api_dict["id"] = f"model_{uuid.uuid4().hex[:8]}"

            # 处理 API Key 掩码：如果包含 ****，说明用户未修改，保留原值
            api_key = api_dict.get("api_key", "")
            if "****" in api_key or api_key == "":
                # 保留原配置中的 key
                old_api = current_apis_map.get(api_dict["id"])
                if old_api and old_api.get("api_key"):
                    api_dict["api_key"] = old_api["api_key"]
                else:
                    api_dict["api_key"] = ""

            processed_apis.append(api_dict)

        # 处理 TTS APIs 列表 - 保留未修改的 API Key
        current_tts_map = {api["id"]: api for api in current_config.get("tts_apis", [])}
        processed_tts_apis = []
        for item in request.tts_apis:
            tts_dict = item.model_dump()

            # 如果是新增，生成ID
            if not tts_dict.get("id"):
                tts_dict["id"] = f"tts_{uuid.uuid4().hex[:8]}"

            # 处理 API Key 掩码
            api_key = tts_dict.get("api_key", "")
            if "****" in api_key or api_key == "":
                old_tts = current_tts_map.get(tts_dict["id"])
                if old_tts and old_tts.get("api_key"):
                    tts_dict["api_key"] = old_tts["api_key"]
                else:
                    tts_dict["api_key"] = ""

            processed_tts_apis.append(tts_dict)

        # 构建新配置
        new_config = {
            "model_apis": processed_apis,
            "module_models": request.module_models,
            "tavily_api_key": current_config.get("tavily_api_key", ""),
            "dashscope_api_key": current_config.get("dashscope_api_key", ""),
            "tts_apis": processed_tts_apis,
            "tts_model": request.tts_model if request.tts_model is not None else current_config.get("tts_model", ""),
        }

        # 处理 Tavily Key
        if request.tavily_api_key is not None and "****" not in request.tavily_api_key:
            new_config["tavily_api_key"] = request.tavily_api_key

        # 处理 DashScope Key
        if request.dashscope_api_key is not None and "****" not in request.dashscope_api_key:
            new_config["dashscope_api_key"] = request.dashscope_api_key

        # 保存配置
        save_model_config(new_config)

        # 同步更新 .env 文件中的相关配置（保持兼容性）
        _sync_to_env(new_config)

        # 重置缓存
        clear_config_cache()
        from app.services.engine_manager import reset_ai_provider_cache
        reset_ai_provider_cache()

        # 重置 TTS 服务
        reset_tts_provider_cache()

        # 重置 Tavily 服务
        try:
            from app.services.tavily_service import reset_tavily_service
            reset_tavily_service()
        except Exception:
            pass

        return Response(
            success=True,
            message="配置已保存并生效",
            data={"saved": True}
        )

    except Exception as e:
        return Response(
            success=False,
            message=f"保存配置失败: {str(e)}",
            data=None
        )


@router.post("/test-model", response_model=Response)
async def test_model_connection(
    api_key: str = "",
    base_url: str = "",
    model: str = "",
    provider: str = "custom"
):
    """
    测试模型 API 连接
    """
    from app.services.ai_model_provider import CustomProvider, OllamaProvider

    try:
        if provider == "ollama":
            test_provider = OllamaProvider(
                base_url=base_url or "http://localhost:11434",
                model=model or "qwen3.5:9B"
            )
        else:
            test_provider = CustomProvider(
                api_key=api_key,
                base_url=base_url,
                model=model
            )

        # 发送测试消息
        test_messages = [
            {"role": "user", "content": "你好，请回复 OK"}
        ]

        response = await test_provider.chat(test_messages)

        if response and len(response) > 0:
            return Response(
                success=True,
                message=f"模型连接成功！响应: {response[:50]}...",
                data={"connected": True, "response": response[:100]}
            )
        else:
            return Response(
                success=False,
                message="模型返回为空",
                data={"connected": False}
            )

    except Exception as e:
        return Response(
            success=False,
            message=f"连接失败: {str(e)}",
            data={"connected": False}
        )


@router.post("/test-tavily", response_model=Response)
async def test_tavily_connection(api_key: str):
    """
    测试 Tavily API 连接
    """
    from app.services.tavily_service import TavilySearchService

    try:
        tavily = TavilySearchService(api_key=api_key)

        # 执行一个简单的测试搜索
        result = await tavily.search(
            query="test",
            max_results=1
        )

        if result and result.get("results"):
            return Response(
                success=True,
                message="Tavily API 连接成功",
                data={"connected": True}
            )
        else:
            return Response(
                success=False,
                message="Tavily API 返回数据异常",
                data={"connected": False}
            )

    except ValueError as e:
        return Response(
            success=False,
            message=str(e),
            data={"connected": False}
        )
    except Exception as e:
        return Response(
            success=False,
            message=f"连接失败: {str(e)}",
            data={"connected": False}
        )


@router.post("/test-tts", response_model=Response)
async def test_tts_connection(
    provider: str = "dashscope",
    api_key: str = "",
    base_url: str = "",
    model: str = "",
    voice: str = "",
):
    """
    测试 TTS 服务连接
    """
    try:
        tts_provider = create_tts_provider(
            provider_type=provider,
            config={
                "api_key": api_key,
                "base_url": base_url,
                "model": model,
                "voice": voice,
            }
        )

        # 健康检查
        health = await tts_provider.health_check()
        if not health.get("available"):
            return Response(
                success=False,
                message=f"TTS 服务不可用: {health.get('reason', '未知原因')}",
                data={"connected": False}
            )

        # 尝试合成一段测试文本
        result = await tts_provider.synthesize("你好，这是一个语音合成测试。")
        if result.get("success"):
            return Response(
                success=True,
                message=f"TTS 服务连接成功！(提供商: {provider}, 音色: {voice or '默认'})",
                data={"connected": True, "provider": provider}
            )
        else:
            return Response(
                success=False,
                message=f"TTS 合成测试失败: {result.get('error', '未知错误')}",
                data={"connected": False}
            )

    except Exception as e:
        return Response(
            success=False,
            message=f"TTS 连接失败: {str(e)}",
            data={"connected": False}
        )


# ========== 内部辅助函数 ==========

def _sync_to_env(config: Dict[str, Any]):
    """
    将关键配置同步写入 .env 文件（保持兼容性）
    """
    import os

    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), ".env")

    # 构建 .env 更新映射
    updates = {}

    # 同步 Tavily Key
    tavily_key = config.get("tavily_api_key", "")
    if tavily_key:
        updates["TAVILY_API_KEY"] = tavily_key

    # 同步 DashScope Key (从 tts_apis 中提取)
    dashscope_key = config.get("dashscope_api_key", "")
    # 也从 tts_apis 中查找 dashscope 提供商的 key
    for tts_api in config.get("tts_apis", []):
        if tts_api.get("provider") == "dashscope" and tts_api.get("api_key"):
            dashscope_key = tts_api["api_key"]
            break
    if dashscope_key:
        updates["DASHSCOPE_API_KEY"] = dashscope_key

    # 同步当前默认 Provider（使用 agent 模块的模型）
    module_models = config.get("module_models", {})
    model_apis = {api["id"]: api for api in config.get("model_apis", [])}

    agent_model_id = module_models.get("agent", "")
    if agent_model_id and agent_model_id in model_apis:
        agent_api = model_apis[agent_model_id]
        if agent_api["type"] == "ollama":
            updates["CURRENT_PROVIDER"] = "ollama"
            updates["OLLAMA_BASE_URL"] = agent_api.get("base_url", "http://localhost:11434")
            updates["OLLAMA_MODEL"] = agent_api.get("model", "qwen3.5:9B")
        else:
            updates["CURRENT_PROVIDER"] = "custom"
            updates["CUSTOM_API_BASE_URL"] = agent_api.get("base_url", "")
            updates["CUSTOM_MODEL"] = agent_api.get("model", "")
            updates["CUSTOM_SUPPORTS_THINKING"] = str(agent_api.get("supports_thinking", False)).lower()
            if agent_api.get("api_key"):
                updates["CUSTOM_API_KEY"] = agent_api["api_key"]

    if not updates:
        return

    # 读取并更新 .env 文件
    try:
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        else:
            lines = []

        updated_keys = set()
        new_lines = []
        for line in lines:
            stripped = line.strip()
            if "=" in stripped and not stripped.startswith("#"):
                key = stripped.split("=", 1)[0].strip()
                if key in updates:
                    new_lines.append(f"{key}={updates[key]}\n")
                    updated_keys.add(key)
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)

        # 添加新的配置项
        for key, value in updates.items():
            if key not in updated_keys:
                new_lines.append(f"{key}={value}\n")

        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)

        # 同步运行时 settings 对象
        try:
            from app.core.config import settings as app_settings
            for key, value in updates.items():
                if hasattr(app_settings, key):
                    if key == "CUSTOM_SUPPORTS_THINKING":
                        setattr(app_settings, key, value.lower() == "true")
                    else:
                        setattr(app_settings, key, value)
        except Exception:
            pass

    except Exception as e:
        print(f"[Settings] 同步 .env 文件出错: {e}")
