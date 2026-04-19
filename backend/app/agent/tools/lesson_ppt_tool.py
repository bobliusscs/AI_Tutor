"""
课件交付工具函数

提供从学习计划中获取当前学习进度课件的功能。
支持按章节定位，也可自动定位到学生当前进度。
优先使用Section级别的真实PPT课件内容。
"""
import json
import logging
from typing import Optional
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


async def get_current_lesson_ppt(
    goal_id: int,
    student_id: int,
    chapter_number: Optional[int] = None,
    section_number: Optional[int] = None,
    db: Session = None
) -> str:
    """
    获取指定章节或当前学习进度下的课时课件内容。
    
    定位逻辑：
    - 若指定chapter_number和section_number：返回该节下的课件
    - 若只指定chapter_number：返回该章下第一个未完成课时所在节的课件
    - 若都不指定：自动定位到学生当前学习进度
    
    课件来源优先级：
    1. Section.ppt_content（真实生成的丰富PPT）
    2. Lesson字段构建（回退方案，内容较简略）
    
    Args:
        goal_id: 学习目标ID
        student_id: 学生ID
        chapter_number: 章节序号（可选，从1开始）
        section_number: 节序号（可选，从1开始，需同时指定chapter_number）
        db: 数据库会话
        
    Returns:
        JSON字符串，包含课件数据和进度信息
    """
    try:
        from app.models.study_goal import StudyGoal
        from app.models.learning_plan import LearningPlan, Lesson, Chapter, Section
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
        
        # ========== 3. 定位当前课时和节 ==========
        target_lesson = None
        target_chapter = None
        target_section = None
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
                
                # 在该节下找第一个未完成的课时
                target_lesson = db.query(Lesson).filter(
                    Lesson.plan_id == plan.id,
                    Lesson.section_id == target_section.id,
                    Lesson.is_completed == False
                ).order_by(Lesson.lesson_number).first()
                
                # 该节全部完成，返回最后一个
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
                
                # 获取课时所在的节
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
                        progress_source = f"上一课时「{last_completed.title}」已完成，继续下一课时"
            
            # 优先级3：从头开始
            if not target_lesson:
                target_lesson = db.query(Lesson).filter(
                    Lesson.plan_id == plan.id,
                    Lesson.is_completed == False
                ).order_by(Lesson.lesson_number).first()
                if target_lesson:
                    progress_source = "刚开始学习，从第一课时开始"
            
            # 全部完成
            if not target_lesson:
                target_lesson = db.query(Lesson).filter(
                    Lesson.plan_id == plan.id
                ).order_by(Lesson.lesson_number.desc()).first()
                if target_lesson:
                    progress_source = "所有课时已完成"
            
            # 获取课时所在的节和章
            if target_lesson:
                if target_lesson.section_id:
                    target_section = db.query(Section).filter(Section.id == target_lesson.section_id).first()
                if target_lesson.chapter_id:
                    target_chapter = db.query(Chapter).filter(Chapter.id == target_lesson.chapter_id).first()
        
        if not target_lesson:
            return json.dumps({
                "success": False,
                "error": "没有找到可学习的课时"
            }, ensure_ascii=False)
        
        # 补充获取章节信息（自动定位时可能还没获取）
        if not target_chapter and target_lesson.chapter_id:
            target_chapter = db.query(Chapter).filter(Chapter.id == target_lesson.chapter_id).first()
        if not target_section and target_lesson.section_id:
            target_section = db.query(Section).filter(Section.id == target_lesson.section_id).first()
        
        # ========== 4. 构建进度信息 ==========
        total_lessons = plan.total_lessons or db.query(Lesson).filter(Lesson.plan_id == plan.id).count()
        completed_lessons = plan.completed_lessons or 0
        progress_percent = round(completed_lessons / total_lessons * 100, 1) if total_lessons > 0 else 0
        
        # 该节下的课时列表（用于前端导航）
        section_lessons = []
        if target_section:
            lessons_in_section = db.query(Lesson).filter(
                Lesson.section_id == target_section.id
            ).order_by(Lesson.lesson_number).all()
            section_lessons = [{
                "lesson_id": l.id,
                "lesson_number": l.lesson_number,
                "title": l.title,
                "is_completed": l.is_completed,
                "is_current": l.id == target_lesson.id
            } for l in lessons_in_section]
        
        # ========== 5. 获取课件内容（优先Section级PPT） ==========
        slides = None
        content_source = ""
        
        # 优先使用Section级别的真实PPT课件
        if target_section and target_section.ppt_generated and target_section.ppt_content:
            slides = _adapt_section_ppt(target_section.ppt_content, target_lesson, target_chapter, target_section)
            content_source = "section_ppt"
            logger.info(f"使用Section级PPT: section_id={target_section.id}, slides={len(slides)}")
        
        # 回退：从Lesson字段构建简略课件
        if not slides:
            slides = _build_slides_from_lesson(target_lesson, target_chapter, target_section)
            content_source = "lesson_fields"
            logger.info(f"回退到Lesson字段构建: lesson_id={target_lesson.id}, slides={len(slides)}")
        
        # 检查是否有有效的课件内容（新格式：封面+结束页至少2页，但内容页才是关键）
        content_slides = [s for s in slides if s.get("type") not in ("cover", "ending")]
        if not content_slides:
            return json.dumps({
                "success": False,
                "error": "该课时还没有生成课件内容"
            }, ensure_ascii=False)
        
        # ========== 6. 构建返回数据 ==========
        slide_titles = [s.get("title", "") for s in slides]
        summary = f"课件《{target_lesson.title}》包含{len(slides)}页幻灯片，涵盖：{'、'.join(slide_titles[:5])}{'等' if len(slides) > 5 else ''}"
        
        result = {
            "success": True,
            "ppt_type": "lesson",
            "content_source": content_source,  # 标记课件来源
            "lesson_id": target_lesson.id,
            "lesson_title": target_lesson.title,
            "lesson_number": target_lesson.lesson_number,
            "chapter_number": target_chapter.chapter_number if target_chapter else None,
            "chapter_title": target_chapter.title if target_chapter else "",
            "section_id": target_section.id if target_section else None,
            "section_number": target_section.section_number if target_section else None,
            "section_title": target_section.title if target_section else "",
            "slide_count": len(slides),
            "summary": summary,
            "slides": slides,
            "goal_id": goal_id,
            "is_completed": target_lesson.is_completed,
            # 学习进度
            "progress": {
                "completed_lessons": completed_lessons,
                "total_lessons": total_lessons,
                "progress_percent": progress_percent,
                "current_position": f"第{target_chapter.chapter_number}章第{target_section.section_number}节" if target_chapter and target_section else f"第{target_lesson.lesson_number}课时",
                "progress_source": progress_source,
            },
            # 该节下的课时列表（前端导航用）
            "section_lessons": section_lessons,
        }
        
        logger.info(f"成功获取课时课件: lesson_id={target_lesson.id}, "
                    f"ch={target_chapter.chapter_number if target_chapter else '?'}/"
                    f"sec={target_section.section_number if target_section else '?'}, "
                    f"slides={len(slides)}, source={content_source}, "
                    f"progress={completed_lessons}/{total_lessons}")
        
        return json.dumps(result, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"获取课时课件失败: {e}", exc_info=True)
        return json.dumps({
            "success": False,
            "error": f"获取课件失败: {str(e)}"
        }, ensure_ascii=False)


