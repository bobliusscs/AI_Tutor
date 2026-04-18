"""
数据模型 - 知识图谱
"""
from sqlalchemy import Column, Integer, String, Float, JSON, ForeignKey, Boolean, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base


class KnowledgeGraph(Base):
    """知识图谱表"""
    __tablename__ = "knowledge_graphs"
    
    id = Column(Integer, primary_key=True, index=True)
    study_goal_id = Column(Integer, ForeignKey("study_goals.id"), nullable=True)  # 关联学习目标，一对一（可选）
    
    title = Column(String(200), nullable=False)  # 图谱标题，如"人工智能基础"
    description = Column(String(500))  # 图谱描述
    
    # 图谱数据（JSON 格式）
    nodes = Column(JSON, nullable=False)  # 节点列表 [{id, label, difficulty, ...}]
    edges = Column(JSON, nullable=False)  # 边列表 [{source, target, type, ...}]
    
    # 元数据
    total_nodes = Column(Integer, default=0)
    total_edges = Column(Integer, default=0)
    estimated_hours = Column(Float, default=0.0)  # 预计总学时
    
    # 关联
    study_goal = relationship("StudyGoal", back_populates="knowledge_graphs")
    learning_plans = relationship("LearningPlan", back_populates="knowledge_graph")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<KnowledgeGraph {self.title}>"


class KnowledgeNode(Base):
    """知识点详情表（用于存储单个知识点的详细信息）"""
    __tablename__ = "knowledge_nodes"
    
    id = Column(Integer, primary_key=True, index=True)
    graph_id = Column(Integer, ForeignKey("knowledge_graphs.id"), nullable=False)
    
    node_id = Column(String(100), nullable=False)  # 节点 ID（在图谱中的唯一标识）
    name = Column(String(200), nullable=False)  # 知识点名称
    description = Column(String(1000))  # 详细描述
    
    # 属性
    difficulty = Column(String(20))  # easy/medium/hard
    estimated_hours = Column(Float, default=1.0)  # 预计学时
    prerequisites = Column(JSON)  # 前置知识点 ID 列表
    
    # 教学资源
    resources = Column(JSON)  # 相关链接、资料等
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<KnowledgeNode {self.name}>"
