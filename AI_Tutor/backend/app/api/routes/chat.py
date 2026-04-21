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
import asyncio
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
    tts_enabled: Optional[bool] = False  # 是否启用流式TTS


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
            logger.info("[Chat] 收到请求: message='%s', images=%s, documents=%s, tts_enabled=%s",
                       request.message[:50] if request.message else '',
                       len(request.images) if request.images else 0,
                       len(request.documents) if request.documents else 0,
                       request.tts_enabled)
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

            if request.tts_enabled:
                # === 流式 TTS 模式 ===
                coordinator = None
                try:
                    from app.services.streaming_tts import create_streaming_coordinator
                    coordinator = create_streaming_coordinator()
                    logger.info(f"[Chat] 流式TTS已启用，coordinator创建成功, provider={type(coordinator._provider).__name__}, enabled={coordinator._provider.enabled}")
                except Exception as e:
                    logger.warning(f"[Chat] 创建流式TTS协调器失败，降级为普通模式: {e}", exc_info=True)
                    coordinator = None

            if request.tts_enabled and coordinator:
                # 合并队列：agent 事件和 audio 事件都放入同一个队列
                merged_queue = asyncio.Queue()

                async def run_agent():
                    """运行 agent 并将事件放入合并队列"""
                    try:
                        # 用于在工具调用时临时保存未合成的文本
                        accumulated_text = ""
                        
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
                            # 工具调用事件：先 flush 已积累的文本，再通知前端
                            if "tool_call" in event:
                                # flush 已积累的文本（工具调用前模型的预输出）
                                if accumulated_text and coordinator:
                                    logger.info(f"[Chat-TTS] 工具调用前flush，文本长度={len(accumulated_text)}")
                                    coordinator.feed_chunk(accumulated_text)
                                    accumulated_text = ""
                                    await coordinator.flush()
                                # 通知前端本轮文本结束（但流不终止，音频事件会继续到达）
                                await merged_queue.put(("agent", {"text_done": True, "full_response": ""}))
                                await merged_queue.put(("agent", event))
                                continue
                            
                            # 文本chunk：累积到buffer
                            if event.get("type") == "chunk" and event.get("content"):
                                accumulated_text += event["content"]
                                await merged_queue.put(("agent", event))
                            # agent 最终完成
                            elif event.get("done"):
                                # flush 最后积累的文本
                                if accumulated_text and coordinator:
                                    logger.info(f"[Chat-TTS] 最终flush，文本长度={len(accumulated_text)}")
                                    coordinator.feed_chunk(accumulated_text)
                                    accumulated_text = ""
                                    await coordinator.flush()
                                await merged_queue.put(("agent", event))
                    except Exception as e:
                        logger.error(f"Agent 运行出错: {e}")
                        await merged_queue.put(("agent", {"error": str(e)}))
                        await merged_queue.put(("agent", {"done": True}))
                        if coordinator and not coordinator._flushed:
                            try:
                                await coordinator.flush()
                            except Exception as flush_err:
                                logger.warning(f"Agent异常后flush失败: {flush_err}")
                                coordinator.stop()

                async def run_tts():
                    """从 coordinator 获取音频事件放入合并队列"""
                    try:
                        async for audio_event in coordinator.get_audio_events():
                            await merged_queue.put(("tts", audio_event))
                    except Exception as e:
                        logger.error(f"TTS 流出错: {e}", exc_info=True)
                    finally:
                        await merged_queue.put(("tts", None))  # TTS 流结束标记

                # 并行启动两个任务
                agent_task = asyncio.create_task(run_agent())
                tts_task = asyncio.create_task(run_tts())

                agent_done = False
                tts_done = False

                while not (agent_done and tts_done):
                    source, event = await merged_queue.get()


                    if source == "agent":
                        yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                        if event.get("done"):
                            agent_done = True
                            # agent 完成时发送 audio_done（只发一次，覆盖所有轮次的音频）
                            total = coordinator.get_total_sentences() if coordinator else 0
                            logger.info(f"[Chat-TTS] agent完成，发送audio_done(total={total})")
                            yield f"data: {json.dumps({'type': 'audio_done', 'total': total}, ensure_ascii=False)}\n\n"
                    elif source == "tts":
                        if event is None:
                            tts_done = True
                        else:
                            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

                # 确保任务完成
                await asyncio.gather(agent_task, tts_task, return_exceptions=True)

            else:
                # === 原有非 TTS 模式（保持不变）===
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
