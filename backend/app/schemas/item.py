from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ItemCreate(BaseModel):
    problem_text: str = ""
    diagram_desc: str = ""
    method_chain: str = ""
    solution_outline: str = ""
    user_notes: str = ""
    user_tags: List[str] = Field(default_factory=list)
    meta: Dict[str, Any] = Field(default_factory=dict)
    images: List[str] = Field(default_factory=list)


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
