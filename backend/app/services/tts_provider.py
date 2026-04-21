"""
TTS 多提供商抽象层 - 统一不同厂家的语音合成接口
支持的提供商: DashScope (阿里云), OpenAI 兼容 (OpenAI/硅基流动等), Edge TTS (免费)
"""
import asyncio
import base64
import logging
import os
import time
from abc import ABC, abstractmethod
from typing import Optional, Dict, List

import requests

logger = logging.getLogger(__name__)


# ========== TTS 提供商类型定义 ==========

TTS_PROVIDER_DEFINITIONS = [
    {
        "id": "dashscope",
        "name": "阿里云百炼 (DashScope)",
        "description": "使用 qwen3-tts-flash 等模型，支持丰富中文音色",
        "requires_api_key": True,
        "default_base_url": "https://dashscope.aliyuncs.com/api/v1",
        "default_model": "qwen3-tts-flash",
        "default_voice": "Cherry",
    },
    {
        "id": "openai",
        "name": "OpenAI 兼容",
        "description": "支持 OpenAI、硅基流动等兼容 /v1/audio/speech 接口的服务",
        "requires_api_key": True,
        "default_base_url": "https://api.openai.com/v1",
        "default_model": "tts-1",
        "default_voice": "alloy",
    },
    {
        "id": "edge",
        "name": "Edge TTS (免费)",
        "description": "微软 Edge 浏览器 TTS，完全免费，无需 API Key",
        "requires_api_key": False,
        "default_base_url": "",
        "default_model": "",
        "default_voice": "zh-CN-XiaoxiaoNeural",
    },
]

# 各提供商支持的音色列表
TTS_VOICES = {
    "dashscope": [
        {"id": "Cherry", "name": "知夏 (女)"},
        {"id": "XiaoWei", "name": "小伟 (男)"},
        {"id": "XiaoMo", "name": "小陌 (女)"},
        {"id": "XiaoYu", "name": "小雨 (女)"},
        {"id": "XiaoYang", "name": "小阳 (男)"},
        {"id": "XiaoXuan", "name": "小璇 (女)"},
        {"id": "ShuoShuo", "name": "硕硕 (男)"},
        {"id": "AiAi", "name": "艾艾 (女)"},
        {"id": "NvSheng", "name": "女生 (通用)"},
        {"id": "NanSheng", "name": "男生 (通用)"},
        {"id": "SiYu", "name": "思予 (女)"},
        {"id": "JingYuan", "name": "静媛 (女)"},
        {"id": "ShuaiGe", "name": "帅哥 (男)"},
        {"id": "LianZi", "name": "莲子 (女)"},
        {"id": "FeiFei", "name": "飞飞 (女)"},
        {"id": "XiaoNuan", "name": "小暖 (女)"},
    ],
    "openai": [
        {"id": "alloy", "name": "Alloy"},
        {"id": "ash", "name": "Ash"},
        {"id": "ballad", "name": "Ballad"},
        {"id": "coral", "name": "Coral"},
        {"id": "echo", "name": "Echo"},
        {"id": "fable", "name": "Fable"},
        {"id": "onyx", "name": "Onyx"},
        {"id": "nova", "name": "Nova"},
        {"id": "sage", "name": "Sage"},
        {"id": "shimmer", "name": "Shimmer"},
    ],
    "edge": [
        {"id": "zh-CN-XiaoxiaoNeural", "name": "晓晓 (女，通用)"},
        {"id": "zh-CN-YunxiNeural", "name": "云希 (男，通用)"},
        {"id": "zh-CN-YunjianNeural", "name": "云健 (男，新闻)"},
        {"id": "zh-CN-XiaoyiNeural", "name": "晓伊 (女，客服)"},
        {"id": "zh-CN-YunyangNeural", "name": "云扬 (男，客服)"},
        {"id": "zh-CN-XiaochenNeural", "name": "晓辰 (女，助手)"},
        {"id": "zh-CN-XiaohanNeural", "name": "晓涵 (女，新闻)"},
        {"id": "zh-CN-XiaomengNeural", "name": "晓梦 (女，童声)"},
        {"id": "zh-CN-XiaomoNeural", "name": "晓墨 (女，方言)"},
        {"id": "zh-CN-XiaoqiuNeural", "name": "晓秋 (女，助眠)"},
        {"id": "zh-CN-XiaoruiNeural", "name": "晓瑞 (女，方言)"},
        {"id": "zh-CN-XiaoshuangNeural", "name": "晓双 (女，童声)"},
        {"id": "zh-CN-XiaoxuanNeural", "name": "晓萱 (女，抒情)"},
        {"id": "zh-CN-XiaozhenNeural", "name": "晓甄 (女，客服)"},
        {"id": "zh-CN-YunfengNeural", "name": "云枫 (男，新闻)"},
        {"id": "zh-CN-YunhaoNeural", "name": "云皓 (男，客服)"},
        {"id": "zh-CN-YunxiaNeural", "name": "云夏 (男，童声)"},
        {"id": "zh-CN-YunzeNeural", "name": "云泽 (男，解说)"},
    ],
}


