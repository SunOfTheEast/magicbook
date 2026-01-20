from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text

from backend.app.db.engine import engine

router = APIRouter()


# --------- Schemas（先放这里，跑通后再挪去 schemas/item.py）---------
class ItemCreate(BaseModel):
    problem_text: str = ""
    diagram_desc: str = ""
    method_chain: str = ""
    solution_outline: str = ""
    user_notes: str = ""
    user_tags: List[str] = Field(default_factory=list)
    meta: Dict[str, Any] = Field(default_factory=dict)
    images: List[str] = Field(default_factory=list)  # 先用字符串路径数组，后面再做上传


class ItemUpdate(BaseModel):
    problem_text: Optional[str] = None
    diagram_desc: Optional[str] = None
    method_chain: Optional[str] = None
    solution_outline: Optional[str] = None
    user_notes: Optional[str] = None
    user_tags: Optional[List[str]] = None
    meta: Optional[Dict[str, Any]] = None
    images: Optional[List[str]] = None


class ItemOut(BaseModel):
    id: str
    problem_text: str
    diagram_desc: str
    method_chain: str
    solution_outline: str
    user_notes: str
    user_tags: List[str]
    meta: Dict[str, Any]
    images: List[str]


# --------- Helpers（先粗暴，够用）---------
VIEW_ORDER = ["problem", "diagram", "method", "note", "solution_outline"]


def build_bm25_text(
    problem_text: str,
    diagram_desc: str,
    method_chain: str,
    solution_outline: str,
    user_notes: str,
    user_tags: List[str],
    meta: Dict[str, Any],
) -> str:
    parts: List[str] = []
    for s in [problem_text, diagram_desc, method_chain, solution_outline, user_notes]:
        if s and s.strip():
            parts.append(s.strip())

    if user_tags:
        parts.append(" ".join([t.strip() for t in user_tags if t and t.strip()]))

    # 把 meta 里有用的“可检索事实”拼进去（浙江/2019/压轴…这类）
    if meta:
        for k, v in meta.items():
            if v is None:
                continue
            parts.append(f"{k}:{v}")

    return "\n".join(parts)


def upsert_search_views(conn, item_id: str, views: Dict[str, str]) -> None:
    """
    views: {"problem": "...", "method": "...", "note": "...", "diagram": "...", "solution_outline": "..."}
    """
    upsert_sql = text("""
        INSERT INTO search_views (item_id, view_type, text, updated_at)
        VALUES (:item_id, :view_type::view_type, :text, now())
        ON CONFLICT (item_id, view_type)
        DO UPDATE SET text = EXCLUDED.text, updated_at = now();
    """)
    for vt in VIEW_ORDER:
        if vt in views and views[vt] is not None:
            conn.execute(upsert_sql, {"item_id": item_id, "view_type": vt, "text": views[vt]})


# --------- API ---------
@router.get("/items/ping")
def ping_items():
    return {"ok": True}


@router.post("/items", response_model=ItemOut)
def create_item(payload: ItemCreate) -> ItemOut:
    item_id = str(uuid.uuid4())

    bm25_text = build_bm25_text(
        payload.problem_text,
        payload.diagram_desc,
        payload.method_chain,
        payload.solution_outline,
        payload.user_notes,
        payload.user_tags,
        payload.meta,
    )

    insert_sql = text("""
        INSERT INTO problem_items (
          id, images, problem_text, diagram_desc, method_chain,
          solution_outline, user_notes, user_tags, meta, bm25_text
        ) VALUES (
          :id, :images::jsonb, :problem_text, :diagram_desc, :method_chain,
          :solution_outline, :user_notes, :user_tags, :meta::jsonb, :bm25_text
        );
    """)

    # engine.begin() 会自动开启事务并提交；中间任何异常会回滚
    with engine.begin() as conn:
        conn.execute(insert_sql, {
            "id": item_id,
            "images": json.dumps(payload.images),
            "problem_text": payload.problem_text,
            "diagram_desc": payload.diagram_desc,
            "method_chain": payload.method_chain,
            "solution_outline": payload.solution_outline,
            "user_notes": payload.user_notes,
            "user_tags": payload.user_tags,
            "meta": json.dumps(payload.meta),
            "bm25_text": bm25_text,
        })

        # 自动维护 search_views（你的 search 就靠它）
        upsert_search_views(conn, item_id, {
            "problem": payload.problem_text,
            "diagram": payload.diagram_desc,
            "method": payload.method_chain,
            "note": payload.user_notes,
            "solution_outline": payload.solution_outline,
        })

    return ItemOut(
        id=item_id,
        problem_text=payload.problem_text,
        diagram_desc=payload.diagram_desc,
        method_chain=payload.method_chain,
        solution_outline=payload.solution_outline,
        user_notes=payload.user_notes,
        user_tags=payload.user_tags,
        meta=payload.meta,
        images=payload.images,
    )


