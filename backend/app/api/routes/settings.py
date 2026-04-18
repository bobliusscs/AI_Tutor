"""
设置 API 路由 - 管理用户和系统设置
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os

from app.schemas import Response


router = APIRouter()


class SettingsResponse(BaseModel):
    """设置响应模型"""
    tavily_api_key: Optional[str] = ""
    tavily_configured: bool = False
    # 当前选中的提供商
    current_provider: str = "ollama"  # ollama, custom
    # Ollama 配置
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3.5:9B"
    # 自定义 API 配置
    custom_api_key: Optional[str] = ""
    custom_api_base_url: str = "https://api.openai.com/v1"
    custom_model: str = "gpt-3.5-turbo"
    custom_supports_thinking: bool = False
    # 默认联网模式
    default_web_search: str = "off"


class ModelPreset(BaseModel):
    """模型预设"""
    name: str
    base_url: str
    model: str
    api_key_required: bool = True
    supports_thinking: bool = False


# 内置模型预设
BUILTIN_PRESETS: List[Dict[str, Any]] = [
    {
        "id": "ollama-local",
        "name": "Ollama 本地模型",
        "base_url": "http://localhost:11434",
        "model": "qwen3.5:9B",
        "api_key_required": False,
        "supports_thinking": True,
        "description": "本地部署的 Ollama 模型"
    },
    {
        "id": "qwen-dashscope",
        "name": "通义千问 (DashScope)",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model": "qwen3.5-Plus",
        "api_key_required": True,
        "supports_thinking": False,
        "description": "阿里云通义千问 Plus"
    },
    {
        "id": "deepseek",
        "name": "DeepSeek",
        "base_url": "https://api.deepseek.com/v1",
        "model": "deepseek-chat",
        "api_key_required": True,
        "supports_thinking": False,
        "description": "DeepSeek V3 模型"
    },
    {
        "id": "kimi",
        "name": "Kimi (月之暗面)",
        "base_url": "https://api.moonshot.cn/v1",
        "model": "Kimi-K2.5",
        "api_key_required": True,
        "supports_thinking": False,
        "description": "月之暗面 Kimi 模型"
    },
    {
        "id": "minimax",
        "name": "MiniMax",
        "base_url": "https://api.minimax.chat/v1",
        "model": "MiniMax-M2.7",
        "api_key_required": True,
        "supports_thinking": False,
        "description": "MiniMax 海螺 AI 模型"
    },
    {
        "id": "zhipu",
        "name": "智谱 AI",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "model": "GLM-5",
        "api_key_required": True,
        "supports_thinking": False,
        "description": "智谱 GLM-4 模型"
    },
    {
        "id": "openai",
        "name": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "model": "GPT-5.4",
        "api_key_required": True,
        "supports_thinking": False,
        "description": "OpenAI GPT-4o Mini"
    },
    {
        "id": "custom",
        "name": "自定义配置",
        "base_url": "",
        "model": "",
        "api_key_required": True,
        "supports_thinking": False,
        "description": "手动配置 API 端点和模型"
    }
]


class SettingsUpdateRequest(BaseModel):
    """设置更新请求"""
    tavily_api_key: Optional[str] = None
    # 当前选中的提供商
    current_provider: Optional[str] = None  # ollama, custom
    # Ollama 配置
    ollama_base_url: Optional[str] = None
    ollama_model: Optional[str] = None
    # 自定义 API 配置
    custom_api_key: Optional[str] = None
    custom_api_base_url: Optional[str] = None
    custom_model: Optional[str] = None
    custom_supports_thinking: Optional[bool] = None
    default_web_search: Optional[str] = None


@router.get("/current", response_model=Response)
async def get_settings():
    """
    获取当前设置
    """
    # 从环境变量和配置文件读取设置
    tavily_key = os.getenv("TAVILY_API_KEY", "")
    tavily_configured = bool(tavily_key and len(tavily_key) > 0)
    
    # 隐藏 API Key 的实际值
    masked_tavily_key = ""
    if tavily_key:
        if len(tavily_key) > 8:
            masked_tavily_key = tavily_key[:4] + "****" + tavily_key[-4:]
        else:
            masked_tavily_key = "****"
    
    # 从 .env 文件读取配置
    current_provider = os.getenv("CURRENT_PROVIDER", "ollama")
    ollama_base_url = "http://localhost:11434"
    ollama_model = "qwen3.5:9B"
    custom_api_key = os.getenv("CUSTOM_API_KEY", "")
    custom_api_base_url = os.getenv("CUSTOM_API_BASE_URL", "https://api.openai.com/v1")
    custom_model = os.getenv("CUSTOM_MODEL", "gpt-4o-mini")
    custom_supports_thinking = os.getenv("CUSTOM_SUPPORTS_THINKING", "false").lower() == "true"
    
    try:
        env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), ".env")
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        if "=" in line:
                            key, value = line.split("=", 1)
                            key = key.strip()
                            value = value.strip()
                            if key == "CURRENT_PROVIDER":
                                current_provider = value
                            elif key == "OLLAMA_BASE_URL":
                                ollama_base_url = value
                            elif key == "OLLAMA_MODEL":
                                ollama_model = value
                            elif key == "CUSTOM_API_KEY":
                                custom_api_key = value
                            elif key == "CUSTOM_API_BASE_URL":
                                custom_api_base_url = value
                            elif key == "CUSTOM_MODEL":
                                custom_model = value
                            elif key == "CUSTOM_SUPPORTS_THINKING":
                                custom_supports_thinking = value.lower() == "true"
                            elif key == "TAVILY_API_KEY":
                                tavily_key = value
                            elif key == "CURRENT_PROVIDER":
                                current_provider = value
    except Exception as e:
        print(f"读取 .env 文件出错: {e}")
    
    # 重新检查 tavily 配置状态
    tavily_configured = bool(tavily_key and len(tavily_key) > 0)
    
    # 隐藏自定义 API Key（但保持可检测性）
    # 如果 custom_api_key 有值，返回空字符串表示已配置（前端可通过此判断是否配置）
    # 如果 custom_api_key 为空，返回 None 表示未配置
    custom_api_key_configured = bool(custom_api_key and len(custom_api_key) > 0)
    custom_api_key_response = "" if custom_api_key_configured else None
    
    return Response(
        success=True,
        message="获取设置成功",
        data={
            "tavily_api_key": masked_tavily_key,
            "tavily_configured": tavily_configured,
            "current_provider": current_provider,
            "ollama_base_url": ollama_base_url,
            "ollama_model": ollama_model,
            "custom_api_key": custom_api_key_response,  # 空字符串表示已配置，None表示未配置
            "custom_api_base_url": custom_api_base_url,
            "custom_model": custom_model,
            "custom_supports_thinking": custom_supports_thinking,
            "default_web_search": "off",
            "presets": BUILTIN_PRESETS
        }
    )


@router.post("/update", response_model=Response)
async def update_settings(request: SettingsUpdateRequest):
    """
    更新设置
    """
    try:
        # 获取 .env 文件路径（settings.py 在 app/api/routes/ 下）
        backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        env_path = os.path.join(backend_dir, ".env")
        
        # 更新配置（如果值包含掩码标记则不更新）
        def is_masked(value: str) -> bool:
            """检查值是否为掩码格式"""
            return value and '****' in value
        
        # 读取并更新 .env 文件，保留原有格式和注释
        if os.path.exists(env_path):
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
            except Exception as e:
                print(f"读取 .env 文件出错: {e}")
                lines = []
        else:
            lines = []
        
        # 需要更新的配置映射
        updates = {}
        if request.tavily_api_key and not is_masked(request.tavily_api_key):
            updates["TAVILY_API_KEY"] = request.tavily_api_key
        if request.current_provider is not None:
            updates["CURRENT_PROVIDER"] = request.current_provider
        if request.ollama_base_url is not None:
            updates["OLLAMA_BASE_URL"] = request.ollama_base_url
        if request.ollama_model is not None:
            updates["OLLAMA_MODEL"] = request.ollama_model
        if request.custom_api_key and not is_masked(request.custom_api_key):
            updates["CUSTOM_API_KEY"] = request.custom_api_key
        if request.custom_api_base_url is not None:
            updates["CUSTOM_API_BASE_URL"] = request.custom_api_base_url
        if request.custom_model is not None:
            updates["CUSTOM_MODEL"] = request.custom_model
        if request.custom_supports_thinking is not None:
            updates["CUSTOM_SUPPORTS_THINKING"] = str(request.custom_supports_thinking).lower()
        
        # 逐行处理文件
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
        
        # 添加新的配置项（如果不存在）
        for key, value in updates.items():
            if key not in updated_keys:
                new_lines.append(f"{key}={value}\n")
        
        # 写入配置文件
        try:
            with open(env_path, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
        except Exception as e:
            return Response(
                success=False,
                message=f"保存配置失败: {str(e)}",
                data=None
            )
        
        # 同步更新 settings 对象的属性，确保运行时读取最新配置
        try:
            from app.core.config import settings
            if "TAVILY_API_KEY" in updates:
                settings.TAVILY_API_KEY = updates["TAVILY_API_KEY"]
            if "CURRENT_PROVIDER" in updates:
                settings.CURRENT_PROVIDER = updates["CURRENT_PROVIDER"]
            if "OLLAMA_BASE_URL" in updates:
                settings.OLLAMA_BASE_URL = updates["OLLAMA_BASE_URL"]
            if "OLLAMA_MODEL" in updates:
                settings.OLLAMA_MODEL = updates["OLLAMA_MODEL"]
            if "CUSTOM_API_KEY" in updates:
                settings.CUSTOM_API_KEY = updates["CUSTOM_API_KEY"]
            if "CUSTOM_API_BASE_URL" in updates:
                settings.CUSTOM_API_BASE_URL = updates["CUSTOM_API_BASE_URL"]
            if "CUSTOM_MODEL" in updates:
                settings.CUSTOM_MODEL = updates["CUSTOM_MODEL"]
            if "CUSTOM_SUPPORTS_THINKING" in updates:
                settings.CUSTOM_SUPPORTS_THINKING = updates["CUSTOM_SUPPORTS_THINKING"] == "true"
        except Exception as e:
            print(f"同步 settings 对象失败: {e}")
        
        # 重置 Tavily 服务实例以应用新配置
        from app.services.tavily_service import reset_tavily_service
        reset_tavily_service()
        
        # 重置 AI Provider 缓存以应用新配置
        from app.services.engine_manager import reset_ai_provider_cache
        reset_ai_provider_cache()
        
        return Response(
            success=True,
            message="设置已保存并生效",
            data={"saved": True}
        )
        
    except Exception as e:
        return Response(
            success=False,
            message=f"更新设置失败: {str(e)}",
            data=None
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


@router.get("/presets", response_model=Response)
async def get_model_presets():
    """
    获取内置模型预设
    """
    return Response(
        success=True,
        message="获取成功",
        data={"presets": BUILTIN_PRESETS}
    )