# ========== 抽象基类 ==========

class BaseTTSProvider(ABC):
    """TTS 提供商抽象基类"""

    def __init__(self, api_key: str = "", base_url: str = "", model: str = "", voice: str = ""):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.voice = voice
        self._session = None

    @property
    def provider_type(self) -> str:
        """返回提供商类型标识"""
        return self.__class__.__name__.replace("TTSProvider", "").lower()

    @property
    def default_speaker(self) -> str:
        """返回默认音色"""
        return self.voice

    @abstractmethod
    async def health_check(self) -> dict:
        """检查服务健康状态"""
        pass

    @abstractmethod
    async def synthesize(self, text: str, speaker: Optional[str] = None) -> dict:
        """
        合成单条文本的语音

        Returns:
            {"success": bool, "audio_base64": str, "duration": float, "error": str}
        """
        pass

    async def synthesize_slides(self, slides: list, speaker: Optional[str] = None) -> list:
        """
        批量合成幻灯片讲解语音（默认实现，子类可覆盖优化）
        """
        if not self.enabled:
            return [
                {"index": i, "title": s.get("title", ""), "notes": s.get("notes", ""),
                 "audio_base64": "", "duration": 0, "error": "TTS未配置"}
                for i, s in enumerate(slides)
            ]

        speaker_id = speaker or self.voice
        results = []
        semaphore = asyncio.Semaphore(3)

        async def synth_one(index: int, slide: dict) -> dict:
            notes = slide.get("notes", "")
            title = slide.get("title", "")

            if not notes or not notes.strip():
                return {
                    "index": index, "title": title, "notes": notes,
                    "audio_base64": "", "duration": 0,
                    "error": None, "skipped": True
                }

            async with semaphore:
                result = await self.synthesize(notes, speaker_id)
                return {
                    "index": index, "title": title, "notes": notes,
                    "audio_base64": result.get("audio_base64", ""),
                    "duration": result.get("duration", 0),
                    "error": result.get("error"),
                    "skipped": False,
                    "success": result.get("success", False)
                }

        tasks = [synth_one(i, slide) for i, slide in enumerate(slides)]
        results = await asyncio.gather(*tasks)
        results.sort(key=lambda x: x.get("index", 0))

        success_count = sum(1 for r in results if r.get("success"))
        skipped_count = sum(1 for r in results if r.get("skipped"))
        logger.info(f"TTS幻灯片语音合成完成: 共{len(results)}页, 成功{success_count}, 跳过{skipped_count}")

        return results

    @property
    def enabled(self) -> bool:
        """服务是否可用"""
        return True


# ========== DashScope TTS 提供商 ==========

