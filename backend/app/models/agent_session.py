"""
数据模型 - Agent学习引导会话
"""
from sqlalchemy import Column, Integer, String, Float, JSON, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base


class AgentSession(Base):
    """
    Agent学习引导会话表
    记录每个学生的学习引导会话状态和上下文
    """
    __tablename__ = "agent_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    study_goal_id = Column(Integer, ForeignKey("study_goals.id"), nullable=True)
    learning_plan_id = Column(Integer, ForeignKey("learning_plans.id"), nullable=True)
    
    # 会话状态
    current_lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=True)  # 当前课时
    current_stage = Column(String(50), default="init")  # init/guide/learning/testing/reward/completed
    session_context = Column(JSON, default=dict)  # 存储短期记忆摘要
    
    # 会话历史摘要（用于上下文压缩）
    conversation_summary = Column(Text, nullable=True)  # AI生成的对话摘要
    
    # 会话元数据
    total_messages = Column(Integer, default=0)
    total_tests_taken = Column(Integer, default=0)  # 总测试次数
    total_score_sum = Column(Integer, default=0)  # 总分数累计
    avg_score = Column(Float, default=0.0)  # 平均分
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    
    # 关联
    student = relationship("Student", back_populates="agent_sessions")
    study_goal = relationship("StudyGoal", back_populates="agent_sessions")
    learning_plan = relationship("LearningPlan", back_populates="agent_sessions")
    current_lesson = relationship("Lesson")
    learning_stages = relationship("LearningStage", back_populates="session", cascade="all, delete-orphan")
    motivations = relationship("Motivation", back_populates="session", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<AgentSession {self.id} student={self.student_id} stage={self.current_stage}>"
    
    def update_avg_score(self, new_score: float):
        """更新平均分"""
        self.total_tests_taken += 1
        self.total_score_sum += int(new_score)
        self.avg_score = self.total_score_sum / self.total_tests_taken
