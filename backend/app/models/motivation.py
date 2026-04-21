"""
数据模型 - 激励记录
"""
from sqlalchemy import Column, Integer, String, Text, Float, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base


class Motivation(Base):
    """
    激励记录表
    存储学生的激励信息、成就称号等
    """
    __tablename__ = "motivations"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    session_id = Column(Integer, ForeignKey("agent_sessions.id"), nullable=True)
    
    # 激励类型: encouragement/achievement/streak
    motivation_type = Column(String(30), nullable=False)
    
    # 称号信息
    title = Column(String(100), nullable=True)  # 称号如"连续达人"、"满分达人"
    icon = Column(String(50), nullable=True)  # 图标标识
    
    # 激励内容
    content = Column(Text, nullable=True)  # 激励文本内容
    
    # 触发条件
    trigger = Column(String(100), nullable=True)  # 什么条件下触发
    value = Column(Float, nullable=True)  # 关联值（分数/天数等）
    
    # 是否已查看
    is_read = Column(Boolean, default=False)
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关联
    student = relationship("Student", back_populates="motivations")
    session = relationship("AgentSession", back_populates="motivations")
    
    def __repr__(self):
        return f"<Motivation {self.id} type={self.motivation_type} title={self.title}>"


# 预定义成就配置
ACHIEVEMENTS_CONFIG = {
    "perfect_score": {
        "title": "满分达人",
        "icon": "trophy",
        "description": "在测试中获得90分以上",
        "condition": "test_score >= 90"
    },
    "streak_week": {
        "title": "坚持不懈",
        "icon": "fire",
        "description": "连续学习7天",
        "condition": "study_streak >= 7"
    },
    "streak_month": {
        "title": "学习达人",
        "icon": "star",
        "description": "连续学习30天",
        "condition": "study_streak >= 30"
    },
    "first_lesson": {
        "title": "初出茅庐",
        "icon": "rocket",
        "description": "完成第一个课时",
        "condition": "completed_lessons >= 1"
    },
    "module_master": {
        "title": "模块大师",
        "icon": "crown",
        "description": "完整掌握一个学习模块",
        "condition": "module_score >= 85"
    },
    "perfect_lesson": {
        "title": "精益求精",
        "icon": "gem",
        "description": "一次性完成课时学习",
        "condition": "lesson_completed_first_try"
    },
    "learning_explorer": {
        "title": "学习探险家",
        "icon": "compass",
        "description": "开始第一个学习目标",
        "condition": "goals_created >= 1"
    },
    "consistent_learner": {
        "title": "持之以恒",
        "icon": "medal",
        "description": "完成10个课时",
        "condition": "completed_lessons >= 10"
    }
}


# 鼓励语模板
ENCOURAGEMENT_TEMPLATES = {
    "excellent": [
        "太棒了！继续保持！",
        "你学得真快！",
        "继续保持这个势头！",
        "优秀！继续保持！",
        "进步神速！"
    ],
    "good": [
        "做得不错！",
        "有进步！",
        "继续保持！",
        "不错，继续加油！",
        "有提升空间，继续努力！"
    ],
    "needs_improvement": [
        "别灰心，继续努力！",
        "这是学习的一部分，继续前进！",
        "我们一起看看哪里可以改进。",
        "暂时没掌握好，不要紧，我们再接再厉！",
        "每个人都有不懂的时候，继续加油！"
    ]
}


def check_and_unlock_achievements(student_id: int, context: dict, db) -> list:
    """
    检查并解锁成就

    Args:
        student_id: 学生ID
        context: 上下文（包含 test_score, completed_lessons, study_streak 等）
        db: 数据库会话

    Returns:
        新解锁的成就列表
    """
    from sqlalchemy.orm import Session
    if not isinstance(db, Session):
        raise ValueError("需要传入数据库会话")

    unlocked = []

    # 获取当前已解锁的成就
    existing = db.query(Motivation).filter(
        Motivation.student_id == student_id,
        Motivation.motivation_type == "achievement"
    ).all()
    existing_titles = {m.title for m in existing}

    # 获取上下文数据
    test_score = context.get("test_score", 0)
    completed_lessons = context.get("completed_lessons", 0)
    study_streak = context.get("study_streak", 0)

    # 满分达人
    if "满分达人" not in existing_titles and test_score >= 90:
        unlocked.append({
            "title": "满分达人",
            "icon": "trophy",
            "description": "测试获得90分以上"
        })

    # 初出茅庐
    if "初出茅庐" not in existing_titles and completed_lessons >= 1:
        unlocked.append({
            "title": "初出茅庐",
            "icon": "rocket",
            "description": "完成第一个课时"
        })

    # 持之以恒
    if "持之以恒" not in existing_titles and completed_lessons >= 10:
        unlocked.append({
            "title": "持之以恒",
            "icon": "medal",
            "description": "完成10个课时"
        })

    # 学习达人（连续学习30天）
    if "学习达人" not in existing_titles and study_streak >= 30:
        unlocked.append({
            "title": "学习达人",
            "icon": "star",
            "description": "连续学习30天"
        })

    # 保存新解锁的成就
    for achievement in unlocked:
        motivation = Motivation(
            student_id=student_id,
            motivation_type="achievement",
            title=achievement["title"],
            icon=achievement["icon"],
            content=achievement["description"],
            trigger="achievement_unlock",
            value=test_score or completed_lessons or study_streak
        )
        db.add(motivation)

    if unlocked:
        db.commit()

    return unlocked


def generate_encouragement(score: float, context: dict = None) -> str:
    """
    生成个性化鼓励语

    Args:
        score: 测试分数
        context: 上下文信息（可选）

    Returns:
        鼓励语文本
    """
    import random

    if score >= 90:
        templates = ENCOURAGEMENT_TEMPLATES.get("excellent", [])
    elif score >= 60:
        templates = ENCOURAGEMENT_TEMPLATES.get("good", [])
    else:
        templates = ENCOURAGEMENT_TEMPLATES.get("needs_improvement", [])

    if templates:
        return random.choice(templates)
    return "继续加油！"
