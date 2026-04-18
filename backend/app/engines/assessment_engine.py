"""
诊断测评引擎 - 智能出题 + 深度分析，精准定位薄弱点
"""
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from datetime import datetime
import json
import math

from app.models.assessment import Assessment, QuestionBank
from app.models.memory import MemoryCurve
from app.services.ai_model_provider import AIModelProvider


class AssessmentEngine:
    """诊断测评引擎"""
    
    def __init__(self, db: Session, ai_provider: AIModelProvider):
        self.db = db
        self.ai_provider = ai_provider
    
    async def generate_assessment(
        self,
        student_id: int,
        lesson_id: int,
        knowledge_point_id: str,
        difficulty: str = "medium",
        question_count: int = 3
    ) -> Assessment:
        """
        生成测评题目
        
        Args:
            student_id: 学生 ID
            lesson_id: 课时 ID
            knowledge_point_id: 知识点 ID
            difficulty: 难度级别
            question_count: 题目数量
            
        Returns:
            Assessment: 测评记录对象
        """
        # 1. 从题库获取题目（如果有）
        questions = self._get_questions_from_bank(
            knowledge_point_id, 
            difficulty, 
            question_count
        )
        
        # 2. 如果题库不足，使用 AI 生成新题目
        if len(questions) < question_count:
            new_questions = await self.ai_provider.generate_questions(
                knowledge_point=knowledge_point_id,
                difficulty=difficulty,
                count=question_count - len(questions)
            )
            questions.extend(new_questions)
        
        # 3. 创建测评记录
        assessment = Assessment(
            student_id=student_id,
            lesson_id=lesson_id,
            assessment_type="practice",
            questions=json.dumps(questions, ensure_ascii=False),
            total_questions=len(questions),
            correct_answers=0,
            mastery_before=self._get_current_mastery(student_id, knowledge_point_id)
        )
        
        self.db.add(assessment)
        self.db.commit()
        self.db.refresh(assessment)
        
        return assessment
    
    def _get_questions_from_bank(
        self, 
        knowledge_point_id: str, 
        difficulty: str, 
        count: int
    ) -> List[dict]:
        """从题库获取题目"""
        questions = self.db.query(QuestionBank).filter(
            QuestionBank.knowledge_point_id == knowledge_point_id,
            QuestionBank.difficulty == difficulty
        ).limit(count).all()
        
        return [
            {
                "id": q.id,
                "question": q.question_text,
                "options": q.options,
                "answer": q.correct_answer,
                "explanation": q.explanation,
                "error_analysis": q.error_analysis
            }
            for q in questions
        ]
    
    def submit_assessment(
        self, 
        assessment_id: int, 
        user_answers: List[dict]
    ) -> Assessment:
        """
        提交测评答案
        
        Args:
            assessment_id: 测评 ID
            user_answers: 用户答案列表 [{question_id, answer, time_spent}]
            
        Returns:
            Assessment: 更新后的测评记录
        """
        assessment = self.db.query(Assessment).filter(Assessment.id == assessment_id).first()
        if not assessment:
            raise ValueError(f"测评不存在：{assessment_id}")
        
        questions = json.loads(assessment.questions) if isinstance(assessment.questions, str) else assessment.questions
        
        # 判题并统计
        correct_count = 0
        wrong_questions = []
        error_analysis = []
        
        for idx, qa in enumerate(user_answers):
            if idx >= len(questions):
                break
            
            question = questions[idx]
            is_correct = qa.get("answer", "").strip().upper() == question.get("answer", "").strip().upper()
            
            if is_correct:
                correct_count += 1
            else:
                wrong_questions.append({
                    "question_id": question.get("id"),
                    "question": question.get("question"),
                    "user_answer": qa.get("answer"),
                    "correct_answer": question.get("answer")
                })
                
                # 错误原因分析
                error_type = self._analyze_error_type(question, qa.get("answer"))
                error_analysis.append({
                    "question_id": question.get("id"),
                    "error_type": error_type,
                    "explanation": question.get("explanation")
                })
        
        # 更新测评记录
        assessment.correct_answers = correct_count
        assessment.score = (correct_count / len(questions)) * 100 if questions else 0
        assessment.wrong_questions = json.dumps(wrong_questions, ensure_ascii=False)
        assessment.error_analysis = json.dumps(error_analysis, ensure_ascii=False)
        
        # 计算测评后掌握度
        assessment.mastery_after = self._calculate_mastery_after(assessment)
        
        # 更新记忆曲线
        self._update_memory_curve(
            assessment.student_id,
            questions[0].get("knowledge_point_id") if questions else "",
            assessment.mastery_after
        )
        
        self.db.commit()
        self.db.refresh(assessment)
        
        return assessment
    
    def _analyze_error_type(self, question: dict, user_answer: str) -> str:
        """分析错误类型"""
        # TODO: 实现更智能的错误分析
        error_patterns = {
            "概念混淆": ["混淆", "误解"],
            "计算错误": ["算错", "粗心"],
            "思路偏差": ["方向错误", "方法不对"]
        }
        
        # 简单规则匹配
        for error_type, keywords in error_patterns.items():
            if any(keyword in (user_answer or "") for keyword in keywords):
                return error_type
        
        return "理解不深"
    
    def _calculate_mastery_after(self, assessment: Assessment) -> float:
        """计算测评后的掌握度"""
        score = assessment.score or 0
        
        # 使用 S 型函数将分数映射到 0-1 的掌握度
        mastery = 1 / (1 + math.exp(-(score - 50) / 15))
        
        return round(mastery, 2)
    
    def _get_current_mastery(self, student_id: int, knowledge_point_id: str) -> float:
        """获取当前掌握度"""
        memory_curve = self.db.query(MemoryCurve).filter(
            MemoryCurve.student_id == student_id,
            MemoryCurve.knowledge_point_id == knowledge_point_id
        ).first()
        
        if memory_curve:
            return memory_curve.memory_strength
        return 0.0
    
    def _update_memory_curve(
        self, 
        student_id: int, 
        knowledge_point_id: str, 
        mastery_level: float
    ):
        """更新记忆曲线"""
        memory_curve = self.db.query(MemoryCurve).filter(
            MemoryCurve.student_id == student_id,
            MemoryCurve.knowledge_point_id == knowledge_point_id
        ).first()
        
        if memory_curve:
            memory_curve.memory_strength = mastery_level
            memory_curve.last_reviewed_at = datetime.utcnow()
            memory_curve.review_count += 1
            
            # 计算下次复习时间
            memory_curve.next_review_at = self._calculate_next_review_time(mastery_level)
        else:
            # 创建新的记忆曲线
            memory_curve = MemoryCurve(
                student_id=student_id,
                knowledge_point_id=knowledge_point_id,
                first_learned_at=datetime.utcnow(),
                memory_strength=mastery_level,
                review_count=1,
                next_review_at=self._calculate_next_review_time(mastery_level)
            )
            self.db.add(memory_curve)
        
        self.db.commit()
    
    def _calculate_next_review_time(self, mastery_level: float) -> datetime:
        """根据掌握度计算下次复习时间"""
        # 艾宾浩斯遗忘曲线简化模型
        # 掌握度越高，间隔时间越长
        days_map = {
            (0.0, 0.3): 1,    # 掌握度低，1 天后复习
            (0.3, 0.6): 3,    # 掌握度中，3 天后复习
            (0.6, 0.8): 7,    # 掌握度较高，7 天后复习
            (0.8, 1.0): 14    # 掌握度高，14 天后复习
        }
        
        days = 7  # 默认
        for (min_val, max_val), d in days_map.items():
            if min_val <= mastery_level < max_val:
                days = d
                break
        
        return datetime.utcnow() + timedelta(days=days)
    
    def generate_diagnostic_report(self, student_id: int) -> dict:
        """
        生成诊断报告
        
        Args:
            student_id: 学生 ID
            
        Returns:
            诊断报告数据
        """
        # 获取所有测评记录
        assessments = self.db.query(Assessment).filter(
            Assessment.student_id == student_id
        ).order_by(Assessment.created_at.desc()).limit(10).all()
        
        if not assessments:
            return {"message": "暂无测评记录"}
        
        # 统计整体情况
        total_questions = sum(a.total_questions or 0 for a in assessments)
        total_correct = sum(a.correct_answers or 0 for a in assessments)
        overall_accuracy = (total_correct / total_questions * 100) if total_questions > 0 else 0
        
        # 知识图谱热力图数据
        mastery_map = {}
        for assessment in assessments:
            questions = json.loads(assessment.questions) if isinstance(assessment.questions, str) else assessment.questions
            if questions:
                kp_id = questions[0].get("knowledge_point_id")
                if kp_id:
                    mastery_map[kp_id] = assessment.mastery_after
        
        return {
            "overall_accuracy": round(overall_accuracy, 1),
            "total_assessments": len(assessments),
            "mastery_map": mastery_map,
            "recent_performance": [
                {
                    "date": a.created_at.strftime("%Y-%m-%d"),
                    "score": a.score,
                    "lesson": a.lesson.title if a.lesson else "Unknown"
                }
                for a in assessments[:5]
            ],
            "weak_points": self._identify_weak_points(assessments)
        }
    
    def _identify_weak_points(self, assessments: List[Assessment]) -> List[dict]:
        """识别薄弱点"""
        weak_points = []
        
        for assessment in assessments:
            if assessment.score and assessment.score < 60:
                questions = json.loads(assessment.questions) if isinstance(assessment.questions, str) else assessment.questions
                if questions:
                    weak_points.append({
                        "knowledge_point": questions[0].get("name"),
                        "mastery": assessment.mastery_after,
                        "suggestion": "建议重新学习相关课时"
                    })
        
        return weak_points[:3]  # 返回最弱的 3 个点


# 需要导入 timedelta
from datetime import timedelta
