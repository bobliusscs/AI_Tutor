"""
数据模型 - Agent 记忆
"""
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey
from sqlalchemy.sql import func

from app.core.database import Base


class AgentMemory(Base):
    """Agent 长期记忆表"""
    __tablename__ = "agent_memories"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    category = Column(String(50), nullable=False, index=True)  # learning_preference/knowledge_mastery/interaction_pattern/milestone
    content = Column(Text, nullable=False)
    keywords = Column(String(500), default="")  # 逗号分隔的关键词，用于检索
    importance = Column(Float, default=0.5)  # 0.0-1.0 重要性权重
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    access_count = Column(Integer, default=0)  # 访问次数，用于记忆衰减/强化
    embedding = Column(Text, nullable=True)  # 向量嵌入（JSON 序列化的浮点数组）
    version = Column(Integer, default=1)  # 策略版本号，用于自进化系统的策略版本追踪

    def __repr__(self):
        return f"<AgentMemory id={self.id} student_id={self.student_id} category={self.category}>"
