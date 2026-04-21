"""
课时学习 API 路由
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_engine_manager, get_db
from app.services.engine_manager import EngineManager
from app.schemas import LessonInteractRequest, ExerciseSubmitRequest, Response


router = APIRouter()


@router.get("/{lesson_id}", response_model=Response)
async def get_lesson(
    lesson_id: int,
    engine_manager: EngineManager = Depends(get_engine_manager)
):
    """获取课时详情"""
    lesson = engine_manager.lesson_engine.get_lesson(lesson_id)
    
    if not lesson:
        raise HTTPException(status_code=404, detail="课时不存在")
    
    return Response(
        success=True,
        message="获取成功",
        data={
            "id": lesson.id,
            "title": lesson.title,
            "lesson_number": lesson.lesson_number,
            "estimated_minutes": lesson.estimated_minutes,
            "is_completed": lesson.is_completed
        }
    )


@router.post("/{lesson_id}/interact", response_model=Response)
async def interact_with_lesson(
    lesson_id: int,
    request: LessonInteractRequest,
    engine_manager: EngineManager = Depends(get_engine_manager)
):
    """
    与课时内容进行交互式对话
    
    ## 功能说明
    - 分段呈现课时内容（引入→讲解→示例→练习→总结）
    - 支持学生提问和反馈
    - 根据学生状态推进教学流程
    """
    result = await engine_manager.lesson_engine.interact_with_student(
        lesson_id=lesson_id,
        student_message=request.student_message,
        current_section=request.current_section
    )
    
    return Response(
        success=True,
        message="交互成功",
        data=result
    )


@router.post("/{lesson_id}/exercise", response_model=Response)
async def submit_exercise(
    lesson_id: int,
    request: ExerciseSubmitRequest,
    engine_manager: EngineManager = Depends(get_engine_manager)
):
    """提交练习答案"""
    result = engine_manager.lesson_engine.evaluate_exercise(
        lesson_id=lesson_id,
        exercise_index=request.exercise_index,
        user_answer=request.user_answer
    )
    
    return Response(
        success=True,
        message="练习已批改",
        data=result
    )


@router.get("/{lesson_id}/content", response_model=Response)
async def get_lesson_content(
    lesson_id: int,
    section: str = "all",
    engine_manager: EngineManager = Depends(get_engine_manager)
):
    """
    获取课时内容（可指定章节）
    
    ## 参数
    - section: introduction/explanation/example/exercises/summary/all
    """
    lesson = engine_manager.lesson_engine.get_lesson(lesson_id)
    
    if not lesson:
        raise HTTPException(status_code=404, detail="课时不存在")
    
    content = engine_manager.lesson_engine.format_lesson_for_chat(lesson, section)
    
    return Response(
        success=True,
        message="获取成功",
        data=content
    )


@router.post("/{lesson_id}/regenerate", response_model=Response)
async def regenerate_lesson_content(
    lesson_id: int,
    db: Session = Depends(get_db),
    engine_manager: EngineManager = Depends(get_engine_manager)
):
    """
    重新生成课时内容
    
    ## 功能说明
    - 使用 AI 重新生成课时的详细内容（引入、讲解、示例、练习、总结）
    - 用于修复内容简略或缺失的课时
    """
    from app.models.learning_plan import Lesson
    from app.models.knowledge_graph import KnowledgeGraph
    from app.models.study_goal import StudyGoal
    import json
    
    # 获取课时
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="课时不存在")
    
    # 获取关联的学习计划和学习目标
    plan = lesson.learning_plan  # 使用正确的关系名
    if not plan:
        raise HTTPException(status_code=400, detail="课时未关联学习计划")
    
    # 获取知识图谱中的节点信息
    knowledge_graph = db.query(KnowledgeGraph).filter(KnowledgeGraph.id == plan.graph_id).first()
    if not knowledge_graph:
        raise HTTPException(status_code=400, detail="关联的知识图谱不存在")
    
    nodes = json.loads(knowledge_graph.nodes) if isinstance(knowledge_graph.nodes, str) else knowledge_graph.nodes
    
    # 找到当前课时对应的知识点
    node = None
    for n in nodes:
        if n.get("id") == lesson.knowledge_point_id:
            node = n
            break
    
    if not node:
        raise HTTPException(status_code=400, detail="课时关联的知识点不存在")
    
    # 获取学习目标信息
    study_goal_title = None
    study_goal_description = None
    if plan.study_goal_id:
        study_goal = db.query(StudyGoal).filter(StudyGoal.id == plan.study_goal_id).first()
        if study_goal:
            study_goal_title = study_goal.title
            study_goal_description = study_goal.description
    
    try:
        # 调用 AI 重新生成课时内容（PPT幻灯片格式）
        lesson_data = await engine_manager.ai_provider.generate_lesson_content(
            knowledge_point=node,
            student_level="beginner",
            study_goal_title=study_goal_title,
            study_goal_description=study_goal_description
        )
        
        # 提取幻灯片数据
        slides = lesson_data.get("slides", [])
        
        # 从幻灯片中提取各部分内容
        introduction = ""
        explanation = ""
        example = ""
        summary = ""
        exercises = []
        
        for slide in slides:
            slide_type = slide.get("type", "")
            if slide_type == "cover":
                introduction = slide.get("content", "")
            elif slide_type == "content" and slide.get("title") == "课程引入":
                introduction = slide.get("content", "")
            elif slide_type == "content" and slide.get("title") == "核心讲解":
                explanation = slide.get("content", "")
            elif slide_type == "example":
                example = slide.get("content", "")
            elif slide_type == "exercise":
                exercises = slide.get("questions", [])
            elif slide_type == "summary":
                summary = slide.get("content", "")
        
        # 如果没有提取到讲解内容，使用第一个内容幻灯片
        if not explanation:
            for slide in slides:
                if slide.get("type") == "content":
                    explanation = slide.get("content", "")
                    break
        
        # 更新课时内容
        lesson.introduction = introduction
        lesson.explanation = explanation
        lesson.example = example
        lesson.exercises = json.dumps(exercises, ensure_ascii=False)
        lesson.summary = summary
        
        db.commit()
        db.refresh(lesson)
        
        return Response(
            success=True,
            message="课时内容重新生成成功",
            data={
                "lesson_id": lesson.id,
                "title": lesson.title,
                "slides_count": len(slides),
                "introduction_length": len(introduction),
                "explanation_length": len(explanation),
                "example_length": len(example),
                "summary_length": len(summary)
            }
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"重新生成课时内容失败: {str(e)}")
