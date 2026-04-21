"""
学习目标管理 API 路由
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.api.deps import get_current_student_id
from app.schemas import Response
from app.models.study_goal import StudyGoal, StudyGoalStatus
from app.models.knowledge_graph import KnowledgeGraph
from app.models.learning_plan import LearningPlan, Lesson
from app.models.node_mastery import NodeMastery


router = APIRouter()


# ==================== 学习目标上下文 Skill 函数 ====================

def _get_mastery_level_name(level: float) -> str:
    """获取掌握度等级名称"""
    if level >= 81:
        return "精通"
    elif level >= 61:
        return "熟练"
    elif level >= 41:
        return "理解"
    elif level >= 21:
        return "发展"
    elif level >= 1:
        return "入门"
    else:
        return "萌芽"


def _format_context_for_ai(goal: StudyGoal, graph: KnowledgeGraph, plan: LearningPlan, 
                           node_masteries: List, next_lesson: Lesson = None) -> dict:
    """
    格式化学习目标上下文，用于 AI 对话
    
    返回结构化的上下文信息，便于模型理解用户的学习状态
    """
    # 计算掌握度分布
    mastery_distribution = {
        "萌芽": 0, "入门": 0, "发展": 0, "理解": 0, "熟练": 0, "精通": 0
    }
    weak_points = []
    
    for mastery in node_masteries:
        level_name = _get_mastery_level_name(mastery.mastery_level)
        mastery_distribution[level_name] += 1
        if mastery.mastery_level < 30:  # 掌握度低于30%视为薄弱点
            weak_points.append({
                "name": mastery.node_name,
                "level": mastery.mastery_level
            })
    
    # 计算总体进度
    knowledge_progress = 0
    if goal.total_knowledge_points > 0:
        knowledge_progress = (goal.mastered_points / goal.total_knowledge_points) * 100
    
    lesson_progress = 0
    if plan and plan.total_lessons > 0:
        lesson_progress = (plan.completed_lessons / plan.total_lessons) * 100
    
    # 获取知识点列表（从图谱nodes中提取）
    knowledge_points = []
    if graph and graph.nodes:
        try:
            nodes = graph.nodes if isinstance(graph.nodes, list) else []
            knowledge_points = [n.get("label", n.get("name", "")) for n in nodes[:20]]  # 最多20个
        except:
            pass
    
    context = {
        "基本信息": {
            "目标ID": goal.id,
            "标题": goal.title,
            "学科": goal.subject or "未指定",
            "状态": "进行中" if goal.status == "active" else goal.status,
            "每周学习时长": f"{goal.target_hours_per_week}小时"
        },
        "进度统计": {
            "知识点进度": f"{knowledge_progress:.1f}%",
            "已掌握": f"{goal.mastered_points}/{goal.total_knowledge_points}个",
            "课时进度": f"{lesson_progress:.1f}%" if plan else "无学习计划",
            "已完成课时": f"{goal.completed_lessons}个"
        },
        "掌握度分布": mastery_distribution,
        "薄弱知识点": weak_points[:5] if weak_points else [],  # 最多5个
        "知识点列表": knowledge_points,
        "下一个课时": None
    }
    
    if next_lesson:
        context["下一个课时"] = {
            "标题": next_lesson.title,
            "序号": f"第{next_lesson.lesson_number}课时",
            "预计时长": f"{next_lesson.estimated_minutes}分钟"
        }
    
    return context


@router.get("/summary", response_model=Response)
async def get_study_goals_summary(
    current_student_id: int = Depends(get_current_student_id),
    db: Session = Depends(get_db)
):
    """
    获取用户所有学习目标的摘要列表（用于 AI 上下文）
    
    返回格式化的摘要信息，便于模型快速了解用户的学习目标概况
    """
    goals = db.query(StudyGoal).filter(
        StudyGoal.student_id == current_student_id
    ).order_by(StudyGoal.created_at.desc()).all()
    
    if not goals:
        return Response(
            success=True,
            message="暂无学习目标",
            data={"goals": [], "total": 0}
        )
    
    result = []
    for g in goals:
        # 计算进度
        progress_pct = 0
        if g.total_knowledge_points > 0:
            progress_pct = (g.mastered_points / g.total_knowledge_points) * 100
        
        result.append({
            "id": g.id,
            "title": g.title,
            "subject": g.subject or "未指定",
            "status": "进行中" if g.status == "active" else g.status,
            "progress_percentage": round(progress_pct, 1),
            "mastered_points": g.mastered_points,
            "total_points": g.total_knowledge_points,
            "completed_lessons": g.completed_lessons,
            "created_at": g.created_at.isoformat() if g.created_at else None
        })
    
    return Response(
        success=True,
        message="获取成功",
        data={
            "goals": result,
            "total": len(result),
            "active_count": sum(1 for g in result if g["status"] == "进行中")
        }
    )


@router.get("/{goal_id}/context", response_model=Response)
async def get_goal_context(
    goal_id: int,
    current_student_id: int = Depends(get_current_student_id),
    db: Session = Depends(get_db)
):
    """
    获取学习目标的详细上下文（用于 AI 对话）
    
    返回结构化的上下文信息，包含：
    - 基本信息
    - 进度统计
    - 掌握度分布
    - 薄弱知识点
    - 下一个课时
    """
    goal = db.query(StudyGoal).filter(
        StudyGoal.id == goal_id,
        StudyGoal.student_id == current_student_id
    ).first()
    
    if not goal:
        raise HTTPException(status_code=404, detail="学习目标不存在")
    
    # 获取关联的知识图谱
    graph = db.query(KnowledgeGraph).filter(
        KnowledgeGraph.study_goal_id == goal.id
    ).first()
    
    # 获取关联的学习计划
    plan = db.query(LearningPlan).filter(
        LearningPlan.study_goal_id == goal.id
    ).first()
    
    # 获取下一个未完成的课时
    next_lesson = None
    if plan:
        next_lesson = db.query(Lesson).filter(
            Lesson.plan_id == plan.id,
            Lesson.is_completed == False
        ).order_by(Lesson.lesson_number).first()
    
    # 获取知识点掌握情况
    node_masteries = db.query(NodeMastery).filter(
        NodeMastery.study_goal_id == goal.id,
        NodeMastery.student_id == current_student_id
    ).all()
    
    # 格式化上下文
    context = _format_context_for_ai(goal, graph, plan, node_masteries, next_lesson)
    
    return Response(
        success=True,
        message="获取成功",
        data=context
    )


@router.post("/detect-intent", response_model=Response)
async def detect_goal_intent(
    message: str,
    current_student_id: int = Depends(get_current_student_id),
    db: Session = Depends(get_db)
):
    """
    检测用户消息是否涉及学习目标查询意图
    
    如果用户询问某个学习目标的信息，返回目标ID和相关信息
    """
    import re
    
    message = message.strip().lower()
    
    # 尝试匹配"我的XX目标"或"XX学习"
    goal_patterns = [
        r"我的(.+?)目标",
        r"我的(.+?)学习",
        r"(.+?)目标进度",
        r"(.+?)目标怎么样",
        r"关于(.+?)目标",
        r"(.+?)学得怎么样",
    ]
    
    detected_goal = None
    matched_keyword = None
    
    for pattern in goal_patterns:
        match = re.search(pattern, message)
        if match:
            keyword = match.group(1).strip()
            if len(keyword) >= 2:
                matched_keyword = keyword
                break
    
    # 如果匹配到关键词，尝试查找对应的学习目标
    if matched_keyword:
        goals = db.query(StudyGoal).filter(
            StudyGoal.student_id == current_student_id,
            StudyGoal.status == "active"
        ).all()
        
        for g in goals:
            # 模糊匹配：标题或学科包含关键词
            if matched_keyword in g.title.lower() or \
               (g.subject and matched_keyword in g.subject.lower()):
                detected_goal = {
                    "id": g.id,
                    "title": g.title,
                    "subject": g.subject
                }
                break
            
            # 如果没有明确匹配，但关键词较短，尝试包含匹配
            if len(matched_keyword) <= 4:
                if matched_keyword in g.title.lower():
                    if not detected_goal:
                        detected_goal = {
                            "id": g.id,
                            "title": g.title,
                            "subject": g.subject
                        }
    
    # 检测问题类型
    question_types = []
    if any(k in message for k in ["进度", "完成", "怎么样", "如何"]):
        question_types.append("progress")
    if any(k in message for k in ["知识点", "掌握", "学得"]):
        question_types.append("mastery")
    if any(k in message for k in ["计划", "下一个", "接下来"]):
        question_types.append("plan")
    if any(k in message for k in ["薄弱", "不足", "需要加强"]):
        question_types.append("weakness")
    
    return Response(
        success=True,
        message="检测完成",
        data={
            "needs_goal_context": detected_goal is not None,
            "detected_goal": detected_goal,
            "matched_keyword": matched_keyword,
            "question_types": question_types
        }
    )


@router.post("/", response_model=Response)
async def create_study_goal(
    title: str,
    description: Optional[str] = None,
    subject: Optional[str] = None,
    target_hours_per_week: float = 5.0,
    target_completion_date: Optional[datetime] = None,
    student_background: Optional[dict] = None,
    current_student_id: int = Depends(get_current_student_id),
    db: Session = Depends(get_db),
):
    """
    创建学习目标（轻量版）
    
    ## 功能说明
    - 学生设置新的学习目标（仅创建框架）
    - 不自动生成知识图谱和学习计划
    - 这些内容由用户后续在各模块中单独生成
    
    ## 参数
    - title: 学习目标标题
    - description: 学习目标描述
    - subject: 学科/领域
    - target_hours_per_week: 每周可用小时数
    - target_completion_date: 目标完成日期
    - student_background: 学生学习背景
    """
    try:
        # 创建学习目标（仅创建框架，不自动生成图谱和计划）
        goal = StudyGoal(
            student_id=current_student_id,
            title=title,
            description=description,
            subject=subject,
            target_hours_per_week=target_hours_per_week,
            target_completion_date=target_completion_date,
            student_background=student_background,
            status=StudyGoalStatus.ACTIVE.value
        )
        
        db.add(goal)
        db.commit()
        db.refresh(goal)
        
        return Response(
            success=True,
            message="学习目标创建成功",
            data={
                "goal_id": goal.id,
                "title": goal.title,
                "subject": goal.subject,
                "target_hours_per_week": goal.target_hours_per_week,
            }
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=Response)
async def list_study_goals(
    current_student_id: int = Depends(get_current_student_id),
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    获取学习目标列表
    
    ## 参数
    - status: 筛选状态 (active/completed/archived)
    """
    query = db.query(StudyGoal).filter(StudyGoal.student_id == current_student_id)
    
    if status:
        query = query.filter(StudyGoal.status == status)
    
    goals = query.order_by(StudyGoal.created_at.desc()).all()
    
    # 获取每个目标的关联知识图谱和学习计划
    result = []
    for g in goals:
        # 获取第一个关联的知识图谱
        graph = db.query(KnowledgeGraph).filter(
            KnowledgeGraph.study_goal_id == g.id
        ).first()
        
        # 获取第一个关联的学习计划
        plan = db.query(LearningPlan).filter(
            LearningPlan.study_goal_id == g.id
        ).first()
        
        result.append({
            "id": g.id,
            "title": g.title,
            "description": g.description,
            "subject": g.subject,
            "status": g.status,
            "progress": {
                "total_knowledge_points": g.total_knowledge_points,
                "mastered_points": g.mastered_points,
                "completed_lessons": g.completed_lessons
            },
            "target_hours_per_week": g.target_hours_per_week,
            "graph_id": graph.id if graph else None,
            "plan_id": plan.id if plan else None,
            "created_at": g.created_at.isoformat() if g.created_at else None,
            "updated_at": g.updated_at.isoformat() if g.updated_at else None
        })
    
    return Response(
        success=True,
        message="获取成功",
        data=result
    )


