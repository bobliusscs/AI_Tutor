"""
数据模型 - 知识点掌握度
记录学生对每个知识点的掌握情况
"""
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base


class NodeMastery(Base):
    """知识点掌握度表"""
    __tablename__ = "node_masteries"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    study_goal_id = Column(Integer, ForeignKey("study_goals.id"), nullable=False)
    
    # 知识点标识
    node_id = Column(String(100), nullable=False)  # 在知识图谱中的节点ID
    node_name = Column(String(200))  # 知识点名称（冗余存储便于查询）
    
    # 掌握度信息
    mastery_level = Column(Float, default=0.0)  # 掌握度 0-100
    confidence = Column(Float, default=0.0)  # 置信度 0-1
    
    # 学习统计
    total_attempts = Column(Integer, default=0)  # 总尝试次数
    correct_attempts = Column(Integer, default=0)  # 正确次数
    
    # 测评记录
    last_assessment_score = Column(Float)  # 最近一次测评得分
    last_assessment_at = Column(DateTime)  # 最近一次测评时间
    
    # 学习记录
    study_count = Column(Integer, default=0)  # 学习次数
    last_studied_at = Column(DateTime)  # 最后学习时间
    
    # 分析数据
    weak_points = Column(Text)  # 薄弱点分析
    improvement_suggestions = Column(Text)  # 改进建议
    
    # 关联
    student = relationship("Student", back_populates="node_masteries")
    study_goal = relationship("StudyGoal", back_populates="node_masteries")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<NodeMastery {self.node_name}: {self.mastery_level}%>"
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            "id": self.id,
            "node_id": self.node_id,
            "node_name": self.node_name,
            "mastery_level": self.mastery_level,
            "confidence": self.confidence,
            "total_attempts": self.total_attempts,
            "correct_attempts": self.correct_attempts,
            "last_assessment_score": self.last_assessment_score,
            "last_studied_at": self.last_studied_at.isoformat() if self.last_studied_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
