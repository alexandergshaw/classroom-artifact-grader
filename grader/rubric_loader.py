from __future__ import annotations

from pathlib import Path

import yaml

from grader.models import Rubric


class RubricLoadError(Exception):
    """Raised when a rubric cannot be loaded."""


def load_rubric(assignment_path: str | Path) -> Rubric:
    assignment_dir = Path(assignment_path)
    rubric_path = assignment_dir / "rubric.yaml"
    if not rubric_path.exists():
        raise RubricLoadError(f"Rubric not found: {rubric_path}")

    try:
        with rubric_path.open("r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
        return Rubric.model_validate(raw)
    except Exception as exc:  # pragma: no cover
        raise RubricLoadError(f"Failed to load rubric: {exc}") from exc
