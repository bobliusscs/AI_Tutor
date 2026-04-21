"""
数据模型初始化 - 导入所有模型
"""
from app.core.database import Base

# 导入所有模型类（用于创建表）
from app.models.student import Student
from app.models.study_goal import StudyGoal
from app.models.knowledge_graph import KnowledgeGraph, KnowledgeNode
from app.models.learning_plan import LearningPlan, Lesson, Chapter, Section
from app.models.assessment import Assessment, QuestionBank
from app.models.memory import MemoryCurve, ReviewSchedule
from app.models.chat_history import ChatHistory
from app.models.node_mastery import NodeMastery
from app.models.study_material import StudyMaterial
from app.models.agent_session import AgentSession
from app.models.learning_stage import LearningStage
from app.models.motivation import Motivation, ACHIEVEMENTS_CONFIG, ENCOURAGEMENT_TEMPLATES
from app.models.agent_memory import AgentMemory
from app.models.study_record import StudyRecord


def init_db():
    """初始化数据库表"""
    # 这里暂时不创建表，因为我们使用 Alembic 进行迁移
    # Base.metadata.create_all(bind=engine)
    pass
