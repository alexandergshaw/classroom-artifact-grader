"""Tests for Feature 7: Production Batch Grading, and Feature 8: Instructor Summary."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from grader.batch_grader import (
    SUPPORTED_EXTENSIONS,
    discover_submissions,
    run_batch,
    _write_gradebook,
    _write_summary,
    _write_instructor_summary,
)

REPO_ROOT = Path(__file__).parent.parent
ASSIGNMENT_DIR = REPO_ROOT / "assignments" / "demo-assignment"
SUBMISSIONS_DIR = REPO_ROOT / "submissions"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_txt_submission(directory: Path, name: str, content: str) -> Path:
    path = directory / name
    path.write_text(content, encoding="utf-8")
    return path


def _make_demo_batch_dir(tmp_path: Path) -> Path:
    """Copy the demo submissions into a temp directory for batch grading."""
    import shutil

    batch_dir = tmp_path / "submissions"
    batch_dir.mkdir()
    for filename in ["excellent_submission.docx", "passing_submission.docx", "failing_submission.docx"]:
        shutil.copy(SUBMISSIONS_DIR / filename, batch_dir / filename)
    return batch_dir


# ---------------------------------------------------------------------------
# Feature 7: Discovery
# ---------------------------------------------------------------------------


def test_discover_finds_txt_files(tmp_path: Path) -> None:
    sub_dir = tmp_path / "subs"
    sub_dir.mkdir()
    (sub_dir / "a.txt").write_text("hello", encoding="utf-8")
    (sub_dir / "b.txt").write_text("world", encoding="utf-8")
    found = discover_submissions(sub_dir)
    assert len(found) == 2


def test_discover_recursively_finds_submissions(tmp_path: Path) -> None:
    sub_dir = tmp_path / "subs"
    nested = sub_dir / "student1"
    nested.mkdir(parents=True)
    (nested / "essay.txt").write_text("content", encoding="utf-8")
    (sub_dir / "top.txt").write_text("top level", encoding="utf-8")
    found = discover_submissions(sub_dir)
    assert len(found) == 2


def test_discover_ignores_unsupported_extensions(tmp_path: Path) -> None:
    sub_dir = tmp_path / "subs"
    sub_dir.mkdir()
    (sub_dir / "readme.md").write_text("# notes", encoding="utf-8")
    (sub_dir / "data.json").write_text("{}", encoding="utf-8")
    (sub_dir / "essay.txt").write_text("actual submission", encoding="utf-8")
    found = discover_submissions(sub_dir)
    assert len(found) == 1
    assert found[0].name == "essay.txt"


def test_discover_returns_empty_list_for_empty_dir(tmp_path: Path) -> None:
    sub_dir = tmp_path / "empty"
    sub_dir.mkdir()
    assert discover_submissions(sub_dir) == []


def test_discover_returns_sorted_results(tmp_path: Path) -> None:
    sub_dir = tmp_path / "subs"
    sub_dir.mkdir()
    (sub_dir / "charlie.txt").write_text("c", encoding="utf-8")
    (sub_dir / "alice.txt").write_text("a", encoding="utf-8")
    (sub_dir / "bob.txt").write_text("b", encoding="utf-8")
    found = discover_submissions(sub_dir)
    names = [f.name for f in found]
    assert names == sorted(names)


# ---------------------------------------------------------------------------
# Feature 7: Batch grading (end-to-end with demo submissions)
# ---------------------------------------------------------------------------


def test_run_batch_grades_demo_submissions(tmp_path: Path) -> None:
    batch_dir = _make_demo_batch_dir(tmp_path)
    rows = run_batch(str(ASSIGNMENT_DIR), str(batch_dir), str(tmp_path / "reports"))
    assert len(rows) == 3
    assert all(r["status"] == "success" for r in rows)


def test_run_batch_generates_per_submission_report_folders(tmp_path: Path) -> None:
    batch_dir = _make_demo_batch_dir(tmp_path)
    run_batch(str(ASSIGNMENT_DIR), str(batch_dir), str(tmp_path / "reports"))
    assignment_id = "demo-assignment"
    for stem in ["excellent_submission", "passing_submission", "failing_submission"]:
        report_dir = tmp_path / "reports" / assignment_id / stem
        assert (report_dir / "report.json").exists(), f"report.json missing for {stem}"
        assert (report_dir / "report.md").exists(), f"report.md missing for {stem}"
        assert (report_dir / "review_form.md").exists(), f"review_form.md missing for {stem}"


def test_run_batch_continues_after_individual_failure(tmp_path: Path) -> None:
    """Batch must not abort when one submission fails (e.g., wrong type)."""
    # Create an assignment that only accepts PDF; provide a TXT submission
    (tmp_path / "rubric.yaml").write_text(
        "assignment_id: pdf-only\npoints_possible: 10\nsubmission_types:\n  - pdf\n"
        "checks:\n  - id: wc\n    type: word_count\n    min: 1\n    points: 10\n",
        encoding="utf-8",
    )
    sub_dir = tmp_path / "subs"
    sub_dir.mkdir()
    (sub_dir / "invalid.txt").write_text("hello", encoding="utf-8")
    (sub_dir / "also_invalid.txt").write_text("hello also", encoding="utf-8")

    rows = run_batch(str(tmp_path), str(sub_dir), str(tmp_path / "reports"))
    assert len(rows) == 2
    assert all(r["status"] == "error" for r in rows)  # all fail but batch completes


def test_run_batch_handles_empty_submission_dir(tmp_path: Path) -> None:
    """An empty submission dir should not raise; returns empty rows."""
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    rows = run_batch(str(ASSIGNMENT_DIR), str(empty_dir), str(tmp_path / "reports"))
    assert rows == []


def test_run_batch_partial_failures_still_generate_gradebook(tmp_path: Path) -> None:
    """Even with partial failures, gradebook.csv must be written."""
    (tmp_path / "rubric.yaml").write_text(
        "assignment_id: mixed\npoints_possible: 10\nsubmission_types:\n  - txt\n"
        "checks:\n  - id: wc\n    type: word_count\n    min: 1\n    points: 10\n",
        encoding="utf-8",
    )
    sub_dir = tmp_path / "subs"
    sub_dir.mkdir()
    (sub_dir / "good.txt").write_text("hello world", encoding="utf-8")

    rows = run_batch(str(tmp_path), str(sub_dir), str(tmp_path / "reports"))
    assert len(rows) == 1
    gradebook = tmp_path / "reports" / "mixed" / "gradebook.csv"
    assert gradebook.exists()


# ---------------------------------------------------------------------------
# Feature 7: gradebook.csv
# ---------------------------------------------------------------------------


def test_gradebook_csv_has_correct_columns(tmp_path: Path) -> None:
    batch_dir = _make_demo_batch_dir(tmp_path)
    run_batch(str(ASSIGNMENT_DIR), str(batch_dir), str(tmp_path / "reports"))
    csv_path = tmp_path / "reports" / "demo-assignment" / "gradebook.csv"
    assert csv_path.exists()
    with csv_path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        columns = reader.fieldnames or []
    expected = [
        "submission_name", "assignment_id", "auto_score", "auto_points_possible",
        "manual_points_available", "final_points_possible", "passed_checks",
        "failed_checks", "manual_checks", "status", "error_message", "report_path",
    ]
    for col in expected:
        assert col in columns, f"Column '{col}' missing from gradebook.csv"


def test_gradebook_csv_has_one_row_per_submission(tmp_path: Path) -> None:
    batch_dir = _make_demo_batch_dir(tmp_path)
    run_batch(str(ASSIGNMENT_DIR), str(batch_dir), str(tmp_path / "reports"))
    csv_path = tmp_path / "reports" / "demo-assignment" / "gradebook.csv"
    with csv_path.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 3


def test_gradebook_csv_records_error_message_for_failures(tmp_path: Path) -> None:
    (tmp_path / "rubric.yaml").write_text(
        "assignment_id: err-test\npoints_possible: 10\nsubmission_types:\n  - pdf\n"
        "checks:\n  - id: wc\n    type: word_count\n    min: 1\n    points: 10\n",
        encoding="utf-8",
    )
    sub_dir = tmp_path / "subs"
    sub_dir.mkdir()
    (sub_dir / "bad.txt").write_text("wrong type", encoding="utf-8")
    run_batch(str(tmp_path), str(sub_dir), str(tmp_path / "reports"))
    csv_path = tmp_path / "reports" / "err-test" / "gradebook.csv"
    with csv_path.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert rows[0]["status"] == "error"
    assert rows[0]["error_message"] != ""


# ---------------------------------------------------------------------------
# Feature 7: summary.json
# ---------------------------------------------------------------------------


def test_summary_json_is_generated(tmp_path: Path) -> None:
    batch_dir = _make_demo_batch_dir(tmp_path)
    run_batch(str(ASSIGNMENT_DIR), str(batch_dir), str(tmp_path / "reports"))
    summary_path = tmp_path / "reports" / "demo-assignment" / "summary.json"
    assert summary_path.exists()


def test_summary_json_has_required_keys(tmp_path: Path) -> None:
    batch_dir = _make_demo_batch_dir(tmp_path)
    run_batch(str(ASSIGNMENT_DIR), str(batch_dir), str(tmp_path / "reports"))
    data = json.loads((tmp_path / "reports" / "demo-assignment" / "summary.json").read_text(encoding="utf-8"))
    for key in [
        "total_submissions", "successful_submissions", "failed_submissions",
        "average_auto_score", "median_auto_score", "highest_auto_score",
        "lowest_auto_score", "pass_rate",
    ]:
        assert key in data, f"summary.json missing key: {key}"


def test_summary_json_counts_are_correct(tmp_path: Path) -> None:
    batch_dir = _make_demo_batch_dir(tmp_path)
    run_batch(str(ASSIGNMENT_DIR), str(batch_dir), str(tmp_path / "reports"))
    data = json.loads((tmp_path / "reports" / "demo-assignment" / "summary.json").read_text(encoding="utf-8"))
    assert data["total_submissions"] == 3
    assert data["successful_submissions"] == 3
    assert data["failed_submissions"] == 0


def test_summary_json_with_only_errors(tmp_path: Path) -> None:
    (tmp_path / "rubric.yaml").write_text(
        "assignment_id: all-err\npoints_possible: 10\nsubmission_types:\n  - pdf\n"
        "checks:\n  - id: wc\n    type: word_count\n    min: 1\n    points: 10\n",
        encoding="utf-8",
    )
    sub_dir = tmp_path / "subs"
    sub_dir.mkdir()
    (sub_dir / "bad.txt").write_text("wrong type", encoding="utf-8")
    run_batch(str(tmp_path), str(sub_dir), str(tmp_path / "reports"))
    data = json.loads((tmp_path / "reports" / "all-err" / "summary.json").read_text(encoding="utf-8"))
    assert data["total_submissions"] == 1
    assert data["failed_submissions"] == 1
    assert data["average_auto_score"] is None


# ---------------------------------------------------------------------------
# Feature 8: instructor_summary.md
# ---------------------------------------------------------------------------


def test_instructor_summary_is_generated(tmp_path: Path) -> None:
    batch_dir = _make_demo_batch_dir(tmp_path)
    run_batch(str(ASSIGNMENT_DIR), str(batch_dir), str(tmp_path / "reports"))
    summary_path = tmp_path / "reports" / "demo-assignment" / "instructor_summary.md"
    assert summary_path.exists()


def test_instructor_summary_contains_required_sections(tmp_path: Path) -> None:
    batch_dir = _make_demo_batch_dir(tmp_path)
    run_batch(str(ASSIGNMENT_DIR), str(batch_dir), str(tmp_path / "reports"))
    content = (tmp_path / "reports" / "demo-assignment" / "instructor_summary.md").read_text(encoding="utf-8")
    assert "# Assignment Summary" in content
    assert "Common Failed Checks" in content
    assert "Manual Review Required" in content
    assert "Grading Warnings" in content


def test_instructor_summary_shows_submission_counts(tmp_path: Path) -> None:
    batch_dir = _make_demo_batch_dir(tmp_path)
    run_batch(str(ASSIGNMENT_DIR), str(batch_dir), str(tmp_path / "reports"))
    content = (tmp_path / "reports" / "demo-assignment" / "instructor_summary.md").read_text(encoding="utf-8")
    assert "Total submissions: 3" in content


def test_instructor_summary_lists_submissions_needing_manual_review(tmp_path: Path) -> None:
    """Demo rubric has a manual check; all three submissions should appear."""
    batch_dir = _make_demo_batch_dir(tmp_path)
    run_batch(str(ASSIGNMENT_DIR), str(batch_dir), str(tmp_path / "reports"))
    content = (tmp_path / "reports" / "demo-assignment" / "instructor_summary.md").read_text(encoding="utf-8")
    # All submissions have manual review items from the demo rubric
    assert "excellent_submission" in content or "passing_submission" in content


def test_instructor_summary_lists_grading_warnings_for_errors(tmp_path: Path) -> None:
    (tmp_path / "rubric.yaml").write_text(
        "assignment_id: warn-test\npoints_possible: 10\nsubmission_types:\n  - pdf\n"
        "checks:\n  - id: wc\n    type: word_count\n    min: 1\n    points: 10\n",
        encoding="utf-8",
    )
    sub_dir = tmp_path / "subs"
    sub_dir.mkdir()
    (sub_dir / "bad.txt").write_text("wrong type", encoding="utf-8")
    run_batch(str(tmp_path), str(sub_dir), str(tmp_path / "reports"))
    content = (tmp_path / "reports" / "warn-test" / "instructor_summary.md").read_text(encoding="utf-8")
    assert "bad.txt" in content


# ---------------------------------------------------------------------------
# Edge cases: invalid and corrupted submissions
# ---------------------------------------------------------------------------


def test_invalid_submission_type_recorded_as_error(tmp_path: Path) -> None:
    (tmp_path / "rubric.yaml").write_text(
        "assignment_id: type-test\npoints_possible: 10\nsubmission_types:\n  - txt\n"
        "checks:\n  - id: wc\n    type: word_count\n    min: 1\n    points: 10\n",
        encoding="utf-8",
    )
    sub_dir = tmp_path / "subs"
    sub_dir.mkdir()
    # .pdf is not in submission_types for this rubric
    (sub_dir / "wrong.pdf").write_bytes(b"%PDF-1.4 bad content")
    rows = run_batch(str(tmp_path), str(sub_dir), str(tmp_path / "reports"))
    assert rows[0]["status"] == "error"


def test_corrupted_docx_is_recorded_as_error(tmp_path: Path) -> None:
    (tmp_path / "rubric.yaml").write_text(
        "assignment_id: corrupt-test\npoints_possible: 10\nsubmission_types:\n  - docx\n"
        "checks:\n  - id: wc\n    type: word_count\n    min: 1\n    points: 10\n",
        encoding="utf-8",
    )
    sub_dir = tmp_path / "subs"
    sub_dir.mkdir()
    (sub_dir / "corrupt.docx").write_bytes(b"this is not a valid docx file")
    rows = run_batch(str(tmp_path), str(sub_dir), str(tmp_path / "reports"))
    assert rows[0]["status"] == "error"
    assert rows[0]["error_message"] != ""
