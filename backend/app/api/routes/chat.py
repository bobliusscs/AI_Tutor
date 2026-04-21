"""
聊天 API 路由 - AgentCore 本地接口

将消息交由本地 AgentCore 处理，替代 OpenClaw Gateway 转发。
保持 SSE 事件格式与前端完全兼容。
"""
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
import json
import logging

from app.core.database import get_db
from app.api.deps import get_current_student_id
from app.agent.core import AgentCore
from app.services.engine_manager import get_module_provider
from app.models.study_goal import StudyGoal, StudyGoalStatus
from app.schemas import Response

logger = logging.getLogger(__name__)

router = APIRouter()


class ChatRequest(BaseModel):
    """聊天请求"""
    message: str
    history: Optional[List[dict]] = []
    session_id: Optional[str] = None
    images: Optional[List[str]] = None  # base64 编码的图片列表
    documents: Optional[List[dict]] = None  # 文档附件列表 [{"name": "xxx.pdf", "type": "pdf", "data": "base64..."}]
    videos: Optional[List[str]] = None  # base64 编码的视频列表
    audios: Optional[List[str]] = None  # base64 编码的音频列表
    goal_id: Optional[int] = None  # 当前学习目标ID


@router.get("/welcome")
async def get_welcome_message():
    """
    获取欢迎消息
    """
    welcome = """你好！我是你的 AI 学习助手。

我可以帮助你解答问题、讨论各种话题。

有什么我可以帮助你的吗？"""

    return {
        "success": True,
        "data": {"response": welcome}
    }


@router.post("/message")
async def chat_message(
    request: ChatRequest,
    current_student_id: int = Depends(get_current_student_id),
    db: Session = Depends(get_db)
):
    """
    与 AI 进行对话（非流式）
    收集 AgentCore 流式输出，拼接为完整回复后返回。
    学生ID从 JWT token 自动获取。
    """
    try:
        ai_provider = get_module_provider("agent")
        agent = AgentCore(
            db=db,
            ai_provider=ai_provider,
            student_id=current_student_id,
        )

        # 构建 current_goal 字典（用于会话摘要保存和意图检测）
        # 从数据库获取学习目标完整信息，包含 title 用于"继续学习"意图识别
        current_goal = None
        if request.goal_id:
            try:
                goal = db.query(StudyGoal).filter(StudyGoal.id == request.goal_id).first()
                if goal:
                    current_goal = {
                        "id": goal.id,
                        "title": goal.title,
                        "description": goal.description,
                    }
                    logger.info(f"[Chat] 获取学习目标信息: id={goal.id}, title={goal.title}")
            except Exception as e:
                logger.warning(f"[Chat] 获取学习目标失败: {e}")
                current_goal = {"id": request.goal_id}
        else:
            current_goal = None
        
        full_response = ""
        async for event in agent.run(
            message=request.message,
            session_id=request.session_id,
            history=request.history,
            images=request.images,
            documents=request.documents,
            videos=request.videos,
            audios=request.audios,
            current_goal=current_goal,
        ):
            if "content" in event:
                full_response += event["content"]
            elif event.get("done"):
                # 优先使用 full_response 字段（AgentCore 已保证完整）
                full_response = event.get("full_response", full_response)

        return {
            "success": True,
            "data": {
                "response": full_response,
                "message": request.message,
            }
        }

    except Exception as e:
        logger.error("非流式聊天出错: %s", e)
        return {
            "success": False,
            "data": {
                "response": f"聊天出错：{str(e)}",
                "message": request.message,
            }
        }


@router.post("/message/stream")
async def chat_message_stream(
    request: ChatRequest,
    current_student_id: int = Depends(get_current_student_id),
    db: Session = Depends(get_db)
):
    """
    与 AI 进行对话（流式输出 SSE）
    直接将 AgentCore 的事件流转发给前端。
    学生ID从 JWT token 自动获取，无需前端传递。
    """
    async def event_generator():
        try:
            print(f"[DEBUG] Chat request: message='{request.message[:30]}...', images={len(request.images) if request.images else 0}, documents={len(request.documents) if request.documents else 0}")
            logger.info("[Chat] 收到请求: message='%s', images=%s, documents=%s",
                       request.message[:50] if request.message else '',
                       len(request.images) if request.images else 0,
                       len(request.documents) if request.documents else 0)
            ai_provider = get_module_provider("agent")
            agent = AgentCore(
                db=db,
                ai_provider=ai_provider,
                student_id=current_student_id,
            )

            # 构建 current_goal 字典（用于会话摘要保存和意图检测）
            # 从数据库获取学习目标完整信息，包含 title 用于"继续学习"意图识别
            current_goal = None
            if request.goal_id:
                try:
                    goal = db.query(StudyGoal).filter(StudyGoal.id == request.goal_id).first()
                    if goal:
                        current_goal = {
                            "id": goal.id,
                            "title": goal.title,
                            "description": goal.description,
                        }
                        logger.info(f"[Chat] 获取学习目标信息: id={goal.id}, title={goal.title}")
                except Exception as e:
                    logger.warning(f"[Chat] 获取学习目标失败: {e}")
                    current_goal = {"id": request.goal_id}
            else:
                current_goal = None
            
            async for event in agent.run(
                message=request.message,
                session_id=request.session_id,
                history=request.history,
                images=request.images,
                documents=request.documents,
                videos=request.videos,
                audios=request.audios,
                current_goal=current_goal,
            ):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

        except Exception as e:
            logger.error("流式聊天出错: %s", e)
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'done': True}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.post("/session/end")
async def end_session(
    session_id: str,
    student_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """
    会话结束端点(已禁用自进化功能)
    
    注:极简架构下不再支持自进化和会话摘要功能,
    此端点仅用于保持前端兼容性。
    """
    # 极简架构下不执行任何操作
    logger.info(f"[Chat] 会话结束: session_id={session_id}")

    return {"status": "ok"}


class CreateGoalRequest(BaseModel):
    """创建学习目标请求"""
    title: str
    description: Optional[str] = None
    subject: Optional[str] = None
    target_hours_per_week: float = 5.0
    target_completion_date: Optional[str] = None
    study_depth: str = "intermediate"  # 学习深度：basic(了解), intermediate(熟悉), advanced(深入)
    student_background: Optional[dict] = None


@router.post("/create-goal-from-chat", response_model=Response)
async def create_goal_from_chat(
    request: CreateGoalRequest,
    current_student_id: int = Depends(get_current_student_id),
    db: Session = Depends(get_db)
):
    """
    从聊天表单创建学习目标
    
    ## 功能说明
    - 接收前端表单数据创建学习目标
    - 不自动生成知识图谱和学习计划
    - 返回创建的目标信息供前端跳转使用
    """
    try:
        # 解析目标完成日期
        target_date = None
        if request.target_completion_date:
            try:
                target_date = datetime.strptime(request.target_completion_date, '%Y-%m-%d')
            except ValueError:
                pass
        
        # 创建学习目标
        goal = StudyGoal(
            student_id=current_student_id,
            title=request.title,
            description=request.description or "",
            subject=request.subject,
            target_hours_per_week=request.target_hours_per_week,
            target_completion_date=target_date,
            study_depth=request.study_depth or "intermediate",
            student_background=request.student_background or {},
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
                "study_depth": goal.study_depth,
                "total_nodes": 0,
                "estimated_hours": 0,
            }
        )
    except Exception as e:
        db.rollback()
        logger.error("创建学习目标失败: %s", e)
        return Response(
            success=False,
            message=f"创建学习目标失败: {str(e)}",
            data=None
        )