def _adapt_section_ppt(section_ppt_content: list, target_lesson, chapter=None, section=None) -> list:
    """
    将Section级别的PPT内容适配为工具返回格式。
    Section PPT是按节维度生成的完整课件，需要适配为课时维度的返回格式。
    新格式content可能是JSON对象（结构化），也可能是字符串（旧格式），需兼容。
    
    Args:
        section_ppt_content: Section.ppt_content（已生成的幻灯片列表）
        target_lesson: 当前定位到的课时对象
        chapter: 章对象
        section: 节对象
    
    Returns:
        适配后的幻灯片列表
    """
    adapted = []
    
    for i, slide in enumerate(section_ppt_content):
        # 适配字段名：Section PPT可能用"index"而非内置序号
        adapted_slide = {
            "type": slide.get("type", "content"),
            "layout": slide.get("layout", "focus"),
            "title": slide.get("title", ""),
            "content": slide.get("content", ""),  # 可能是字符串或JSON对象
            "audio_url": slide.get("audio_url", ""),
            "audio_duration": slide.get("audio_duration", 0),
        }
        
        # 保留notes（讲者备注）
        if slide.get("notes"):
            adapted_slide["notes"] = slide["notes"]
        
        # 保留exercise类型的questions字段
        if slide.get("type") == "exercise" and slide.get("questions"):
            adapted_slide["questions"] = slide["questions"]
        
        # 保留visual_hint（视觉提示）
        if slide.get("visual_hint"):
            adapted_slide["visual_hint"] = slide["visual_hint"]
        
        adapted.append(adapted_slide)
    
    return adapted


