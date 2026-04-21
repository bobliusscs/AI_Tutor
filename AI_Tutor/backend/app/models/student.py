"""
数据模型 - 学生信息
"""
from sqlalchemy import Column, Integer, String, DateTime, JSON
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base


class Student(Base):
    """学生表"""
    __tablename__ = "students"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=True)
    hashed_password = Column(String(255), nullable=False)
    
    # 基本信息
    nickname = Column(String(50))
    avatar_url = Column(String(255))
    grade = Column(String(20))  # 年级
    
    # 学习统计
    total_learning_time = Column(Integer, default=0)  # 总学习分钟数
    study_streak = Column(Integer, default=0)  # 连续学习天数
    last_study_date = Column(DateTime)
    
    # 扩展信息（JSON 格式存储）
    background = Column(JSON)  # 学习背景、偏好等
    
    # 学习风格（JSON 格式存储）
    # {
    #   "primary_style": "visual",  # 主要风格: visual/auditory/reading/kinesthetic
    #   "style_scores": {           # 各风格得分 (0-100)
    #     "visual": 75,
    #     "auditory": 60,
    #     "reading": 80,
    #     "kinesthetic": 45
    #   },
    #   "preferred_time": "morning",  # 最佳学习时段: morning/afternoon/evening
    #   "study_duration": 45,         # 最佳学习时长(分钟)
    #   "last_updated": "2026-03-21"
    # }
    learning_style = Column(JSON)
    
    # 关联关系
    study_goals = relationship("StudyGoal", back_populates="student")
    node_masteries = relationship("NodeMastery", back_populates="student")
    agent_sessions = relationship("AgentSession", back_populates="student")
    motivations = relationship("Motivation", back_populates="student")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Student {self.username}>"
