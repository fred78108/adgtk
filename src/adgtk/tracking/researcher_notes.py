"""researcher_notes.py — Sidecar notes for post-run researcher annotations.

Stored at results/{experiment}/{run_id}/conclusions/researcher_notes.json.
The RunManifest is never modified; notes live alongside it.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime

from pydantic import BaseModel

NOTES_FILE = "researcher_notes.json"


class ResearcherNote(BaseModel):
    note_id: str
    timestamp: str
    text: str


def load_notes(conclusion_folder: str) -> list[ResearcherNote]:
    path = os.path.join(conclusion_folder, NOTES_FILE)
    if not os.path.exists(path):
        return []
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return [ResearcherNote(**item) for item in data]
    except (json.JSONDecodeError, Exception):
        return []


def save_notes(notes: list[ResearcherNote], conclusion_folder: str) -> None:
    os.makedirs(conclusion_folder, exist_ok=True)
    path = os.path.join(conclusion_folder, NOTES_FILE)
    with open(path, "w", encoding="utf-8") as f:
        json.dump([n.model_dump() for n in notes], f, indent=2)


def add_note(text: str, conclusion_folder: str) -> ResearcherNote:
    notes = load_notes(conclusion_folder)
    note = ResearcherNote(
        note_id=str(uuid.uuid4()),
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        text=text.strip(),
    )
    notes.append(note)
    save_notes(notes, conclusion_folder)
    return note


def delete_note(note_id: str, conclusion_folder: str) -> bool:
    notes = load_notes(conclusion_folder)
    filtered = [n for n in notes if n.note_id != note_id]
    if len(filtered) == len(notes):
        return False
    save_notes(filtered, conclusion_folder)
    return True
