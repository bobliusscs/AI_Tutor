"""
API 路由器 - 统一挂载所有路由
"""
from fastapi import APIRouter

from app.api.routes import (
    knowledge_graph, learning_plan, lesson, assessment, memory, 
    student, chat, study_goal, analysis, material, question, settings, agent, skill_manager,
    practice, tts
)

api_router = APIRouter()

# 挂载各模块路由
api_router.include_router(knowledge_graph.router, prefix="/knowledge-graph", tags=["知识图谱"])
api_router.include_router(learning_plan.router, prefix="/learning-plan", tags=["学习规划"])
api_router.include_router(lesson.router, prefix="/lesson", tags=["课时学习"])
api_router.include_router(assessment.router, prefix="/assessment", tags=["诊断测评"])
api_router.include_router(memory.router, prefix="/memory", tags=["记忆系统"])
api_router.include_router(student.router, prefix="/student", tags=["学生管理"])
api_router.include_router(chat.router, prefix="/chat", tags=["聊天"])
api_router.include_router(settings.router, prefix="/settings", tags=["设置"])
api_router.include_router(agent.router, prefix="/agent", tags=["Agent"])

# 学习目标驱动的新路由
api_router.include_router(study_goal.router, prefix="/study-goals", tags=["学习目标"])
api_router.include_router(analysis.router, prefix="/analysis", tags=["学情分析"])
api_router.include_router(material.router, prefix="/materials", tags=["学习资料"])
api_router.include_router(question.router, prefix="/questions", tags=["习题库"])
api_router.include_router(practice.router, prefix="/practice", tags=["练习巩固"])
# 注意：learning_guide 路由已废弃，功能迁移到 Skill Chain 系统

# Skill管理路由
api_router.include_router(skill_manager.router, prefix="/skills", tags=["Skill管理"])

# TTS语音合成路由
api_router.include_router(tts.router, prefix="/tts", tags=["语音合成"])
