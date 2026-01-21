from __future__ import annotations

from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from backend.app.db.engine import engine
from backend.app.schemas.feedback import FeedbackIn, FeedbackOut

router = APIRouter()

# ---------- API ----------
@router.get("/feedback/ping")
def ping_feedback():
    return {"ok": True}


@router.post("/feedback", response_model=FeedbackOut)
def create_feedback(payload: FeedbackIn) -> FeedbackOut:
    if payload.vote not in (1, -1):
        raise HTTPException(status_code=400, detail="vote must be 1 or -1")

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
