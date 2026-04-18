"""
习题交付工具函数

提供从学习计划中获取指定章节或当前学习进度的习题功能。
支持按章节定位，也可自动定位到学生当前进度。
基于知识点掌握度自适应筛选题目难度。
"""
import json
import logging
from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func

logger = logging.getLogger(__name__)


async def get_section_exercises(
    goal_id: int,
    student_id: int,
    chapter_number: Optional[int] = None,
    section_number: Optional[int] = None,
    db: Session = None
) -> str:
    """
    获取指定章节或当前学习进度下的习题（自适应难度）。
    
    定位逻辑：
    - 若指定chapter_number和section_number：返回该节下的习题
    - 若只指定chapter_number：返回该章下第一个未完成课时所在节的习题
    - 若都不指定：自动定位到学生当前学习进度
    
    题目筛选逻辑：
    - 根据各知识点的掌握度自适应选择难度
    - 正确率<60% → 基础题；60%-80% → 综合题；≥80% → 挑战题
    - 每个知识点出一道题
    
    Args:
        goal_id: 学习目标ID
        student_id: 学生ID
        chapter_number: 章节序号（可选，从1开始）
        section_number: 节序号（可选，从1开始，需同时指定chapter_number）
        db: 数据库会话
        
    Returns:
        JSON字符串，包含习题数据和进度信息
    """
    try:
        from app.models.study_goal import StudyGoal
        from app.models.learning_plan import LearningPlan, Lesson, Chapter, Section
        from app.models.assessment import QuestionBank
        from app.models.node_mastery import NodeMastery
        from app.models.knowledge_graph import KnowledgeGraph
        from app.models.agent_session import AgentSession
        
        # ========== 1. 验证学习目标 ==========
        goal = db.query(StudyGoal).filter(
            StudyGoal.id == goal_id,
            StudyGoal.student_id == student_id
        ).first()
        
        if not goal:
            return json.dumps({
                "success": False,
                "error": "学习目标不存在或无权访问"
            }, ensure_ascii=False)
        
        # ========== 2. 获取学习计划 ==========
        plan = db.query(LearningPlan).filter(
            LearningPlan.study_goal_id == goal_id,
            LearningPlan.student_id == student_id
        ).first()
        
        if not plan:
            return json.dumps({
                "success": False,
                "error": "该学习目标还没有学习计划"
            }, ensure_ascii=False)
        
        # ========== 3. 定位当前节 ==========
        target_section = None
        target_chapter = None
        target_lesson = None
        progress_source = ""
        
        # --- 路径A：按指定章节定位 ---
        if chapter_number is not None:
            target_chapter = db.query(Chapter).filter(
                Chapter.plan_id == plan.id,
                Chapter.chapter_number == chapter_number
            ).first()
            
            if not target_chapter:
                return json.dumps({
                    "success": False,
                    "error": f"第{chapter_number}章不存在"
                }, ensure_ascii=False)
            
            if section_number is not None:
                target_section = db.query(Section).filter(
                    Section.chapter_id == target_chapter.id,
                    Section.section_number == section_number
                ).first()
                
                if not target_section:
                    return json.dumps({
                        "success": False,
                        "error": f"第{chapter_number}章第{section_number}节不存在"
                    }, ensure_ascii=False)
                
                # 找该节下第一个未完成课时
                target_lesson = db.query(Lesson).filter(
                    Lesson.plan_id == plan.id,
                    Lesson.section_id == target_section.id,
                    Lesson.is_completed == False
                ).order_by(Lesson.lesson_number).first()
                
                if not target_lesson:
                    target_lesson = db.query(Lesson).filter(
                        Lesson.plan_id == plan.id,
                        Lesson.section_id == target_section.id
                    ).order_by(Lesson.lesson_number.desc()).first()
                
                progress_source = f"指定位置：第{chapter_number}章第{section_number}节"
            else:
                # 只指定章，在该章下找第一个未完成课时
                target_lesson = db.query(Lesson).filter(
                    Lesson.plan_id == plan.id,
                    Lesson.chapter_id == target_chapter.id,
                    Lesson.is_completed == False
                ).order_by(Lesson.lesson_number).first()
                
                if not target_lesson:
                    target_lesson = db.query(Lesson).filter(
                        Lesson.plan_id == plan.id,
                        Lesson.chapter_id == target_chapter.id
                    ).order_by(Lesson.lesson_number.desc()).first()
                
                if target_lesson and target_lesson.section_id:
                    target_section = db.query(Section).filter(Section.id == target_lesson.section_id).first()
                
                progress_source = f"指定位置：第{chapter_number}章"
        
        # --- 路径B：自动定位当前进度 ---
        else:
            # 优先级1：活跃的AgentSession
            active_session = db.query(AgentSession).filter(
                AgentSession.student_id == student_id,
                AgentSession.study_goal_id == goal_id,
                AgentSession.current_lesson_id.isnot(None)
            ).order_by(AgentSession.updated_at.desc()).first()
            
            if active_session and active_session.current_lesson_id:
                target_lesson = db.query(Lesson).filter(
                    Lesson.id == active_session.current_lesson_id
                ).first()
                if target_lesson:
                    progress_source = f"上次学习位置(会话#{active_session.id})"
            
            # 优先级2：最后完成课时的下一节
            if not target_lesson:
                last_completed = db.query(Lesson).filter(
                    Lesson.plan_id == plan.id,
                    Lesson.is_completed == True
                ).order_by(Lesson.lesson_number.desc()).first()
                
                if last_completed:
                    target_lesson = db.query(Lesson).filter(
                        Lesson.plan_id == plan.id,
                        Lesson.lesson_number > last_completed.lesson_number,
                        Lesson.is_completed == False
                    ).order_by(Lesson.lesson_number).first()
                    if target_lesson:
                        progress_source = f"上一课时「{last_completed.title}」已完成"
            
            # 优先级3：从头开始
            if not target_lesson:
                target_lesson = db.query(Lesson).filter(
                    Lesson.plan_id == plan.id,
                    Lesson.is_completed == False
                ).order_by(Lesson.lesson_number).first()
                if target_lesson:
                    progress_source = "刚开始学习，从第一课时开始"
            
            if not target_lesson:
                target_lesson = db.query(Lesson).filter(
                    Lesson.plan_id == plan.id
                ).order_by(Lesson.lesson_number.desc()).first()
                if target_lesson:
                    progress_source = "所有课时已完成"
            
            if target_lesson:
                if target_lesson.section_id:
                    target_section = db.query(Section).filter(Section.id == target_lesson.section_id).first()
                if target_lesson.chapter_id:
                    target_chapter = db.query(Chapter).filter(Chapter.id == target_lesson.chapter_id).first()
        
        if not target_section:
            return json.dumps({
                "success": False,
                "error": "没有找到可练习的小节"
            }, ensure_ascii=False)
        
        # 补充获取章节信息
        if not target_chapter and target_section.chapter_id:
            target_chapter = db.query(Chapter).filter(Chapter.id == target_section.chapter_id).first()
        
        # ========== 4. 收集知识点 ==========
        knowledge_point_ids = []
        
        # 方法1: 从Section的knowledge_point_ids获取
        if target_section.knowledge_point_ids:
            section_kps = target_section.knowledge_point_ids
            if isinstance(section_kps, str):
                try:
                    section_kps = json.loads(section_kps)
                except json.JSONDecodeError:
                    section_kps = []
            if isinstance(section_kps, list):
                knowledge_point_ids = [str(kp) for kp in section_kps if kp]
        
        # 方法2: 从Lesson的knowledge_point_id获取
        lessons = db.query(Lesson).filter(Lesson.section_id == target_section.id).all()
        for lesson in lessons:
            if lesson.knowledge_point_id and lesson.knowledge_point_id not in knowledge_point_ids:
                knowledge_point_ids.append(lesson.knowledge_point_id)
        
        if not knowledge_point_ids:
            return json.dumps({
                "success": False,
                "error": f"该小节「{target_section.title}」暂未配置知识点，无法提供习题"
            }, ensure_ascii=False)
        
        # ========== 5. 获取知识点名称映射 ==========
        node_name_map = {}
        kg = db.query(KnowledgeGraph).filter(KnowledgeGraph.study_goal_id == goal_id).first()
        if kg:
            nodes = _parse_nodes(kg.nodes)
            for node in nodes:
                node_id = str(node.get('id', ''))
                node_name_map[node_id] = node.get('label', '') or node.get('name', '') or node_id
        
        # ========== 6. 自适应筛选题目 ==========
        mastery_info = _get_node_mastery_info(db, student_id, goal_id, knowledge_point_ids)
        
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
            
            # 如果该知识点没有找到合适题目，尝试从整个题库中随机选取
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
        
        if not selected_questions:
            return json.dumps({
                "success": False,
                "error": "该小节暂无可练习的题目，请先学习课件内容"
            }, ensure_ascii=False)
        
        # ========== 7. 构建返回数据 ==========
        total_lessons = plan.total_lessons or db.query(Lesson).filter(Lesson.plan_id == plan.id).count()
        completed_lessons = plan.completed_lessons or 0
        progress_percent = round(completed_lessons / total_lessons * 100, 1) if total_lessons > 0 else 0
        
        # 难度统计
        difficulty_stats = {"basic": 0, "comprehensive": 0, "challenge": 0}
        for q in selected_questions:
            diff = q.get("difficulty", "basic")
            if diff in difficulty_stats:
                difficulty_stats[diff] += 1
        
        lesson_id_for_complete = None
        if target_lesson:
            lesson_id_for_complete = target_lesson.id
        else:
            first_uncompleted = db.query(Lesson).filter(
                Lesson.section_id == target_section.id,
                Lesson.is_completed == False
            ).order_by(Lesson.lesson_number).first()
            if first_uncompleted:
                lesson_id_for_complete = first_uncompleted.id
        
        result = {
            "success": True,
            "exercise_type": "section_practice",
            "exercise_id": f"ex_{goal_id}_{target_section.id}_{int(datetime.utcnow().timestamp())}",
            "goal_id": goal_id,
            "section_id": target_section.id,
            "section_title": target_section.title,
            "chapter_number": target_chapter.chapter_number if target_chapter else None,
            "chapter_title": target_chapter.title if target_chapter else "",
            "section_number": target_section.section_number if target_section else None,
            "lesson_id": lesson_id_for_complete,
            "exercises": selected_questions,
            "total": len(selected_questions),
            "difficulty_stats": difficulty_stats,
            "summary": f"共{len(selected_questions)}道习题（基础{difficulty_stats['basic']}题/综合{difficulty_stats['comprehensive']}题/挑战{difficulty_stats['challenge']}题），自适应匹配当前掌握度",
            "progress": {
                "completed_lessons": completed_lessons,
                "total_lessons": total_lessons,
                "progress_percent": progress_percent,
                "current_position": f"第{target_chapter.chapter_number}章第{target_section.section_number}节" if target_chapter and target_section else "",
                "progress_source": progress_source,
            },
            "mastery_summary": {
                node_id: info for node_id, info in mastery_info.items()
            }
        }
        
        logger.info(f"成功获取习题: section_id={target_section.id}, "
                    f"ch={target_chapter.chapter_number if target_chapter else '?'}/"
                    f"sec={target_section.section_number if target_section else '?'}, "
                    f"questions={len(selected_questions)}, "
                    f"progress={completed_lessons}/{total_lessons}")
        
        return json.dumps(result, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"获取习题失败: {e}", exc_info=True)
        return json.dumps({
            "success": False,
            "error": f"获取习题失败: {str(e)}"
        }, ensure_ascii=False)


# ========== 辅助函数 ==========

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
    
    - 刚开始学习(total_attempts < 3)或正确率<60% → basic
    - 正确率<80% → comprehensive
    - 正确率>=80% → challenge
    """
    if total_attempts < 3 or correct_rate < 60:
        return "basic"
    elif correct_rate < 80:
        return "comprehensive"
    else:
        return "challenge"


def _get_node_mastery_info(db: Session, student_id: int, goal_id: int, node_ids: list) -> dict:
    """获取多个知识点的掌握度信息"""
    from app.models.node_mastery import NodeMastery
    
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
    
    for node_id in node_ids:
        if str(node_id) not in result:
            result[str(node_id)] = {
                "mastery_level": 0,
                "correct_rate": 0,
                "total_attempts": 0
            }
    
    return result
