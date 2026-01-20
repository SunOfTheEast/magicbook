from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_n: int = Field(10, ge=1, le=50)
    meta_filters: Optional[Dict[str, Any]] = None


class Evidence(BaseModel):
    view_type: str
    snippet: str
    rank: float


class SearchResult(BaseModel):
    item_id: str
    title: str
    score: float
    evidence: List[Evidence]
    user_tags: List[str] = []
    images: List[str] = []


class SearchResponse(BaseModel):
    query_id: str
    results: List[SearchResult]
