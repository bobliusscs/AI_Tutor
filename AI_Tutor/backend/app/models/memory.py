"""
数据模型 - 记忆曲线
"""
from sqlalchemy import Column, Integer, String, Float, JSON, ForeignKey, DateTime, Boolean
from datetime import datetime

from app.core.database import Base


class MemoryCurve(Base):
    """记忆曲线表 - 跟踪每个知识点的遗忘情况"""
    __tablename__ = "memory_curves"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, nullable=False, index=True)
    knowledge_point_id = Column(String(100), nullable=False, index=True)
    
    # 学习历史
    first_learned_at = Column(DateTime, nullable=False)  # 首次学习时间
    last_reviewed_at = Column(DateTime)  # 最后复习时间
    
    # 复习次数
    review_count = Column(Integer, default=0)
    next_review_at = Column(DateTime)  # 下次复习时间
    
    # 记忆强度
    memory_strength = Column(Float, default=0.0)  # 0-1，1 为最强
    predicted_forgetting_rate = Column(Float, default=1.0)  # 预测遗忘率（0-1）
    
    # 复习历史（JSON）
    review_history = Column(JSON)  # [{date, result, time_spent}, ...]
    
    # 状态
    is_mastered = Column(Boolean, default=False)  # 是否已牢固掌握
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<MemoryCurve {self.student_id}-{self.knowledge_point_id}>"


class ReviewSchedule(Base):
    """复习计划表"""
    __tablename__ = "review_schedules"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, nullable=False, index=True)
    
    # 待复习知识点
    knowledge_point_id = Column(String(100), nullable=False)
    scheduled_date = Column(DateTime, nullable=False, index=True)  # 计划复习日期
    
    # 复习内容
    review_type = Column(String(20))  # quick_review/deep_review
    questions = Column(JSON)  # 复习题目
    
    # 状态
    is_completed = Column(Boolean, default=False)
    completed_at = Column(DateTime)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<ReviewSchedule {self.id}>"
