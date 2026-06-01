"""Tests for Feature 6: Deterministic Feedback Engine."""

from __future__ import annotations

from pathlib import Path

import pytest

from grader.feedback_engine import FeedbackEngine
from grader.main import build_report
from grader.models import Check, CheckResult


REPO_ROOT = Path(__file__).parent.parent
ASSIGNMENT_DIR = REPO_ROOT / "assignments" / "demo-assignment"
SUBMISSIONS_DIR = REPO_ROOT / "submissions"


# ---------------------------------------------------------------------------
# FeedbackEngine unit tests
# ---------------------------------------------------------------------------


def test_engine_generates_message_for_known_check_type() -> None:
    engine = FeedbackEngine()
    failed = [
        CheckResult(id="wc", type="word_count", passed=False, earned_points=0,
                    possible_points=5, feedback="Too short.")
    ]
    messages = engine.generate(failed)
    assert len(messages) == 1
    # Should use the rule from feedback_rules.yaml, not the check's raw feedback
    assert "word count" in messages[0].lower() or "minimum" in messages[0].lower()


def test_engine_falls_back_to_check_feedback_for_unknown_type() -> None:
    engine = FeedbackEngine()
    failed = [
        CheckResult(id="custom", type="unknown_custom_type", passed=False, earned_points=0,
                    possible_points=5, feedback="Custom failure message.")
    ]
    messages = engine.generate(failed)
    assert "Custom failure message." in messages


def test_engine_deduplicates_messages() -> None:
    engine = FeedbackEngine()
    failed = [
        CheckResult(id="wc1", type="word_count", passed=False, earned_points=0,
                    possible_points=5, feedback="Too short."),
        CheckResult(id="wc2", type="word_count", passed=False, earned_points=0,
                    possible_points=5, feedback="Too short."),
    ]
    messages = engine.generate(failed)
    # Both have the same type → same rule message → deduplicated
    assert len(messages) == 1


def test_engine_generates_no_messages_for_empty_list() -> None:
    engine = FeedbackEngine()
    assert engine.generate([]) == []


def test_engine_loads_assignment_override(tmp_path: Path) -> None:
    """Assignment-specific feedback_rules.yaml overrides the default rule."""
    feedback_dir = tmp_path / "feedback"
    feedback_dir.mkdir()
    override = feedback_dir / "feedback_rules.yaml"
    override.write_text("word_count:\n  fail: 'Assignment-specific word count message.'\n", encoding="utf-8")

    engine = FeedbackEngine(assignment_path=tmp_path)
    failed = [
        CheckResult(id="wc", type="word_count", passed=False, earned_points=0,
                    possible_points=5, feedback="Too short.")
    ]
    messages = engine.generate(failed)
    assert messages == ["Assignment-specific word count message."]


def test_engine_handles_missing_assignment_override_gracefully(tmp_path: Path) -> None:
    """Missing assignment-level rules file should not raise."""
    engine = FeedbackEngine(assignment_path=tmp_path)  # no feedback/ subdirectory
    failed = [
        CheckResult(id="wc", type="word_count", passed=False, earned_points=0,
                    possible_points=5, feedback="Too short.")
    ]
    messages = engine.generate(failed)
    assert len(messages) == 1


def test_engine_handles_corrupted_rules_file_gracefully(tmp_path: Path) -> None:
    """Corrupted feedback_rules.yaml should not raise; engine uses default rules only."""
    feedback_dir = tmp_path / "feedback"
    feedback_dir.mkdir()
    (feedback_dir / "feedback_rules.yaml").write_text(":{invalid yaml:::", encoding="utf-8")

    engine = FeedbackEngine(assignment_path=tmp_path)
    # Should not raise
    assert isinstance(engine.generate([]), list)


def test_databases_assignment_uses_override(tmp_path: Path) -> None:
    """databases-assignment-01 has custom feedback overrides that should be used."""
    db_assignment = REPO_ROOT / "assignments" / "databases-assignment-01"
    engine = FeedbackEngine(assignment_path=db_assignment)
    failed = [
        CheckResult(id="erd", type="erd_mentioned", passed=False, earned_points=0,
                    possible_points=15, feedback="Default fallback.")
    ]
    messages = engine.generate(failed)
    assert len(messages) == 1
    assert "ERD" in messages[0] or "entity" in messages[0].lower()


# ---------------------------------------------------------------------------
# Integration: feedback in report
# ---------------------------------------------------------------------------


def test_feedback_included_in_report_json(tmp_path: Path) -> None:
    """The GradeReport's feedback list should appear in report.json."""
    report = build_report(
        assignment=str(ASSIGNMENT_DIR),
        submission=str(SUBMISSIONS_DIR / "failing_submission.docx"),
        output_dir=str(tmp_path),
    )
    import json
    data = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert "feedback" in data
    assert isinstance(data["feedback"], list)


def test_feedback_included_in_report_md(tmp_path: Path) -> None:
    """The Feedback section should appear in report.md."""
    build_report(
        assignment=str(ASSIGNMENT_DIR),
        submission=str(SUBMISSIONS_DIR / "failing_submission.docx"),
        output_dir=str(tmp_path),
    )
    content = (tmp_path / "report.md").read_text(encoding="utf-8")
    assert "Feedback" in content


def test_no_feedback_for_perfect_submission(tmp_path: Path) -> None:
    """A submission that passes all automated checks should have no feedback."""
    report = build_report(
        assignment=str(ASSIGNMENT_DIR),
        submission=str(SUBMISSIONS_DIR / "excellent_submission.docx"),
        output_dir=str(tmp_path),
    )
    # excellent_submission passes all automated checks
    assert report.feedback == []


def test_multiple_check_types_produce_distinct_messages(tmp_path: Path) -> None:
    engine = FeedbackEngine()
    failed = [
        CheckResult(id="wc", type="word_count", passed=False, earned_points=0,
                    possible_points=5, feedback="short"),
        CheckResult(id="cit", type="citation_count", passed=False, earned_points=0,
                    possible_points=5, feedback="no citations"),
    ]
    messages = engine.generate(failed)
    assert len(messages) == 2
    assert messages[0] != messages[1]
