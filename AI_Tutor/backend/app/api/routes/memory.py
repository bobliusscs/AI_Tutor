"""
记忆系统 API 路由
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.deps import get_engine_manager, get_current_student_id
from app.services.engine_manager import EngineManager
from app.schemas import ReviewSessionRequest, ReviewResultRequest, Response


router = APIRouter()


class LearningStyleUpdateRequest(BaseModel):
    """学习风格更新请求"""
    primary_style: str = None
    style_scores: dict = None
    preferred_time: str = None
    study_duration: int = None


@router.get("/schedule", response_model=Response)
async def get_review_schedule(
    current_student_id: int = Depends(get_current_student_id),
    days: int = 7,
    engine_manager: EngineManager = Depends(get_engine_manager)
):
    """
    获取未来 N 天的复习计划
    
    ## 返回
    - 待复习知识点列表
    - 紧急程度（high/medium/low）
    - 当前记忆保留率
    """
    schedule = engine_manager.memory_engine.get_review_schedule(current_student_id, days)
    
    return Response(
        success=True,
        message="复习计划获取成功",
        data=schedule
    )


@router.post("/session/generate", response_model=Response)
async def generate_review_session(
    request: ReviewSessionRequest,
    current_student_id: int = Depends(get_current_student_id),
    engine_manager: EngineManager = Depends(get_engine_manager)
):
    """
    生成微复习会话
    
    ## 功能说明
    - 3-5 道精选题目的快速检测
    - 不是重学，而是快速回忆
    - 预计用时 2-5 分钟
    """
    session = engine_manager.memory_engine.generate_review_session(
        student_id=current_student_id,
        knowledge_point_id=request.knowledge_point_id,
        question_count=request.question_count
    )
    
    return Response(
        success=True,
        message="复习会话生成成功",
        data=session
    )


@router.post("/session/submit", response_model=Response)
async def submit_review_session(
    request: ReviewResultRequest,
    current_student_id: int = Depends(get_current_student_id),
    engine_manager: EngineManager = Depends(get_engine_manager)
):
    """
    提交复习结果
    
    ## 参数
    - result: excellent/good/poor
    
    ## 功能
    - 更新记忆曲线
    - 计算下次复习时间
    """
    try:
        memory_curve = engine_manager.memory_engine.update_memory_after_review(
            student_id=current_student_id,
            knowledge_point_id=request.knowledge_point_id,
            review_result=request.result
        )
        
        return Response(
            success=True,
            message="复习完成！",
            data={
                "next_review_date": memory_curve.next_review_at.isoformat(),
                "memory_strength": memory_curve.memory_strength,
                "is_mastered": memory_curve.is_mastered
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics", response_model=Response)
async def get_memory_statistics(
    current_student_id: int = Depends(get_current_student_id),
    engine_manager: EngineManager = Depends(get_engine_manager)
):
    """
    获取记忆统计数据
    
    ## 返回
    - 总知识点数
    - 已牢固掌握的知识点数
    - 平均记忆强度
    - 遗忘风险分布
    """
    stats = engine_manager.memory_engine.get_memory_statistics(current_student_id)
    
    return Response(
        success=True,
        message="获取成功",
        data=stats
    )


@router.get("/streak", response_model=Response)
async def check_streak(
    current_student_id: int = Depends(get_current_student_id),
    engine_manager: EngineManager = Depends(get_engine_manager)
):
    """检查学习连续性"""
    streak_info = engine_manager.memory_engine.check_streak(current_student_id)
    
    return Response(
        success=True,
        message="获取成功",
        data=streak_info
    )


@router.post("/streak/update", response_model=Response)
async def update_streak(
    current_student_id: int = Depends(get_current_student_id),
    engine_manager: EngineManager = Depends(get_engine_manager)
):
    """更新学习连续性（每次学习后调用）"""
    engine_manager.memory_engine.update_study_streak(current_student_id)
    
    return Response(
        success=True,
        message="已更新学习记录"
    )


@router.get("/learning-style", response_model=Response)
async def get_learning_style(
    current_student_id: int = Depends(get_current_student_id),
    engine_manager: EngineManager = Depends(get_engine_manager)
):
    """
    获取用户学习风格分析
    
    ## 返回
    - 主要学习风格类型 (visual/auditory/reading/kinesthetic)
    - 各风格得分 (0-100)
    - 最佳学习时段
    - 推荐学习时长
    """
    style = engine_manager.memory_engine.analyze_learning_style(current_student_id)
    
    return Response(
        success=True,
        message="学习风格获取成功",
        data=style
    )


@router.put("/learning-style", response_model=Response)
async def update_learning_style(
    request: LearningStyleUpdateRequest,
    current_student_id: int = Depends(get_current_student_id),
    engine_manager: EngineManager = Depends(get_engine_manager)
):
    """
    更新用户学习风格偏好
    
    ## 参数
    - primary_style: 主要风格 (visual/auditory/reading/kinesthetic)
    - style_scores: 各风格得分
    - preferred_time: 最佳时段 (morning/afternoon/evening)
    - study_duration: 推荐学习时长(分钟)
    """
    style_data = {k: v for k, v in request.dict().items() if v is not None}
    style = engine_manager.memory_engine.update_learning_style(current_student_id, style_data)
    
    return Response(
        success=True,
        message="学习风格更新成功",
        data=style
    )


@router.get("/learning-summary", response_model=Response)
async def get_learning_summary(
    current_student_id: int = Depends(get_current_student_id),
    engine_manager: EngineManager = Depends(get_engine_manager)
):
    """
    获取学习综合情况摘要
    
    ## 返回
    - 学习目标数量 (总计/已完成/进行中)
    - 知识点掌握情况
    - 整体掌握度
    - 待复习数量
    - 学习连续天数
    """
    summary = engine_manager.memory_engine.get_learning_summary(current_student_id)
    
    return Response(
        success=True,
        message="获取成功",
        data=summary
    )
