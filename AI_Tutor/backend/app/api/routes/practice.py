"""
练习巩固 API 路由

提供基于知识点的自适应练习功能：
1. 根据学生掌握度筛选合适难度的习题
2. 提交答题结果并更新学情分析数据
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime
import json

from app.core.database import get_db
from app.api.deps import get_current_student_id
from app.schemas import Response
from app.models.study_goal import StudyGoal
from app.models.node_mastery import NodeMastery
from app.models.assessment import QuestionBank, Assessment
from app.models.knowledge_graph import KnowledgeGraph
from app.models.learning_plan import LearningPlan, Lesson, Section
from pydantic import BaseModel

router = APIRouter()


def _parse_nodes(graph_nodes):
    """解析知识图谱节点"""
    if not graph_nodes:
        return []
    if isinstance(graph_nodes, str):
        try:
            return json.loads(graph_nodes)
        except json.JSONDecodeError:
            return []
    if isinstance(graph_nodes, list):
        return graph_nodes
    return []


def _determine_difficulty(correct_rate: float, total_attempts: int) -> str:
    """
    根据正确率和尝试次数确定题目难度
    
    规则：
    - 刚开始学习(total_attempts < 3)或正确率<60% → basic (简单题)
    - 正确率<80% → comprehensive (中等题)
    - 正确率>=80% → challenge (困难题)
    """
    if total_attempts < 3 or correct_rate < 60:
        return "basic"
    elif correct_rate < 80:
        return "comprehensive"
    else:
        return "challenge"


def _get_node_mastery_info(db: Session, student_id: int, goal_id: int, node_ids: List[str]) -> dict:
    """
    获取多个知识点的掌握度信息
    
    返回: {node_id: {"mastery_level": float, "correct_rate": float, "total_attempts": int}}
    """
    masteries = db.query(NodeMastery).filter(
        NodeMastery.student_id == student_id,
        NodeMastery.study_goal_id == goal_id,
        NodeMastery.node_id.in_(node_ids)
    ).all()
    
    result = {}
    for m in masteries:
        total = m.total_attempts or 0
        correct = m.correct_attempts or 0
        result[str(m.node_id)] = {
            "mastery_level": m.mastery_level or 0,
            "correct_rate": round(correct / total * 100, 1) if total > 0 else 0,
            "total_attempts": total
        }
    
    # 对于没有记录的节点，标记为刚开始学习
    for node_id in node_ids:
        if str(node_id) not in result:
            result[str(node_id)] = {
                "mastery_level": 0,
                "correct_rate": 0,
                "total_attempts": 0
            }
    
    return result


class SubmitAnswerRequest(BaseModel):
    """提交答题结果请求"""
    exercise_id: str  # 练习会话ID（字符串格式如 ex_goalId_sectionId_timestamp）
    answers: List[dict]  # 答题结果 [{"question_id": int, "user_answer": str, "is_correct": bool}]


@router.get("/{goal_id}/current-section", response_model=Response)
async def get_current_section(
    goal_id: int,
    current_student_id: int = Depends(get_current_student_id),
    db: Session = Depends(get_db)
):
    """
    获取当前学习位置的小节信息
    
    返回当前应该练习的小节（优先返回下一个未完成课时所属的小节）
    """
    # 验证学习目标
    goal = db.query(StudyGoal).filter(
        StudyGoal.id == goal_id,
        StudyGoal.student_id == current_student_id
    ).first()
    
    if not goal:
        raise HTTPException(status_code=404, detail="学习目标不存在")
    
    # 获取学习计划
    plan = db.query(LearningPlan).filter(
        LearningPlan.study_goal_id == goal_id
    ).first()
    
    if not plan:
        return Response(
            success=True,
            message="该学习目标还没有学习计划",
            data={"section_id": None, "section_title": None}
        )
    
    # 查找下一个未完成的课时
    next_lesson = db.query(Lesson).filter(
        Lesson.plan_id == plan.id,
        Lesson.is_completed == False
    ).order_by(Lesson.lesson_number).first()
    
    if not next_lesson:
        # 所有课时已完成，返回最后一个已完成的课时
        last_completed = db.query(Lesson).filter(
            Lesson.plan_id == plan.id,
            Lesson.is_completed == True
        ).order_by(Lesson.lesson_number.desc()).first()
        
        if last_completed:
            section = None
            if last_completed.section_id:
                section = db.query(Section).filter(Section.id == last_completed.section_id).first()
            elif last_completed.chapter_id:
                section = db.query(Section).filter(Section.chapter_id == last_completed.chapter_id).first()
            
            if section:
                return Response(
                    success=True,
                    message="所有课时已完成，返回最后一个小节",
                    data={
                        "section_id": section.id,
                        "section_title": section.title
                    }
                )
        
        return Response(
            success=True,
            message="暂无可练习的小节",
            data={"section_id": None, "section_title": None}
        )
    
    # 获取该课时所属的小节
    section = None
    if next_lesson.section_id:
        section = db.query(Section).filter(Section.id == next_lesson.section_id).first()
    elif next_lesson.chapter_id:
        # 如果课时没有直接关联小节，尝试找到该章节下的第一个小节
        section = db.query(Section).filter(Section.chapter_id == next_lesson.chapter_id).first()
    
    if section:
        return Response(
            success=True,
            message="获取当前学习位置成功",
            data={
                "section_id": section.id,
                "section_title": section.title,
                "lesson_id": next_lesson.id,
                "lesson_title": next_lesson.title
            }
        )
    
    return Response(
        success=True,
        message="暂无可练习的小节",
        data={"section_id": None, "section_title": None}
    )


@router.get("/{goal_id}/section/{section_id}/exercises", response_model=Response)
async def get_section_exercises(
    goal_id: int,
    section_id: int,
    current_student_id: int = Depends(get_current_student_id),
    db: Session = Depends(get_db)
):
    """
    获取小节的练习题（自适应难度）

    根据学生对该小节各知识点的掌握程度，自动筛选合适难度的题目：
    - 刚开始学习或正确率<60% → 基础题
    - 正确率60%-80% → 综合题
    - 正确率>=80% → 挑战题

    每个知识点出一道题。
    """
    print(f"[PRACTICE] 请求练习题: goal_id={goal_id}, section_id={section_id}, student_id={current_student_id}")

    # 验证学习目标
    goal = db.query(StudyGoal).filter(
        StudyGoal.id == goal_id,
        StudyGoal.student_id == current_student_id
    ).first()
    
    if not goal:
        raise HTTPException(status_code=404, detail="学习目标不存在")
    
    # 获取小节信息
    section = db.query(Section).filter(Section.id == section_id).first()
    if not section:
        raise HTTPException(status_code=404, detail="小节不存在")
    
    # 【关键修复】验证小节是否属于该学习目标的学习计划
    # Section.plan_id 对应 LearningPlan.id，LearningPlan.study_goal_id 对应学习目标ID
    section_in_valid_plan = False
    
    if section.plan_id:
        # 获取该学习计划
        plan = db.query(LearningPlan).filter(
            LearningPlan.id == section.plan_id,
            LearningPlan.student_id == current_student_id
        ).first()
        if plan and plan.study_goal_id == goal_id:
            section_in_valid_plan = True
    
    if not section_in_valid_plan:
        # 间接检查：Section 的课时是否属于该学习目标的学习计划
        lessons_in_plan = db.query(Lesson).join(LearningPlan).filter(
            Lesson.section_id == section_id,
            LearningPlan.study_goal_id == goal_id,
            LearningPlan.student_id == current_student_id
        ).first()
        section_in_valid_plan = (lessons_in_plan is not None)
    
    # 如果小节不属于该学习目标，返回错误
    if not section_in_valid_plan:
        raise HTTPException(
            status_code=400, 
            detail=f"小节 {section_id} 不属于学习目标 {goal_id}"
        )
    
    # 获取该小节包含的所有课时
    lessons = db.query(Lesson).filter(Lesson.section_id == section_id).all()
    
    # 获取第一个未完成的课时ID（用于标记完成学习）
    first_uncompleted_lesson = db.query(Lesson).filter(
        Lesson.section_id == section_id,
        Lesson.is_completed == False
    ).order_by(Lesson.lesson_number).first()
    
    # 兜底策略：当所有课时已完成时，查找最后一个已完成的课时作为 lesson_id
    # 这样用户可以重复标记已完成的课时
    all_completed = False
    lesson_id_to_return = None
    
    if first_uncompleted_lesson:
        # 有未完成的课时，正常返回
        lesson_id_to_return = first_uncompleted_lesson.id
    else:
        # 没有未完成的课时，检查是否有已完成的课时
        all_completed = True
        last_completed_lesson = db.query(Lesson).filter(
            Lesson.section_id == section_id,
            Lesson.is_completed == True
        ).order_by(Lesson.lesson_number.desc()).first()
        
        if last_completed_lesson:
            lesson_id_to_return = last_completed_lesson.id
            print(f"[PRACTICE] 小节 {section_id} 所有课时已完成，使用最后一个已完成课时作为兜底: lesson_id={lesson_id_to_return}")
        else:
            # section 下完全没有课时
            lesson_id_to_return = None
            print(f"[PRACTICE] 小节 {section_id} 下没有任何课时")
    
    # 收集该小节的所有知识点ID
    knowledge_point_ids = []
    
    # 方法1: 优先从 Section 的 knowledge_point_ids 获取
    if section.knowledge_point_ids:
        section_kps = section.knowledge_point_ids
        if isinstance(section_kps, str):
            try:
                section_kps = json.loads(section_kps)
            except json.JSONDecodeError:
                section_kps = []
        if isinstance(section_kps, list):
            knowledge_point_ids = [str(kp) for kp in section_kps if kp]
    
    # 方法2: 从 Lesson 的 knowledge_point_id 获取
    for lesson in lessons:
        if lesson.knowledge_point_id and lesson.knowledge_point_id not in knowledge_point_ids:
            knowledge_point_ids.append(lesson.knowledge_point_id)
    
    # 方法3已移除：不再从整个学习目标题库获取知识点，避免范围过大偏离当前学习内容
    # 如果方法1和方法2都找不到知识点，打印警告并返回空的练习题列表
    if not knowledge_point_ids:
        print(f"[警告] 小节 {section_id} ({section.title}) 未找到关联的知识点，请检查该小节是否已正确配置知识点。")
        print(f"[警告] Section.knowledge_point_ids={section.knowledge_point_ids}, Lessons count={len(lessons)}")
        return Response(
            success=True,
            message=f"该小节「{section.title}」暂未配置知识点，请先在学习计划中为该小节关联知识点。",
            data={
                "section_id": section_id,
                "section_title": section.title,
                "lesson_id": lesson_id_to_return,
                "all_completed": all_completed,
                "exercises": [],
                "total": 0,
                "hint": "请联系管理员或在学习计划中为该小节配置知识点"
            }
        )

    print(f"[PRACTICE] 收集到知识点: {knowledge_point_ids}")
    
    # 获取知识点名称映射
    node_name_map = {}
    kg = db.query(KnowledgeGraph).filter(KnowledgeGraph.study_goal_id == goal_id).first()
    if kg:
        nodes = _parse_nodes(kg.nodes)
        for node in nodes:
            node_id = str(node.get('id', ''))
            node_name_map[node_id] = node.get('label', '') or node.get('name', '') or node_id
    
    # 获取各知识点的掌握度信息
    mastery_info = _get_node_mastery_info(db, current_student_id, goal_id, knowledge_point_ids)
    
    # 为每个知识点筛选题目
    selected_questions = []
    question_ids_used = set()
    
    for node_id in knowledge_point_ids:
        info = mastery_info.get(str(node_id), {
            "mastery_level": 0,
            "correct_rate": 0,
            "total_attempts": 0
        })
        
        target_difficulty = _determine_difficulty(
            info["correct_rate"],
            info["total_attempts"]
        )
        
        # 按难度筛选题目（优先精确匹配，其次降级）
        difficulties_to_try = [target_difficulty]
        if target_difficulty == "challenge":
            difficulties_to_try.extend(["comprehensive", "basic"])
        elif target_difficulty == "comprehensive":
            difficulties_to_try.extend(["basic", "challenge"])
        else:
            difficulties_to_try.extend(["comprehensive", "challenge"])
        
        question = None
        for diff in difficulties_to_try:
            q = db.query(QuestionBank).filter(
                QuestionBank.study_goal_id == goal_id,
                QuestionBank.knowledge_point_id == str(node_id),
                QuestionBank.difficulty == diff,
                ~QuestionBank.id.in_(question_ids_used) if question_ids_used else True
            ).first()
            
            if q:
                question = q
                break
        
        # 如果该知识点没有找到合适题目，尝试从整个题库中随机选取一道
        if not question:
            q = db.query(QuestionBank).filter(
                QuestionBank.study_goal_id == goal_id,
                ~QuestionBank.id.in_(question_ids_used) if question_ids_used else True
            ).order_by(func.random()).first()
            if q:
                question = q
        
        if question:
            selected_questions.append({
                "id": question.id,
                "knowledge_point_id": question.knowledge_point_id,
                "knowledge_point_name": node_name_map.get(str(node_id), question.knowledge_point_id),
                "question_text": question.question_text,
                "question_type": question.question_type,
                "difficulty": question.difficulty,
                "options": question.options,
                "correct_answer": question.correct_answer,
                "explanation": question.explanation,
                "target_difficulty": target_difficulty,
                "mastery_info": info
            })
            question_ids_used.add(question.id)
    
    print(f"[PRACTICE] 返回 {len(selected_questions)} 道题目")
    
    # 创建练习会话记录
    exercise_session = {
        "goal_id": goal_id,
        "section_id": section_id,
        "section_title": section.title,
        "questions": selected_questions,
        "created_at": datetime.utcnow().isoformat()
    }
    
    return Response(
        success=True,
        message=f"已为{len(selected_questions)}个知识点生成练习题",
        data={
            "exercise_id": f"ex_{goal_id}_{section_id}_{int(datetime.utcnow().timestamp())}",
            "section_id": section_id,
            "section_title": section.title,
            "lesson_id": lesson_id_to_return,
            "all_completed": all_completed,
            "exercises": selected_questions,
            "total": len(selected_questions),
            "mastery_summary": {
                node_id: info for node_id, info in mastery_info.items()
            }
        }
    )


@router.post("/{goal_id}/submit", response_model=Response)
async def submit_exercise_results(
    goal_id: int,
    request: SubmitAnswerRequest,
    current_student_id: int = Depends(get_current_student_id),
    db: Session = Depends(get_db)
):
    """
    提交练习结果并更新学情分析数据
    
    1. 统计答题正确率
    2. 更新各知识点的掌握度
    3. 创建测评记录
    """
    # 验证学习目标
    goal = db.query(StudyGoal).filter(
        StudyGoal.id == goal_id,
        StudyGoal.student_id == current_student_id
    ).first()
    
    if not goal:
        raise HTTPException(status_code=404, detail="学习目标不存在")
    
    answers = request.answers
    total_questions = len(answers)
    correct_count = sum(1 for a in answers if a.get("is_correct"))
    accuracy = round(correct_count / total_questions * 100, 1) if total_questions > 0 else 0
    
    # 获取所有涉及的题目和知识点
    question_ids = [a["question_id"] for a in answers]
    questions = db.query(QuestionBank).filter(QuestionBank.id.in_(question_ids)).all()
    question_map = {q.id: q for q in questions}
    
    # 统计各知识点的答题情况
    knowledge_point_stats = {}
    for answer in answers:
        q = question_map.get(answer["question_id"])
        if q:
            kp_id = str(q.knowledge_point_id)
            if kp_id not in knowledge_point_stats:
                knowledge_point_stats[kp_id] = {"total": 0, "correct": 0, "node_name": kp_id}
            knowledge_point_stats[kp_id]["total"] += 1
            if answer.get("is_correct"):
                knowledge_point_stats[kp_id]["correct"] += 1
    
    # 更新各知识点的掌握度
    updated_masteries = []
    for kp_id, stats in knowledge_point_stats.items():
        # 获取或创建知识点掌握度记录
        mastery = db.query(NodeMastery).filter(
            NodeMastery.student_id == current_student_id,
            NodeMastery.study_goal_id == goal_id,
            NodeMastery.node_id == kp_id
        ).first()
        
        if not mastery:
            # 创建新记录
            mastery = NodeMastery(
                student_id=current_student_id,
                study_goal_id=goal_id,
                node_id=kp_id,
                node_name=stats["node_name"],
                mastery_level=0,
                confidence=0
            )
            db.add(mastery)
        
        # 更新统计数据
        mastery.total_attempts = (mastery.total_attempts or 0) + stats["total"]
        mastery.correct_attempts = (mastery.correct_attempts or 0) + stats["correct"]
        
        # 计算新的掌握度（基于正确率，范围0-100）
        new_accuracy = round(mastery.correct_attempts / mastery.total_attempts * 100, 1) if mastery.total_attempts > 0 else 0
        
        # 掌握度计算：考虑历史掌握度和当前表现
        old_mastery = mastery.mastery_level or 0
        # 新掌握度 = 旧掌握度 * 0.3 + 当前正确率 * 0.7
        mastery.mastery_level = round(old_mastery * 0.3 + new_accuracy * 0.7, 1)
        
        # 更新置信度（基于尝试次数，次数越多置信度越高，上限1.0）
        mastery.confidence = min(1.0, mastery.total_attempts / 20)
        
        mastery.last_assessment_score = new_accuracy
        mastery.last_assessment_at = datetime.utcnow()
        mastery.study_count = (mastery.study_count or 0) + 1
        mastery.last_studied_at = datetime.utcnow()
        mastery.updated_at = datetime.utcnow()
        
        updated_masteries.append({
            "node_id": kp_id,
            "node_name": mastery.node_name,
            "old_mastery": old_mastery,
            "new_mastery": mastery.mastery_level,
            "accuracy": new_accuracy,
            "total_attempts": mastery.total_attempts,
            "correct_attempts": mastery.correct_attempts
        })
    
    # 更新学习目标的总掌握度
    all_masteries = db.query(NodeMastery).filter(
        NodeMastery.student_id == current_student_id,
        NodeMastery.study_goal_id == goal_id
    ).all()
    
    if all_masteries:
        avg_mastery = sum(m.mastery_level or 0 for m in all_masteries) / len(all_masteries)
        goal.total_knowledge_points = len(all_masteries)
        goal.mastered_points = len([m for m in all_masteries if m.mastery_level >= 80])
        goal.updated_at = datetime.utcnow()
    
    # 创建测评记录
    assessment = Assessment(
        student_id=current_student_id,
        lesson_id=0,  # 练习模式可能不关联具体课时
        assessment_type="practice",
        questions=json.dumps(answers, ensure_ascii=False),
        total_questions=total_questions,
        correct_answers=correct_count,
        score=accuracy,
        time_spent=None,
        mastery_before=avg_mastery if all_masteries else 0,
        mastery_after=round(avg_mastery, 1) if all_masteries else 0
    )
    db.add(assessment)
    
    db.commit()
    
    return Response(
        success=True,
        message=f"答题结果已保存，正确率{accuracy}%",
        data={
            "goal_id": goal_id,
            "total_questions": total_questions,
            "correct_count": correct_count,
            "accuracy": accuracy,
            "updated_masteries": updated_masteries,
            "overall_mastery": round(avg_mastery, 1) if all_masteries else 0,
            "assessment_id": assessment.id
        }
    )


@router.get("/{goal_id}/node/{node_id}/difficulty", response_model=Response)
async def get_node_exercise_difficulty(
    goal_id: int,
    node_id: str,
    current_student_id: int = Depends(get_current_student_id),
    db: Session = Depends(get_db)
):
    """
    获取指定知识点的推荐练习难度
    """
    mastery = db.query(NodeMastery).filter(
        NodeMastery.student_id == current_student_id,
        NodeMastery.study_goal_id == goal_id,
        NodeMastery.node_id == str(node_id)
    ).first()
    
    total_attempts = mastery.total_attempts if mastery else 0
    correct_rate = 0
    if mastery and mastery.total_attempts > 0:
        correct_rate = round(mastery.correct_attempts / mastery.total_attempts * 100, 1)
    
    difficulty = _determine_difficulty(correct_rate, total_attempts)
    
    difficulty_labels = {
        "basic": "基础题",
        "comprehensive": "综合题",
        "challenge": "挑战题"
    }
    
    return Response(
        success=True,
        message="获取成功",
        data={
            "node_id": node_id,
            "total_attempts": total_attempts,
            "correct_rate": correct_rate,
            "recommended_difficulty": difficulty,
            "difficulty_label": difficulty_labels[difficulty],
            "mastery_level": mastery.mastery_level if mastery else 0
        }
    )