@router.get("/{goal_id}", response_model=Response)
async def get_study_goal(
    goal_id: int,
    current_student_id: int = Depends(get_current_student_id),
    db: Session = Depends(get_db)
):
    """获取学习目标详情"""
    goal = db.query(StudyGoal).filter(
        StudyGoal.id == goal_id,
        StudyGoal.student_id == current_student_id
    ).first()
    
    if not goal:
        raise HTTPException(status_code=404, detail="学习目标不存在")
    
    # 获取关联的知识图谱
    graph = db.query(KnowledgeGraph).filter(
        KnowledgeGraph.study_goal_id == goal.id
    ).first()
    
    # 获取关联的学习计划
    plan = db.query(LearningPlan).filter(
        LearningPlan.study_goal_id == goal.id
    ).first()
    
    return Response(
        success=True,
        message="获取成功",
        data={
            "id": goal.id,
            "title": goal.title,
            "description": goal.description,
            "subject": goal.subject,
            "status": goal.status,
            "target_hours_per_week": goal.target_hours_per_week,
            "target_completion_date": goal.target_completion_date.isoformat() if goal.target_completion_date else None,
            "student_background": goal.student_background,
            "progress": {
                "total_knowledge_points": goal.total_knowledge_points,
                "mastered_points": goal.mastered_points,
                "completed_lessons": goal.completed_lessons
            },
            "graph_id": graph.id if graph else None,
            "plan_id": plan.id if plan else None,
            "created_at": goal.created_at.isoformat() if goal.created_at else None,
            "updated_at": goal.updated_at.isoformat() if goal.updated_at else None
        }
    )