def _build_slides_from_lesson(lesson, chapter=None, section=None) -> list:
    """
    从课时字段构建幻灯片列表（回退方案，内容较简略）
    使用新的结构化content格式
    """
    slides = []
    
    # 1. 封面页
    location_parts = []
    if chapter:
        location_parts.append(f"第{chapter.chapter_number}章 {chapter.title}")
    if section:
        location_parts.append(f"第{section.section_number}节 {section.title}")
    location_str = " > ".join(location_parts)
    
    objectives = []
    if lesson.introduction:
        objectives.append(f"理解{lesson.title}的基本概念")
    if lesson.explanation:
        objectives.append(f"掌握{lesson.title}的核心原理")
    if lesson.example:
        objectives.append(f"能够运用{lesson.title}解决实际问题")
    
    slides.append({
        "type": "cover",
        "layout": "hero",
        "title": lesson.title,
        "content": {
            "title": lesson.title,
            "subtitle": location_str,
            "objectives": objectives[:3]
        },
        "notes": f"欢迎学习本课时的内容。本课时的主题是{lesson.title}。",
        "audio_url": "",
        "audio_duration": 0
    })
    
    # 2. 引入页
    if lesson.introduction:
        slides.append({
            "type": "intro",
            "layout": "focus",
            "title": "课程引入",
            "content": {
                "scene": lesson.introduction,
                "question": f"为什么{lesson.title}如此重要？",
                "answer_hint": "让我们一起来探索"
            },
            "notes": "通过生动的例子引入本节课的主题。",
            "audio_url": "",
            "audio_duration": 0
        })
    
    # 3. 核心讲解
    if lesson.explanation:
        # 尝试将内容拆分为要点
        explanation_points = []
        for para in lesson.explanation.split('\n'):
            para = para.strip()
            if para and len(para) > 5:
                explanation_points.append(para)
        
        if len(explanation_points) <= 1:
            slides.append({
                "type": "content",
                "layout": "list-highlight",
                "title": "核心讲解",
                "content": {
                    "main_idea": lesson.title,
                    "points": [
                        {"title": "核心内容", "detail": lesson.explanation, "icon": "lightbulb"}
                    ]
                },
                "notes": "详细讲解核心概念和原理。",
                "audio_url": "",
                "audio_duration": 0
            })
        else:
            points = []
            icons = ["lightbulb", "cog", "link", "star", "check"]
            for idx, para in enumerate(explanation_points[:5]):
                # 取前15字作为标题
                title_text = para[:20].rstrip('，。、：；') + '...' if len(para) > 20 else para
                points.append({
                    "title": title_text,
                    "detail": para,
                    "icon": icons[idx % len(icons)]
                })
            slides.append({
                "type": "content",
                "layout": "list-highlight",
                "title": "核心讲解",
                "content": {
                    "main_idea": f"深入理解{lesson.title}的核心原理",
                    "points": points
                },
                "notes": "详细讲解核心概念和原理。",
                "audio_url": "",
                "audio_duration": 0
            })
    
    # 4. 示例页
    if lesson.example:
        slides.append({
            "type": "example",
            "layout": "step-flow",
            "title": "示例演示",
            "content": {
                "case_title": f"{lesson.title}应用示例",
                "background": lesson.example[:100] if len(lesson.example) > 100 else lesson.example,
                "steps": [
                    {"label": "示例内容", "content": lesson.example}
                ],
                "insight": "通过具体示例帮助理解。"
            },
            "notes": "通过具体示例帮助理解。",
            "audio_url": "",
            "audio_duration": 0
        })
    
    # 5. 练习题
    if lesson.exercises:
        exercises = lesson.exercises
        if isinstance(exercises, str):
            try:
                exercises = json.loads(exercises)
            except:
                exercises = []
        
        if exercises:
            slides.append({
                "type": "exercise",
                "layout": "qa",
                "title": "巩固练习",
                "content": "请完成以下练习题：",
                "questions": exercises,
                "notes": "让学生独立完成练习，然后讲解答案。",
                "audio_url": "",
                "audio_duration": 0
            })
    
    # 6. 总结页
    if lesson.summary:
        summary_points = []
        for para in lesson.summary.split('\n'):
            para = para.strip()
            if para and len(para) > 3:
                keyword = para[:8].rstrip('，。、：；')
                summary_points.append({"point": para, "keyword": keyword})
        
        if not summary_points:
            summary_points = [{"point": lesson.summary, "keyword": lesson.title[:8]}]
        
        slides.append({
            "type": "summary",
            "layout": "list-highlight",
            "title": "课程总结",
            "content": {
                "key_takeaways": summary_points[:5],
                "mind_map_hint": f"{lesson.title}知识结构"
            },
            "notes": "总结本节课的重点内容。",
            "audio_url": "",
            "audio_duration": 0
        })
    
    # 7. 结束页
    slides.append({
        "type": "ending",
        "layout": "hero",
        "title": "本课结束",
        "content": {
            "message": f"恭喜完成「{lesson.title}」的学习！",
            "review_tip": f"建议复习{lesson.title}的核心概念"
        },
        "notes": "本课时学习完成，鼓励学生继续。",
        "audio_url": "",
        "audio_duration": 0
    })
    
    return slides
