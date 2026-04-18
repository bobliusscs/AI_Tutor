"""
学习规划 API 路由
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from datetime import datetime
import json
import asyncio

from app.api.deps import get_engine_manager, get_current_student_id, get_db
from app.services.engine_manager import EngineManager
from app.schemas import GeneratePlanRequest, GenerateChapteredPlanRequest, PlanResponse, Response
from app.models.agent_session import AgentSession
from app.models.learning_stage import LearningStage
from app.models.motivation import ACHIEVEMENTS_CONFIG, ENCOURAGEMENT_TEMPLATES, Motivation
from app.models import StudyGoal, LearningPlan as LP, Lesson, Chapter, Section
from app.services.cancel_manager import request_cancel


router = APIRouter()


# ============ 取消学习计划生成 =============

@router.post("/cancel-generation", response_model=Response)
async def cancel_plan_generation():
    """
    取消当前正在进行的学习计划生成
    """
    try:
        request_cancel()
        return Response(
            success=True,
            message="已发送取消请求"
        )
    except Exception as e:
        return Response(
            success=False,
            message=f"取消失败: {str(e)}"
        )


# ============ PPT生成SSE流式进度接口 ===============

@router.post("/section/{section_id}/generate-ppt-stream")
async def generate_section_ppt_stream(
    section_id: int,
    engine_manager: EngineManager = Depends(get_engine_manager)
):
    """
    为节生成PPT内容（带SSE流式进度）

    ## 功能说明
    - 调用AI生成节PPT
    - 通过SSE实时推送生成进度
    - 支持取消操作
    """
    # 重置取消状态，确保新请求不受上次取消的影响
    from app.services.cancel_manager import reset_cancel
    reset_cancel()
    
    queue = asyncio.Queue()
    
    async def progress_callback(progress: int, message: str):
        """进度回调 - 将进度放入队列"""
        await queue.put({
            "type": "progress",
            "progress": progress,
            "message": message
        })
    
    async def event_generator():
        """SSE事件生成器"""
        try:
            # 发送初始进度
            yield f"data: {json.dumps({'type': 'progress', 'progress': 0, 'message': '正在准备生成PPT...'})}\n\n"
            
            # 在后台任务中运行PPT生成
            async def run_generation():
                import traceback
                try:
                    from app.services.cancel_manager import GenerationCancelledError
                    
                    print(f"[run_generation] 开始调用 generate_section_ppt，section_id={section_id}")
                    
                    ppt_content = await engine_manager.learning_plan_engine.generate_section_ppt(
                        section_id=section_id,
                        progress_callback=progress_callback
                    )
                    
                    slides = ppt_content.get("slides", [])
                    slide_count = len(slides)
                    
                    await queue.put({
                        "type": "complete",
                        "success": True,
                        "data": {
                            "section_id": section_id,
                            "ppt_generated": True,
                            "slide_count": slide_count,
                            "slides": slides
                        }
                    })
                except GenerationCancelledError as e:
                    print(f"PPT生成被用户取消: {e}")
                    print(f"[run_generation] GenerationCancelledError 调用栈: {traceback.format_exc()}")
                    await queue.put({
                        "type": "cancelled",
                        "status": "cancelled",
                        "message": "用户取消了生成"
                    })
                except Exception as e:
                    await queue.put({
                        "type": "error",
                        "success": False,
                        "message": str(e)
                    })
            
            # 启动后台生成任务
            task = asyncio.create_task(run_generation())
            
            # 从队列中读取并发送事件
            while not task.done() or not queue.empty():
                try:
                    data = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
                except asyncio.TimeoutError:
                    # 发送心跳保持连接
                    yield f": heartbeat\n\n"
                    continue
                
                if data.get("type") in ("complete", "error", "cancelled"):
                    break
            
            # 确保任务完成
            if not task.done():
                task.cancel()
                
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'success': False, 'message': str(e)})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.post("/generate", response_model=Response)
async def generate_learning_plan(
    request: GeneratePlanRequest,
    current_student_id: int = Depends(get_current_student_id),
    engine_manager: EngineManager = Depends(get_engine_manager)
):
    """
    生成学习计划
    
    ## 功能说明
    - 基于知识依赖关系自动生成学习顺序
    - 根据每周可用时间智能排课
    - 创建结构化课时内容
    
    ## 示例
    ```json
    {
      "graph_id": 1,
      "weekly_hours": 5.0
    }
    ```
    """
    try:
        plan = await engine_manager.learning_plan_engine.generate_plan(
            student_id=current_student_id,
            graph_id=request.graph_id,
            study_goal_id=request.study_goal_id,
            weekly_hours=request.weekly_hours,
            title=request.title,
            description=request.description
        )
        
        return Response(
            success=True,
            message="学习计划生成成功",
            data={
                "plan_id": plan.id,
                "title": plan.title,
                "total_lessons": plan.total_lessons,
                "estimated_weeks": (plan.end_date - plan.start_date).days // 7
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{plan_id}", response_model=Response)
async def delete_learning_plan(
    plan_id: int,
    current_student_id: int = Depends(get_current_student_id),
    db: Session = Depends(get_db)
):
    """删除学习计划"""
    # 查找学习计划
    plan = db.query(LP).filter(LP.id == plan_id).first()
    
    if not plan:
        raise HTTPException(status_code=404, detail="学习计划不存在")
    
    # 验证权限（只能删除自己的计划）
    if plan.student_id != current_student_id:
        raise HTTPException(status_code=403, detail="无权删除此学习计划")
    
    try:
        # 删除关联的课时（先删课时，因为它们有关联）
        db.query(Lesson).filter(Lesson.plan_id == plan_id).delete()
        
        # 删除关联的节（级联删除课时后，节没有课时关联）
        db.query(Section).filter(Section.plan_id == plan_id).delete()
        
        # 删除关联的章节
        db.query(Chapter).filter(Chapter.plan_id == plan_id).delete()
        
        # 删除学习计划
        db.delete(plan)
        db.commit()
        
        return Response(
            success=True,
            message="学习计划删除成功"
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


@router.post("/{plan_id}/reset-progress", response_model=Response)
async def reset_learning_progress(
    plan_id: int,
    current_student_id: int = Depends(get_current_student_id),
    db: Session = Depends(get_db)
):
    """
    重置学习进度
    将所有课时的完成状态重置为未完成，但保留学习计划结构
    """
    # 查找学习计划
    plan = db.query(LP).filter(LP.id == plan_id).first()
    
    if not plan:
        raise HTTPException(status_code=404, detail="学习计划不存在")
    
    # 验证权限
    if plan.student_id != current_student_id:
        raise HTTPException(status_code=403, detail="无权操作此学习计划")
    
    try:
        # 重置所有课时为未完成状态
        db.query(Lesson).filter(Lesson.plan_id == plan_id).update({
            Lesson.is_completed: False,
            Lesson.completed_at: None
        })
        
        # 重置学习计划的完成课时数
        plan.completed_lessons = 0
        plan.status = "active"
        
        db.commit()
        
        return Response(
            success=True,
            message="学习进度已重置"
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"重置失败: {str(e)}")


@router.get("/{plan_id}", response_model=Response)
async def get_learning_plan(
    plan_id: int,
    engine_manager: EngineManager = Depends(get_engine_manager)
):
    """获取学习计划详情"""
    plan = engine_manager.learning_plan_engine.get_plan(plan_id)
    
    if not plan:
        raise HTTPException(status_code=404, detail="学习计划不存在")
    
    return Response(
        success=True,
        message="获取成功",
        data={
            "id": plan.id,
            "title": plan.title,
            "status": plan.status,
            "total_lessons": plan.total_lessons,
            "completed_lessons": plan.completed_lessons,
            "progress": f"{plan.completed_lessons}/{plan.total_lessons}"
        }
    )


@router.get("/{plan_id}/lessons", response_model=Response)
async def get_plan_lessons(
    plan_id: int,
    engine_manager: EngineManager = Depends(get_engine_manager)
):
    """获取计划的所有课时"""
    lessons = engine_manager.learning_plan_engine.get_lessons(plan_id)
    
    return Response(
        success=True,
        message="获取成功",
        data=[
            {
                "id": lesson.id,
                "lesson_number": lesson.lesson_number,
                "title": lesson.title,
                "estimated_minutes": lesson.estimated_minutes,
                "is_completed": lesson.is_completed
            }
            for lesson in lessons
        ]
    )


@router.get("/{plan_id}/next-lesson", response_model=Response)
async def get_next_lesson(
    plan_id: int,
    engine_manager: EngineManager = Depends(get_engine_manager)
):
    """获取下一个未完成的课时"""
    lesson = engine_manager.learning_plan_engine.get_next_lesson(plan_id)
    
    if not lesson:
        return Response(
            success=True,
            message="已完成所有课时",
            data=None
        )
    
    return Response(
        success=True,
        message="获取成功",
        data={
            "id": lesson.id,
            "lesson_number": lesson.lesson_number,
            "title": lesson.title
        }
    )


@router.post("/lesson/{lesson_id}/complete", response_model=Response)
async def complete_lesson(
    lesson_id: int,
    engine_manager: EngineManager = Depends(get_engine_manager)
):
    """
    标记课时完成

    - 课时不存在时返回 success=False, message="课时不存在"
    - 课时已完成时返回 success=True, message="课时已完成"（幂等处理）
    - 正常完成时返回 success=True, message="课时已标记完成"
    """
    result = engine_manager.learning_plan_engine.complete_lesson(lesson_id)

    # 课时不存在
    if result is None:
        return Response(
            success=False,
            message="课时不存在",
            data={"lesson_id": lesson_id}
        )

    # 课时已完成（幂等处理）
    if result.get("already_completed"):
        return Response(
            success=True,
            message="课时已完成",
            data={
                "lesson_id": lesson_id,
                "already_completed": True,
                "all_completed": result.get("all_completed", False)
            }
        )

    # 正常完成
    return Response(
        success=True,
        message="课时已标记完成",
        data={
            "lesson_id": lesson_id,
            "already_completed": False,
            "all_completed": result.get("all_completed", False)
        }
    )


@router.get("/current-lesson/{goal_id}", response_model=Response)
async def get_current_lesson(
    goal_id: int,
    db: Session = Depends(get_db),
    current_student_id: int = Depends(get_current_student_id)
):
    """获取指定学习目标的当前课时"""
    # 验证学习目标
    goal = db.query(StudyGoal).filter(
        StudyGoal.id == goal_id,
        StudyGoal.student_id == current_student_id
    ).first()

    if not goal:
        raise HTTPException(status_code=404, detail="学习目标不存在")

    # 获取学习计划
    plan = db.query(LP).filter(LP.study_goal_id == goal_id).first()

    if not plan:
        return Response(
            success=True,
            message="暂无学习计划",
            data=None
        )

    # 获取当前课时
    lesson = db.query(Lesson).filter(
        Lesson.plan_id == plan.id,
        Lesson.is_completed == False
    ).order_by(Lesson.lesson_number).first()

    if not lesson:
        return Response(
            success=True,
            message="所有课时已完成",
            data={
                "goal_id": goal_id,
                "goal_title": goal.title,
                "completed": True
            }
        )

    return Response(
        success=True,
        message="获取成功",
        data={
            "goal_id": goal_id,
            "goal_title": goal.title,
            "lesson_id": lesson.id,
            "lesson_title": lesson.title,
            "lesson_number": lesson.lesson_number,
            "estimated_minutes": lesson.estimated_minutes,
            "completed_lessons": plan.completed_lessons,
            "total_lessons": plan.total_lessons
        }
    )


@router.post("/milestone/start", response_model=Response)
async def start_learning_milestone(
    goal_id: int,
    lesson_id: int = None,
    db: Session = Depends(get_db),
    current_student_id: int = Depends(get_current_student_id)
):
    """
    开始学习里程碑（复用 LearningStage 模型）

    1. 创建/更新 AgentSession
    2. 创建 LearningStage 记录
    3. 返回当前课时内容
    """
    # 验证学习目标
    goal = db.query(StudyGoal).filter(
        StudyGoal.id == goal_id,
        StudyGoal.student_id == current_student_id
    ).first()

    if not goal:
        raise HTTPException(status_code=404, detail="学习目标不存在")

    # 获取学习计划
    plan = db.query(LP).filter(LP.study_goal_id == goal_id).first()

    if not plan:
        raise HTTPException(status_code=400, detail="暂无学习计划")

    # 获取当前课时
    if not lesson_id:
        lesson = db.query(Lesson).filter(
            Lesson.plan_id == plan.id,
            Lesson.is_completed == False
        ).order_by(Lesson.lesson_number).first()
    else:
        lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()

    if not lesson:
        return Response(
            success=True,
            message="所有课时已完成",
            data={"completed": True, "goal_id": goal_id}
        )

    # 创建/更新 AgentSession
    session = db.query(AgentSession).filter(
        AgentSession.student_id == current_student_id,
        AgentSession.study_goal_id == goal_id,
        AgentSession.end_time.is_(None)
    ).first()

    if session:
        session.current_stage = f"learning_lesson_{lesson.id}"
        session.current_lesson_id = lesson.id
    else:
        session = AgentSession(
            student_id=current_student_id,
            study_goal_id=goal_id,
            current_stage=f"learning_lesson_{lesson.id}",
            current_lesson_id=lesson.id
        )
        db.add(session)

    db.commit()
    db.refresh(session)

    # 创建 LearningStage 记录
    stage = LearningStage(
        session_id=session.id,
        stage_type="learning",
        stage_name=lesson.title,
        lesson_id=lesson.id,
        status="in_progress"
    )
    db.add(stage)
    db.commit()
    db.refresh(stage)

    return Response(
        success=True,
        message="开始学习里程碑",
        data={
            "session_id": session.id,
            "stage_id": stage.id,
            "lesson_id": lesson.id,
            "lesson_title": lesson.title,
            "lesson_number": lesson.lesson_number,
            "content": lesson.content
        }
    )


def _generate_encouragement(score: float) -> str:
    """根据分数生成鼓励语"""
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


def _check_achievements(db: Session, student_id: int, goal_id: int, test_score: float) -> list:
    """检查并解锁成就"""
    unlocked = []

    # 获取当前已解锁的成就
    existing = db.query(Motivation).filter(
        Motivation.student_id == student_id,
        Motivation.motivation_type == "achievement"
    ).all()
    existing_titles = {m.title for m in existing}

    # 检查各成就条件
    goal = db.query(StudyGoal).filter(StudyGoal.id == goal_id).first()

    # 满分达人
    if "满分达人" not in existing_titles and test_score >= 90:
        unlocked.append({"title": "满分达人", "icon": "trophy", "description": "测试获得90分以上"})

    # 初出茅庐
    if "初出茅庐" not in existing_titles and goal and goal.completed_lessons >= 1:
        unlocked.append({"title": "初出茅庐", "icon": "rocket", "description": "完成第一个课时"})

    # 持之以恒
    if "持之以恒" not in existing_titles and goal and goal.completed_lessons >= 10:
        unlocked.append({"title": "持之以恒", "icon": "medal", "description": "完成10个课时"})

    # 保存新解锁的成就
    for achievement in unlocked:
        motivation = Motivation(
            student_id=student_id,
            motivation_type="achievement",
            title=achievement["title"],
            icon=achievement["icon"],
            content=achievement["description"],
            trigger="achievement_unlock",
            value=test_score
        )
        db.add(motivation)

    if unlocked:
        db.commit()

    return unlocked


@router.post("/milestone/complete", response_model=Response)
async def complete_milestone(
    milestone_id: int,
    test_score: float = 0,
    test_answers: list = None,
    db: Session = Depends(get_db),
    current_student_id: int = Depends(get_current_student_id)
):
    """
    完成学习里程碑（复用 Motivation 模型）

    1. 更新 LearningStage
    2. 生成激励（调用 Motivation 逻辑）
    3. 检查成就解锁
    4. 返回激励内容
    """
    # 获取里程碑
    stage = db.query(LearningStage).filter(LearningStage.id == milestone_id).first()

    if not stage:
        raise HTTPException(status_code=404, detail="里程碑不存在")

    # 更新里程碑状态
    stage.test_score = test_score
    stage.test_answers = json.dumps(test_answers or [], ensure_ascii=False)
    stage.completed_at = datetime.utcnow()
    stage.status = "completed"

    # 如果有课时，根据分数决定是否自动标记完成
    # 分数 >= 60 才自动标记完成，否则需要用户手动确认
    AUTO_COMPLETE_THRESHOLD = 60
    auto_completed = False
    
    if stage.lesson_id:
        lesson = db.query(Lesson).filter(Lesson.id == stage.lesson_id).first()
        if lesson:
            # 只有分数达到60分才自动标记完成
            if test_score >= AUTO_COMPLETE_THRESHOLD and not lesson.is_completed:
                lesson.is_completed = True
                lesson.completed_at = datetime.utcnow()
                auto_completed = True
                
                # 更新学习计划进度
                plan = db.query(LP).filter(LP.id == lesson.plan_id).first()
                if plan:
                    plan.completed_lessons = db.query(Lesson).filter(
                        Lesson.plan_id == plan.id,
                        Lesson.is_completed == True
                    ).count()

                # 更新学习目标
                goal = db.query(StudyGoal).filter(StudyGoal.id == plan.study_goal_id).first()
                if goal:
                    goal.completed_lessons = plan.completed_lessons

    db.commit()

    # 获取学习目标ID
    goal_id = None
    if stage.lesson_id:
        lesson = db.query(Lesson).filter(Lesson.id == stage.lesson_id).first()
        if lesson:
            plan = db.query(LP).filter(LP.id == lesson.plan_id).first()
            if plan:
                goal_id = plan.study_goal_id

    # 生成鼓励语
    encouragement = _generate_encouragement(test_score)

    # 检查成就
    unlocked_achievements = []
    if goal_id:
        unlocked_achievements = _check_achievements(db, current_student_id, goal_id, test_score)

    return Response(
        success=True,
        message="里程碑完成",
        data={
            "milestone_id": milestone_id,
            "score": test_score,
            "encouragement": encouragement,
            "achievements": unlocked_achievements,
            "auto_completed": auto_completed,  # 是否自动完成（分数>=60时）
            "need_manual_confirm": not auto_completed,  # 是否需要手动确认
            "next_lesson": _get_next_lesson_info(db, goal_id) if goal_id else None
        }
    )


def _get_next_lesson_info(db: Session, goal_id: int) -> dict:
    """获取下一个课时信息"""
    plan = db.query(LP).filter(LP.study_goal_id == goal_id).first()
    if not plan:
        return None

    next_lesson = db.query(Lesson).filter(
        Lesson.plan_id == plan.id,
        Lesson.is_completed == False
    ).order_by(Lesson.lesson_number).first()

    if not next_lesson:
        return {"completed": True, "message": "所有课时已完成"}

    return {
        "completed": False,
        "lesson_id": next_lesson.id,
        "lesson_title": next_lesson.title,
        "lesson_number": next_lesson.lesson_number
    }


# ==================== 章-节结构学习计划 API ====================

@router.post("/generate-chaptered-stream")
async def generate_chaptered_learning_plan_stream(
    request: GenerateChapteredPlanRequest,
    current_student_id: int = Depends(get_current_student_id),
    engine_manager: EngineManager = Depends(get_engine_manager)
):
    """
    生成带章节结构的学习计划（AI驱动）- SSE流式版本
    
    使用 Server-Sent Events 推送进度更新
    """
    # 重置取消状态，确保新请求不受上次取消的影响
    from app.services.cancel_manager import reset_cancel
    reset_cancel()
    
    from fastapi.responses import StreamingResponse
    import json
    import asyncio
    
    # 使用 asyncio.Queue 来传递进度
    queue = asyncio.Queue()
    
    async def progress_callback(progress: int, message: str):
        """进度回调 - 将进度放入队列"""
        await queue.put({"type": "progress", "progress": progress, "message": message})
    
    async def event_generator():
        """SSE 事件生成器"""
        try:
            # 发送初始进度
            yield f"data: {json.dumps({'type': 'progress', 'progress': 0, 'message': '正在准备生成学习计划...'})}\n\n"
            
            # 如果已有学习计划，先删除
            if request.study_goal_id:
                from app.models import StudyGoal, LearningPlan as LP, Lesson, Chapter, Section
                db = engine_manager.db
                goal = db.query(StudyGoal).filter(StudyGoal.id == request.study_goal_id).first()
                # 查询关联的学习计划
                existing_plan = db.query(LP).filter(LP.study_goal_id == request.study_goal_id).first()
                if existing_plan:
                    try:
                        db.query(Lesson).filter(Lesson.plan_id == existing_plan.id).delete()
                        db.query(Section).filter(Section.plan_id == existing_plan.id).delete()
                        db.query(Chapter).filter(Chapter.plan_id == existing_plan.id).delete()
                        db.delete(existing_plan)
                        db.commit()
                        await queue.put({"type": "progress", "progress": 2, "message": "已删除旧学习计划"})
                    except Exception as e:
                        print(f"删除旧计划失败: {e}")
            
            yield f"data: {json.dumps({'type': 'progress', 'progress': 5, 'message': '正在获取知识图谱...'})}\n\n"
            
            # 在后台任务中运行学习计划生成
            async def run_generation():
                try:
                    from app.services.cancel_manager import GenerationCancelledError
                    plan = await engine_manager.learning_plan_engine.generate_chaptered_plan(
                        student_id=current_student_id,
                        graph_id=request.graph_id,
                        study_goal_id=request.study_goal_id,
                        weekly_hours=request.weekly_hours,
                        max_chapters=request.max_chapters,
                        max_sections_per_chapter=request.max_sections_per_chapter,
                        title=request.title,
                        description=request.description,
                        progress_callback=progress_callback
                    )
                    
                    chapters = engine_manager.learning_plan_engine.get_chapters(plan.id)
                    chapter_count = len(chapters)
                    
                    await queue.put({
                        "type": "complete",
                        "success": True,
                        "data": {
                            "plan_id": plan.id,
                            "title": plan.title,
                            "total_lessons": plan.total_lessons,
                            "chapter_count": chapter_count,
                            "estimated_weeks": (plan.end_date - plan.start_date).days // 7 if plan.end_date and plan.start_date else 0
                        }
                    })
                except GenerationCancelledError as e:
                    print(f"学习计划生成被用户取消: {e}")
                    await queue.put({
                        "type": "cancelled",
                        "status": "cancelled",
                        "message": "用户取消了生成"
                    })
                except Exception as e:
                    await queue.put({"type": "error", "success": False, "message": str(e)})
            
            # 启动后台生成任务
            task = asyncio.create_task(run_generation())
            
            # 从队列中读取并发送事件
            while not task.done() or not queue.empty():
                try:
                    data = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
                except asyncio.TimeoutError:
                    # 发送心跳保持连接
                    yield f": heartbeat\n\n"
                    continue
                
                if data.get("type") in ("complete", "error", "cancelled"):
                    break
            
            # 确保任务完成
            if not task.done():
                task.cancel()
                
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'success': False, 'message': str(e)})}\n\n"
                
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.post("/generate-chaptered", response_model=Response)
async def generate_chaptered_learning_plan(
    request: GenerateChapteredPlanRequest,
    current_student_id: int = Depends(get_current_student_id),
    engine_manager: EngineManager = Depends(get_engine_manager)
):
    """
    生成带章节结构的学习计划（AI驱动）

    ## 功能说明
    - 基于知识图谱自动生成章-节层级结构
    - AI根据认知规律组织知识点
    - 支持最多14章、每章8节

    ## 示例
    ```json
    {
      "graph_id": 1,
      "weekly_hours": 5.0,
      "max_chapters": 12,
      "max_sections_per_chapter": 6
    }
    ```
    """
    try:
        plan = await engine_manager.learning_plan_engine.generate_chaptered_plan(
            student_id=current_student_id,
            graph_id=request.graph_id,
            study_goal_id=request.study_goal_id,
            weekly_hours=request.weekly_hours,
            max_chapters=request.max_chapters,
            max_sections_per_chapter=request.max_sections_per_chapter,
            title=request.title,
            description=request.description
        )

        # 获取章节数量
        chapters = engine_manager.learning_plan_engine.get_chapters(plan.id)
        chapter_count = len(chapters)

        return Response(
            success=True,
            message="章节式学习计划生成成功",
            data={
                "plan_id": plan.id,
                "title": plan.title,
                "total_lessons": plan.total_lessons,
                "chapter_count": chapter_count,
                "estimated_weeks": (plan.end_date - plan.start_date).days // 7 if plan.end_date and plan.start_date else 0
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{plan_id}/structure", response_model=Response)
async def get_plan_structure(
    plan_id: int,
    engine_manager: EngineManager = Depends(get_engine_manager)
):
    """
    获取学习计划的完整章-节-课时结构

    ## 功能说明
    - 返回完整的层级结构数据
    - 包含章节、节、课时信息
    - 显示PPT生成状态
    """
    structure = engine_manager.learning_plan_engine.get_plan_structure(plan_id)

    if not structure:
        raise HTTPException(status_code=404, detail="学习计划不存在")

    return Response(
        success=True,
        message="获取学习计划结构成功",
        data=structure
    )


@router.get("/chapter/{chapter_id}/ppt", response_model=Response)
async def get_chapter_ppt(
    chapter_id: int,
    engine_manager: EngineManager = Depends(get_engine_manager)
):
    """
    获取章节PPT内容

    ## 功能说明
    - 返回已生成的PPT幻灯片列表
    - 如果尚未生成，返回生成状态
    """
    ppt_data = engine_manager.learning_plan_engine.get_chapter_ppt(chapter_id)

    if not ppt_data:
        raise HTTPException(status_code=404, detail="章节不存在")

    return Response(
        success=True,
        message="获取章节PPT成功" if ppt_data["ppt_generated"] else "PPT尚未生成",
        data=ppt_data
    )


@router.post("/chapter/{chapter_id}/generate-ppt", response_model=Response)
async def generate_chapter_ppt(
    chapter_id: int,
    engine_manager: EngineManager = Depends(get_engine_manager)
):
    """
    为章节生成PPT内容

    ## 功能说明
    - 调用AI生成章节PPT
    - 包含章节内所有节的内容概览
    - 返回幻灯片列表
    """
    try:
        ppt_content = await engine_manager.learning_plan_engine.generate_chapter_ppt(chapter_id)

        return Response(
            success=True,
            message="章节PPT生成成功",
            data={
                "chapter_id": chapter_id,
                "ppt_generated": True,
                "slide_count": len(ppt_content.get("slides", [])),
                "slides": ppt_content.get("slides", [])
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/section/{section_id}/ppt", response_model=Response)
async def get_section_ppt(
    section_id: int,
    engine_manager: EngineManager = Depends(get_engine_manager)
):
    """
    获取节PPT内容

    ## 功能说明
    - 返回已生成的PPT幻灯片列表
    - 如果尚未生成，返回生成状态
    """
    ppt_data = engine_manager.learning_plan_engine.get_section_ppt(section_id)

    if not ppt_data:
        raise HTTPException(status_code=404, detail="节不存在")

    return Response(
        success=True,
        message="获取节PPT成功" if ppt_data["ppt_generated"] else "PPT尚未生成",
        data=ppt_data
    )


@router.post("/section/{section_id}/generate-ppt", response_model=Response)
async def generate_section_ppt(
    section_id: int,
    engine_manager: EngineManager = Depends(get_engine_manager)
):
    """
    为节生成PPT内容（增强稳定性版）

    ## 功能说明
    - 调用AI生成PPT
    - 聚焦该节的知识点讲解
    - 返回幻灯片列表
    - 支持自动重试和增强的JSON解析
    - 错误时返回success=false，不抛出异常以保证批量处理稳定性
    """
    try:
        print(f"[generate_section_ppt] 开始为小节 {section_id} 生成PPT...")
        ppt_content = await engine_manager.learning_plan_engine.generate_section_ppt(section_id)
        print(f"[generate_section_ppt] 小节 {section_id} PPT生成成功")

        # 检查slides是否为空
        slides = ppt_content.get("slides", [])
        slide_count = len(slides)
        
        if slide_count == 0:
            # slides为空但AI调用成功（可能是解析问题）
            return Response(
                success=True,  # 保持success，因为API调用本身成功了
                message="PPT生成完成，但内容解析异常",
                data={
                    "section_id": section_id,
                    "ppt_generated": True,
                    "slide_count": 0,
                    "slides": [],
                    "warning": ppt_content.get("error", "AI返回内容为空")
                }
            )

        return Response(
            success=True,
            message="节PPT生成成功",
            data={
                "section_id": section_id,
                "ppt_generated": True,
                "slide_count": slide_count,
                "slides": slides
            }
        )
    except ValueError as e:
        # 业务逻辑错误（如节不存在）
        print(f"[generate_section_ppt] 业务错误: {str(e)}")
        # 返回错误响应而不是抛出异常，保证批量处理继续
        return Response(
            success=False,
            message=f"节不存在或参数错误: {str(e)}",
            data={
                "section_id": section_id,
                "ppt_generated": False,
                "error": str(e)
            }
        )
    except Exception as e:
        # 记录详细错误日志
        import traceback
        error_detail = str(e)
        print(f"[generate_section_ppt] API层错误: {error_detail}")
        print(traceback.format_exc())
        # 返回错误响应而不是抛出HTTPException，保证批量处理稳定性
        return Response(
            success=False,
            message=f"PPT生成失败: {error_detail}",
            data={
                "section_id": section_id,
                "ppt_generated": False,
                "error": error_detail
            }
        )


@router.get("/{plan_id}/chapters", response_model=Response)
async def get_plan_chapters(
    plan_id: int,
    engine_manager: EngineManager = Depends(get_engine_manager)
):
    """
    获取学习计划的所有章节（不含节详情）
    """
    chapters = engine_manager.learning_plan_engine.get_chapters(plan_id)

    return Response(
        success=True,
        message="获取章节列表成功",
        data=[
            {
                "id": ch.id,
                "chapter_number": ch.chapter_number,
                "title": ch.title,
                "description": ch.description,
                "estimated_minutes": ch.estimated_minutes,
                "ppt_generated": ch.ppt_generated
            }
            for ch in chapters
        ]
    )


@router.get("/chapter/{chapter_id}/sections", response_model=Response)
async def get_chapter_sections(
    chapter_id: int,
    engine_manager: EngineManager = Depends(get_engine_manager)
):
    """
    获取章节的所有节
    """
    sections = engine_manager.learning_plan_engine.get_sections(chapter_id)

    return Response(
        success=True,
        message="获取节列表成功",
        data=[
            {
                "id": sec.id,
                "section_number": sec.section_number,
                "title": sec.title,
                "description": sec.description,
                "knowledge_point_ids": sec.knowledge_point_ids or [],
                "key_concepts": sec.key_concepts or [],
                "estimated_minutes": sec.estimated_minutes,
                "ppt_generated": sec.ppt_generated
            }
            for sec in sections
        ]
    )


# ============ 学习进度重置 ==============

@router.post("/goal/{goal_id}/reset-progress", response_model=Response)
async def reset_goal_progress(
    goal_id: int,
    db: Session = Depends(get_db),
    current_student_id: int = Depends(get_current_student_id)
):
    """
    重置学习目标的学习进度

    重置内容：
    - 所有课时恢复为未完成状态
    - 学习计划完成课时数归零
    - 学习目标完成课时数归零
    - 重置Agent会话的当前课时位置
    """
    try:
        # 验证学习目标属于当前学生
        goal = db.query(StudyGoal).filter(
            StudyGoal.id == goal_id,
            StudyGoal.student_id == current_student_id
        ).first()

        if not goal:
            raise HTTPException(status_code=404, detail="学习目标不存在")

        # 获取关联的学习计划
        plan = db.query(LP).filter(LP.study_goal_id == goal_id).first()

        # 重置所有课时为未完成
        if plan:
            lessons = db.query(Lesson).filter(Lesson.plan_id == plan.id).all()
            for lesson in lessons:
                lesson.is_completed = False
                lesson.completed_at = None

            # 重置学习计划完成数
            plan.completed_lessons = 0
            plan.status = "active"

        # 重置学习目标完成数
        goal.completed_lessons = 0
        goal.mastered_points = 0

        # 重置或删除相关的Agent会话
        sessions = db.query(AgentSession).filter(
            AgentSession.study_goal_id == goal_id,
            AgentSession.student_id == current_student_id
        ).all()

        for session in sessions:
            session.current_lesson_id = None
            session.current_stage = "init"
            session.conversation_summary = None
            session.total_messages = 0
            session.total_tests_taken = 0
            session.avg_score = 0.0

        db.commit()

        return Response(
            success=True,
            message=f"学习进度已重置：目标「{goal.title}」的所有课时已恢复为未完成状态"
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        return Response(
            success=False,
            message=f"重置失败: {str(e)}"
        )


@router.post("/reset-all-progress", response_model=Response)
async def reset_all_progress(
    db: Session = Depends(get_db),
    current_student_id: int = Depends(get_current_student_id)
):
    """
    重置该学生所有学习目标的学习进度

    警告：此操作不可逆！
    """
    try:
        # 获取该学生的所有学习目标
        goals = db.query(StudyGoal).filter(
            StudyGoal.student_id == current_student_id,
            StudyGoal.status == "active"
        ).all()

        if not goals:
            return Response(
                success=True,
                message="没有需要重置的学习目标"
            )

        reset_count = 0
        for goal in goals:
            # 获取关联的学习计划
            plan = db.query(LP).filter(LP.study_goal_id == goal.id).first()

            # 重置所有课时
            if plan:
                lessons = db.query(Lesson).filter(Lesson.plan_id == plan.id).all()
                for lesson in lessons:
                    lesson.is_completed = False
                    lesson.completed_at = None

                plan.completed_lessons = 0
                plan.status = "active"

            # 重置学习目标
            goal.completed_lessons = 0
            goal.mastered_points = 0

            # 重置Agent会话
            sessions = db.query(AgentSession).filter(
                AgentSession.study_goal_id == goal.id,
                AgentSession.student_id == current_student_id
            ).all()

            for session in sessions:
                session.current_lesson_id = None
                session.current_stage = "init"
                session.conversation_summary = None
                session.total_messages = 0
                session.total_tests_taken = 0
                session.avg_score = 0.0

            reset_count += 1

        db.commit()

        return Response(
            success=True,
            message=f"已重置 {reset_count} 个学习目标的学习进度"
        )

    except Exception as e:
        db.rollback()
        return Response(
            success=False,
            message=f"重置失败: {str(e)}"
        )
