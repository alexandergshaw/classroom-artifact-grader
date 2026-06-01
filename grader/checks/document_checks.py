from __future__ import annotations

from grader.models import Check, CheckResult


def heading_exists(check: Check, text: str, headings: list[str]) -> CheckResult:
    expected = str(check.model_dump().get("heading", "")).strip()
    heading_lower = {h.strip().lower() for h in headings}
    passed = expected.lower() in heading_lower or expected.lower() in text.lower()
    return CheckResult(
        id=check.id,
        type=check.type,
        passed=passed,
        earned_points=check.points if passed else 0,
        possible_points=check.points,
        feedback=("Heading found." if passed else f"Heading not found: {expected}"),
        evidence={"expected": expected, "headings": headings},
    )
