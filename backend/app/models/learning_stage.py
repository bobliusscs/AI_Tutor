"""
数据模型 - 学习阶段记录
"""
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base


class LearningStage(Base):
    """
    学习阶段记录表
    记录每个课时的学习阶段和测试结果
    """
    __tablename__ = "learning_stages"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("agent_sessions.id"), nullable=False)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=False)
    
    # 阶段类型: pre_lesson/learning/post_test
    stage_type = Column(String(30), default="pre_lesson")
    
    # 测试结果
    test_score = Column(Float, nullable=True)  # 0-100
    correct_count = Column(Integer, default=0)
    total_questions = Column(Integer, default=0)
    
    # 测试答案详情（JSON格式保存）
    test_answers = Column(JSON, nullable=True)  # 用户答案详情
    wrong_questions = Column(JSON, nullable=True)  # 错题列表
    
    # 阶段状态
    status = Column(String(20), default="in_progress")  # in_progress/completed/skipped
    
    # 时间戳
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关联
    session = relationship("AgentSession", back_populates="learning_stages")
    lesson = relationship("Lesson")
    
    def __repr__(self):
        return f"<LearningStage {self.id} lesson={self.lesson_id} type={self.stage_type}>"
    
    def complete_stage(self, test_score: float = None, correct: int = 0, total: int = 0):
        """完成阶段记录"""
        self.status = "completed"
        self.completed_at = datetime.utcnow()
        if test_score is not None:
            self.test_score = test_score
            self.correct_count = correct
            self.total_questions = total
