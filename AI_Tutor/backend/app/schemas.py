"""
Pydantic Schemas - API 请求和响应的数据验证
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime


# ============ 通用响应 ============

class Response(BaseModel):
    """通用响应格式"""
    success: bool = True
    message: str = "success"
    data: Optional[Any] = None


# ============ 知识图谱相关 ============

class GenerateGraphRequest(BaseModel):
    """生成知识图谱请求"""
    topic: str = Field(..., description="学习目标，如'人工智能'")
    title: Optional[str] = None
    description: Optional[str] = None
    student_background: Dict[str, Any] = Field(default_factory=dict)
    study_depth: Optional[str] = Field(default="intermediate", description="学习深度：basic(了解), intermediate(熟悉), advanced(深入)")


class GraphVisualizeResponse(BaseModel):
    """图谱可视化响应"""
    nodes: List[Dict]
    edges: List[Dict]
    categories: List[Dict]
    metadata: Dict


# ============ 学习规划相关 ============

class GeneratePlanRequest(BaseModel):
    """生成学习计划请求"""
    graph_id: int
    study_goal_id: Optional[int] = None
    weekly_hours: float = 5.0
    title: Optional[str] = None
    description: Optional[str] = None


class GenerateChapteredPlanRequest(BaseModel):
    """生成章节式学习计划请求"""
    graph_id: int
    study_goal_id: Optional[int] = None
    weekly_hours: float = 5.0
    max_chapters: int = 12
    max_sections_per_chapter: int = 6
    title: Optional[str] = None
    description: Optional[str] = None


class PlanResponse(BaseModel):
    """学习计划响应"""
    id: int
    title: str
    description: str
    status: str
    total_lessons: int
    completed_lessons: int
    weekly_hours: float
    start_date: datetime
    end_date: datetime


class ChapterResponse(BaseModel):
    """章节响应"""
    id: int
    chapter_number: int
    title: str
    description: str
    learning_objectives: List[str]
    estimated_minutes: int
    ppt_generated: bool
    sections: List["SectionResponse"] = []


class SectionResponse(BaseModel):
    """节响应"""
    id: int
    section_number: int
    title: str
    description: str
    knowledge_point_ids: List[str]
    key_concepts: List[str]
    learning_objectives: List[str]
    estimated_minutes: int
    ppt_generated: bool
    lessons: List["LessonBriefResponse"] = []


class LessonBriefResponse(BaseModel):
    """课时简要响应"""
    id: int
    lesson_number: int
    title: str
    is_completed: bool
    estimated_minutes: int


class PlanStructureResponse(BaseModel):
    """学习计划结构响应（包含章-节-课时）"""
    id: int
    title: str
    description: str
    status: str
    total_lessons: int
    completed_lessons: int
    weekly_hours: float
    chapters: List[ChapterResponse]


class ChapterPPTResponse(BaseModel):
    """章节PPT响应"""
    chapter_id: int
    chapter_title: str
    ppt_generated: bool
    slides: Optional[List[dict]] = None


class SectionPPTResponse(BaseModel):
    """节PPT响应"""
    section_id: int
    section_title: str
    ppt_generated: bool
    slides: Optional[List[dict]] = None


# ============ 课时学习相关 ============

class LessonInteractRequest(BaseModel):
    """课时交互请求"""
    lesson_id: int
    student_message: str
    current_section: str = "introduction"


class ExerciseSubmitRequest(BaseModel):
    """练习提交请求"""
    lesson_id: int
    exercise_index: int
    user_answer: str


# ============ 诊断测评相关 ============

class GenerateAssessmentRequest(BaseModel):
    """生成测评请求"""
    lesson_id: int
    knowledge_point_id: str
    difficulty: str = "medium"
    question_count: int = 3


class SubmitAssessmentRequest(BaseModel):
    """提交测评请求"""
    assessment_id: int
    user_answers: List[Dict]


class DiagnosticReportResponse(BaseModel):
    """诊断报告响应"""
    overall_accuracy: float
    total_assessments: int
    mastery_map: Dict[str, float]
    recent_performance: List[Dict]
    weak_points: List[Dict]


# ============ 记忆系统相关 ============

class ReviewSessionRequest(BaseModel):
    """复习会话请求"""
    knowledge_point_id: str
    question_count: int = 3


class ReviewResultRequest(BaseModel):
    """复习结果请求"""
    knowledge_point_id: str
    result: str  # excellent/good/poor


class MemoryStatisticsResponse(BaseModel):
    """记忆统计响应"""
    total_knowledge_points: int
    mastered_points: int
    average_memory_strength: float
    forgetting_risk: Dict[str, int]
    next_review_count: int


# ============ 学生相关 ============

class StudentCreate(BaseModel):
    """学生创建请求"""
    username: str
    email: Optional[str] = None
    password: str
    nickname: Optional[str] = None
    background: Dict[str, Any] = Field(default_factory=dict)


class StudentLogin(BaseModel):
    """学生登录请求"""
    username: str
    password: str
