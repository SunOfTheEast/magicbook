from __future__ import annotations

from uuid import UUID
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy import text

from backend.app.db.engine import engine

router = APIRouter()


# ---------- Schemas ----------
class FeedbackIn(BaseModel):
    query_id: UUID
    item_id: UUID
    vote: int = Field(..., description="+1 or -1")
    reason: Optional[str] = None

    # Pydantic v1 写法：用 validator 也行；这里用简单逻辑在 endpoint 里检查
    # 保持最小可运行，避免你环境是 v2/v1 不一致


class FeedbackOut(BaseModel):
    ok: bool
    feedback_id: int


# ---------- API ----------
@router.get("/feedback/ping")
def ping_feedback():
    return {"ok": True}


@router.post("/feedback", response_model=FeedbackOut)
def create_feedback(payload: FeedbackIn) -> FeedbackOut:
    if payload.vote not in (1, -1):
        # FastAPI 会返回 422 更合适，但这里先用最简单的方式：
        raise ValueError("vote must be 1 or -1")

    sql = text("""
        INSERT INTO feedback (query_id, item_id, vote, reason)
        VALUES (:query_id, :item_id, :vote, :reason)
        RETURNING id;
    """)

    with engine.begin() as conn:
        feedback_id = conn.execute(
            sql,
            {
                "query_id": str(payload.query_id),
                "item_id": str(payload.item_id),
                "vote": payload.vote,
                "reason": payload.reason,
            },
        ).scalar_one()

    return FeedbackOut(ok=True, feedback_id=int(feedback_id))
