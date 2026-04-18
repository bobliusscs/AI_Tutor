"""
诊断测评 API 路由
"""
from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_engine_manager, get_current_student_id
from app.services.engine_manager import EngineManager
from app.schemas import GenerateAssessmentRequest, SubmitAssessmentRequest, Response


router = APIRouter()


@router.post("/generate", response_model=Response)
async def generate_assessment(
    request: GenerateAssessmentRequest,
    current_student_id: int = Depends(get_current_student_id),
    engine_manager: EngineManager = Depends(get_engine_manager)
):
    """
    生成测评题目
    
    ## 功能说明
    - 从题库智能选题或 AI 自动生成新题
    - 支持三级难度（easy/medium/hard）
    - 每题包含详细解析和错误分析
    """
    try:
        assessment = await engine_manager.assessment_engine.generate_assessment(
            student_id=current_student_id,
            lesson_id=request.lesson_id,
            knowledge_point_id=request.knowledge_point_id,
            difficulty=request.difficulty,
            question_count=request.question_count
        )
        
        return Response(
            success=True,
            message="测评生成成功",
            data={
                "assessment_id": assessment.id,
                "total_questions": assessment.total_questions,
                "questions": assessment.questions
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/submit", response_model=Response)
async def submit_assessment(
    request: SubmitAssessmentRequest,
    engine_manager: EngineManager = Depends(get_engine_manager)
):
    """
    提交测评答案
    
    ## 返回
    - 判题结果
    - 得分
    - 错题解析
    - 掌握度评估
    """
    try:
        assessment = engine_manager.assessment_engine.submit_assessment(
            assessment_id=request.assessment_id,
            user_answers=request.user_answers
        )
        
        return Response(
            success=True,
            message="测评已提交",
            data={
                "score": assessment.score,
                "correct_answers": assessment.correct_answers,
                "total_questions": assessment.total_questions,
                "mastery_after": assessment.mastery_after,
                "wrong_questions": assessment.wrong_questions,
                "error_analysis": assessment.error_analysis
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{assessment_id}", response_model=Response)
async def get_assessment(
    assessment_id: int,
    engine_manager: EngineManager = Depends(get_engine_manager)
):
    """获取测评记录详情"""
    assessment = engine_manager.assessment_engine.db.query(
        engine_manager.assessment_engine.db.model
    ).filter(
        engine_manager.assessment_engine.db.model.id == assessment_id
    ).first()
    
    from app.models.assessment import Assessment
    assessment = engine_manager.assessment_engine.db.query(Assessment).filter(
        Assessment.id == assessment_id
    ).first()
    
    if not assessment:
        raise HTTPException(status_code=404, detail="测评记录不存在")
    
    return Response(
        success=True,
        message="获取成功",
        data={
            "id": assessment.id,
            "assessment_type": assessment.assessment_type,
            "score": assessment.score,
            "total_questions": assessment.total_questions,
            "correct_answers": assessment.correct_answers,
            "mastery_before": assessment.mastery_before,
            "mastery_after": assessment.mastery_after
        }
    )


@router.get("/report/{report_student_id}", response_model=Response)
async def get_diagnostic_report(
    report_student_id: int,
    current_student_id: int = Depends(get_current_student_id),
    engine_manager: EngineManager = Depends(get_engine_manager)
):
    """
    生成诊断报告
    
    注意：此接口允许查看指定学生的报告，需要权限校验
    目前实现中限制只能查看自己的报告
    """
    # 权限校验：只能查看自己的报告
    if report_student_id != current_student_id:
        raise HTTPException(status_code=403, detail="无权查看其他用户的诊断报告")
    
    report = engine_manager.assessment_engine.generate_diagnostic_report(current_student_id)
    
    return Response(
        success=True,
        message="诊断报告生成成功",
        data=report
    )
