"""
Repository/data-access layer for notes.

Keeps SQL operations and session handling out of route functions.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from src.db.models import NoteORM


class NotesRepository:
    """CRUD operations for notes."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def count_notes(self) -> int:
        """Count notes in DB."""
        with Session(self._engine) as session:
            return int(session.execute(select(func.count(NoteORM.id))).scalar_one())

    def list_notes(self) -> list[NoteORM]:
        """Return all notes ordered by updated_at desc."""
        with Session(self._engine) as session:
            stmt = select(NoteORM).order_by(NoteORM.updated_at.desc(), NoteORM.id.desc())
            return list(session.execute(stmt).scalars().all())

    def get_note(self, note_id: int) -> NoteORM | None:
        """Get note by id."""
        with Session(self._engine) as session:
            return session.get(NoteORM, note_id)

    def create_note(self, title: str, content: str, now: datetime) -> NoteORM:
        """Create note and return it."""
        with Session(self._engine) as session:
            note = NoteORM(title=title, content=content, created_at=now, updated_at=now)
            session.add(note)
            session.commit()
            session.refresh(note)
            return note

    def update_note(self, note_id: int, title: str, content: str, now: datetime) -> NoteORM | None:
        """Update note; returns updated note or None if not found."""
        with Session(self._engine) as session:
            existing = session.get(NoteORM, note_id)
            if existing is None:
                return None
            existing.title = title
            existing.content = content
            existing.updated_at = now
            session.add(existing)
            session.commit()
            session.refresh(existing)
            return existing

    def delete_note(self, note_id: int) -> bool:
        """Delete note by id; returns True if deleted."""
        with Session(self._engine) as session:
            existing = session.get(NoteORM, note_id)
            if existing is None:
                return False
            session.delete(existing)
            session.commit()
            return True
