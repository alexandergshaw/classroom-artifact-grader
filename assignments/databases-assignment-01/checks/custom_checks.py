"""Custom checks for databases-assignment-01.

Provides a check that verifies students mention ERDs (Entity-Relationship
Diagrams) in their submission.
"""

from __future__ import annotations

from grader.models import Check, CheckResult


def check_erd_mentioned(check: Check, context: dict) -> CheckResult:
    """Pass when the submission mentions 'ERD' or 'entity-relationship diagram'."""
    text = str(context.get("text", "")).lower()
    keywords = ["erd", "entity-relationship diagram", "entity relationship diagram"]
    passed = any(kw in text for kw in keywords)
    return CheckResult(
        id=check.id,
        type=check.type,
        passed=passed,
        earned_points=check.points if passed else 0,
        possible_points=check.points,
        feedback=(
            "ERD or entity-relationship diagram is mentioned."
            if passed
            else "Submission does not reference an ERD or entity-relationship diagram."
        ),
        evidence={"keywords_checked": keywords},
    )


def register_checks() -> dict:
    return {"erd_mentioned": check_erd_mentioned}
