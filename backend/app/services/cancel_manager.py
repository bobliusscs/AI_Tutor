"""
取消生成信号管理器
用于在生成过程中接收取消信号，实现优雅停止
"""
import threading
from typing import Optional


class GenerationCancelledError(Exception):
    """生成被取消异常"""
    pass


# 全局取消状态
_cancel_requested: bool = False
_lock = threading.Lock()


def reset_cancel():
    """
    重置取消状态（清除取消标志）
    """
    global _cancel_requested
    with _lock:
        _cancel_requested = False


def request_cancel():
    """
    请求取消生成（设置取消标志）
    """
    global _cancel_requested
    with _lock:
        _cancel_requested = True
    print("[取消管理器] 已发送取消请求")


def is_cancelled() -> bool:
    """
    检查是否已请求取消
    """
    global _cancel_requested
    with _lock:
        return _cancel_requested


async def wait_if_cancelled():
    """
    异步等待：检查是否已请求取消
    如果已请求取消，抛出取消异常
    """
    global _cancel_requested
    with _lock:
        cancelled = _cancel_requested
    if cancelled:
        print("[取消管理器] 检测到取消请求，正在停止...")
        raise GenerationCancelledError()
