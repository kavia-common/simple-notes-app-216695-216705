from __future__ import annotations

import sqlite3
from typing import List

from fastapi import FastAPI, HTTPException, Response, status
from fastapi.middleware.cors import CORSMiddleware

from src.api.db import fetch_one_note, get_connection, init_db
from src.api.models import NoteCreate, NoteOut, NoteUpdate

openapi_tags = [
    {"name": "Health", "description": "Service health checks."},
    {"name": "Notes", "description": "CRUD operations for notes."},
]

app = FastAPI(
    title="Simple Notes API",
    description="FastAPI backend for a simple notes app with SQLite persistence.",
    version="0.1.0",
    openapi_tags=openapi_tags,
)

# Allow React dev server explicitly as requested.
# If additional origins are needed (e.g., deployed frontend), extend allow_origins.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure schema exists on startup (idempotent).
init_db()


@app.get("/", tags=["Health"], summary="Health check", description="Basic service health check.")
def health_check():
    """Return a basic health response."""
    return {"message": "Healthy"}


@app.post(
    "/notes",
    response_model=NoteOut,
    status_code=status.HTTP_201_CREATED,
    tags=["Notes"],
    summary="Create note",
    description="Create a new note with title and content.",
    operation_id="create_note",
)
def create_note(payload: NoteCreate) -> NoteOut:
    """Create a note and return the persisted note."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO notes (title, content) VALUES (?, ?)",
            (payload.title, payload.content),
        )
        note_id = cur.lastrowid
        conn.commit()

        created = fetch_one_note(conn, int(note_id))
        if not created:
            # Extremely unlikely, but keeps API predictable.
            raise HTTPException(status_code=500, detail="Failed to load created note")
        return NoteOut(**created)
    except sqlite3.IntegrityError as e:
        raise HTTPException(status_code=400, detail=f"Invalid note data: {e}") from e
    finally:
        conn.close()


@app.get(
    "/notes",
    response_model=List[NoteOut],
    tags=["Notes"],
    summary="List notes",
    description="List all notes ordered by most recently updated.",
    operation_id="list_notes",
)
def list_notes() -> List[NoteOut]:
    """Return all notes."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, title, content, created_at, updated_at
            FROM notes
            ORDER BY datetime(updated_at) DESC, id DESC
            """
        )
        rows = cur.fetchall()
        return [NoteOut(**{"id": r["id"], "title": r["title"], "content": r["content"], "created_at": r["created_at"], "updated_at": r["updated_at"]}) for r in rows]
    finally:
        conn.close()


@app.get(
    "/notes/{note_id}",
    response_model=NoteOut,
    tags=["Notes"],
    summary="Get note",
    description="Retrieve a single note by id.",
    operation_id="get_note",
)
def get_note(note_id: int) -> NoteOut:
    """Retrieve a single note by id."""
    conn = get_connection()
    try:
        note = fetch_one_note(conn, note_id)
        if not note:
            raise HTTPException(status_code=404, detail="Note not found")
        return NoteOut(**note)
    finally:
        conn.close()


@app.put(
    "/notes/{note_id}",
    response_model=NoteOut,
    tags=["Notes"],
    summary="Update note",
    description="Update an existing note. Fields not provided remain unchanged.",
    operation_id="update_note",
)
def update_note(note_id: int, payload: NoteUpdate) -> NoteOut:
    """Update a note by id and return the updated note."""
    if payload.title is None and payload.content is None:
        raise HTTPException(status_code=400, detail="At least one of 'title' or 'content' must be provided")

    conn = get_connection()
    try:
        existing = fetch_one_note(conn, note_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Note not found")

        new_title = payload.title if payload.title is not None else existing["title"]
        new_content = payload.content if payload.content is not None else existing["content"]

        cur = conn.cursor()
        cur.execute(
            "UPDATE notes SET title = ?, content = ? WHERE id = ?",
            (new_title, new_content, note_id),
        )
        conn.commit()

        updated = fetch_one_note(conn, note_id)
        if not updated:
            raise HTTPException(status_code=500, detail="Failed to load updated note")
        return NoteOut(**updated)
    except sqlite3.IntegrityError as e:
        raise HTTPException(status_code=400, detail=f"Invalid note data: {e}") from e
    finally:
        conn.close()


@app.delete(
    "/notes/{note_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Notes"],
    summary="Delete note",
    description="Delete a note by id.",
    operation_id="delete_note",
)
def delete_note(note_id: int) -> Response:
    """Delete a note by id."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        conn.commit()

        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Note not found")

        return Response(status_code=status.HTTP_204_NO_CONTENT)
    finally:
        conn.close()
