"""
FinVoice — AI Advisor Chat API.
Streams GPT responses via Server-Sent Events (SSE).
"""

import json
import logging
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import User
from api.auth import get_current_user
from services.chat import stream_chat_response

logger = logging.getLogger(__name__)

router = APIRouter()

SEBI_DISCLAIMER = (
    "FinVoice is a decision-support tool. Invest at your own risk. "
    "Consult a SEBI-registered advisor for personalized advice."
)


# ─── Request / Response Schemas ───


class ChatMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    history: list[ChatMessage] = Field(default_factory=list, max_length=50)


# ─── SSE Stream Helper ───


async def _sse_generator(
    db: AsyncSession,
    user: User,
    message: str,
    history: list[dict],
) -> AsyncGenerator[str, None]:
    """
    Wraps the chat stream into SSE format:
      data: {"token": "..."}
      ...
      data: {"done": true}
    """
    try:
        async for token in stream_chat_response(db, user, message, history):
            payload = json.dumps({"token": token}, ensure_ascii=False)
            yield f"data: {payload}\n\n"

        # Signal completion
        yield f"data: {json.dumps({'done': True})}\n\n"

    except Exception as e:
        logger.error(f"SSE stream error: {e}")
        error_payload = json.dumps({"error": str(e)})
        yield f"data: {error_payload}\n\n"


# ─── Endpoint ───


@router.post("/chat")
async def chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Stream AI advisor response via Server-Sent Events.

    The AI has full context of the user's portfolio, risk profile,
    and financial data. Conversation history is passed from the frontend
    for multi-turn context.
    """
    history_dicts = [{"role": m.role, "content": m.content} for m in request.history]

    return StreamingResponse(
        _sse_generator(db, current_user, request.message, history_dicts),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )
