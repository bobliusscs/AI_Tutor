"""
学情分析引擎 - 分析学生学习数据，生成学习报告
"""
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta

from app.models.study_goal import StudyGoal
from app.models.node_mastery import NodeMastery
from app.models.assessment import Assessment
from app.models.learning_plan import Lesson


class AnalysisEngine:
    """学情分析引擎"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def analyze_goal_progress(self, goal_id: int, student_id: int) -> Dict:
        """
        分析学习目标进度
        
        Returns:
            {
                "overall_mastery": float,  # 总体掌握度 0-100
                "knowledge_distribution": {
                    "mastered": int,
                    "learning": int,
                    "not_started": int
                },
                "completion_rate": float,  # 完成率
                "study_time": {
                    "total_minutes": int,
                    "avg_daily_minutes": float
                }
            }
        """
        goal = self.db.query(StudyGoal).filter(
            StudyGoal.id == goal_id,
            StudyGoal.student_id == student_id
        ).first()
        
        if not goal:
            return {}
        
        # 获取掌握度数据
        masteries = self.db.query(NodeMastery).filter(
            NodeMastery.study_goal_id == goal_id,
            NodeMastery.student_id == student_id
        ).all()
        
        total_nodes = goal.total_knowledge_points or 1
        mastered = len([m for m in masteries if m.mastery_level >= 80])
        learning = len([m for m in masteries if 20 <= m.mastery_level < 80])
        not_started = total_nodes - len(masteries)
        
        # 计算平均掌握度
        avg_mastery = sum(m.mastery_level for m in masteries) / len(masteries) if masteries else 0
        
        return {
            "overall_mastery": round(avg_mastery, 1),
            "knowledge_distribution": {
                "mastered": mastered,
                "learning": learning,
                "not_started": not_started,
                "total": total_nodes
            },
            "completion_rate": round((mastered / total_nodes) * 100, 1),
            "study_time": {
                "target_hours_per_week": goal.target_hours_per_week,
                "completed_lessons": goal.completed_lessons
            }
        }
    
    def get_learning_trends(self, goal_id: int, student_id: int, days: int = 30) -> List[Dict]:
        """
        获取学习趋势
        
        Returns:
            每日学习数据列表
        """
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # 获取每日的掌握度更新
        daily_updates = self.db.query(
            func.date(NodeMastery.updated_at).label('date'),
            func.avg(NodeMastery.mastery_level).label('avg_mastery'),
            func.count(NodeMastery.id).label('update_count')
        ).filter(
            NodeMastery.study_goal_id == goal_id,
            NodeMastery.student_id == student_id,
            NodeMastery.updated_at >= start_date
        ).group_by(func.date(NodeMastery.updated_at)).all()
        
        # 构建完整日期范围的数据
        trends = []
        current_date = start_date
        
        while current_date <= end_date:
            date_str = current_date.strftime('%Y-%m-%d')
            
            day_data = next(
                (d for d in daily_updates if d.date == current_date.date()),
                None
            )
            
            trends.append({
                "date": date_str,
                "avg_mastery": round(day_data.avg_mastery, 1) if day_data else None,
                "update_count": day_data.update_count if day_data else 0
            })
            
            current_date += timedelta(days=1)
        
        return trends
    
    def identify_weak_points(self, goal_id: int, student_id: int, limit: int = 10) -> List[Dict]:
        """
        识别薄弱知识点
        
        Returns:
            薄弱知识点列表
        """
        weak_points = self.db.query(NodeMastery).filter(
            NodeMastery.study_goal_id == goal_id,
            NodeMastery.student_id == student_id,
            NodeMastery.mastery_level < 60
        ).order_by(NodeMastery.mastery_level.asc()).limit(limit).all()
        
        result = []
        for wp in weak_points:
            accuracy = (wp.correct_attempts / wp.total_attempts * 100) if wp.total_attempts > 0 else 0
            
            result.append({
                "node_id": wp.node_id,
                "node_name": wp.node_name,
                "mastery_level": wp.mastery_level,
                "status": "weak" if wp.mastery_level < 30 else "needs_improvement",
                "total_attempts": wp.total_attempts,
                "correct_attempts": wp.correct_attempts,
                "accuracy": round(accuracy, 1),
                "suggestion": wp.improvement_suggestions or self._generate_suggestion(wp)
            })
        
        return result
    
    def _generate_suggestion(self, mastery: NodeMastery) -> str:
        """生成学习建议"""
        if mastery.mastery_level < 30:
            return "建议从基础概念开始学习，多做基础练习题"
        elif mastery.mastery_level < 50:
            return "需要加强练习，重点理解核心概念"
        else:
            return "继续巩固，尝试做一些综合应用题"
    
    def get_practice_statistics(self, goal_id: int, student_id: int) -> Dict:
        """
        获取练习统计
        
        Returns:
            {
                "total_attempts": int,
                "total_correct": int,
                "overall_accuracy": float,
                "difficulty_distribution": {
                    "easy": {"attempts": int, "correct": int},
                    "medium": {...},
                    "hard": {...}
                }
            }
        """
        masteries = self.db.query(NodeMastery).filter(
            NodeMastery.study_goal_id == goal_id,
            NodeMastery.student_id == student_id
        ).all()
        
        total_attempts = sum(m.total_attempts for m in masteries)
        total_correct = sum(m.correct_attempts for m in masteries)
        
        return {
            "total_attempts": total_attempts,
            "total_correct": total_correct,
            "overall_accuracy": round(total_correct / total_attempts * 100, 1) if total_attempts > 0 else 0
        }
    
    def generate_learning_report(self, goal_id: int, student_id: int) -> Dict:
        """
        生成完整的学习报告
        
        Returns:
            包含各项分析数据的完整报告
        """
        progress = self.analyze_goal_progress(goal_id, student_id)
        trends = self.get_learning_trends(goal_id, student_id, 30)
        weak_points = self.identify_weak_points(goal_id, student_id, 5)
        practice_stats = self.get_practice_statistics(goal_id, student_id)
        
        # 生成建议
        suggestions = []
        if progress.get("completion_rate", 0) < 30:
            suggestions.append("学习进度较慢，建议增加每周学习时间")
        if weak_points:
            suggestions.append(f"有 {len(weak_points)} 个薄弱知识点需要加强")
        if practice_stats.get("overall_accuracy", 0) < 60:
            suggestions.append("练习正确率偏低，建议先巩固基础概念")
        
        return {
            "progress": progress,
            "trends": trends,
            "weak_points": weak_points,
            "practice_statistics": practice_stats,
            "suggestions": suggestions,
            "generated_at": datetime.utcnow().isoformat()
        }
