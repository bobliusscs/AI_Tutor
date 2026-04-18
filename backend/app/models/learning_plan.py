"""
数据模型 - 学习计划
"""
from sqlalchemy import Column, Integer, String, Float, JSON, ForeignKey, DateTime, Enum, Boolean
from sqlalchemy.orm import relationship
import enum
from datetime import datetime

from app.core.database import Base


class PlanStatus(str, enum.Enum):
    """学习计划状态"""
    ACTIVE = "active"  # 进行中
    COMPLETED = "completed"  # 已完成
    PAUSED = "paused"  # 已暂停
    CANCELLED = "cancelled"  # 已取消


class LearningPlan(Base):
    """学习计划表"""
    __tablename__ = "learning_plans"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    study_goal_id = Column(Integer, ForeignKey("study_goals.id"), nullable=False)  # 关联学习目标
    graph_id = Column(Integer, ForeignKey("knowledge_graphs.id"), nullable=False)
    
    title = Column(String(200), nullable=False)
    description = Column(String(500))
    
    # 计划详情
    status = Column(String(20), default=PlanStatus.ACTIVE.value)
    start_date = Column(DateTime)
    end_date = Column(DateTime)  # 预计完成日期
    
    # 时间安排
    weekly_hours = Column(Float, default=5.0)  # 每周可用小时数
    total_lessons = Column(Integer, default=0)  # 总课时数
    completed_lessons = Column(Integer, default=0)  # 已完成课时数
    
    # 学习路径（JSON 格式）
    lesson_sequence = Column(JSON)  # 课时顺序 [{lesson_id, order, ...}]
    
    # 关联
    study_goal = relationship("StudyGoal", back_populates="learning_plans")
    knowledge_graph = relationship("KnowledgeGraph", back_populates="learning_plans")
    lessons = relationship("Lesson", back_populates="learning_plan", order_by="Lesson.lesson_number")
    chapters = relationship("Chapter", back_populates="learning_plan", order_by="Chapter.chapter_number")
    agent_sessions = relationship("AgentSession", back_populates="learning_plan")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<LearningPlan {self.title}>"


class Chapter(Base):
    """章节表"""
    __tablename__ = "chapters"
    
    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("learning_plans.id"), nullable=False)
    
    chapter_number = Column(Integer, nullable=False)  # 章节序号
    title = Column(String(200), nullable=False)      # 章节标题
    description = Column(String(500))                # 章节简介
    learning_objectives = Column(JSON)                # 学习目标列表
    
    # 时间安排
    estimated_minutes = Column(Integer, default=0)   # 章节总时长
    
    # PPT生成状态
    ppt_generated = Column(Boolean, default=False)   # PPT是否已生成
    ppt_content = Column(JSON)                         # PPT内容（幻灯片列表）
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关联
    learning_plan = relationship("LearningPlan", back_populates="chapters")
    sections = relationship("Section", back_populates="chapter", order_by="Section.section_number")
    lessons = relationship("Lesson", back_populates="chapter")
    
    def __repr__(self):
        return f"<Chapter {self.chapter_number}: {self.title}>"


class Section(Base):
    """节表"""
    __tablename__ = "sections"
    
    id = Column(Integer, primary_key=True, index=True)
    chapter_id = Column(Integer, ForeignKey("chapters.id"), nullable=False)
    plan_id = Column(Integer, ForeignKey("learning_plans.id"), nullable=False)
    
    section_number = Column(Integer, nullable=False)    # 节序号
    title = Column(String(200), nullable=False)         # 节标题
    description = Column(String(500))                   # 节简介
    
    # 包含的知识点（JSON数组存储知识点ID列表）
    knowledge_point_ids = Column(JSON)                  # 关联的知识点ID列表
    key_concepts = Column(JSON)                         # 关键知识点列表
    learning_objectives = Column(JSON)                 # 学习目标
    
    # 时间安排
    estimated_minutes = Column(Integer, default=0)
    
    # PPT生成状态
    ppt_generated = Column(Boolean, default=False)
    ppt_content = Column(JSON)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关联
    chapter = relationship("Chapter", back_populates="sections")
    lessons = relationship("Lesson", back_populates="section")
    
    def __repr__(self):
        return f"<Section {self.section_number}: {self.title}>"


class Lesson(Base):
    """课时表"""
    __tablename__ = "lessons"
    
    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("learning_plans.id"), nullable=False)
    chapter_id = Column(Integer, ForeignKey("chapters.id"), nullable=True)   # 所属章节
    section_id = Column(Integer, ForeignKey("sections.id"), nullable=True)   # 所属节
    
    lesson_number = Column(Integer, nullable=False)  # 课时序号
    title = Column(String(200), nullable=False)
    knowledge_point_id = Column(String(100))  # 关联的知识点 ID
    
    # 课时内容结构
    introduction = Column(String(2000))  # 引入（2 分钟）
    explanation = Column(String(5000))  # 讲解（8 分钟）
    example = Column(String(3000))  # 示例（5 分钟）
    exercises = Column(JSON)  # 练习题（10 分钟）[{question, options, answer, explanation}]
    summary = Column(String(1000))  # 总结（2 分钟）
    
    # 时间估算
    estimated_minutes = Column(Integer, default=27)
    
    # 状态
    is_completed = Column(Boolean, default=False)
    completed_at = Column(DateTime)
    
    # 关联
    learning_plan = relationship("LearningPlan", back_populates="lessons")
    chapter = relationship("Chapter", back_populates="lessons")
    section = relationship("Section", back_populates="lessons")
    assessments = relationship("Assessment", back_populates="lesson")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<Lesson {self.title}>"
