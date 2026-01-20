# backend/app/api/v1/routes_search.py
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.engine import RowMapping

from backend.app.db.engine import engine

router = APIRouter()

# ---------- Schemas ----------
class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_n: int = Field(10, ge=1, le=50)
    meta_filters: Optional[Dict[str, Any]] = None #Optional代表可选

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


# ---------- Helpers ----------
def _build_where_meta(meta_filters: Optional[Dict[str, Any]]) -> Tuple[str, Dict[str, Any]]:
    if not meta_filters:
        return "", {}

    clauses = []
    params: Dict[str, Any] = {}

    if meta_filters.get("grade"):
        clauses.append("pi.meta ->> 'grade' = :grade")
        params["grade"] = str(meta_filters["grade"])

    if meta_filters.get("source"):
        clauses.append("pi.meta ->> 'source' = :source")
        params["source"] = str(meta_filters["source"])

    if not clauses:
        return "", {}

    return " AND " + " AND ".join(clauses), params


def _aggregate_rows(rows: List[RowMapping], top_n: int) -> List[SearchResult]:
    by_item: Dict[str, Dict[str, Any]] = {}

    for r in rows:
        item_id = str(r["item_id"])
        if item_id not in by_item:
            by_item[item_id] = {
                "item_id": item_id,
                "title": r["title"] or "",
                "score": float(r["rank"] or 0.0),
                "evidence": [],
                "user_tags": r["user_tags"] or [],
                "images": r["images"] or [],
            }

        by_item[item_id]["score"] = max(by_item[item_id]["score"], float(r["rank"] or 0.0))
        by_item[item_id]["evidence"].append(
            Evidence(
                view_type=str(r["view_type"]),
                snippet=str(r["snippet"]),
                rank=float(r["rank"] or 0.0),
            )
        )

    results: List[SearchResult] = []
    for item in by_item.values():
        item["evidence"].sort(key=lambda e: e.rank, reverse=True)
        item["evidence"] = item["evidence"][:3]
        results.append(SearchResult(**item))

    results.sort(key=lambda x: x.score, reverse=True)
    return results[:top_n]


# ---------- API ----------
@router.post("/search", response_model=SearchResponse)
def search(req: SearchRequest) -> SearchResponse:
    query_id = str(uuid.uuid4())
    meta_where, meta_params = _build_where_meta(req.meta_filters)

    sql = text(
        f"""
        SELECT
          sv.item_id,
          sv.view_type,
          ts_rank_cd(sv.fts, plainto_tsquery('simple', :q)) AS rank,
          ts_headline(
            'simple',
            sv.text,
            plainto_tsquery('simple', :q),
            'StartSel=[[, StopSel=]], MaxFragments=2, MinWords=4, MaxWords=16'
          ) AS snippet,
          COALESCE(NULLIF(pi.problem_text, ''), pi.bm25_text) AS title,
          pi.user_tags,
          pi.images
        FROM search_views sv
        JOIN problem_items pi ON pi.id = sv.item_id
        WHERE sv.fts @@ plainto_tsquery('simple', :q)
        {meta_where}
        ORDER BY rank DESC
        LIMIT :k;
        """
    )

    recall_k = max(req.top_n * 8, 50)
    params = {"q": req.query, "k": recall_k, **meta_params}

    with engine.connect() as conn:
        rows = list(conn.execute(sql, params).mappings().all())

    results = _aggregate_rows(rows, top_n=req.top_n)
    return SearchResponse(query_id=query_id, results=results)
