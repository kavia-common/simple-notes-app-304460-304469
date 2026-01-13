"""
FastAPI backend for Simple Notes App.

Exposes REST endpoints for CRUD operations on notes stored in a SQLite database.
The API is intended to be consumed by the React frontend running on port 3000.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import List

from fastapi import FastAPI, HTTPException, Response, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.db.database import get_engine
from src.db.models import Base, NoteORM
from src.db.repository import NotesRepository

openapi_tags = [
    {"name": "Health", "description": "Service health and diagnostics."},
    {"name": "Notes", "description": "CRUD operations for notes."},
]

app = FastAPI(
    title="Simple Notes API",
    description="Backend API for a simple notes app (CRUD notes).",
    version="1.0.0",
    openapi_tags=openapi_tags,
)

# CORS: allow React dev server
frontend_origin = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Note(BaseModel):
    """A note as returned by the API."""

    id: int = Field(..., description="Unique identifier for the note.")
    title: str = Field(..., description="Note title.")
    content: str = Field(..., description="Note content/body.")
    created_at: datetime = Field(..., description="When the note was created (UTC).")
    updated_at: datetime = Field(..., description="When the note was last updated (UTC).")


class NoteCreate(BaseModel):
    """Payload for creating a new note."""

    title: str = Field(..., min_length=1, description="Non-empty note title.")
    content: str = Field("", description="Note content/body.")


class NoteUpdate(BaseModel):
    """Payload for updating an existing note."""

    title: str = Field(..., min_length=1, description="Non-empty note title.")
    content: str = Field("", description="Note content/body.")


def _to_api_model(note: NoteORM) -> Note:
    """Convert ORM object into API model."""
    return Note(
        id=note.id,
        title=note.title,
        content=note.content or "",
        created_at=note.created_at,
        updated_at=note.updated_at,
    )


@app.on_event("startup")
def _startup() -> None:
    """Create DB schema and seed sample data if the notes table is empty."""
    engine = get_engine()
    Base.metadata.create_all(bind=engine)

    repo = NotesRepository(engine)
    if repo.count_notes() == 0:
        now = datetime.now(timezone.utc)
        repo.create_note(
            title="Welcome to Simple Notes",
            content="Create, edit, and delete notes using the editor on the right.",
            now=now,
        )
        repo.create_note(
            title="Tip",
            content="Your note title is required. Content is optional.",
            now=now,
        )


# PUBLIC_INTERFACE
@app.get(
    "/health",
    tags=["Health"],
    summary="Health check",
    description="Returns a basic health status for the service.",
    operation_id="healthCheck",
)
def health_check() -> dict:
    """Health check endpoint.

    Returns:
        JSON object with status.
    """
    return {"status": "ok"}


# PUBLIC_INTERFACE
@app.get(
    "/notes",
    response_model=List[Note],
    tags=["Notes"],
    summary="List notes",
    description="Return all notes ordered by updated_at desc.",
    operation_id="listNotes",
)
def list_notes() -> List[Note]:
    """List all notes.

    Returns:
        List of notes.
    """
    repo = NotesRepository(get_engine())
    notes = repo.list_notes()
    return [_to_api_model(n) for n in notes]


# PUBLIC_INTERFACE
@app.get(
    "/notes/{note_id}",
    response_model=Note,
    tags=["Notes"],
    summary="Get note",
    description="Retrieve a single note by id.",
    operation_id="getNote",
)
def get_note(note_id: int) -> Note:
    """Get a note by id.

    Args:
        note_id: Note id.

    Returns:
        Note.

    Raises:
        HTTPException: If note not found.
    """
    repo = NotesRepository(get_engine())
    note = repo.get_note(note_id)
    if note is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    return _to_api_model(note)


# PUBLIC_INTERFACE
@app.post(
    "/notes",
    response_model=Note,
    status_code=status.HTTP_201_CREATED,
    tags=["Notes"],
    summary="Create note",
    description="Create a new note. Title must be non-empty.",
    operation_id="createNote",
)
def create_note(payload: NoteCreate) -> Note:
    """Create a new note.

    Args:
        payload: NoteCreate payload.

    Returns:
        Created note.

    Raises:
        HTTPException: If validation fails.
    """
    title = payload.title.strip()
    if not title:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Title must not be empty")

    repo = NotesRepository(get_engine())
    now = datetime.now(timezone.utc)
    note = repo.create_note(title=title, content=payload.content or "", now=now)
    return _to_api_model(note)


# PUBLIC_INTERFACE
@app.put(
    "/notes/{note_id}",
    response_model=Note,
    tags=["Notes"],
    summary="Update note",
    description="Update an existing note by id. Title must be non-empty.",
    operation_id="updateNote",
)
def update_note(note_id: int, payload: NoteUpdate) -> Note:
    """Update an existing note.

    Args:
        note_id: Note id.
        payload: NoteUpdate payload.

    Returns:
        Updated note.

    Raises:
        HTTPException: If note not found or validation fails.
    """
    title = payload.title.strip()
    if not title:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Title must not be empty")

    repo = NotesRepository(get_engine())
    now = datetime.now(timezone.utc)
    note = repo.update_note(note_id=note_id, title=title, content=payload.content or "", now=now)
    if note is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    return _to_api_model(note)


# PUBLIC_INTERFACE
@app.delete(
    "/notes/{note_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Notes"],
    summary="Delete note",
    description="Delete a note by id.",
    operation_id="deleteNote",
)
def delete_note(note_id: int) -> Response:
    """Delete a note by id.

    Args:
        note_id: Note id.

    Returns:
        Empty response (204) if deleted.

    Raises:
        HTTPException: If note not found.
    """
    repo = NotesRepository(get_engine())
    deleted = repo.delete_note(note_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
