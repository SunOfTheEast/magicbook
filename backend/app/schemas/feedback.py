from __future__ import annotations

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class FeedbackIn(BaseModel):
    query_id: UUID
    item_id: UUID
    vote: int = Field(..., description="+1 or -1")
    reason: Optional[str] = None


class FeedbackOut(BaseModel):
    ok: bool
    feedback_id: int
