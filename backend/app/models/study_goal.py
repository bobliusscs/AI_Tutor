"""
数据模型 - 学习目标
"""
from sqlalchemy import Column, Integer, String, Float, JSON, ForeignKey, DateTime, Enum, Text
from sqlalchemy.orm import relationship
import enum
from datetime import datetime

from app.core.database import Base


class StudyGoalStatus(str, enum.Enum):
    """学习目标状态"""
    ACTIVE = "active"  # 进行中
    COMPLETED = "completed"  # 已完成
    ARCHIVED = "archived"  # 已归档


class StudyDepth(str, enum.Enum):
    """学习深度"""
    BASIC = "basic"       # 了解
    INTERMEDIATE = "intermediate"  # 熟悉
    ADVANCED = "advanced"  # 深入


class StudyGoal(Base):
    """学习目标表"""
    __tablename__ = "study_goals"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    
    # 学习目标内容
    title = Column(String(200), nullable=False)  # 学习目标标题
    description = Column(Text)  # 学习目标描述
    subject = Column(String(100))  # 学科/领域
    
    # 状态
    status = Column(String(20), default=StudyGoalStatus.ACTIVE.value)
    
    # 学习设置
    target_hours_per_week = Column(Float, default=5.0)  # 每周可用小时数
    target_completion_date = Column(DateTime)  # 目标完成日期
    study_depth = Column(String(20), default=StudyDepth.INTERMEDIATE.value)  # 学习深度
    
    # 学习背景（JSON）
    student_background = Column(JSON)  # 学生学习背景、基础等
    
    # 进度统计
    total_knowledge_points = Column(Integer, default=0)  # 知识点总数
    mastered_points = Column(Integer, default=0)  # 已掌握点数
    completed_lessons = Column(Integer, default=0)  # 已完成课时
    
    # 关联
    student = relationship("Student", back_populates="study_goals")
    knowledge_graphs = relationship("KnowledgeGraph", back_populates="study_goal")
    learning_plans = relationship("LearningPlan", back_populates="study_goal")
    materials = relationship("StudyMaterial", back_populates="study_goal")
    exercises = relationship("QuestionBank", back_populates="study_goal")
    chat_histories = relationship("ChatHistory", back_populates="study_goal")
    node_masteries = relationship("NodeMastery", back_populates="study_goal")
    agent_sessions = relationship("AgentSession", back_populates="study_goal")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<StudyGoal {self.title}>"
