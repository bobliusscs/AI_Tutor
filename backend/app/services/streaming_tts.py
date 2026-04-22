"""
流式 TTS 协调器 - 实现模型边输出、语音边实时合成

核心功能：
1. 句子分割：智能分割文本，避免在数字小数点处断开
2. 并发合成：控制并发数，实现实时语音流
3. 异步队列：音频事件通过队列异步传递给 SSE 流
"""

import asyncio
import logging
import re
from typing import Optional, AsyncGenerator

from app.services.tts_provider import BaseTTSProvider

logger = logging.getLogger(__name__)


# ========== 句子分割函数 ==========

def split_sentences(text: str, min_length: int = 5, max_length: int = 200) -> list[str]:
    """
    智能分割文本为句子列表
    
    分割规则：
    1. 硬断句：中文标点（。！？；…）和英文句末（.!?后跟空格或行尾）
    2. 最小长度：太短的片段与下一句合并
    3. 最大长度：超长句子在逗号、分号等位置软断句
    4. 数字保护：不在数字中的小数点处分割
    
    Args:
        text: 待分割文本
        min_length: 最小句子长度，低于此长度会与下一句合并
        max_length: 最大句子长度，超过会在软断句处分割
    
    Returns:
        分割后的句子列表（已过滤空白和纯标点）
    """
    if not text or not text.strip():
        return []
    
    # 预处理：统一换行符
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    
    sentences = []
    current = ""
    i = 0
    
    while i < len(text):
        char = text[i]
        current += char
        
        # 检查是否是句末标点
        is_sentence_end = False
        
        # 中文硬断句标点
        if char in '。！？；…':
            is_sentence_end = True
        # 英文句末标点（后跟空格、换行或行尾）
        elif char in '.!?' and (i == len(text) - 1 or text[i + 1] in ' \n\t'):
            # 检查是否是数字中的小数点（如 3.14）
            if char == '.' and i > 0 and i < len(text) - 1:
                prev_char = text[i - 1]
                next_char = text[i + 1]
                if prev_char.isdigit() and next_char.isdigit():
                    is_sentence_end = False
                else:
                    is_sentence_end = True
            else:
                is_sentence_end = True
        
        if is_sentence_end:
            stripped = current.strip()
            if stripped and not _is_pure_punctuation(stripped):
                sentences.append(stripped)
            current = ""
        
        i += 1
    
    # 处理剩余内容
    if current.strip() and not _is_pure_punctuation(current.strip()):
        sentences.append(current.strip())
    
    # 合并短句
    sentences = _merge_short_sentences(sentences, min_length)
    
    # 长句软分割
    sentences = _split_long_sentences(sentences, max_length)
    
    return sentences


def _is_pure_punctuation(text: str) -> bool:
    """检查文本是否只包含标点符号"""
    if not text:
        return True
    punctuation = '。！？；，、：""''（）【】《》〈〉「」『』〔〕…—～·.!?,:;()[]{}<>"\'`~\\/|@#$%^&*'
    return all(c in punctuation or c.isspace() for c in text)


def _merge_short_sentences(sentences: list[str], min_length: int = 5) -> list[str]:
    """合并过短的句子片段，避免TTS合成过于碎片化
    
    合并策略：只有当前句子单独少于 min_length 字符时，才与下一句合并（而非链式合并），
    且合并后如果已超过 min_length 就停止合并。
    """
    if not sentences:
        return []
    
    merged = []
    buffer = ""
    
    for sent in sentences:
        if buffer:
            buffer += sent
            # 合并后如果达到最小长度，就输出
            if len(buffer) >= min_length:
                merged.append(buffer)
                buffer = ""
        elif len(sent) < min_length:
            # 当前句子太短，开始缓冲
            buffer = sent
        else:
            merged.append(sent)
    
    # 处理剩余缓冲
    if buffer:
        if merged:
            merged[-1] += buffer  # 追加到最后一个已合并的句子
        else:
            merged.append(buffer)
    
    return merged


