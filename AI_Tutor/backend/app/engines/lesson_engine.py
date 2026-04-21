"""
课时教学引擎 - 结构化课时内容，对话式交互教学
"""
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
import json

from app.models.learning_plan import Lesson
from app.models.assessment import Assessment


class LessonEngine:
    """课时教学引擎"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_lesson(self, lesson_id: int) -> Optional[Lesson]:
        """获取课时详情"""
        return self.db.query(Lesson).filter(Lesson.id == lesson_id).first()
    
    def format_lesson_for_chat(self, lesson: Lesson, section: str = "all") -> dict:
        """
        将课时内容格式化为PPT幻灯片形式（新结构化格式）
        
        Args:
            lesson: 课时对象
            section: 要展示的章节（introduction/explanation/example/exercises/summary/all）
            
        Returns:
            格式化后的PPT幻灯片内容
        """
        # 获取原始内容，确保不为空
        introduction_raw = lesson.introduction or ""
        explanation_raw = lesson.explanation or ""
        example_raw = lesson.example or ""
        summary_raw = lesson.summary or ""
        
        # 解析练习题
        exercises_data = []
        if lesson.exercises:
            try:
                exercises_data = json.loads(lesson.exercises) if isinstance(lesson.exercises, str) else lesson.exercises
            except:
                exercises_data = []
        
        # 尝试解析内容为 slides 格式（新的PPT格式）
        try:
            # 检查是否已经是 slides 格式存储在 introduction 中
            intro_data = json.loads(introduction_raw)
            if isinstance(intro_data, dict) and 'slides' in intro_data:
                return intro_data
        except:
            pass
        
        # 兼容旧格式：将传统章节转换为结构化 slides 格式
        slides = []
        
        # 封面
        objectives = []
        if introduction_raw:
            objectives.append(f"理解{lesson.title}的基本概念")
        if explanation_raw:
            objectives.append(f"掌握{lesson.title}的核心原理")
        if example_raw:
            objectives.append(f"能够运用{lesson.title}解决实际问题")
        
        slides.append({
            "type": "cover",
            "layout": "hero",
            "title": lesson.title,
            "content": {
                "title": lesson.title,
                "subtitle": f"预计学习时长：{lesson.estimated_minutes} 分钟",
                "objectives": objectives[:3]
            }
        })
        
        # 课程引入
        if introduction_raw:
            slides.append({
                "type": "intro",
                "layout": "focus",
                "title": "课程引入",
                "content": {
                    "scene": introduction_raw,
                    "question": f"为什么{lesson.title}如此重要？",
                    "answer_hint": "让我们一起来探索"
                }
            })
        
        # 核心讲解
        if explanation_raw:
            # 尝试拆分为要点
            points = []
            icons = ["lightbulb", "cog", "link", "star", "check"]
            for idx, para in enumerate([p.strip() for p in explanation_raw.split('\n') if p.strip() and len(p.strip()) > 5][:5]):
                title_text = para[:20].rstrip('，。、：；') + '...' if len(para) > 20 else para
                points.append({"title": title_text, "detail": para, "icon": icons[idx % len(icons)]})
            if not points:
                points = [{"title": "核心内容", "detail": explanation_raw, "icon": "lightbulb"}]
            
            slides.append({
                "type": "content",
                "layout": "list-highlight",
                "title": "核心讲解",
                "content": {
                    "main_idea": f"深入理解{lesson.title}",
                    "points": points
                }
            })
        
        # 示例演示
        if example_raw:
            slides.append({
                "type": "example",
                "layout": "step-flow",
                "title": "示例演示",
                "content": {
                    "case_title": f"{lesson.title}应用示例",
                    "background": example_raw[:100] if len(example_raw) > 100 else example_raw,
                    "steps": [{"label": "示例", "content": example_raw}],
                    "insight": "通过具体示例帮助理解"
                }
            })
        
        # 课堂练习
        if exercises_data:
            slides.append({
                "type": "exercise",
                "layout": "qa",
                "title": "课堂练习",
                "content": "请完成以下练习题：",
                "questions": exercises_data
            })
        
        # 课程总结
        if summary_raw:
            takeaways = []
            for para in [p.strip() for p in summary_raw.split('\n') if p.strip() and len(p.strip()) > 3][:5]:
                keyword = para[:8].rstrip('，。、：；')
                takeaways.append({"point": para, "keyword": keyword})
            if not takeaways:
                takeaways = [{"point": summary_raw, "keyword": lesson.title[:8]}]
            
            slides.append({
                "type": "summary",
                "layout": "list-highlight",
                "title": "课程总结",
                "content": {
                    "key_takeaways": takeaways,
                    "mind_map_hint": f"{lesson.title}知识结构"
                }
            })
        
        if section == "all":
            return {
                "slides": slides,
                "estimated_minutes": lesson.estimated_minutes
            }
        else:
            content_map = {
                "introduction": introduction_raw,
                "explanation": explanation_raw,
                "example": example_raw,
                "exercises": str(exercises_data),
                "summary": summary_raw
            }
            return {
                "section": section,
                "content": content_map.get(section, "")
            }
    
    def _format_exercises(self, exercises: List[dict]) -> str:
        """格式化练习题"""
        formatted = []
        for idx, exercise in enumerate(exercises, 1):
            difficulty_map = {
                "easy": "⭐",
                "medium": "⭐⭐",
                "hard": "⭐⭐⭐"
            }
            
            difficulty = exercise.get("difficulty", "easy")
            question = exercise.get("question", "")
            options = exercise.get("options")
            
            formatted.append(f"""