class DashScopeTTSProvider(BaseTTSProvider):
    """阿里云百炼 DashScope TTS 提供商"""

    # 常用音色映射（兼容旧版）
    COMMON_SPEAKERS = {
        "zh": "Cherry",
        "female": "Cherry",
        "male": "XiaoWei",
        "cherry": "Cherry",
        "xiaomo": "XiaoMo",
        "xiaoyu": "XiaoYu",
        "xiaoyang": "XiaoYang",
        "xiaoxuan": "XiaoXuan",
    }

    def __init__(self, api_key: str = "", base_url: str = "", model: str = "", voice: str = ""):
        super().__init__(
            api_key=api_key,
            base_url=base_url or "https://dashscope.aliyuncs.com/api/v1",
            model=model or "qwen3-tts-flash",
            voice=voice or "Cherry",
        )

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def _normalize_speaker(self, speaker: str) -> str:
        """将常见音色名映射到实际音色ID"""
        if not speaker:
            return self.voice or "Cherry"

        speaker_lower = speaker.lower().strip()

        # 检查常用名称映射
        if speaker_lower in self.COMMON_SPEAKERS:
            return self.COMMON_SPEAKERS[speaker_lower]

        # 检查是否是完整音色名（在 TTS_VOICES 列表中）
        for v in TTS_VOICES.get("dashscope", []):
            if speaker_lower == v["id"].lower():
                return v["id"]

        # 模糊匹配
        for v in TTS_VOICES.get("dashscope", []):
            if speaker_lower in v["id"].lower() or v["id"].lower() in speaker_lower:
                return v["id"]

        return self.voice or "Cherry"

    async def health_check(self) -> dict:
        if not self.enabled:
            return {
                "available": False,
                "model_loaded": False,
                "speakers": [v["id"] for v in TTS_VOICES.get("dashscope", [])],
                "reason": "API Key 未配置"
            }

        return {
            "available": True,
            "model_loaded": True,
            "model": self.model,
            "speakers": [v["id"] for v in TTS_VOICES.get("dashscope", [])],
            "status": "ready",
            "reason": ""
        }

    async def synthesize(self, text: str, speaker: Optional[str] = None) -> dict:
        if not self.enabled:
            return {"success": False, "error": "DashScope TTS 未配置API Key"}

        if not text or not text.strip():
            return {"success": False, "error": "文本内容为空"}

        speaker_id = self._normalize_speaker(speaker)
        start_time = time.time()

        try:
            result = await asyncio.to_thread(self._synthesize_sync, text.strip(), speaker_id)
            return result
        except requests.exceptions.ConnectionError:
            return {"success": False, "error": "无法连接云端TTS服务"}
        except requests.exceptions.Timeout:
            return {"success": False, "error": "TTS合成超时，请稍后重试"}
        except Exception as e:
            logger.error(f"DashScope TTS 合成异常: {e}")
            return {"success": False, "error": str(e)}

    def _synthesize_sync(self, text: str, speaker_id: str) -> dict:
        """同步合成方法"""
        import dashscope

        dashscope.api_key = self.api_key

        response = dashscope.MultiModalConversation.call(
            model=self.model,
            text=text,
            voice=speaker_id
        )

        if response.status_code == 200:
            output = response.output
            audio_obj = output.audio

            audio_url = getattr(audio_obj, 'url', '')
            audio_data = getattr(audio_obj, 'data', '')

            audio_base64 = None

            if audio_data and isinstance(audio_data, str) and len(audio_data) > 0:
                audio_base64 = audio_data
            elif audio_url and isinstance(audio_url, str) and len(audio_url) > 0:
                audio_bytes = self._download_audio(audio_url)
                if audio_bytes:
                    audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
                else:
                    return {"success": False, "error": "音频下载失败"}
            else:
                return {"success": False, "error": "未获取到音频数据"}

            if audio_base64:
                audio_bytes = base64.b64decode(audio_base64)
                duration = len(audio_bytes) / (24000 * 2)
                return {
                    "success": True,
                    "audio_base64": audio_base64,
                    "duration": duration,
                    "sample_rate": 24000
                }
            else:
                return {"success": False, "error": "未获取到音频数据"}
        else:
            error_msg = response.message if hasattr(response, 'message') else f"HTTP {response.status_code}"
            return {"success": False, "error": f"API返回错误: {error_msg}"}

    def _download_audio(self, url: str) -> Optional[bytes]:
        """从 URL 下载音频文件"""
        try:
            audio_response = requests.get(url, timeout=30)
            if audio_response.status_code == 200:
                return audio_response.content
            return None
        except Exception as e:
            logger.error(f"下载音频异常: {e}")
            return None


# ========== OpenAI 兼容 TTS 提供商 ==========