def _split_long_sentences(sentences: list[str], max_length: int) -> list[str]:
    """在软断句位置分割超长句子"""
    result = []
    
    for sent in sentences:
        if len(sent) <= max_length:
            result.append(sent)
            continue
        
        # 超长句子，在软断句位置分割
        # 软断句标点：逗号、分号、冒号、顿号、换行
        soft_breaks = '，；：、\n,;: '
        
        while len(sent) > max_length:
            # 在 max_length 附近找软断句点
            split_pos = -1
            
            # 向前查找软断句点（优先找靠近 max_length 的）
            for i in range(min(max_length, len(sent) - 1), max_length // 2, -1):
                if sent[i] in soft_breaks:
                    split_pos = i + 1  # 包含标点
                    break
            
            # 如果没找到，强制在 max_length 处分割
            if split_pos == -1:
                split_pos = max_length
            
            result.append(sent[:split_pos].strip())
            sent = sent[split_pos:].strip()
        
        if sent:
            result.append(sent)
    
    return result


# ========== 流式 TTS 协调器 ==========

class StreamingTTSCoordinator:
    """
    流式 TTS 协调器
    
    实现模型边流式输出、语音边实时合成的功能。
    通过句子分割和并发控制，实现低延迟的语音合成。
    
    Usage:
        coordinator = StreamingTTSCoordinator(tts_provider, speaker="Cherry")
        
        # 在 SSE 生成器中同步调用
        coordinator.feed_chunk("你好，")
        coordinator.feed_chunk("这是一个测试。")
        
        # 文本输入完成后
        await coordinator.flush()
        
        # 异步生成音频事件
        async for event in coordinator.get_audio_events():
            yield event
    """
    
    def __init__(self, tts_provider: BaseTTSProvider, speaker: str = None):
        self._provider = tts_provider
        self._speaker = speaker
        self._buffer = ""           # 文本缓冲区
        self._sentence_index = 0    # 句子计数器
        self._audio_queue = asyncio.Queue()  # 音频事件队列
        self._semaphore = asyncio.Semaphore(2)  # 并发控制
        self._tasks: list[asyncio.Task] = []  # 合成任务列表
        self._flushed = False       # 是否已 flush
        self._stopped = False       # 是否已停止
        self._pending_tasks: set[asyncio.Task] = set()  # 待处理任务集合（用于 flush 等待）
        self._audio_format = None   # 音频格式（从首次合成结果推断，如 mp3/wav）
    
    def feed_chunk(self, text_chunk: str) -> None:
        """
        接收文本片段，尝试提取完整句子并启动 TTS 合成
        
        注意：这是同步方法，适用于 SSE 生成器同步调用。
        内部通过 asyncio.create_task 启动异步合成任务。
        
        Args:
            text_chunk: 文本片段（可能包含多个句子或半句）
        """
        if self._stopped:
            return
        
        if not text_chunk:
            return
        
        # 追加到缓冲区
        self._buffer += text_chunk
        
        logger.debug(f"[StreamingTTS] feed_chunk: buffer_len={len(self._buffer)}, chunk='{text_chunk[:50]}'")
        
        # 尝试提取完整句子
        sentences = split_sentences(self._buffer)
        
        if not sentences:
            return
        
        # 检查最后一个句子是否以句末标点结尾
        last_sent = sentences[-1]
        ends_with_punctuation = bool(re.search(r'[。！？；\.\!\?…]$', last_sent.rstrip()))
        
        # 如果最后一个句子不以句末标点结尾，保留在 buffer 中
        if not ends_with_punctuation and len(sentences) > 1:
            # 前 N-1 个句子提交合成
            for sent in sentences[:-1]:
                self._submit_sentence(sent)
            # 最后一个放回 buffer
            self._buffer = sentences[-1]
        elif ends_with_punctuation:
            # 所有句子都提交
            for sent in sentences:
                self._submit_sentence(sent)
            self._buffer = ""
        else:
            # 只有一个句子且不以标点结尾，保留在 buffer
            self._buffer = sentences[0]
    
    def _submit_sentence(self, text: str) -> None:
        """提交单个句子进行 TTS 合成"""
        if not text or not text.strip():
            return
        if self._stopped:
            return
        
        index = self._sentence_index
        self._sentence_index += 1
        
        logger.info(f"[StreamingTTS] 提交句子 #{index}: '{text[:50]}' (len={len(text)})")
        
        # 创建异步任务
        task = asyncio.create_task(
            self._synthesize_sentence(index, text.strip())
        )
        
        self._tasks.append(task)
        self._pending_tasks.add(task)
        
        # 任务完成后从 pending 中移除
        def on_done(t):
            self._pending_tasks.discard(t)
            if t in self._tasks:
                self._tasks.remove(t)
        
        task.add_done_callback(on_done)
    
    async def _synthesize_sentence(self, index: int, text: str) -> None:
        """
        合成单个句子的语音
        
        使用 semaphore 控制并发，成功后将音频事件放入队列。
        失败时记录 warning 但不阻塞后续句子。
        
        Args:
            index: 句子序号（用于保证播放顺序）
            text: 要合成的文本
        """
        if self._stopped:
            return
        
        try:
            async with self._semaphore:
                if self._stopped:
                    return
                
                result = await self._provider.synthesize(text, self._speaker)
                
                logger.info(f"[StreamingTTS] 合成结果 #{index}: success={result.get('success')}, format={result.get('format', 'N/A')}, audio_len={len(result.get('audio_base64', ''))}")
                
                if self._stopped:
                    return
                
                if result.get("success"):
                    audio_base64 = result.get("audio_base64", "")
                    if audio_base64:
                        # 推断音频格式（仅首次）
                        if self._audio_format is None:
                            self._audio_format = result.get("format", "wav")
                        await self._audio_queue.put({
                            "type": "audio_chunk",
                            "index": index,
                            "audio_base64": audio_base64,
                            "duration": result.get("duration", 0),
                            "format": self._audio_format,
                        })
                else:
                    error = result.get("error", "未知错误")
                    logger.warning(f"TTS 合成失败 (sentence {index}): {error}")
                    # 失败不阻塞，继续处理后续句子
                    
        except asyncio.CancelledError:
            # 任务被取消，正常退出
            raise
        except Exception as e:
            logger.warning(f"TTS 合成异常 (sentence {index}): {e}")
            # 异常不阻塞，继续处理后续句子
    
    async def flush(self) -> None:
        """
        刷新缓冲区，提交剩余内容并等待当前批次的合成任务完成
        
        支持多轮调用：每次 flush 只提交当前 buffer 中的内容并等待完成，
        不设置 _flushed 标志（允许后续 feed_chunk 继续注入新文本）。
        最终的 _flushed 标志在 agent 完成时由外部统一管理。
        """
        if self._stopped:
            return
        
        # 提交 buffer 中剩余的内容
        if self._buffer and self._buffer.strip():
            logger.info(f"[StreamingTTS] flush: 提交剩余buffer len={len(self._buffer)}")
            self._submit_sentence(self._buffer.strip())
            self._buffer = ""
        else:
            logger.info(f"[StreamingTTS] flush: buffer为空 (sentences={self._sentence_index})")
        
        # 等待所有 pending 任务完成（包括 feed_chunk 和 flush 创建的任务）
        while self._pending_tasks:
            try:
                # 等待任意一个任务完成
                done, _ = await asyncio.wait(
                    self._pending_tasks,
                    return_when=asyncio.FIRST_COMPLETED
                )
                # 清理已完成的任务
                for task in done:
                    self._pending_tasks.discard(task)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.warning(f"等待 TTS 任务完成时出错: {e}")
                break
        
        # 不再放入 sentinel！audio_done 由 chat.py 在 agent 完成时显式发送一次
        # 避免中间 flush 触发的提前退出问题
    
    def get_total_sentences(self) -> int:
        """返回已提交的句子总数"""
        return self._sentence_index
    
    async def get_audio_events(self) -> AsyncGenerator[dict, None]:
        """
        异步生成音频事件
        
        从音频队列中持续取出事件并 yield，
        收到 sentinel (None) 后退出。
        audio_done 事件由 chat.py 在 agent 完成时显式发送。
        
        Yields:
            {"type": "audio_chunk", "index": int, "audio_base64": str, "duration": float}
        """
        while True:
            try:
                event = await self._audio_queue.get()
                
                if event is None:
                    # Sentinel 仅在显式 close() 时才出现（正常流程不会走到这里）
                    logger.info("[StreamingTTS] get_audio_events: 收到sentinel，退出")
                    break
                
                yield event
                
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"获取音频事件时出错: {e}")
                break
    
    def stop(self) -> None:
        """
        停止所有 TTS 合成任务
        
        设置停止标志，取消所有未完成的任务。
        调用后 coordinator 不再接受新的文本输入。
        """
        self._stopped = True
        
        # 取消所有任务
        for task in list(self._tasks):
            if not task.done():
                task.cancel()
        
        # 清空队列（避免阻塞）
        while not self._audio_queue.empty():
            try:
                self._audio_queue.get_nowait()
            except asyncio.QueueEmpty:
                break
        
        # 放入 sentinel 确保 get_audio_events() 能退出
        try:
            self._audio_queue.put_nowait(None)
        except asyncio.QueueFull:
            pass
    
    async def close(self):
        """安全关闭：等待所有 pending 任务完成，然后发送 sentinel 让 get_audio_events 退出"""
        if self._stopped:
            return
        try:
            await self.flush()
        except Exception as e:
            logger.warning(f"close() 中 flush 失败: {e}")
        finally:
            # 只放入 sentinel，不清空队列，确保已合成的音频都能被消费完
            self._stopped = True
            try:
                self._audio_queue.put_nowait(None)
            except asyncio.QueueFull:
                pass


# ========== 便捷函数 ==========

def create_streaming_coordinator(speaker: str = None) -> StreamingTTSCoordinator:
    """
    创建流式 TTS 协调器（使用当前配置的 TTS 提供商）
    
    Args:
        speaker: 音色 ID，None 使用默认音色
    
    Returns:
        StreamingTTSCoordinator 实例
    """
    from app.services.tts_provider import get_tts_provider
    provider = get_tts_provider()
    if not provider.enabled:
        logger.warning(f"TTS 提供商不可用: {provider.__class__.__name__}，流式TTS将不会生成音频")
        # 仍然返回 coordinator，但合成时会失败并被跳过
    return StreamingTTSCoordinator(provider, speaker)
