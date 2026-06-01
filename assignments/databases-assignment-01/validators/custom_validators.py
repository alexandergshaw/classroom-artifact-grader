"""Custom validators for databases-assignment-01."""

from __future__ import annotations

from grader.models import Rubric


def validate_has_manual_check(rubric: Rubric) -> None:
    """Ensure the rubric includes at least one manual check for reflection grading."""
    manual_checks = [c for c in rubric.checks if c.type == "manual"]
    if not manual_checks:
        raise ValueError(f"Rubric '{rubric.assignment_id}' must include at least one manual check.")


def register_validators() -> list:
    return [validate_has_manual_check]
