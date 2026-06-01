from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Check(BaseModel):
    id: str
    type: str
    points: float = 0

    model_config = ConfigDict(extra="allow")


class Rubric(BaseModel):
    assignment_id: str
    points_possible: float
    submission_types: list[str] = Field(default_factory=list)
    checks: list[Check] = Field(default_factory=list)


class CheckResult(BaseModel):
    id: str
    type: str
    passed: bool
    earned_points: float
    possible_points: float
    feedback: str
    evidence: Any | None = None
    manual_review: bool = False


class GradeReport(BaseModel):
    assignment_id: str
    submission_path: str
    total_score: float
    points_possible: float
    passed_checks: list[CheckResult]
    failed_checks: list[CheckResult]
    manual_review_items: list[CheckResult]
    instructor_notes: str = ""