class OpenAITTSProvider(BaseTTSProvider):
    """OpenAI 兼容 TTS 提供商（支持 OpenAI、硅基流动等）"""

    def __init__(self, api_key: str = "", base_url: str = "", model: str = "", voice: str = ""):
        super().__init__(
            api_key=api_key,
            base_url=base_url or "https://api.openai.com/v1",
            model=model or "tts-1",
            voice=voice or "alloy",
        )

    @property
    def enabled(self) -> bool:
        return bool(self.api_key) and bool(self.base_url)

    @property
    def session(self) -> requests.Session:
        if self._session is None:
            self._session = requests.Session()
            self._session.headers.update({
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            })
            self._session.timeout = 60.0
        return self._session

    async def health_check(self) -> dict:
        if not self.enabled:
            return {
                "available": False,
                "model_loaded": False,
                "speakers": [v["id"] for v in TTS_VOICES.get("openai", [])],
                "reason": "API Key 或服务地址未配置"
            }

        return {
            "available": True,
            "model_loaded": True,
            "model": self.model,
            "speakers": [v["id"] for v in TTS_VOICES.get("openai", [])],
            "status": "ready",
            "reason": ""
        }

    async def synthesize(self, text: str, speaker: Optional[str] = None) -> dict:
        if not self.enabled:
            return {"success": False, "error": "OpenAI TTS 未配置"}

        if not text or not text.strip():
            return {"success": False, "error": "文本内容为空"}

        voice = speaker or self.voice or "alloy"
        start_time = time.time()

        try:
            result = await asyncio.to_thread(self._synthesize_sync, text.strip(), voice)
            return result
        except requests.exceptions.ConnectionError:
            return {"success": False, "error": "无法连接 TTS 服务"}
        except requests.exceptions.Timeout:
            return {"success": False, "error": "TTS 合成超时"}
        except Exception as e:
            logger.error(f"OpenAI TTS 合成异常: {e}")
            return {"success": False, "error": str(e)}

    def _synthesize_sync(self, text: str, voice: str) -> dict:
        """同步合成方法"""
        # 构造请求 URL
        base = self.base_url.rstrip("/")
        url = f"{base}/audio/speech"

        payload = {
            "model": self.model,
            "input": text,
            "voice": voice,
            "response_format": "wav",
        }

        try:
            resp = self.session.post(url, json=payload, timeout=60)

            if resp.status_code == 200:
                audio_bytes = resp.content
                if audio_bytes and len(audio_bytes) > 0:
                    audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
                    # 估算时长（假设 24kHz 采样率，16bit 单声道）
                    duration = len(audio_bytes) / (24000 * 2)
                    return {
                        "success": True,
                        "audio_base64": audio_base64,
                        "duration": duration,
                        "sample_rate": 24000
                    }
                else:
                    return {"success": False, "error": "服务返回空音频"}
            else:
                try:
                    error_data = resp.json()
                    error_msg = error_data.get("error", {}).get("message", f"HTTP {resp.status_code}")
                except Exception:
                    error_msg = f"HTTP {resp.status_code}"
                return {"success": False, "error": f"TTS 服务错误: {error_msg}"}
        except Exception as e:
            return {"success": False, "error": str(e)}


# ========== Edge TTS 提供商 ==========

class EdgeTTSProvider(BaseTTSProvider):
    """Microsoft Edge TTS 提供商（免费，无需 API Key）"""

    def __init__(self, api_key: str = "", base_url: str = "", model: str = "", voice: str = ""):
        super().__init__(
            api_key="",
            base_url="",
            model="",
            voice=voice or "zh-CN-XiaoxiaoNeural",
        )

    @property
    def enabled(self) -> bool:
        # Edge TTS 始终可用（只要 edge-tts 库已安装）
        try:
            import edge_tts
            return True
        except ImportError:
            return False

    async def health_check(self) -> dict:
        if not self.enabled:
            return {
                "available": False,
                "model_loaded": False,
                "speakers": [v["id"] for v in TTS_VOICES.get("edge", [])],
                "reason": "edge-tts 库未安装，请运行 pip install edge-tts"
            }

        return {
            "available": True,
            "model_loaded": True,
            "model": "Edge TTS",
            "speakers": [v["id"] for v in TTS_VOICES.get("edge", [])],
            "status": "ready",
            "reason": ""
        }

    async def synthesize(self, text: str, speaker: Optional[str] = None) -> dict:
        if not self.enabled:
            return {"success": False, "error": "edge-tts 库未安装"}

        if not text or not text.strip():
            return {"success": False, "error": "文本内容为空"}

        voice = speaker or self.voice or "zh-CN-XiaoxiaoNeural"
        start_time = time.time()

        try:
            import edge_tts
            import io

            communicate = edge_tts.Communicate(text.strip(), voice)

            # 收集音频数据
            audio_buffer = io.BytesIO()
            async for chunk in communicate.stream():
                # 新版 edge-tts 返回字典，type 为字符串
                if chunk.get("type") == "audio":
                    audio_buffer.write(chunk["data"])

            audio_bytes = audio_buffer.getvalue()
            if audio_bytes and len(audio_bytes) > 0:
                audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
                # MP3 格式估算时长（约 32kbps）
                duration = len(audio_bytes) / (32000 / 8)
                return {
                    "success": True,
                    "audio_base64": audio_base64,
                    "duration": duration,
                    "sample_rate": 24000,
                    "format": "mp3"
                }
            else:
                return {"success": False, "error": "Edge TTS 返回空音频"}

        except ImportError:
            return {"success": False, "error": "edge-tts 库未安装，请运行 pip install edge-tts"}
        except Exception as e:
            logger.error(f"Edge TTS 合成异常: {e}")
            return {"success": False, "error": str(e)}


