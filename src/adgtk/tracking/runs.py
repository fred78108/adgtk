"""runs.py manages the per-run registry for tracking experiment executions.

Design
======
Stores one entry per experiment run in .tracking/runs.json. Experiment-level
aggregation is computed at query time by grouping runs — no separate record is
maintained so the two can never drift out of sync.

Note
====
Follows the same module-global pattern as project.py for consistency.
"""

import json
import os
from typing import Optional

from pydantic import ValidationError

from adgtk.utils.defaults import TRACKING_FOLDER
from adgtk.tracking.structure import RunEntryModel
from adgtk.utils import create_logger

_logger = create_logger(
    "adgtk.project.log",
    logger_name=__name__,
    subdir="framework"
)

RUNS_FILE = "runs.json"

_runs: list[RunEntryModel] = []
_loaded: bool = False


# ----------------------------------------------------------------------
# Internal helpers
# ----------------------------------------------------------------------

def _load(clear_existing: bool = False) -> None:
    global _runs, _loaded

    file_w_path = os.path.join(TRACKING_FOLDER, RUNS_FILE)
    os.makedirs(TRACKING_FOLDER, exist_ok=True)

    if not os.path.exists(file_w_path):
        with open(file_w_path, "w", encoding="utf-8") as f:
            f.write("[]")
        _logger.info("Created runs registry: %s", file_w_path)

    with open(file=file_w_path, mode="r", encoding="utf-8") as infile:
        data = json.load(infile)

    if clear_existing:
        if _runs:
            _logger.warning("Cleared existing run entries on reload")
        _runs = []

    try:
        for entry in data:
            _runs.append(RunEntryModel(**entry))
    except ValidationError as e:
        msg = f"Corrupt runs registry: {e}"
        _logger.error(msg)
        raise

    _logger.info("Loaded runs registry from %s", file_w_path)
    _loaded = True


def _save() -> None:
    file_w_path = os.path.join(TRACKING_FOLDER, RUNS_FILE)
    os.makedirs(TRACKING_FOLDER, exist_ok=True)

    runs_as_dict = [r.model_dump() for r in _runs]
    with open(file=file_w_path, mode="w", encoding="utf-8") as outfile:
        json.dump(runs_as_dict, outfile, indent=2)

    _logger.info("Saved runs registry to %s", file_w_path)


# ----------------------------------------------------------------------
# Public API
# ----------------------------------------------------------------------

def add_run(entry: RunEntryModel) -> None:
    """Registers a completed run. Skips silently if already registered.

    Args:
        entry: The run record to store.
    """
    if not _loaded:
        _load()

    for r in _runs:
        if r.run_id == entry.run_id:
            if r.experiment_name == entry.experiment_name:
                _logger.warning(
                    "Run %s / %s already registered — skipping",
                    entry.experiment_name, entry.run_id)
                return

    _runs.append(entry)
    _logger.info("Registered run %s / %s", entry.experiment_name, entry.run_id)
    _save()


def get_runs(experiment_name: Optional[str] = None) -> list[RunEntryModel]:
    """Returns all registered runs, optionally filtered by experiment.

    Args:
        experiment_name: If provided, only return runs for this experiment.

    Returns:
        List of matching RunEntryModel instances.
    """
    if not _loaded:
        _load()

    if experiment_name is None:
        return list(_runs)
    return [r for r in _runs if r.experiment_name == experiment_name]


def get_experiment_names() -> list[str]:
    """Returns sorted list of unique experiment names in the registry.

    Returns:
        Sorted list of experiment name strings.
    """
    if not _loaded:
        _load()

    seen: set[str] = set()
    names: list[str] = []
    for r in _runs:
        if r.experiment_name not in seen:
            seen.add(r.experiment_name)
            names.append(r.experiment_name)
    return sorted(names)


def remove_run(run_id: str, experiment_name: str) -> bool:
    """Removes a single run entry from the registry.

    Args:
        run_id: The run identifier.
        experiment_name: The experiment the run belongs to.

    Returns:
        True if an entry was removed, False if not found.
    """
    global _runs
    if not _loaded:
        _load()

    before = len(_runs)
    _runs = [
        r for r in _runs
        if not (r.run_id == run_id and r.experiment_name == experiment_name)
    ]
    if len(_runs) < before:
        _logger.info(
            "Removed run %s / %s from registry", experiment_name, run_id)
        _save()
        return True
    return False


def remove_experiment(experiment_name: str) -> int:
    """Removes all registry entries for an experiment.

    Args:
        experiment_name: The experiment whose entries should be removed.

    Returns:
        Number of entries removed.
    """
    global _runs
    if not _loaded:
        _load()

    before = len(_runs)
    _runs = [r for r in _runs if r.experiment_name != experiment_name]
    removed = before - len(_runs)
    if removed > 0:
        _logger.info(
            "Removed %d run entries for experiment %s",
            removed,
            experiment_name)
        _save()
    return removed
