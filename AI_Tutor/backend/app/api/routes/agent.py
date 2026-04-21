"""
Agent API Routes

REST API endpoints for the Agent.
注:极简架构下,主要的聊天功能在 chat.py 中实现,
此文件仅保留基础的工具列表端点(已废弃)。
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db

# Request/Response Models
class ChatRequest(BaseModel):
    """Request model for chat endpoint"""
    message: str = Field(..., description="User message")
    session_id: Optional[str] = Field(None, description="Session ID for multi-turn conversation")
    student_id: int = Field(1, description="Student ID")
    stream: bool = Field(False, description="Enable streaming response")


class ChatResponse(BaseModel):
    """Response model for chat endpoint"""
    content: str = Field(..., description="Agent response content")
    session_id: str = Field(..., description="Session ID")


# Router
router = APIRouter(tags=["Agent"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: Session = Depends(get_db)
):
    """
    Process a chat message and return agent response.
    注:此端点已被 /api/chat/message 替代,保留仅用于兼容。
    """
    return ChatResponse(
        content="此端点已废弃,请使用 /api/chat/message 或 /api/chat/message/stream",
        session_id=request.session_id or "default",
    )


@router.get("/tools")
async def list_tools():
    """
    List all available tools.
    注:极简架构下已移除所有工具,此端点返回空列表。
    """
    return {
        "tools": [],
        "total": 0,
        "message": "极简架构下已移除所有工具"
    }


@router.post("/reload")
async def reload_agent():
    """
    Reload agent.
    """
    return {"status": "ok", "message": "极简架构无需重载"}
