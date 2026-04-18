"""
数据模型 - 测评记录
"""
from sqlalchemy import Column, Integer, String, Float, JSON, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base


class Assessment(Base):
    """测评记录表"""
    __tablename__ = "assessments"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=False)
    
    # 测评类型
    assessment_type = Column(String(20))  # practice/exam/review
    
    # 答题记录
    questions = Column(JSON)  # 题目列表 [{id, question, options, user_answer, correct_answer, ...}]
    total_questions = Column(Integer, default=0)
    correct_answers = Column(Integer, default=0)
    
    # 结果分析
    score = Column(Float)  # 得分（百分比）
    time_spent = Column(Integer)  # 花费时间（秒）
    
    # 错误分析
    wrong_questions = Column(JSON)  # 错题详情
    error_analysis = Column(JSON)  # 错误原因分析 [{question_id, error_type, explanation}]
    
    # 掌握度评估
    mastery_before = Column(Float)  # 测评前掌握度
    mastery_after = Column(Float)  # 测评后掌握度
    
    # 关联
    lesson = relationship("Lesson", back_populates="assessments")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<Assessment {self.id}>"


class QuestionBank(Base):
    """题库表"""
    __tablename__ = "question_bank"
    
    id = Column(Integer, primary_key=True, index=True)
    study_goal_id = Column(Integer, ForeignKey("study_goals.id"), nullable=False)  # 关联学习目标
    knowledge_point_id = Column(String(100), nullable=False, index=True)
    
    # 题目信息
    question_text = Column(String(2000), nullable=False)
    question_type = Column(String(20))  # choice/fill_blank/short_answer
    difficulty = Column(String(20))  # basic/comprehensive/challenge (基础题/综合题/挑战题)
    
    # 答案选项（选择题）
    options = Column(JSON)  # ["A. xxx", "B. xxx", ...]
    correct_answer = Column(String(500), nullable=False)
    
    # 解析
    explanation = Column(String(2000))  # 答案解析
    error_analysis = Column(JSON)  # 常见错误分析
    
    # IRT 参数（项目反应理论）
    irt_params = Column(JSON)  # {a: 区分度，b: 难度，c: 猜测度}
    
    # 题目来源标记
    is_ai_generated = Column(Boolean, default=True)  # 是否AI生成
    question_number = Column(String(50))  # 题目编号（如 Q-2024-001）
    
    # 关联
    study_goal = relationship("StudyGoal", back_populates="exercises")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<Question {self.id}>"
