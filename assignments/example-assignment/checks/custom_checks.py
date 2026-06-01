from __future__ import annotations

from grader.models import Check, CheckResult


def check_contains_student_name(check: Check, context: dict) -> CheckResult:
    expected = str(check.model_dump().get("name", "")).lower()
    text = str(context.get("text", "")).lower()
    passed = expected in text
    return CheckResult(
        id=check.id,
        type=check.type,
        passed=passed,
        earned_points=check.points if passed else 0,
        possible_points=check.points,
        feedback=("Student name found by plugin." if passed else f"Plugin check missing name: {expected}"),
        evidence={"name": expected},
    )


def register_checks() -> dict:
    return {"contains_student_name": check_contains_student_name}