# ========== TTS Provider 工厂 ==========

def create_tts_provider(provider_type: str, config: dict) -> BaseTTSProvider:
    """
    根据 provider_type 和配置创建 TTS 提供商实例

    Args:
        provider_type: "dashscope" | "openai" | "edge"
        config: {"api_key": str, "base_url": str, "model": str, "voice": str}
    """
    if provider_type == "dashscope":
        return DashScopeTTSProvider(
            api_key=config.get("api_key", ""),
            base_url=config.get("base_url", ""),
            model=config.get("model", "qwen3-tts-flash"),
            voice=config.get("voice", "Cherry"),
        )
    elif provider_type == "openai":
        return OpenAITTSProvider(
            api_key=config.get("api_key", ""),
            base_url=config.get("base_url", ""),
            model=config.get("model", "tts-1"),
            voice=config.get("voice", "alloy"),
        )
    elif provider_type == "edge":
        return EdgeTTSProvider(
            voice=config.get("voice", "zh-CN-XiaoxiaoNeural"),
        )
    else:
        raise ValueError(f"不支持的 TTS 提供商类型: {provider_type}")


# ========== TTS Provider 管理器 ==========

_tts_provider_instance: Optional[BaseTTSProvider] = None


def get_tts_provider() -> BaseTTSProvider:
    """
    获取当前配置的 TTS 提供商实例（单例，配置更新时需调用 reset_tts_provider_cache）
    """
    global _tts_provider_instance

    if _tts_provider_instance is not None:
        # 检查是否仍然启用
        if _tts_provider_instance.enabled:
            return _tts_provider_instance
        else:
            # 重新创建
            _tts_provider_instance = None

    from app.core.model_config import load_model_config
    config = load_model_config()

    tts_apis = config.get("tts_apis", [])
    tts_model_id = config.get("tts_model", "")

    # 如果没有配置 tts_apis，尝试从旧的 dashscope_api_key 迁移
    if not tts_apis:
        dashscope_key = config.get("dashscope_api_key", "")
        if dashscope_key:
            _tts_provider_instance = DashScopeTTSProvider(api_key=dashscope_key)
            return _tts_provider_instance
        # 没有任何 TTS 配置，返回 Edge TTS 作为默认
        _tts_provider_instance = EdgeTTSProvider()
        return _tts_provider_instance

    # 查找选中的 TTS API
    selected_api = None
    for api in tts_apis:
        if api.get("id") == tts_model_id:
            selected_api = api
            break

    # 如果没有选中，使用第一个
    if not selected_api and tts_apis:
        selected_api = tts_apis[0]

    if selected_api:
        _tts_provider_instance = create_tts_provider(
            provider_type=selected_api.get("provider", "edge"),
            config=selected_api,
        )
    else:
        _tts_provider_instance = EdgeTTSProvider()

    return _tts_provider_instance


def reset_tts_provider_cache():
    """重置 TTS 提供商缓存（配置更新时调用）"""
    global _tts_provider_instance
    _tts_provider_instance = None
