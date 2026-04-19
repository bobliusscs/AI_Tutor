"""
DashScope TTS 服务层 - 封装与阿里云 DashScope 云端 TTS API 的交互
使用 qwen3-tts-flash 模型
"""

import base64
import logging
import os
import time
from typing import Optional

import requests

logger = logging.getLogger(__name__)


class DashScopeTTSService:
    """DashScope 云端 TTS 服务封装 - 使用阿里云百炼 API"""
    
    # API 配置
    BASE_URL = "https://dashscope.aliyuncs.com/api/v1"
    MODEL = "qwen3-tts-flash"
    
    # 支持的音色列表（部分）
    SPEAKERS = {
        "Cherry": "知夏",
        "Apple": "苹果",
        "XiaoMo": "小陌",
        "XiaoXuan": "小璇",
        "XiaoYang": "小阳",
        "XiaoYu": "小雨",
        "ShuoShuo": "硕硕",
        "AiXiaoXuan": "艾小璇",
        "AiAi": "艾艾",
        "NongFangNiuNai": "农夫牛奶",
        "AoDi": "奥迪",
        "XianShi": "显仕",
        "LingYun": "凌云",
        "AnAn": "安安",
        "XiaoShan": "小山",
        "NvSheng": "女生",
        "NanSheng": "男生",
        "SiYu": "思予",
        "JingYuan": "静媛",
        "ShuaiGe": "帅哥",
        "QiaoQiao": "悄悄",
        "XiaoJiao": "小娇",
        "XinXin": "欣欣",
        "YuXin": "雨馨",
        "YaYun": "雅云",
        "XiaoWei": "小伟",
        "YeXin": "叶新",
        "XiaoBai": "小白",
        "ShiRou": "食肉",
        "XiaoHui": "小慧",
        "ChengCheng": "成成",
        "AiYa": "艾雅",
        "XiaoMeng": "小梦",
        "YaKu": "雅酷",
        "LianZi": "莲子",
        "FeiFei": "飞飞",
        "MaMa": "妈妈",
        "BaBa": "爸爸",
        "CuiCui": "翠翠",
        "XiaoNuan": "小暖",
    }
    
    # 常用音色映射
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

    def __init__(self):
        # 优先从 settings 中读取（pydantic-settings 已加载.env）
        from app.core.config import settings
        self.api_key = getattr(settings, 'DASHSCOPE_API_KEY', '') or os.getenv("DASHSCOPE_API_KEY", "")
        self.enabled = bool(self.api_key)
        self._session = None
        
        if not self.enabled:
            logger.warning("DASHSCOPE_API_KEY 未设置，DashScope TTS 服务不可用")

    @property
    def session(self) -> requests.Session:
        """懒初始化 requests Session"""
        if self._session is None:
            self._session = requests.Session()
            self._session.headers.update({
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            })
            self._session.timeout = 60.0
        return self._session

    def _normalize_speaker(self, speaker: str) -> str:
        """将常见音色名映射到实际音色ID"""
        if not speaker:
            return self.COMMON_SPEAKERS.get("zh", "Cherry")
        
        speaker_lower = speaker.lower().strip()
        
        # 检查是否是常用名称映射
        if speaker_lower in self.COMMON_SPEAKERS:
            return self.COMMON_SPEAKERS[speaker_lower]
        
        # 检查是否是完整音色名
        for key in self.SPEAKERS:
            if speaker_lower == key.lower():
                return key
        
        # 尝试模糊匹配
        for key in self.SPEAKERS:
            if speaker_lower in key.lower() or key.lower() in speaker_lower:
                return key
        
        # 默认返回 Cherry
        return "Cherry"

    async def health_check(self) -> dict:
        """
        检查 DashScope TTS 服务健康状态

        Returns:
            dict: {"available": bool, "model": str, "speakers": list}
        """
        if not self.enabled:
            return {
                "available": False,
                "model_loaded": False,
                "speakers": list(self.SPEAKERS.keys()),
                "reason": "DASHSCOPE_API_KEY 未配置"
            }

        # API Key已配置，视为可用（实际可用性在合成时验证，避免健康检查超时）
        return {
            "available": True,
            "model_loaded": True,
            "model": self.MODEL,
            "speakers": list(self.SPEAKERS.keys()),
            "status": "ready",
            "reason": ""
        }

    async def synthesize(self, text: str, speaker: Optional[str] = None) -> dict:
        """
        合成单条文本的语音

        Args:
            text: 要合成的文本
            speaker: 音色，默认使用 Cherry

        Returns:
            dict: {"success": bool, "audio_base64": str, "duration": float}
        """
        import asyncio
        
        if not self.enabled:
            return {"success": False, "error": "DashScope TTS 未配置API Key"}

        if not text or not text.strip():
            return {"success": False, "error": "文本内容为空"}

        speaker_id = self._normalize_speaker(speaker)
        start_time = time.time()

        try:
            # 使用 asyncio.to_thread 将同步调用放到线程池中执行，避免阻塞事件循环
            result = await asyncio.to_thread(self._synthesize_sync, text.strip(), speaker_id)
            return result
        except requests.exceptions.ConnectionError:
            logger.error("无法连接 DashScope API")
            return {"success": False, "error": "无法连接云端TTS服务"}
        except requests.exceptions.Timeout:
            logger.error("DashScope TTS 合成超时")
            return {"success": False, "error": "TTS合成超时，请稍后重试"}
        except Exception as e:
            logger.error(f"DashScope TTS 合成异常: {e}")
            return {"success": False, "error": str(e)}
    
    def _synthesize_sync(self, text: str, speaker_id: str) -> dict:
        """
        同步合成方法，实际执行TTS调用
        """
        import dashscope
        
        # 设置 API Key
        dashscope.api_key = self.api_key
        
        # 调用 TTS API
        response = dashscope.MultiModalConversation.call(
            model=self.MODEL,
            text=text,
            voice=speaker_id
        )
        
        # 检查响应状态
        if response.status_code == 200:
            output = response.output
            
            # DashScope TTS 返回 audio 对象，包含 url 字段
            audio_obj = output.audio
            
            logger.debug(f"DashScope TTS audio 对象: {audio_obj}")
            
            # 获取 audio 对象的属性
            audio_url = getattr(audio_obj, 'url', '')
            audio_data = getattr(audio_obj, 'data', '')
            
            logger.debug(f"audio_url: {audio_url[:50] if audio_url else 'None'}...")
            logger.debug(f"audio_data length: {len(audio_data) if audio_data else 0}")
            
            audio_base64 = None
            
            # 如果有 data 字段且不为空，直接使用
            if audio_data and isinstance(audio_data, str) and len(audio_data) > 0:
                audio_base64 = audio_data
                logger.debug("使用 audio.data 字段")
            # 如果有 url，下载音频并转为 base64
            elif audio_url and isinstance(audio_url, str) and len(audio_url) > 0:
                logger.debug(f"从 URL 下载音频: {audio_url[:50]}...")
                audio_bytes = self._download_audio(audio_url)
                if audio_bytes:
                    audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
                    logger.debug(f"音频下载成功，base64 长度: {len(audio_base64)}")
                else:
                    return {"success": False, "error": "音频下载失败"}
            else:
                logger.error(f"DashScope TTS 未返回有效音频数据")
                return {"success": False, "error": "未获取到音频数据"}
            
            if audio_base64:
                # 解码 base64 音频数据
                audio_bytes = base64.b64decode(audio_base64)
                # 估算时长（假设 24kHz 采样率，16bit 单声道）
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
            logger.error(f"DashScope TTS 合成失败: {response}")
            return {"success": False, "error": f"API返回错误: {error_msg}"}

    async def synthesize_slides(self, slides: list, speaker: Optional[str] = None) -> list:
        """
        批量合成幻灯片讲解语音

        Args:
            slides: 幻灯片列表
            speaker: 音色

        Returns:
            list: 合成结果列表
        """
        import asyncio
        
        if not self.enabled:
            return [
                {"index": i, "title": s.get("title", ""), "notes": s.get("notes", ""),
                 "audio_base64": "", "duration": 0, "error": "TTS未配置"}
                for i, s in enumerate(slides)
            ]

        speaker_id = self._normalize_speaker(speaker)
        results = []
        
        # 限制最大并发数为3
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

        # 并行执行
        tasks = [synth_one(i, slide) for i, slide in enumerate(slides)]
        results = await asyncio.gather(*tasks)
        results.sort(key=lambda x: x.get("index", 0))

        success_count = sum(1 for r in results if r.get("success"))
        skipped_count = sum(1 for r in results if r.get("skipped"))
        logger.info(f"DashScope幻灯片语音合成完成: 共{len(results)}页, 成功{success_count}, 跳过{skipped_count}")

        return results
    
    def _download_audio(self, url: str) -> Optional[bytes]:
        """从 URL 下载音频文件
        
        Args:
            url: 音频文件URL
            
        Returns:
            bytes: 音频数据，失败时返回 None
        """
        try:
            audio_response = requests.get(url, timeout=30)
            if audio_response.status_code == 200:
                return audio_response.content
            else:
                logger.error(f"下载音频失败: HTTP {audio_response.status_code}")
                return None
        except Exception as e:
            logger.error(f"下载音频异常: {e}")
            return None


# 全局TTS服务实例
_dashscope_tts_service: Optional[DashScopeTTSService] = None


def get_dashscope_tts_service() -> DashScopeTTSService:
    """获取 DashScope TTS 服务单例"""
    global _dashscope_tts_service
    if _dashscope_tts_service is None:
        _dashscope_tts_service = DashScopeTTSService()
    return _dashscope_tts_service