@router.put("/{goal_id}", response_model=Response)
async def update_study_goal(
    goal_id: int,
    title: Optional[str] = None,
    description: Optional[str] = None,
    status: Optional[str] = None,
    target_hours_per_week: Optional[float] = None,
    target_completion_date: Optional[datetime] = None,
    current_student_id: int = Depends(get_current_student_id),
    db: Session = Depends(get_db)
):
    """更新学习目标"""
    goal = db.query(StudyGoal).filter(
        StudyGoal.id == goal_id,
        StudyGoal.student_id == current_student_id
    ).first()
    
    if not goal:
        raise HTTPException(status_code=404, detail="学习目标不存在")
    
    if title:
        goal.title = title
    if description:
        goal.description = description
    if status:
        goal.status = status
    if target_hours_per_week:
        goal.target_hours_per_week = target_hours_per_week
    if target_completion_date:
        goal.target_completion_date = target_completion_date
    
    db.commit()
    db.refresh(goal)
    
    return Response(
        success=True,
        message="更新成功",
        data={"id": goal.id, "title": goal.title}
    )


@router.delete("/{goal_id}", response_model=Response)
async def delete_study_goal(
    goal_id: int,
    current_student_id: int = Depends(get_current_student_id),
    db: Session = Depends(get_db)
):
    """删除学习目标"""
    from sqlalchemy.exc import IntegrityError
    
    goal = db.query(StudyGoal).filter(
        StudyGoal.id == goal_id,
        StudyGoal.student_id == current_student_id
    ).first()
    
    if not goal:
        raise HTTPException(status_code=404, detail="学习目标不存在")
    
    try:
        # 级联删除关联数据（按依赖顺序）
        
        # 1. 删除 AgentSession（会级联删除 LearningStage 和 Motivation）
        from app.models.agent_session import AgentSession
        db.query(AgentSession).filter(AgentSession.study_goal_id == goal_id).delete(synchronize_session=False)
        
        # 2. 获取学习计划列表
        from app.models.learning_plan import LearningPlan, Lesson, Chapter, Section
        plans = db.query(LearningPlan).filter(LearningPlan.study_goal_id == goal_id).all()
        for plan in plans:
            # 先删除课时
            db.query(Lesson).filter(Lesson.plan_id == plan.id).delete(synchronize_session=False)
            # 删除节（Section 有两个外键：chapter_id 和 plan_id，必须显式删除）
            db.query(Section).filter(Section.plan_id == plan.id).delete(synchronize_session=False)
            # 删除章节
            db.query(Chapter).filter(Chapter.plan_id == plan.id).delete(synchronize_session=False)
            # 最后删除计划
            db.delete(plan)
        
        # 3. 删除知识图谱
        from app.models.knowledge_graph import KnowledgeGraph
        db.query(KnowledgeGraph).filter(KnowledgeGraph.study_goal_id == goal_id).delete(synchronize_session=False)
        
        # 4. 删除学习资料
        from app.models.study_material import StudyMaterial
        db.query(StudyMaterial).filter(StudyMaterial.study_goal_id == goal_id).delete(synchronize_session=False)
        
        # 5. 删除节点掌握情况
        from app.models.node_mastery import NodeMastery
        db.query(NodeMastery).filter(NodeMastery.study_goal_id == goal_id).delete(synchronize_session=False)
        
        # 6. 删除学习记录
        from app.models.study_record import StudyRecord
        db.query(StudyRecord).filter(StudyRecord.goal_id == goal_id).delete(synchronize_session=False)

        # 7. 删除聊天历史
        from app.models.chat_history import ChatHistory
        db.query(ChatHistory).filter(ChatHistory.study_goal_id == goal_id).delete(synchronize_session=False)

        # 8. 删除题库
        from app.models.assessment import QuestionBank
        db.query(QuestionBank).filter(QuestionBank.study_goal_id == goal_id).delete(synchronize_session=False)

        # 9. 最后删除学习目标
        db.delete(goal)
        db.commit()
        
        return Response(
            success=True,
            message="删除成功",
            data={"id": goal_id}
        )
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"删除失败：存在关联数据无法删除")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"删除失败：{str(e)}")


