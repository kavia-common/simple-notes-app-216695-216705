"""Pydantic models for the Notes API."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class NoteBase(BaseModel):
    """Shared note fields."""

    title: str = Field(..., min_length=1, max_length=200, description="Note title")
    content: str = Field(..., min_length=1, description="Note content/body")


class NoteCreate(NoteBase):
    """Request body for creating a note."""


class NoteUpdate(BaseModel):
    """Request body for updating a note (partial update via PUT semantics here)."""

    title: Optional[str] = Field(None, min_length=1, max_length=200, description="Note title")
    content: Optional[str] = Field(None, min_length=1, description="Note content/body")


class NoteOut(NoteBase):
    """Response model representing a persisted note."""

    id: int = Field(..., description="Note id")
    created_at: datetime = Field(..., description="Creation timestamp (UTC/local as stored by SQLite)")
    updated_at: datetime = Field(..., description="Last update timestamp (UTC/local as stored by SQLite)")

    model_config = {"from_attributes": True}
