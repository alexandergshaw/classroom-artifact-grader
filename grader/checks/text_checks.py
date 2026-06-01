from __future__ import annotations

import re

from grader.models import Check, CheckResult


def word_count(check: Check, text: str) -> CheckResult:
    minimum = int(check.model_dump().get("min", 0))
    count = len(re.findall(r"\b\w+\b", text))
    passed = count >= minimum
    return CheckResult(
        id=check.id,
        type=check.type,
        passed=passed,
        earned_points=check.points if passed else 0,
        possible_points=check.points,
        feedback=("Word count requirement met." if passed else f"Expected at least {minimum} words, found {count}."),
        evidence={"count": count, "min": minimum},
    )


def required_terms(check: Check, text: str) -> CheckResult:
    terms = [str(t) for t in check.model_dump().get("terms", [])]
    text_lower = text.lower()
    missing = [term for term in terms if term.lower() not in text_lower]
    passed = not missing
    return CheckResult(
        id=check.id,
        type=check.type,
        passed=passed,
        earned_points=check.points if passed else 0,
        possible_points=check.points,
        feedback=("All required terms found." if passed else f"Missing terms: {', '.join(missing)}"),
        evidence={"missing": missing, "terms": terms},
    )


def citation_count(check: Check, text: str) -> CheckResult:
    minimum = int(check.model_dump().get("min", 0))
    apa_like = re.findall(r"\([A-Z][A-Za-z\-]+,\s*\d{4}\)", text)
    bracket_like = re.findall(r"\[[0-9]+\]", text)
    total = len(apa_like) + len(bracket_like)
    passed = total >= minimum
    return CheckResult(
        id=check.id,
        type=check.type,
        passed=passed,
        earned_points=check.points if passed else 0,
        possible_points=check.points,
        feedback=("Citation count requirement met." if passed else f"Expected at least {minimum} citations, found {total}."),
        evidence={"count": total, "min": minimum},
    )


def regex_contains(check: Check, text: str) -> CheckResult:
    pattern = str(check.model_dump().get("pattern", ""))
    matched = bool(re.search(pattern, text, re.IGNORECASE | re.MULTILINE))
    return CheckResult(
        id=check.id,
        type=check.type,
        passed=matched,
        earned_points=check.points if matched else 0,
        possible_points=check.points,
        feedback=("Regex pattern matched." if matched else f"Pattern not found: {pattern}"),
        evidence=pattern,
    )


def text_contains(check: Check, text: str) -> CheckResult:
    needle = str(check.model_dump().get("text", ""))
    passed = needle.lower() in text.lower()
    return CheckResult(
        id=check.id,
        type=check.type,
        passed=passed,
        earned_points=check.points if passed else 0,
        possible_points=check.points,
        feedback=("Text requirement met." if passed else f"Required text not found: {needle}"),
        evidence=needle,
    )
