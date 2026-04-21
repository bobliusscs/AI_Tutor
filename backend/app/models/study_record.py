"""
数据模型 - 学习记录
按天记录学生在某学习目标下的学习情况（时长、完成课时、练习成绩等）
"""
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Date, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base


class StudyRecord(Base):
    """学习记录表（按天粒度）"""
    __tablename__ = "study_records"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    goal_id = Column(Integer, ForeignKey("study_goals.id"), nullable=False)

    # 记录日期（按天）
    record_date = Column(Date, nullable=False)

    # 学习统计
    study_duration_minutes = Column(Integer, default=0)   # 当天学习时长(分钟)
    lessons_completed = Column(Integer, default=0)         # 完成课时数
    exercises_attempted = Column(Integer, default=0)       # 练习题数
    exercises_correct = Column(Integer, default=0)         # 正确数

    # JSON 字段
    knowledge_points_covered = Column(Text)  # 覆盖的知识点ID列表(JSON)
    mastery_changes = Column(Text)           # 掌握度变化记录(JSON)

    # 文本总结
    summary = Column(Text)  # AI生成的当天学习总结
    notes = Column(Text)    # 补充笔记
    
    # 会话摘要（保存每次会话的摘要，用于跨会话上下文）
    session_summary = Column(Text)  # JSON格式：[{session_id, summary, created_at}]
    
    # 完整会话记录（用于存档和回顾）
    conversation_log = Column(Text)  # JSON格式：完整的对话记录

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 同一天、同一学生、同一学习目标只允许一条记录
    __table_args__ = (
        UniqueConstraint('student_id', 'goal_id', 'record_date', name='uq_study_record_day'),
    )

    def __repr__(self):
        return f"<StudyRecord student={self.student_id} goal={self.goal_id} date={self.record_date}>"