【题目{idx}】{difficulty_map.get(difficulty, '⭐')}
{question}
{self._format_options(options) if options else ''}""")
        
        return "\n".join(formatted)
    
    def _format_options(self, options: List[str]) -> str:
        """格式化选项"""
        return "\n".join([f"{opt}" for opt in options])
    
    async def interact_with_student(
        self, 
        lesson_id: int, 
        student_message: str,
        current_section: str = "introduction"
    ) -> dict:
        """
        与学生进行交互式对话
        
        Args:
            lesson_id: 课时 ID
            student_message: 学生消息
            current_section: 当前章节
            
        Returns:
            AI 回复内容
        """
        lesson = self.get_lesson(lesson_id)
        if not lesson:
            return {"error": "课时不存在"}
        
        # 简单的状态机逻辑
        if "不懂" in student_message or "不明白" in student_message:
            return {
                "response": f"没关系，我再详细解释一下这个知识点...\n\n[AI 会根据学生的具体问题提供针对性解释]",
                "next_action": "stay"
            }
        
        elif "好了" in student_message or "懂了" in student_message or "继续" in student_message:
            next_section = self._get_next_section(current_section)
            if next_section:
                content = self.format_lesson_for_chat(lesson, next_section)
                return {
                    "response": content["content"],
                    "next_action": "proceed",
                    "next_section": next_section
                }
            else:
                return {
                    "response": "太棒了！你已经完成了本节课的所有内容。要做几道练习题检验一下吗？",
                    "next_action": "suggest_assessment"
                }
        
        elif "提问" in student_message or "为什么" in student_message:
            return {
                "response": "[AI 根据学生的问题提供详细解答，使用生活化类比和具体例子]",
                "next_action": "stay"
            }
        
        else:
            return {
                "response": "明白了！如果有任何问题随时问我。准备好了就说'继续'哦~",
                "next_action": "wait"
            }
    
    def _get_next_section(self, current: str) -> Optional[str]:
        """获取下一章节"""
        section_order = ["introduction", "explanation", "example", "exercises", "summary"]
        
        try:
            current_idx = section_order.index(current)
            if current_idx < len(section_order) - 1:
                return section_order[current_idx + 1]
        except ValueError:
            pass
        
        return None
    
    def evaluate_exercise(
        self, 
        lesson_id: int, 
        exercise_index: int, 
        user_answer: str
    ) -> dict:
        """
        评估练习答案
        
        Args:
            lesson_id: 课时 ID
            exercise_index: 题目索引
            user_answer: 用户答案
            
        Returns:
            评估结果
        """
        lesson = self.get_lesson(lesson_id)
        if not lesson:
            return {"error": "课时不存在"}
        
        exercises = json.loads(lesson.exercises) if isinstance(lesson.exercises, str) else lesson.exercises
        
        if exercise_index >= len(exercises):
            return {"error": "题目不存在"}
        
        exercise = exercises[exercise_index]
        correct_answer = exercise.get("answer")
        explanation = exercise.get("explanation")
        
        is_correct = user_answer.strip().upper() == correct_answer.strip().upper()
        
        return {
            "is_correct": is_correct,
            "correct_answer": correct_answer,
            "explanation": explanation,
            "feedback": "✅ 正确！" if is_correct else "❌ 不对哦，再想想~"
        }
    
    def create_assessment(self, lesson_id: int, student_id: int) -> Assessment:
        """创建测评记录"""
        assessment = Assessment(
            student_id=student_id,
            lesson_id=lesson_id,
            assessment_type="practice"
        )
        self.db.add(assessment)
        self.db.commit()
        self.db.refresh(assessment)
        return assessment
