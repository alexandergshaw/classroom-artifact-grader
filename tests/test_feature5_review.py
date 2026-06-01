"""Tests for Feature 5: Instructor Review Workflow."""

from __future__ import annotations

from pathlib import Path

from grader.main import build_report
from grader.models import CheckResult, GradeReport
from grader.report_generator import write_report


REPO_ROOT = Path(__file__).parent.parent
ASSIGNMENT_DIR = REPO_ROOT / "assignments" / "demo-assignment"
SUBMISSIONS_DIR = REPO_ROOT / "submissions"


# ---------------------------------------------------------------------------
# review_form.md generation
# ---------------------------------------------------------------------------


def test_write_report_generates_review_form(tmp_path: Path) -> None:
    """write_report should create review_form.md alongside report.json and report.md."""
    report = GradeReport(
        assignment_id="test-assignment",
        submission_path="submissions/student.txt",
        total_score=8,
        points_possible=20,
        passed_checks=[
            CheckResult(id="wc", type="word_count", passed=True, earned_points=8,
                        possible_points=8, feedback="ok")
        ],
        failed_checks=[
            CheckResult(id="cit", type="citation_count", passed=False, earned_points=0,
                        possible_points=5, feedback="Missing citations.")
        ],
        manual_review_items=[
            CheckResult(id="reflection", type="manual", passed=False, earned_points=0,
                        possible_points=7, feedback="Manual review required.", manual_review=True)
        ],
        feedback=["Missing citations."],
        instructor_notes="",
    )
    json_path, md_path, review_path = write_report(
        report, tmp_path, Path("templates/report_template.md")
    )
    assert review_path.exists(), "review_form.md was not created"
    assert review_path.name == "review_form.md"


def test_review_form_contains_auto_score(tmp_path: Path) -> None:
    report = GradeReport(
        assignment_id="a1",
        submission_path="sub.txt",
        total_score=15,
        points_possible=30,
        passed_checks=[],
        failed_checks=[],
        manual_review_items=[],
        feedback=[],
        instructor_notes="",
    )
    _, _, review_path = write_report(report, tmp_path, Path("templates/report_template.md"))
    content = review_path.read_text(encoding="utf-8")
    assert "Auto score" in content
    assert "15" in content


def test_review_form_contains_manual_review_section(tmp_path: Path) -> None:
    report = GradeReport(
        assignment_id="a1",
        submission_path="sub.txt",
        total_score=0,
        points_possible=20,
        passed_checks=[],
        failed_checks=[],
        manual_review_items=[
            CheckResult(id="quality", type="manual", passed=False, earned_points=0,
                        possible_points=10, feedback="Manual review required.", manual_review=True)
        ],
        feedback=[],
        instructor_notes="",
    )
    _, _, review_path = write_report(report, tmp_path, Path("templates/report_template.md"))
    content = review_path.read_text(encoding="utf-8")
    assert "Manual Review" in content
    assert "quality" in content
    assert "10" in content


def test_review_form_contains_instructor_notes_section(tmp_path: Path) -> None:
    report = GradeReport(
        assignment_id="a1",
        submission_path="sub.txt",
        total_score=0,
        points_possible=10,
        passed_checks=[],
        failed_checks=[],
        manual_review_items=[],
        feedback=[],
        instructor_notes="Great effort overall.",
    )
    _, _, review_path = write_report(report, tmp_path, Path("templates/report_template.md"))
    content = review_path.read_text(encoding="utf-8")
    assert "Instructor Notes" in content
    assert "Great effort overall." in content


def test_review_form_contains_final_score_section(tmp_path: Path) -> None:
    report = GradeReport(
        assignment_id="a1",
        submission_path="sub.txt",
        total_score=5,
        points_possible=10,
        passed_checks=[],
        failed_checks=[],
        manual_review_items=[],
        feedback=[],
        instructor_notes="",
    )
    _, _, review_path = write_report(report, tmp_path, Path("templates/report_template.md"))
    content = review_path.read_text(encoding="utf-8")
    assert "Final Score" in content
    assert "10" in content  # points_possible appears in final score line


def test_review_form_contains_rubric_breakdown(tmp_path: Path) -> None:
    report = GradeReport(
        assignment_id="a1",
        submission_path="sub.txt",
        total_score=5,
        points_possible=10,
        passed_checks=[
            CheckResult(id="wc", type="word_count", passed=True, earned_points=5,
                        possible_points=5, feedback="ok")
        ],
        failed_checks=[
            CheckResult(id="cit", type="citation_count", passed=False, earned_points=0,
                        possible_points=5, feedback="missing")
        ],
        manual_review_items=[],
        feedback=[],
        instructor_notes="",
    )
    _, _, review_path = write_report(report, tmp_path, Path("templates/report_template.md"))
    content = review_path.read_text(encoding="utf-8")
    assert "Passed Checks" in content
    assert "Failed Checks" in content
    assert "wc" in content
    assert "cit" in content


# ---------------------------------------------------------------------------
# End-to-end review form via build_report
# ---------------------------------------------------------------------------


def test_build_report_writes_review_form(tmp_path: Path) -> None:
    """build_report should write review_form.md for each submission."""
    report = build_report(
        assignment=str(ASSIGNMENT_DIR),
        submission=str(SUBMISSIONS_DIR / "excellent_submission.docx"),
        output_dir=str(tmp_path),
    )
    assert (tmp_path / "review_form.md").exists(), "review_form.md not written by build_report"


def test_review_form_includes_manual_items_from_demo(tmp_path: Path) -> None:
    """Demo rubric has one manual check; it should appear in the review form."""
    build_report(
        assignment=str(ASSIGNMENT_DIR),
        submission=str(SUBMISSIONS_DIR / "excellent_submission.docx"),
        output_dir=str(tmp_path),
    )
    content = (tmp_path / "review_form.md").read_text(encoding="utf-8")
    assert "Manual Review" in content
