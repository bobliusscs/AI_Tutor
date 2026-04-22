"""
学习会话管理工具 - 保存会话摘要、加载历史学习记录

当用户表达结束学习的意图时（如"今天的学习到此结束"、"感谢陪伴"等），
模型应调用 save_study_summary 工具将当前学习记录保存到数据库；
下次学习同一目标时，通过 get_recent_sessions_summary 加载最近3次学习记录摘要，
让模型能够给出更连贯的学习引导。
"""
import json
import logging
from datetime import datetime, date
from typing import Optional, List, Dict, Any

from sqlalchemy.orm import Session
from sqlalchemy import desc

logger = logging.getLogger(__name__)


async def save_study_summary(
    db: Session,
    student_id: int,
    goal_id: int,
    conversation_log: str = "",
    summary: str = "",
    study_duration_minutes: int = 0,
    lessons_completed: int = 0,
    exercises_attempted: int = 0,
    exercises_correct: int = 0,
    knowledge_points_covered: List[int] = None,
) -> Dict[str, Any]:
    """
    保存学习会话摘要到学习记录表。

    当用户表达结束学习意图时（如"今天的学习到此结束"、"感谢陪伴"），
    模型应调用此工具保存当前会话的摘要和完整交互记录。

    注意：此工具只返回成功标记，实际保存由前端处理。

    Args:
        db: 数据库会话
        student_id: 学生ID
        goal_id: 学习目标ID
        conversation_log: 完整对话记录（JSON字符串）
        summary: AI生成的会话摘要（100字左右）。**可为空字符串**，前端会异步生成个性化摘要
        study_duration_minutes: 学习时长（分钟）
        lessons_completed: 完成的课时数
        exercises_attempted: 练习题数
        exercises_correct: 正确数
        knowledge_points_covered: 覆盖的知识点ID列表

    Returns:
        保存结果 {"success": true/false, "message": "...", "record_id": ...}
    """
    try:
        # 生成会话 ID
        current_session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        logger.info(f"[StudySession] save_study_summary 工具被调用: student={student_id}, goal={goal_id}, session_id={current_session_id}")
        
        # 返回成功标记，告知前端需要保存数据
        return {
            "success": True,
            "message": "请前端保存学习记录",
            "record_id": None,
            "session_id": current_session_id,
            "_前端保存": True,  # 标记前端需要保存
            "_conversation_log_needed": True  # 标记需要前端传递对话历史
        }

    except Exception as e:
        logger.error(f"[StudySession] 保存会话摘要失败: {e}", exc_info=True)
        db.rollback()
        return {
            "success": False,
            "error": str(e),
            "message": "保存学习记录失败"
        }


async def get_recent_sessions_summary(
    db: Session,
    student_id: int,
    goal_id: int,
    limit: int = 3
) -> Dict[str, Any]:
    """
    获取指定学习目标的最近N次学习会话摘要。

    下次学习同一目标时，模型应调用此工具加载历史学习记录，
    将其作为上下文让AI能够给出更连贯的学习引导。

    Args:
        db: 数据库会话
        student_id: 学生ID
        goal_id: 学习目标ID
        limit: 返回的会话数量，默认3次

    Returns:
        {"success": true/false, "sessions": [...], "total_count": N}
        sessions 格式: [{"summary": "...", "created_at": "...", "study_duration_minutes": N}]
    """
    try:
        from app.models.study_record import StudyRecord

        # 查询该学生、该目标的最近学习记录
        records = db.query(StudyRecord).filter(
            StudyRecord.student_id == student_id,
            StudyRecord.goal_id == goal_id
        ).order_by(desc(StudyRecord.record_date)).limit(20).all()

        all_sessions = []
        for record in records:
            if record.session_summary:
                try:
                    sessions = json.loads(record.session_summary)
                    if isinstance(sessions, list):
                        for s in sessions:
                            s["record_date"] = str(record.record_date) if record.record_date else ""
                            all_sessions.append(s)
                except json.JSONDecodeError:
                    pass

        # 按时间倒序，取最近的limit条
        all_sessions.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        recent_sessions = all_sessions[:limit]

        if recent_sessions:
            logger.info(f"[StudySession] 获取历史会话摘要: goal={goal_id}, count={len(recent_sessions)}")

        return {
            "success": True,
            "sessions": recent_sessions,
            "total_count": len(all_sessions)
        }

    except Exception as e:
        logger.error(f"[StudySession] 获取历史会话摘要失败: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "sessions": []
        }


