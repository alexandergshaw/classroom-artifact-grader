from __future__ import annotations

from grader.models import GradeReport


def add_default_note(report: GradeReport) -> None:
    if not report.instructor_notes:
        report.instructor_notes = "Review manual items before final grade release."


def register_feedback() -> list:
    return [add_default_note]
