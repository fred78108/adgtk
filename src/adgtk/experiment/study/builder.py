"""study/builder.py — Interactive CLI for study blueprints.

Study blueprints are saved as YAML files under the ``studies/``
directory, mirroring how experiment blueprints live in ``blueprints/``.
"""

from __future__ import annotations

import os
from typing import Optional

import yaml

from adgtk.utils.defaults import EXP_RESULTS_FOLDER, STUDY_DEF_DIR
from adgtk.experiment.study.structure import StudyBlueprint


# ----------------------------------------------------------------------
# YAML load/save
# ----------------------------------------------------------------------

def load_study_blueprint(name: str) -> StudyBlueprint:
    """Load a StudyBlueprint from ``studies/{name}.yaml``.

    Args:
        name: Study name (with or without .yaml suffix).

    Returns:
        Parsed StudyBlueprint.

    Raises:
        FileNotFoundError: If the YAML file does not exist.
        ValueError: If the YAML cannot be parsed into a StudyBlueprint.
    """
    filename = name if name.endswith(".yaml") else f"{name}.yaml"
    path = os.path.join(STUDY_DEF_DIR, filename)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Study blueprint not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    try:
        return StudyBlueprint(**data)
    except Exception as exc:
        raise ValueError(
            f"Could not parse study blueprint {path}: {exc}"
        ) from exc


def save_study_blueprint(blueprint: StudyBlueprint) -> str:
    """Save a StudyBlueprint to ``studies/{blueprint.name}.yaml``.

    Args:
        blueprint: The StudyBlueprint to save.

    Returns:
        Path to the written file.
    """
    os.makedirs(STUDY_DEF_DIR, exist_ok=True)
    path = os.path.join(STUDY_DEF_DIR, f"{blueprint.name}.yaml")
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(blueprint.model_dump(), f, sort_keys=False)
    return path


def list_study_blueprints() -> list[str]:
    """Return names of all study blueprints in the ``studies/`` directory."""
    if not os.path.isdir(STUDY_DEF_DIR):
        return []
    return [
        f[:-5]
        for f in sorted(os.listdir(STUDY_DEF_DIR))
        if f.endswith(".yaml")
    ]


# ----------------------------------------------------------------------
# Available experiments helper
# ----------------------------------------------------------------------

def _available_experiments() -> list[str]:
    """Return experiment names that have a results folder on disk."""
    if not os.path.isdir(EXP_RESULTS_FOLDER):
        return []
    return sorted(
        d for d in os.listdir(EXP_RESULTS_FOLDER)
        if os.path.isdir(os.path.join(EXP_RESULTS_FOLDER, d))
    )


# ----------------------------------------------------------------------
# Interactive builder
# ----------------------------------------------------------------------

def build_study(name: Optional[str] = None) -> Optional[StudyBlueprint]:
    """Interactively create a StudyBlueprint and save it to ``studies/``.

    If *name* is supplied the name prompt is skipped.

    Args:
        name: Optional pre-set study name.

    Returns:
        The created StudyBlueprint, or None if the user cancelled.
    """
    print()
    print("=" * 60)
    print("  Build a Study Blueprint")
    print("=" * 60)

    # ── name ──────────────────────────────────────────────────────────
    if name is None:
        name = input("Study name: ").strip()
    if not name:
        print("Cancelled — no name provided.")
        return None

    # Warn if a blueprint already exists
    existing_path = os.path.join(STUDY_DEF_DIR, f"{name}.yaml")
    if os.path.exists(existing_path):
        overwrite = input(
            f"  Blueprint '{name}' already exists. Overwrite? [y/N] "
        ).strip().lower()
        if overwrite != "y":
            print("Cancelled.")
            return None

    # ── description ───────────────────────────────────────────────────
    description = input("Description (optional): ").strip()

    # ── tags ──────────────────────────────────────────────────────────
    tags_raw = input("Tags (comma-separated, optional): ").strip()
    tags = (
        [t.strip() for t in tags_raw.split(",") if t.strip()]
        if tags_raw else []
    )

    # ── experiments ───────────────────────────────────────────────────
    available = _available_experiments()
    selected: list[str] = []

    if not available:
        print(
            "  No experiments found in results/. "
            "Add experiments by name manually."
        )
        manual = input("Experiment names (comma-separated): ").strip()
        selected = [e.strip() for e in manual.split(",") if e.strip()]
    else:
        print()
        print("Available experiments (from results/):")
        for idx, exp in enumerate(available):
            print(f"  {idx:3} : {exp}")
        print()
        print("Enter indices (comma-separated), experiment names, or 'all':")
        raw = input("> ").strip()

        if raw.lower() == "all":
            selected = list(available)
        else:
            for token in raw.split(","):
                token = token.strip()
                if not token:
                    continue
                try:
                    selected.append(available[int(token)])
                except (ValueError, IndexError):
                    selected.append(token)

    if not selected:
        print("  No experiments selected. Cancelled.")
        return None

    # ── confirm ───────────────────────────────────────────────────────
    print()
    print("  Study    :", name)
    if description:
        print("  Desc     :", description)
    if tags:
        print("  Tags     :", ", ".join(tags))
    print("  Experiments:")
    for exp in selected:
        print(f"    - {exp}")
    print()
    confirm = input("Save? [Y/n] ").strip().lower()
    if confirm == "n":
        print("Cancelled.")
        return None

    blueprint = StudyBlueprint(
        name=name,
        description=description,
        tags=tags,
        experiments=selected,
    )
    path = save_study_blueprint(blueprint)
    print(f"  Saved: {path}")
    return blueprint
