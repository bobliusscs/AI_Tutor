"""
Agent工具函数包

包含所有可供Agent调用的工具函数
"""

from .lesson_ppt_tool import get_current_lesson_ppt
from .section_exercise_tool import get_section_exercises

__all__ = [
    "get_current_lesson_ppt",
    "get_section_exercises",
]
