"""experiment_journal.py — Cross-run journal for experiment-level notes.

Stored at results/{experiment}/common/experiment_journal.json.
The journal is mutable and researcher-authored; it is never touched
by the framework run pipeline.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel

JOURNAL_FILE = "experiment_journal.json"


class ExperimentJournalEntry(BaseModel):
    entry_id: str
    timestamp: str
    text: str
    entry_type: Literal[
        "note", "hypothesis", "finding", "question"
    ] = "note"
    tags: list[str] = []
    linked_run_id: Optional[str] = None


def _journal_path(common_folder: str) -> str:
    return os.path.join(common_folder, JOURNAL_FILE)


def load_journal(common_folder: str) -> list[ExperimentJournalEntry]:
    path = _journal_path(common_folder)
    if not os.path.exists(path):
        return []
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return [ExperimentJournalEntry(**item) for item in data]
    except (json.JSONDecodeError, Exception):
        return []


def save_journal(
    entries: list[ExperimentJournalEntry],
    common_folder: str,
) -> None:
    os.makedirs(common_folder, exist_ok=True)
    path = _journal_path(common_folder)
    with open(path, "w", encoding="utf-8") as f:
        json.dump([e.model_dump() for e in entries], f, indent=2)


def add_entry(
    text: str,
    common_folder: str,
    entry_type: Literal[
        "note", "hypothesis", "finding", "question"
    ] = "note",
    tags: Optional[list[str]] = None,
    linked_run_id: Optional[str] = None,
) -> ExperimentJournalEntry:
    entries = load_journal(common_folder)
    entry = ExperimentJournalEntry(
        entry_id=str(uuid.uuid4()),
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        text=text.strip(),
        entry_type=entry_type,
        tags=tags or [],
        linked_run_id=linked_run_id or None,
    )
    entries.append(entry)
    save_journal(entries, common_folder)
    return entry


def delete_entry(entry_id: str, common_folder: str) -> bool:
    entries = load_journal(common_folder)
    filtered = [e for e in entries if e.entry_id != entry_id]
    if len(filtered) == len(entries):
        return False
    save_journal(filtered, common_folder)
    return True
