"""
Agent 模块 - 极简对话Agent

核心组件:
- AgentCore: 极简对话Agent(基于 ReAct 范式)
- SimpleAgent: 具体实现
"""

from .core import AgentCore
from .agent import SimpleAgent

__all__ = [
    "AgentCore",
    "SimpleAgent",
]
