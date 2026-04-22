"""
Agent工具函数包

包含所有可供Agent调用的工具函数
"""

from .lesson_ppt_tool import get_current_lesson_ppt
from .section_exercise_tool import get_section_exercises
from .study_session_tool import save_study_summary, get_recent_sessions_summary, generate_personalized_summary

__all__ = [
    "get_current_lesson_ppt",  # 提供PPT课件
    "get_section_exercises",    # 提供习题
    "save_study_summary",       # 保存学习记录
    "get_recent_sessions_summary",  # 获取历史摘要（构建交互上下文）
    "generate_personalized_summary",  # 生成个性化摘要
]
