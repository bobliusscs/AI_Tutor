"""
学情分析 API 路由
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime, timedelta

from app.core.database import get_db
from app.api.deps import get_current_student_id
from app.schemas import Response
from app.models.study_goal import StudyGoal
from app.models.node_mastery import NodeMastery
from app.models.assessment import Assessment
from app.models.learning_plan import LearningPlan, Lesson, Chapter, Section
from app.models.knowledge_graph import KnowledgeGraph, KnowledgeNode


router = APIRouter()


def get_mastery_label(mastery_level: float) -> str:
    """
    根据掌握度返回标签
    <30: 薄弱, 30-50: 较差, 50-70: 一般, >=70: 良好
    """
    if mastery_level < 30:
        return "薄弱"
    elif mastery_level < 50:
        return "较差"
    elif mastery_level < 70:
        return "一般"
    else:
        return "良好"


@router.get("/{goal_id}/overview", response_model=Response)
async def get_analysis_overview(
    goal_id: int,
    current_student_id: int = Depends(get_current_student_id),
    db: Session = Depends(get_db)
):
    """
    获取学情分析总览
    
    返回：
    - overall_mastery: 总体掌握度（预留接口，后续接入知识追踪模型）
    - mastered_knowledge_points: 已掌握知识点统计
    - learning_progress: 当前学习进度（章/节）
    - practice_accuracy: 练习正确率统计
    """
    goal = db.query(StudyGoal).filter(
        StudyGoal.id == goal_id,
        StudyGoal.student_id == current_student_id
    ).first()
    
    if not goal:
        raise HTTPException(status_code=404, detail="学习目标不存在或无权访问")
    
    # 获取掌握度统计
    masteries = db.query(NodeMastery).filter(
        NodeMastery.study_goal_id == goal_id,
        NodeMastery.student_id == current_student_id
    ).all()
    
    # 从知识图谱获取知识点总数
    kg = db.query(KnowledgeGraph).filter(
        KnowledgeGraph.study_goal_id == goal_id
    ).first()
        
    if kg:
        # 优先使用 total_nodes 字段，否则计算 nodes 列表长度
        total_nodes = kg.total_nodes or (len(kg.nodes) if kg.nodes else 0)
    else:
        # fallback: 使用 goal.total_knowledge_points 或 mastery 记录数
        total_nodes = max(goal.total_knowledge_points or 0, len(masteries))
    
    # 已掌握知识点数（correct_attempts > 0 的记录数）
    mastered_count = len([m for m in masteries if m.correct_attempts and m.correct_attempts > 0])
    
    # 获取学习进度 - 查询该 goal 关联的 LearningPlan，找到第一个 is_completed=False 的 Lesson
    learning_progress = {
        "current_chapter": 1,
        "current_section": 1,
        "chapter_title": "尚未开始",
        "section_title": "尚未开始",
        "description": "请开始学习"
    }
    
    # 查找关联的学习计划
    learning_plan = db.query(LearningPlan).filter(
        LearningPlan.study_goal_id == goal_id,
        LearningPlan.student_id == current_student_id
    ).first()
    
    if learning_plan:
        # 找到第一个未完成的课时
        current_lesson = db.query(Lesson).filter(
            Lesson.plan_id == learning_plan.id,
            Lesson.is_completed == False
        ).order_by(Lesson.lesson_number.asc()).first()
        
        if current_lesson:
            # 获取章节信息
            chapter_number = 1
            section_number = 1
            chapter_title = "第1章"
            section_title = "第1节"
            
            if current_lesson.chapter_id:
                chapter = db.query(Chapter).filter(Chapter.id == current_lesson.chapter_id).first()
                if chapter:
                    chapter_number = chapter.chapter_number
                    chapter_title = chapter.title
            
            if current_lesson.section_id:
                section = db.query(Section).filter(Section.id == current_lesson.section_id).first()
                if section:
                    section_number = section.section_number
                    section_title = section.title
            
            learning_progress = {
                "current_chapter": chapter_number,
                "current_section": section_number,
                "chapter_title": chapter_title,
                "section_title": section_title,
                "description": f"第{chapter_number}章第{section_number}节"
            }
        else:
            # 所有课时都已完成
            learning_progress = {
                "current_chapter": learning_plan.completed_lessons or 1,
                "current_section": 1,
                "chapter_title": "已完成",
                "section_title": "已完成",
                "description": "学习计划已完成"
            }
    
    # 练习正确率统计 - 从 NodeMastery 汇总
    total_attempts = sum(m.total_attempts or 0 for m in masteries)
    total_correct = sum(m.correct_attempts or 0 for m in masteries)
    accuracy_rate = round(total_correct / total_attempts * 100, 1) if total_attempts > 0 else 0.0
    
    # 计算总体掌握度 - 基于 NodeMastery 的平均掌握度
    avg_mastery = sum(m.mastery_level or 0 for m in masteries) / len(masteries) if masteries else 0
    overall_mastery = round(avg_mastery, 1)
    
    return Response(
        success=True,
        message="获取成功",
        data={
            "overall_mastery": overall_mastery,  # 基于 NodeMastery 的平均掌握度
            "mastered_knowledge_points": {
                "mastered": mastered_count,
                "total": total_nodes
            },
            "learning_progress": learning_progress,
            "practice_accuracy": {
                "correct": total_correct,
                "total": total_attempts,
                "rate": accuracy_rate
            }
        }
    )


@router.get("/{goal_id}/trends", response_model=Response)
async def get_learning_trends(
    goal_id: int,
    days: int = 30,
    current_student_id: int = Depends(get_current_student_id),
    db: Session = Depends(get_db)
):
    """
    获取学习趋势数据（总体掌握度随时间变化）
    
    ## 参数
    - days: 查询天数（默认30天）
    
    返回：
    - trends: 每日总体掌握度数据，用于折线图展示
    """
    goal = db.query(StudyGoal).filter(
        StudyGoal.id == goal_id,
        StudyGoal.student_id == current_student_id
    ).first()
    
    if not goal:
        raise HTTPException(status_code=404, detail="学习目标不存在或无权访问")
    
    # 生成日期范围
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    # 从 NodeMastery 的 updated_at 时间戳聚合每日平均掌握度
    mastery_updates = db.query(
        func.date(NodeMastery.updated_at).label('date'),
        func.avg(NodeMastery.mastery_level).label('avg_mastery')
    ).filter(
        NodeMastery.study_goal_id == goal_id,
        NodeMastery.student_id == current_student_id,
        NodeMastery.updated_at >= start_date
    ).group_by(func.date(NodeMastery.updated_at)).all()
    
    # 构建趋势数据
    trends = []
    current_date = start_date
    
    # 如果没有历史数据，使用当前平均掌握度作为最后一天的数据
    all_masteries = db.query(NodeMastery).filter(
        NodeMastery.study_goal_id == goal_id,
        NodeMastery.student_id == current_student_id
    ).all()
    current_avg_mastery = sum((m.mastery_level or 0) for m in all_masteries) / len(all_masteries) if all_masteries else 0
    
    while current_date <= end_date:
        date_str = current_date.strftime('%Y-%m-%d')
        
        # 查找该日期的数据
        day_data = next(
            (m for m in mastery_updates if str(m.date) == current_date.strftime('%Y-%m-%d')),
            None
        )
        
        # 如果有当天数据使用当天数据，否则使用0（表示无更新）
        mastery_value = round(day_data.avg_mastery, 1) if day_data else 0
        
        trends.append({
            "date": date_str,
            "mastery": mastery_value
        })
        
        current_date += timedelta(days=1)
    
    return Response(
        success=True,
        message="获取成功",
        data={
            "trends": trends
        }
    )


@router.get("/{goal_id}/weak-points", response_model=Response)
async def get_weak_points(
    goal_id: int,
    limit: int = 10,
    current_student_id: int = Depends(get_current_student_id),
    db: Session = Depends(get_db)
):
    """
    获取薄弱知识点分析
    
    ## 参数
    - limit: 返回数量限制（默认10个）
    
    返回掌握度 < 70 的知识点列表，按掌握度升序排列
    """
    goal = db.query(StudyGoal).filter(
        StudyGoal.id == goal_id,
        StudyGoal.student_id == current_student_id
    ).first()
    
    if not goal:
        raise HTTPException(status_code=404, detail="学习目标不存在或无权访问")
    
    # 构建知识点ID到中文名称的映射（用于兜底处理脏数据）
    kg = db.query(KnowledgeGraph).filter(KnowledgeGraph.study_goal_id == goal_id).first()
    node_name_map = {}
    if kg:
        node_name_map = {
            n.node_id: n.name
            for n in db.query(KnowledgeNode).filter(KnowledgeNode.graph_id == kg.id).all()
        }
    
    # 获取掌握度 < 70 的知识点，按掌握度升序排列
    weak_points = db.query(NodeMastery).filter(
        NodeMastery.study_goal_id == goal_id,
        NodeMastery.student_id == current_student_id,
        NodeMastery.mastery_level < 70
    ).order_by(NodeMastery.mastery_level.asc()).limit(limit).all()
    
    weak_points_data = [
        {
            "node_id": wp.node_id,
            "node_name": node_name_map.get(wp.node_id, wp.node_name),
            "mastery_level": round(wp.mastery_level or 0, 1),
            "mastery_label": get_mastery_label(wp.mastery_level or 0),
            "total_attempts": wp.total_attempts or 0,
            "correct_attempts": wp.correct_attempts or 0
        }
        for wp in weak_points
    ]
    
    return Response(
        success=True,
        message="获取成功",
        data={
            "weak_points": weak_points_data
        }
    )


@router.get("/{goal_id}/statistics", response_model=Response)
async def get_detailed_statistics(
    goal_id: int,
    current_student_id: int = Depends(get_current_student_id),
    db: Session = Depends(get_db)
):
    """
    获取详细学习统计（简化版，主要练习统计详情）
    """
    goal = db.query(StudyGoal).filter(
        StudyGoal.id == goal_id,
        StudyGoal.student_id == current_student_id
    ).first()
    
    if not goal:
        raise HTTPException(status_code=404, detail="学习目标不存在或无权访问")
    
    # 获取掌握度统计
    masteries = db.query(NodeMastery).filter(
        NodeMastery.study_goal_id == goal_id,
        NodeMastery.student_id == current_student_id
    ).all()
    
    # 计算总练习次数
    total_attempts = sum(m.total_attempts or 0 for m in masteries)
    total_correct = sum(m.correct_attempts or 0 for m in masteries)
    
    # 掌握度分布统计
    distribution = {
        "excellent": len([m for m in masteries if (m.mastery_level or 0) >= 90]),
        "good": len([m for m in masteries if 70 <= (m.mastery_level or 0) < 90]),
        "average": len([m for m in masteries if 50 <= (m.mastery_level or 0) < 70]),
        "poor": len([m for m in masteries if 30 <= (m.mastery_level or 0) < 50]),
        "very_poor": len([m for m in masteries if (m.mastery_level or 0) < 30])
    }
    
    return Response(
        success=True,
        message="获取成功",
        data={
            "practice_statistics": {
                "total_attempts": total_attempts,
                "total_correct": total_correct,
                "overall_accuracy": round(total_correct / total_attempts * 100, 1) if total_attempts > 0 else 0
            },
            "mastery_distribution": distribution,
            "knowledge_points_count": len(masteries)
        }
    )
