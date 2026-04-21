"""
数据模型 - 聊天历史
"""
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base


class ChatHistory(Base):
    """聊天历史表"""
    __tablename__ = "chat_histories"
    
    id = Column(Integer, primary_key=True, index=True)
    study_goal_id = Column(Integer, ForeignKey("study_goals.id"), nullable=False)
    
    # 会话信息
    title = Column(String(200))  # 会话标题（如：第一次对话）
    
    # 消息内容（JSON数组）
    # [{"role": "user", "content": "...", "timestamp": "..."}, {"role": "assistant", "content": "..."}]
    messages = Column(JSON, nullable=False)
    
    # 元数据
    message_count = Column(Integer, default=0)  # 消息数量
    total_tokens = Column(Integer, default=0)  # 消耗的token数
    
    # 关联
    study_goal = relationship("StudyGoal", back_populates="chat_histories")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<ChatHistory {self.id}>"
