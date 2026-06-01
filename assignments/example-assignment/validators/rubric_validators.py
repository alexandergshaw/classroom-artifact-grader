from __future__ import annotations

from grader.models import Rubric


def validate_points_positive(rubric: Rubric) -> None:
    if rubric.points_possible <= 0:
        raise ValueError("points_possible must be > 0")


def register_validators() -> list:
    return [validate_points_positive]