@router.get("/items/{item_id}", response_model=ItemOut)
def get_item(item_id: str) -> ItemOut:
    sql = text("""
        SELECT id, problem_text, diagram_desc, method_chain,
               solution_outline, user_notes, user_tags, meta, images
        FROM problem_items
        WHERE id = :id
    """)
    with engine.connect() as conn:
        row = conn.execute(sql, {"id": item_id}).mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail="item not found")

    return ItemOut(
        id=str(row["id"]),
        problem_text=row["problem_text"] or "",
        diagram_desc=row["diagram_desc"] or "",
        method_chain=row["method_chain"] or "",
        solution_outline=row["solution_outline"] or "",
        user_notes=row["user_notes"] or "",
        user_tags=row["user_tags"] or [],
        meta=row["meta"] or {},
        images=row["images"] or [],
    )


@router.patch("/items/{item_id}", response_model=ItemOut)
def update_item(item_id: str, payload: ItemUpdate) -> ItemOut:
    # 先读原始值
    select_sql = text("""
        SELECT problem_text, diagram_desc, method_chain,
               solution_outline, user_notes, user_tags, meta, images
        FROM problem_items
        WHERE id = :id
    """)

    with engine.connect() as conn:
        row = conn.execute(select_sql, {"id": item_id}).mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail="item not found")

    # 合并（None 表示不改）
    new_problem_text = payload.problem_text if payload.problem_text is not None else (row["problem_text"] or "")
    new_diagram_desc = payload.diagram_desc if payload.diagram_desc is not None else (row["diagram_desc"] or "")
    new_method_chain = payload.method_chain if payload.method_chain is not None else (row["method_chain"] or "")
    new_solution_outline = payload.solution_outline if payload.solution_outline is not None else (row["solution_outline"] or "")
    new_user_notes = payload.user_notes if payload.user_notes is not None else (row["user_notes"] or "")
    new_user_tags = payload.user_tags if payload.user_tags is not None else (row["user_tags"] or [])
    new_meta = payload.meta if payload.meta is not None else (row["meta"] or {})
    new_images = payload.images if payload.images is not None else (row["images"] or [])

    bm25_text = build_bm25_text(
        new_problem_text,
        new_diagram_desc,
        new_method_chain,
        new_solution_outline,
        new_user_notes,
        new_user_tags,
        new_meta,
    )

    update_sql = text("""
        UPDATE problem_items
        SET images = :images::jsonb,
            problem_text = :problem_text,
            diagram_desc = :diagram_desc,
            method_chain = :method_chain,
            solution_outline = :solution_outline,
            user_notes = :user_notes,
            user_tags = :user_tags,
            meta = :meta::jsonb,
            bm25_text = :bm25_text,
            updated_at = now()
        WHERE id = :id
    """)

    with engine.begin() as conn:
        conn.execute(update_sql, {
            "id": item_id,
            "images": json.dumps(new_images),
            "problem_text": new_problem_text,
            "diagram_desc": new_diagram_desc,
            "method_chain": new_method_chain,
            "solution_outline": new_solution_outline,
            "user_notes": new_user_notes,
            "user_tags": new_user_tags,
            "meta": json.dumps(new_meta),
            "bm25_text": bm25_text,
        })

        # 同步更新 views（保证可搜+可证据展示）
        upsert_search_views(conn, item_id, {
            "problem": new_problem_text,
            "diagram": new_diagram_desc,
            "method": new_method_chain,
            "note": new_user_notes,
            "solution_outline": new_solution_outline,
        })

    return ItemOut(
        id=item_id,
        problem_text=new_problem_text,
        diagram_desc=new_diagram_desc,
        method_chain=new_method_chain,
        solution_outline=new_solution_outline,
        user_notes=new_user_notes,
        user_tags=new_user_tags,
        meta=new_meta,
        images=new_images,
    )