@router.get("/{goal_id}/progress", response_model=Response)
async def get_goal_progress(
    goal_id: int,
    current_student_id: int = Depends(get_current_student_id),
    db: Session = Depends(get_db)
):
    """
    获取学习目标进度统计
    
    返回：
    - 知识点掌握情况
    - 课时完成进度
    - 学习时长统计
    """
    goal = db.query(StudyGoal).filter(
        StudyGoal.id == goal_id,
        StudyGoal.student_id == current_student_id
    ).first()
    
    if not goal:
        raise HTTPException(status_code=404, detail="学习目标不存在")
    
    # 计算掌握度百分比
    mastery_percentage = 0
    if goal.total_knowledge_points > 0:
        mastery_percentage = (goal.mastered_points / goal.total_knowledge_points) * 100
    
    return Response(
        success=True,
        message="获取成功",
        data={
            "goal_id": goal.id,
            "title": goal.title,
            "knowledge_progress": {
                "total": goal.total_knowledge_points,
                "mastered": goal.mastered_points,
                "percentage": round(mastery_percentage, 1)
            },
            "lesson_progress": {
                "completed": goal.completed_lessons
            },
            "status": goal.status,
            "updated_at": goal.updated_at.isoformat() if goal.updated_at else None
        }
    )


@router.get("/{goal_id}/records", response_model=Response)
async def get_goal_records(
    goal_id: int,
    current_student_id: int = Depends(get_current_student_id),
    db: Session = Depends(get_db)
):
    """
    获取学习目标的学习记录列表

    返回该目标下的所有学习记录，包括会话摘要和对话日志。
    """
    # 验证目标存在且属于当前学生
    goal = db.query(StudyGoal).filter(
        StudyGoal.id == goal_id,
        StudyGoal.student_id == current_student_id
    ).first()

    if not goal:
        raise HTTPException(status_code=404, detail="学习目标不存在")

    # 获取学习记录
    from app.models.study_record import StudyRecord
    records = db.query(StudyRecord).filter(
        StudyRecord.goal_id == goal_id,
        StudyRecord.student_id == current_student_id
    ).order_by(StudyRecord.record_date.desc()).all()

    # 格式化返回数据
    result = []
    for r in records:
        # 解析会话摘要
        sessions = []
        if r.session_summary:
            try:
                import json
                sessions = json.loads(r.session_summary)
            except Exception:
                pass

        # 解析对话日志
        conversations = []
        if r.conversation_log:
            try:
                import json
                conversations = json.loads(r.conversation_log)
            except Exception:
                pass

        result.append({
            "id": r.id,
            "record_date": r.record_date.isoformat() if r.record_date else None,
            "study_duration_minutes": r.study_duration_minutes,
            "lessons_completed": r.lessons_completed,
            "exercises_attempted": r.exercises_attempted,
            "exercises_correct": r.exercises_correct,
            "summary": r.summary,
            "notes": r.notes,
            "sessions": sessions,  # 会话摘要列表
            "conversations": conversations,  # 对话记录
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        })

    return Response(
        success=True,
        message="获取成功",
        data={
            "goal_id": goal_id,
            "goal_title": goal.title,
            "records": result,
            "total": len(result)
        }
    )
