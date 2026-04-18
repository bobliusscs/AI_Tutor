"""
记忆与复习系统 - 基于艾宾浩斯遗忘曲线的智能复习规划
"""
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import math
import json

from app.models.memory import MemoryCurve, ReviewSchedule
from app.models.assessment import QuestionBank


class MemoryEngine:
    """记忆系统引擎"""
    
    # 艾宾浩斯复习间隔（天）
    REVIEW_INTERVALS = [1, 3, 7, 14, 30]
    
    def __init__(self, db: Session):
        self.db = db
    
    def calculate_forgetting_curve(
        self, 
        memory_strength: float, 
        days_elapsed: int
    ) -> float:
        """
        计算遗忘率 - 基于艾宾浩斯遗忘曲线
        
        R = e^(-t/S)
        R: 记忆保留率
        t: 经过的时间
        S: 记忆强度
        
        Args:
            memory_strength: 记忆强度 (0-1)
            days_elapsed: 经过的天数
            
        Returns:
            当前记忆保留率 (0-1)
        """
        if memory_strength <= 0:
            return 0.0
        
        # 将记忆强度转换为记忆强度参数 S
        # memory_strength 越大，S 越大，遗忘越慢
        S = 10 * memory_strength + 1
        
        # 计算遗忘率
        forgetting_rate = math.exp(-days_elapsed / S)
        
        return round(forgetting_rate, 2)
    
    def calculate_optimal_review_time(
        self, 
        memory_curve: MemoryCurve
    ) -> datetime:
        """
        计算最佳复习时间
        
        Args:
            memory_curve: 记忆曲线对象
            
        Returns:
            最佳复习时间
        """
        # 获取当前复习次数对应的间隔
        review_count = min(memory_curve.review_count, len(self.REVIEW_INTERVALS))
        interval_days = self.REVIEW_INTERVALS[review_count - 1] if review_count > 0 else 1
        
        # 根据记忆保留率微调
        if memory_curve.last_reviewed_at:
            days_since_last_review = (datetime.utcnow() - memory_curve.last_reviewed_at).days
            current_retention = self.calculate_forgetting_curve(
                memory_curve.memory_strength,
                days_since_last_review
            )
            
            # 如果 retention < 0.65（65% 遗忘阈值），提前复习
            if current_retention < 0.65:
                interval_days = max(1, interval_days // 2)
        
        # 计算下次复习时间
        if memory_curve.last_reviewed_at:
            next_review = memory_curve.last_reviewed_at + timedelta(days=interval_days)
        else:
            next_review = datetime.utcnow() + timedelta(days=1)
        
        return next_review
    
    def update_memory_after_learning(
        self,
        student_id: int,
        knowledge_point_id: str
    ) -> MemoryCurve:
        """
        学习后更新记忆曲线
        
        Args:
            student_id: 学生 ID
            knowledge_point_id: 知识点 ID
            
        Returns:
            更新后的记忆曲线
        """
        # 查找或创建记忆曲线
        memory_curve = self.db.query(MemoryCurve).filter(
            MemoryCurve.student_id == student_id,
            MemoryCurve.knowledge_point_id == knowledge_point_id
        ).first()
        
        now = datetime.utcnow()
        
        if memory_curve:
            # 更新现有记录
            memory_curve.first_learned_at = now
            memory_curve.last_reviewed_at = now
            memory_curve.review_count = 0
            memory_curve.memory_strength = 0.3  # 初始学习后，记忆强度设为 0.3
            memory_curve.next_review_at = self.calculate_optimal_review_time(memory_curve)
        else:
            # 创建新记录
            memory_curve = MemoryCurve(
                student_id=student_id,
                knowledge_point_id=knowledge_point_id,
                first_learned_at=now,
                last_reviewed_at=now,
                review_count=0,
                memory_strength=0.3,
                next_review_at=now + timedelta(days=1)
            )
            self.db.add(memory_curve)
        
        self.db.commit()
        self.db.refresh(memory_curve)
        
        return memory_curve
    
    def update_memory_after_review(
        self,
        student_id: int,
        knowledge_point_id: str,
        review_result: str  # "excellent" / "good" / "poor"
    ) -> MemoryCurve:
        """
        复习后更新记忆曲线
        
        Args:
            student_id: 学生 ID
            knowledge_point_id: 知识点 ID
            review_result: 复习效果
            
        Returns:
            更新后的记忆曲线
        """
        memory_curve = self.db.query(MemoryCurve).filter(
            MemoryCurve.student_id == student_id,
            MemoryCurve.knowledge_point_id == knowledge_point_id
        ).first()
        
        if not memory_curve:
            raise ValueError(f"记忆曲线不存在")
        
        # 根据复习效果调整记忆强度
        strength_delta = {
            "excellent": 0.25,  # 优秀，大幅提升
            "good": 0.15,       # 良好，中幅提升
            "poor": 0.05        # 较差，小幅提升
        }
        
        memory_curve.memory_strength = min(1.0, memory_curve.memory_strength + strength_delta.get(review_result, 0.1))
        memory_curve.review_count += 1
        memory_curve.last_reviewed_at = datetime.utcnow()
        
        # 记录复习历史
        review_history = memory_curve.review_history or []
        review_history.append({
            "date": datetime.utcnow().isoformat(),
            "result": review_result,
            "memory_strength": memory_curve.memory_strength
        })
        memory_curve.review_history = review_history
        
        # 检查是否已牢固掌握
        if memory_curve.memory_strength >= 0.9 and memory_curve.review_count >= 5:
            memory_curve.is_mastered = True
        
        # 计算下次复习时间
        memory_curve.next_review_at = self.calculate_optimal_review_time(memory_curve)
        
        self.db.commit()
        self.db.refresh(memory_curve)
        
        return memory_curve
    
    def get_review_schedule(self, student_id: int, days: int = 7) -> List[dict]:
        """
        获取未来 N 天的复习计划
        
        Args:
            student_id: 学生 ID
            days: 天数范围
            
        Returns:
            复习计划列表
        """
        start_date = datetime.utcnow()
        end_date = start_date + timedelta(days=days)
        
        # 查询需要复习的记忆曲线
        memory_curves = self.db.query(MemoryCurve).filter(
            MemoryCurve.student_id == student_id,
            MemoryCurve.next_review_at <= end_date,
            MemoryCurve.is_mastered == False
        ).all()
        
        schedule = []
        for curve in memory_curves:
            # 计算遗忘率
            if curve.last_reviewed_at:
                days_elapsed = (datetime.utcnow() - curve.last_reviewed_at).days
                retention = self.calculate_forgetting_curve(curve.memory_strength, days_elapsed)
            else:
                retention = 0.5
            
            schedule.append({
                "knowledge_point_id": curve.knowledge_point_id,
                "scheduled_date": curve.next_review_at,
                "urgency": "high" if retention < 0.5 else "medium" if retention < 0.7 else "low",
                "current_retention": retention,
                "review_count": curve.review_count,
                "memory_strength": curve.memory_strength
            })
        
        # 按紧急程度排序
        schedule.sort(key=lambda x: x["current_retention"])
        
        return schedule
    
    def generate_review_session(
        self,
        student_id: int,
        knowledge_point_id: str,
        question_count: int = 3
    ) -> dict:
        """
        生成微复习会话
        
        Args:
            student_id: 学生 ID
            knowledge_point_id: 知识点 ID
            question_count: 题目数量
            
        Returns:
            复习会话数据
        """
        # 从题库获取题目
        questions = self.db.query(QuestionBank).filter(
            QuestionBank.knowledge_point_id == knowledge_point_id
        ).limit(question_count).all()
        
        if not questions:
            return {
                "error": "暂无复习题目",
                "questions": []
            }
        
        # 格式化题目
        formatted_questions = []
        for q in questions:
            formatted_questions.append({
                "id": q.id,
                "question": q.question_text,
                "options": q.options,
                "type": "quick_review" if q.difficulty == "easy" else "application"
            })
        
        return {
            "knowledge_point_id": knowledge_point_id,
            "review_type": "micro_review",
            "estimated_minutes": len(formatted_questions) * 2,
            "questions": formatted_questions
        }
    
    def check_streak(self, student_id: int) -> dict:
        """
        检查学习连续性
        
        Args:
            student_id: 学生 ID
            
        Returns:
            streak 信息
        """
        from app.models.student import Student
        
        student = self.db.query(Student).filter(Student.id == student_id).first()
        if not student:
            return {"error": "学生不存在"}
        
        today = datetime.utcnow().date()
        
        # 检查上次学习日期
        if student.last_study_date:
            last_date = student.last_study_date.date()
            days_diff = (today - last_date).days
            
            if days_diff == 0:
                # 今天已经学习过
                message = "今天已经学习过了，继续保持！🔥"
            elif days_diff == 1:
                # 昨天学习过，今天是连续的第 N 天
                message = f"太棒了！今天是你的第{student.study_streak}天连续学习！🎉"
            else:
                # 中断了
                message = "学习中断了，重新开始吧！💪"
                student.study_streak = 0
        else:
            # 第一次学习
            message = "开始你的第一次学习之旅吧！🚀"
            student.study_streak = 0
        
        self.db.commit()
        
        return {
            "current_streak": student.study_streak,
            "last_study_date": student.last_study_date.isoformat() if student.last_study_date else None,
            "message": message
        }
    
    def update_study_streak(self, student_id: int):
        """更新学习连续性"""
        from app.models.student import Student
        
        student = self.db.query(Student).filter(Student.id == student_id).first()
        if not student:
            return
        
        today = datetime.utcnow().date()
        
        if student.last_study_date:
            last_date = student.last_study_date.date()
            days_diff = (today - last_date).days
            
            if days_diff == 1:
                # 连续学习
                student.study_streak += 1
            elif days_diff > 1:
                # 中断后重新开始
                student.study_streak = 1
        else:
            # 第一次学习
            student.study_streak = 1
        
        student.last_study_date = datetime.utcnow()
        self.db.commit()
    
    def get_memory_statistics(self, student_id: int) -> dict:
        """获取记忆统计数据"""
        # 查询所有记忆曲线
        curves = self.db.query(MemoryCurve).filter(
            MemoryCurve.student_id == student_id
        ).all()
        
        if not curves:
            return {"message": "暂无学习记录"}
        
        total_points = len(curves)
        mastered_points = sum(1 for c in curves if c.is_mastered)
        avg_strength = sum(c.memory_strength for c in curves) / total_points
        
        # 按遗忘风险分组
        high_risk = 0
        medium_risk = 0
        low_risk = 0
        
        for curve in curves:
            if curve.last_reviewed_at:
                days_elapsed = (datetime.utcnow() - curve.last_reviewed_at).days
                retention = self.calculate_forgetting_curve(curve.memory_strength, days_elapsed)
                
                if retention < 0.5:
                    high_risk += 1
                elif retention < 0.7:
                    medium_risk += 1
                else:
                    low_risk += 1
        
        return {
            "total_knowledge_points": total_points,
            "mastered_points": mastered_points,
            "average_memory_strength": round(avg_strength, 2),
            "forgetting_risk": {
                "high": high_risk,
                "medium": medium_risk,
                "low": low_risk
            },
            "next_review_count": sum(1 for c in curves if c.next_review_at and c.next_review_at <= datetime.utcnow())
        }
    
    def analyze_learning_style(self, student_id: int) -> dict:
        """
        分析用户学习风格 - 基于学习行为数据和Agent交互分析
        
        学习风格类型:
        - visual: 视觉型 - 偏好图表、颜色、空间信息
        - auditory: 听觉型 - 偏好听讲、讨论、音频
        - reading: 阅读型 - 偏好文字材料、笔记
        - kinesthetic: 动觉型 - 偏好动手实践、案例演练
        
        Args:
            student_id: 学生 ID
            
        Returns:
            学习风格分析结果
        """
        from app.models.student import Student
        from app.models.learning_stage import LearningStage
        from app.models.agent_session import AgentSession
        
        student = self.db.query(Student).filter(Student.id == student_id).first()
        if not student:
            return {"error": "学生不存在"}
        
        # 如果已有学习风格记录，直接返回
        if student.learning_style and student.learning_style.get("style_scores"):
            return {
                "has_record": True,
                "primary_style": student.learning_style.get("primary_style", "visual"),
                "style_scores": student.learning_style.get("style_scores", {}),
                "preferred_time": student.learning_style.get("preferred_time", "morning"),
                "study_duration": student.learning_style.get("study_duration", 45),
                "last_updated": student.learning_style.get("last_updated")
            }
        
        # 收集多维度数据进行分析
        analysis_data = {
            "visual_evidence": 0,      # 视觉偏好证据
            "auditory_evidence": 0,     # 听觉偏好证据
            "reading_evidence": 0,      # 阅读偏好证据
            "kinesthetic_evidence": 0,  # 动觉偏好证据
        }
        
        # 1. 基于学习阶段分析
        learning_stages = self.db.query(LearningStage).filter(
            LearningStage.student_id == student_id
        ).all()
        
        for stage in learning_stages:
            if stage.stage_type == "video":
                analysis_data["visual_evidence"] += 3
            elif stage.stage_type == "reading":
                analysis_data["reading_evidence"] += 3
            elif stage.stage_type == "practice":
                analysis_data["kinesthetic_evidence"] += 3
            elif stage.stage_type == "discussion":
                analysis_data["auditory_evidence"] += 3
        
        # 2. 基于Agent会话分析学习行为模式
        sessions = self.db.query(AgentSession).filter(
            AgentSession.student_id == student_id
        ).limit(20).all()
        
        # 关键词分析
        discussion_keywords = ["讨论", "讲解", "为什么", "如何理解", "举例", "区别", "对话", "音频", "听"]
        reading_keywords = ["阅读", "文字", "笔记", "抄写", "文档", "教材", "书面"]
        visual_keywords = ["图表", "图片", "视觉", "颜色", "图示", "思维导图", "流程图", "可视化"]
        practice_keywords = ["练习", "做题", "实践", "实验", "应用", "案例", "动手", "操作"]
        
        for session in sessions:
            session_text = f"{session.context or ''} {getattr(session, 'messages', '') if hasattr(session, 'messages') else ''}".lower()
            for kw in discussion_keywords:
                if kw in session_text:
                    analysis_data["auditory_evidence"] += 1
            for kw in reading_keywords:
                if kw in session_text:
                    analysis_data["reading_evidence"] += 1
            for kw in visual_keywords:
                if kw in session_text:
                    analysis_data["visual_evidence"] += 1
            for kw in practice_keywords:
                if kw in session_text:
                    analysis_data["kinesthetic_evidence"] += 1
        
        # 3. 基于学生背景分析
        if student.background:
            bg_str = str(student.background).lower()
            if "visual" in bg_str or "视觉" in bg_str:
                analysis_data["visual_evidence"] += 5
            if "auditory" in bg_str or "听觉" in bg_str:
                analysis_data["auditory_evidence"] += 5
            if "reading" in bg_str or "阅读" in bg_str:
                analysis_data["reading_evidence"] += 5
            if "kinesthetic" in bg_str or "动觉" in bg_str or "动手" in bg_str:
                analysis_data["kinesthetic_evidence"] += 5
        
        # 转换为0-100的得分
        max_evidence = max(analysis_data.values()) if max(analysis_data.values()) > 0 else 1
        
        style_scores = {
            "visual": round(analysis_data["visual_evidence"] / max_evidence * 60 + 30),
            "auditory": round(analysis_data["auditory_evidence"] / max_evidence * 60 + 30),
            "reading": round(analysis_data["reading_evidence"] / max_evidence * 60 + 30),
            "kinesthetic": round(analysis_data["kinesthetic_evidence"] / max_evidence * 60 + 30)
        }
        
        # 确保有差异性：如果所有得分太接近，使用默认分布
        score_range = max(style_scores.values()) - min(style_scores.values())
        if score_range < 5:
            # 初次使用，分配一个合理的默认分布
            style_scores = {
                "visual": 65,
                "auditory": 55,
                "reading": 70,
                "kinesthetic": 50
            }
        
        # 根据学习时间推断最佳时段
        preferred_time = "morning"
        if student.last_study_date:
            hour = student.last_study_date.hour
            if 14 <= hour < 18:
                preferred_time = "afternoon"
            elif hour >= 18 or hour < 6:
                preferred_time = "evening"
        
        # 计算最佳学习时长（基于连续学习天数和平均记忆强度）
        avg_strength = 0.5
        if curves := self.db.query(MemoryCurve).filter(MemoryCurve.student_id == student_id).all():
            avg_strength = sum(c.memory_strength for c in curves) / len(curves)
        
        study_duration = 30 + int(avg_strength * 30)  # 30-60分钟
        
        # 确定主要学习风格
        primary_style = max(style_scores, key=style_scores.get)
        
        # 保存到学生记录
        learning_style_data = {
            "primary_style": primary_style,
            "style_scores": style_scores,
            "preferred_time": preferred_time,
            "study_duration": study_duration,
            "last_updated": datetime.utcnow().isoformat()
        }
        
        student.learning_style = learning_style_data
        self.db.commit()
        
        return {
            "has_record": False,
            "primary_style": primary_style,
            "style_scores": style_scores,
            "preferred_time": preferred_time,
            "study_duration": study_duration,
            "last_updated": learning_style_data["last_updated"]
        }
    
    def update_learning_style(self, student_id: int, style_data: dict) -> dict:
        """
        更新用户学习风格偏好
        
        Args:
            student_id: 学生 ID
            style_data: 新的学习风格数据
            
        Returns:
            更新后的学习风格
        """
        from app.models.student import Student
        
        student = self.db.query(Student).filter(Student.id == student_id).first()
        if not student:
            return {"error": "学生不存在"}
        
        # 验证并更新学习风格
        valid_styles = ["visual", "auditory", "reading", "kinesthetic"]
        valid_times = ["morning", "afternoon", "evening"]
        
        style_scores = style_data.get("style_scores", student.learning_style.get("style_scores") if student.learning_style else {})
        primary_style = style_data.get("primary_style", max(style_scores, key=style_scores.get) if style_scores else "visual")
        
        # 确保 primary_style 在有效值中
        if primary_style not in valid_styles:
            primary_style = max(style_scores, key=style_scores.get) if style_scores else "visual"
        
        preferred_time = style_data.get("preferred_time", "morning")
        if preferred_time not in valid_times:
            preferred_time = "morning"
        
        learning_style_data = {
            "primary_style": primary_style,
            "style_scores": style_scores,
            "preferred_time": preferred_time,
            "study_duration": style_data.get("study_duration", student.learning_style.get("study_duration", 45) if student.learning_style else 45),
            "last_updated": datetime.utcnow().isoformat()
        }
        
        student.learning_style = learning_style_data
        self.db.commit()
        
        return learning_style_data
    
    def get_learning_summary(self, student_id: int) -> dict:
        """
        获取学习综合情况 - 用于学习风格组件展示
        
        Returns:
            综合学习情况摘要（包含多维度分析）
        """
        from app.models.student import Student
        from app.models.study_goal import StudyGoal
        from app.models.agent_session import AgentSession
        from app.models.node_mastery import NodeMastery
        
        student = self.db.query(Student).filter(Student.id == student_id).first()
        if not student:
            return {"error": "学生不存在"}
        
        # 获取学习目标统计
        goals = self.db.query(StudyGoal).filter(StudyGoal.student_id == student_id).all()
        total_goals = len(goals)
        completed_goals = sum(1 for g in goals if g.status == "completed")
        in_progress_goals = [g for g in goals if g.status != "completed"]
        
        # 获取知识点掌握情况 - 优先从 NodeMastery 表获取（练习答题更新的数据）
        node_masteries = self.db.query(NodeMastery).filter(
            NodeMastery.student_id == student_id
        ).all()
        
        # 同时获取 MemoryCurve 数据（用于复习相关统计）
        curves = self.db.query(MemoryCurve).filter(MemoryCurve.student_id == student_id).all()
        
        # 使用 NodeMastery 计算掌握情况
        total_knowledge_points = len(node_masteries) if node_masteries else len(curves)
        mastered_points = len([m for m in node_masteries if m.mastery_level >= 80]) if node_masteries else sum(1 for c in curves if c.is_mastered)
        
        # 计算整体掌握度 - 综合 NodeMastery 和 MemoryCurve
        overall_mastery = 0
        avg_memory_strength = 0
        if node_masteries:
            # 优先使用 NodeMastery 的掌握度数据
            overall_mastery = round(sum(m.mastery_level or 0 for m in node_masteries) / len(node_masteries), 1)
            avg_memory_strength = overall_mastery / 100
        elif total_knowledge_points > 0:
            avg_memory_strength = sum(c.memory_strength for c in curves) / total_knowledge_points
            overall_mastery = round(avg_memory_strength * 100)
        
        # 复习紧迫度分析
        urgent_reviews = 0
        upcoming_reviews = 0
        for curve in curves:
            if curve.next_review_at:
                time_diff = (curve.next_review_at - datetime.utcnow()).total_seconds()
                if time_diff <= 0:
                    urgent_reviews += 1
                elif time_diff <= 86400:  # 24小时内
                    upcoming_reviews += 1
        
        # 学习效率分析
        study_efficiency = 0
        if student.total_learning_time > 0 and total_knowledge_points > 0:
            study_efficiency = round((mastered_points / max(1, student.total_learning_time / 60)) * 10, 1)
        
        # 学习模式分析
        learning_pattern = "均衡发展"
        if avg_memory_strength >= 0.7:
            if student.study_streak >= 7:
                learning_pattern = "学霸模式"
            else:
                learning_pattern = "高效学习者"
        elif avg_memory_strength >= 0.4:
            learning_pattern = "稳步提升"
        elif total_knowledge_points > 0:
            learning_pattern = "入门新手"
        
        # 学习时段分布分析
        time_distribution = {"morning": 0, "afternoon": 0, "evening": 0}
        if student.last_study_date:
            hour = student.last_study_date.hour
            if 6 <= hour < 12:
                time_distribution["morning"] = 1
            elif 12 <= hour < 18:
                time_distribution["afternoon"] = 1
            else:
                time_distribution["evening"] = 1
        
        # 获取Agent会话统计
        session_count = self.db.query(AgentSession).filter(
            AgentSession.student_id == student_id
        ).count()
        
        # 学习进度预估
        remaining_points = total_knowledge_points - mastered_points
        estimated_hours_needed = 0
        if remaining_points > 0 and mastered_points > 0:
            avg_hours_per_point = student.total_learning_time / 60 / mastered_points
            estimated_hours_needed = round(remaining_points * avg_hours_per_point, 1)
        
        # 学习活跃度（近7天）
        active_days = 0
        if student.last_study_date:
            days_since_last = (datetime.utcnow() - student.last_study_date).days
            active_days = max(0, 7 - days_since_last)
        
        return {
            # 基础统计
            "total_goals": total_goals,
            "completed_goals": completed_goals,
            "active_goals": len(in_progress_goals),
            "total_knowledge_points": total_knowledge_points,
            "mastered_points": mastered_points,
            "overall_mastery": overall_mastery,
            "urgent_reviews": urgent_reviews,
            "upcoming_reviews": upcoming_reviews,
            
            # 学习习惯
            "study_streak": student.study_streak,
            "total_learning_time": student.total_learning_time,
            "last_study_date": student.last_study_date.isoformat() if student.last_study_date else None,
            "preferred_time": student.learning_style.get("preferred_time") if student.learning_style else "morning",
            
            # 高级分析
            "study_efficiency": study_efficiency,  # 每小时学习掌握的知识点数
            "learning_pattern": learning_pattern,  # 学习模式标签
            "memory_strength_avg": round(avg_memory_strength * 100),  # 平均记忆强度百分比
            "time_distribution": time_distribution,  # 学习时段分布
            "session_count": session_count,  # 与AI对话次数
            
            # 进度预估
            "remaining_points": remaining_points,
            "estimated_hours_needed": estimated_hours_needed,
            "active_days": active_days,  # 过去7天活跃天数
        }
