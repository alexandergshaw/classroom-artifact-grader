"""Tests for the end-to-end demo workflow.

Validates that:
- The demo rubric loads correctly.
- All three demo submissions can be processed by the grader.
- Report files (JSON + Markdown) are generated for each submission.
- Automated score calculations match expected values.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from grader.main import build_report
from grader.models import GradeReport
from grader.rubric_loader import load_rubric

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).parent.parent
ASSIGNMENT_DIR = REPO_ROOT / "assignments" / "demo-assignment"
SUBMISSIONS_DIR = REPO_ROOT / "submissions"

SUBMISSION_FILES = [
    "excellent_submission.docx",
    "passing_submission.docx",
    "failing_submission.docx",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _automated_score(report: GradeReport) -> float:
    """Sum of points earned from non-manual checks."""
    return sum(r.earned_points for r in report.passed_checks)


def _automated_possible(report: GradeReport) -> float:
    """Sum of points possible from non-manual checks."""
    return sum(r.possible_points for r in [*report.passed_checks, *report.failed_checks])


# ---------------------------------------------------------------------------
# Rubric tests
# ---------------------------------------------------------------------------


def test_demo_rubric_loads() -> None:
    """The demo rubric.yaml should parse without errors."""
    rubric = load_rubric(ASSIGNMENT_DIR)
    assert rubric.assignment_id == "demo-assignment"


def test_demo_rubric_points_possible() -> None:
    """The rubric should specify 100 total points."""
    rubric = load_rubric(ASSIGNMENT_DIR)
    assert rubric.points_possible == 100


def test_demo_rubric_has_all_check_types() -> None:
    """The rubric should include each required check type."""
    rubric = load_rubric(ASSIGNMENT_DIR)
    types = {check.type for check in rubric.checks}
    for expected_type in ("word_count", "heading_exists", "required_terms", "citation_count", "manual"):
        assert expected_type in types, f"Check type '{expected_type}' missing from rubric"


def test_demo_rubric_has_manual_check() -> None:
    """There should be exactly one manual-review check worth 30 points."""
    rubric = load_rubric(ASSIGNMENT_DIR)
    manual_checks = [c for c in rubric.checks if c.type == "manual"]
    assert len(manual_checks) == 1
    assert manual_checks[0].points == 30


def test_demo_rubric_submission_types_include_docx() -> None:
    """The rubric should accept docx submissions."""
    rubric = load_rubric(ASSIGNMENT_DIR)
    assert "docx" in [s.lower() for s in rubric.submission_types]


# ---------------------------------------------------------------------------
# Submission existence tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("filename", SUBMISSION_FILES)
def test_demo_submission_exists(filename: str) -> None:
    """Each demo submission file must exist on disk."""
    path = SUBMISSIONS_DIR / filename
    assert path.exists(), f"Demo submission not found: {path}"


# ---------------------------------------------------------------------------
# End-to-end grading tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("filename", SUBMISSION_FILES)
def test_demo_submission_can_be_graded(tmp_path: Path, filename: str) -> None:
    """The grader should process each demo submission without raising."""
    submission_path = SUBMISSIONS_DIR / filename
    report = build_report(
        assignment=str(ASSIGNMENT_DIR),
        submission=str(submission_path),
        output_dir=str(tmp_path),
    )
    assert isinstance(report, GradeReport)


@pytest.mark.parametrize("filename", SUBMISSION_FILES)
def test_demo_reports_are_written(tmp_path: Path, filename: str) -> None:
    """Both report.json and report.md must be created for each submission."""
    submission_path = SUBMISSIONS_DIR / filename
    build_report(
        assignment=str(ASSIGNMENT_DIR),
        submission=str(submission_path),
        output_dir=str(tmp_path),
    )
    assert (tmp_path / "report.json").exists(), "report.json not written"
    assert (tmp_path / "report.md").exists(), "report.md not written"


# ---------------------------------------------------------------------------
# Score correctness tests
# ---------------------------------------------------------------------------


def test_excellent_submission_score(tmp_path: Path) -> None:
    """excellent_submission should pass all automated checks (70/70)."""
    report = build_report(
        assignment=str(ASSIGNMENT_DIR),
        submission=str(SUBMISSIONS_DIR / "excellent_submission.docx"),
        output_dir=str(tmp_path),
    )
    assert _automated_score(report) == 70.0
    assert _automated_possible(report) == 70.0


def test_passing_submission_score(tmp_path: Path) -> None:
    """passing_submission should earn 45 automated points out of 70."""
    report = build_report(
        assignment=str(ASSIGNMENT_DIR),
        submission=str(SUBMISSIONS_DIR / "passing_submission.docx"),
        output_dir=str(tmp_path),
    )
    assert _automated_score(report) == 45.0
    assert _automated_possible(report) == 70.0


def test_failing_submission_score(tmp_path: Path) -> None:
    """failing_submission should earn 5 automated points out of 70."""
    report = build_report(
        assignment=str(ASSIGNMENT_DIR),
        submission=str(SUBMISSIONS_DIR / "failing_submission.docx"),
        output_dir=str(tmp_path),
    )
    assert _automated_score(report) == 5.0
    assert _automated_possible(report) == 70.0


def test_manual_review_items_never_earn_points(tmp_path: Path) -> None:
    """Manual review items should always have earned_points == 0 automatically."""
    for filename in SUBMISSION_FILES:
        report = build_report(
            assignment=str(ASSIGNMENT_DIR),
            submission=str(SUBMISSIONS_DIR / filename),
            output_dir=str(tmp_path),
        )
        for item in report.manual_review_items:
            assert item.earned_points == 0, (
                f"{filename}: manual item '{item.id}' auto-awarded {item.earned_points} points"
            )


def test_excellent_has_no_failed_automated_checks(tmp_path: Path) -> None:
    """excellent_submission should have zero failed automated checks."""
    report = build_report(
        assignment=str(ASSIGNMENT_DIR),
        submission=str(SUBMISSIONS_DIR / "excellent_submission.docx"),
        output_dir=str(tmp_path),
    )
    assert report.failed_checks == []
