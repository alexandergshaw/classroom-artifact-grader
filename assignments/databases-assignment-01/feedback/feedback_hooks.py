"""Feedback hooks for databases-assignment-01."""

from __future__ import annotations

from grader.models import GradeReport


def add_db_instructor_note(report: GradeReport) -> None:
    if not report.instructor_notes:
        report.instructor_notes = (
            "Please review the manual reflection section before releasing grades. "
            "The ERD discussion is worth 15 automated points."
        )


def register_feedback() -> list:
    return [add_db_instructor_note]