async def get_conversation_log(
    db: Session,
    student_id: int,
    goal_id: int,
    limit: int = 1
) -> Dict[str, Any]:
    """
    获取指定学习目标的最近完整对话记录。

    Args:
        db: 数据库会话
        student_id: 学生ID
        goal_id: 学习目标ID
        limit: 返回的记录数，默认1条

    Returns:
        {"success": true/false, "conversations": [...], "total_count": N}
    """
    try:
        from app.models.study_record import StudyRecord

        # 查询该学生、该目标的最近学习记录（按日期倒序）
        records = db.query(StudyRecord).filter(
            StudyRecord.student_id == student_id,
            StudyRecord.goal_id == goal_id
        ).order_by(desc(StudyRecord.record_date)).limit(limit).all()

        conversations = []
        for record in records:
            if record.conversation_log:
                try:
                    conv = json.loads(record.conversation_log) if isinstance(record.conversation_log, str) else record.conversation_log
                    if isinstance(conv, list):
                        conversations.append({
                            "date": str(record.record_date) if record.record_date else "",
                            "messages": conv[-20:] if len(conv) > 20 else conv  # 最近20条消息
                        })
                except (json.JSONDecodeError, TypeError):
                    pass

        return {
            "success": True,
            "conversations": conversations,
            "total_count": len(conversations)
        }

    except Exception as e:
        logger.error(f"[StudySession] 获取对话记录失败: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "conversations": []
        }


async def generate_personalized_summary(
    conversation_log: list,
    goal_title: str = "",
    db: Session = None
) -> Dict[str, Any]:
    """
    调用 LLM 从对话历史中分析生成个性化的学习特征描述。

    生成 2-3 句深度的自然语言描述，反映学生的个性化学习特征。

    Args:
        conversation_log: 对话历史列表 [{"role": "user/assistant", "content": "..."}]
        goal_title: 学习目标标题
        db: 数据库会话

    Returns:
        {"success": true/false, "summary": "自然语言描述", "insights": {...}}
    """
    try:
        if not conversation_log or len(conversation_log) == 0:
            return {
                "success": False,
                "error": "对话历史为空",
                "summary": "本次学习暂无有效对话记录"
            }

        # 构建提示词
        prompt = f"""你是一个专业的学习分析师。请分析以下学生学习对话，生成2-3句深度的个性化学习特征描述。

要求：
1. 分析学生的学习风格（如：喜欢提问、喜欢实践、善于思考等）
2. 识别学生的知识薄弱点或常见错误
3. 总结学生对本次学习内容（{goal_title}）的掌握情况
4. 给出针对性的学习建议

请用自然语言输出，格式为2-3个独立的句子，便于阅读和理解。

对话历史：
"""
        # 添加对话内容
        for msg in conversation_log[-30:]:  # 只取最近30条消息
            role = "学生" if msg.get("role") == "user" else "AI教师"
            content = msg.get("content", "")[:500]  # 每条消息最多500字
            if content:
                prompt += f"\n{role}：{content}"

        prompt += "\n\n请生成个性化学习特征描述（2-3句）："

        # 调用 LLM 生成摘要
        try:
            from app.services.ai_model_provider import get_model_provider
            provider = await get_model_provider()
            
            if provider:
                result = await provider.chat([
                    {"role": "user", "content": prompt}
                ], model="gpt-4o-mini" if hasattr(provider, 'model') else None)
                
                # 清理生成的内容（移除引号等）
                summary = result.strip().strip('"\'').strip('"')
                
                logger.info(f"[StudySession] LLM生成个性化摘要成功，长度={len(summary)}")
                
                return {
                    "success": True,
                    "summary": summary,
                    "insights": {
                        "dialogue_length": len(conversation_log),
                        "goal_title": goal_title
                    }
                }
            else:
                # 没有 LLM 提供商，使用简单规则生成
                summary = _generate_simple_summary(conversation_log, goal_title)
                return {
                    "success": True,
                    "summary": summary,
                    "insights": {"fallback": True}
                }
                
        except Exception as llm_error:
            logger.warning(f"[StudySession] LLM调用失败，使用规则生成: {llm_error}")
            # 降级：使用规则生成简单摘要
            summary = _generate_simple_summary(conversation_log, goal_title)
            return {
                "success": True,
                "summary": summary,
                "insights": {"fallback": True}
            }

    except Exception as e:
        logger.error(f"[StudySession] 生成个性化摘要失败: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "summary": "本次学习记录已保存"
        }


def _generate_simple_summary(conversation_log: list, goal_title: str) -> str:
    """使用简单规则生成学习摘要（降级方案）"""
    user_messages = [m.get("content", "") for m in conversation_log if m.get("role") == "user"]
    assistant_messages = [m.get("content", "") for m in conversation_log if m.get("role") == "assistant"]
    
    # 统计问答数量
    question_count = sum(1 for m in user_messages if "？" in m or "?" in m)
    user_msg_count = len(user_messages)
    
    # 简单描述
    parts = []
    if goal_title:
        parts.append(f"本次学习了{goal_title}相关内容")
    if question_count > 5:
        parts.append("学生积极提问，学习态度认真")
    elif question_count > 0:
        parts.append(f"学生提出了{question_count}个问题")
    else:
        parts.append(f"学生与AI进行了{user_msg_count}轮对话交流")
    
    return "。".join(parts) + "。"