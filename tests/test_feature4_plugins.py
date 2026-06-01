"""Tests for Feature 4: Assignment-Specific Plugin System (hardened)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from grader.main import build_report
from grader.plugin_loader import PluginBundle, load_assignment_plugins


# ---------------------------------------------------------------------------
# Plugin discovery
# ---------------------------------------------------------------------------


def test_databases_assignment_plugins_load(tmp_path: Path) -> None:
    """databases-assignment-01 plugins should load without error."""
    plugins = load_assignment_plugins(Path("assignments/databases-assignment-01"))
    assert "erd_mentioned" in plugins.check_handlers
    assert plugins.validators
    assert plugins.feedback_hooks


def test_plugin_check_handler_is_callable() -> None:
    plugins = load_assignment_plugins(Path("assignments/databases-assignment-01"))
    handler = plugins.check_handlers["erd_mentioned"]
    assert callable(handler)


def test_plugin_with_no_subdirs_returns_empty_bundle(tmp_path: Path) -> None:
    """Assignment directory with no plugin subdirs should yield an empty bundle."""
    (tmp_path / "rubric.yaml").write_text("assignment_id: x\npoints_possible: 10\n", encoding="utf-8")
    bundle = load_assignment_plugins(tmp_path)
    assert bundle.check_handlers == {}
    assert bundle.validators == []
    assert bundle.feedback_hooks == []


# ---------------------------------------------------------------------------
# Plugin failure isolation
# ---------------------------------------------------------------------------


def test_broken_check_plugin_is_skipped(tmp_path: Path) -> None:
    """A check plugin that raises on import should not abort loading."""
    checks_dir = tmp_path / "checks"
    checks_dir.mkdir()
    (checks_dir / "broken_checks.py").write_text("raise RuntimeError('intentional import error')", encoding="utf-8")
    (checks_dir / "good_checks.py").write_text(
        "def register_checks():\n    return {'good_check': lambda c, ctx: None}\n",
        encoding="utf-8",
    )

    bundle = load_assignment_plugins(tmp_path)
    # good plugin should still load despite broken plugin
    assert "good_check" in bundle.check_handlers


def test_broken_validator_plugin_is_skipped(tmp_path: Path) -> None:
    validators_dir = tmp_path / "validators"
    validators_dir.mkdir()
    (validators_dir / "broken.py").write_text("raise ImportError('boom')", encoding="utf-8")

    bundle = load_assignment_plugins(tmp_path)
    assert bundle.validators == []


def test_broken_feedback_plugin_is_skipped(tmp_path: Path) -> None:
    feedback_dir = tmp_path / "feedback"
    feedback_dir.mkdir()
    (feedback_dir / "broken.py").write_text("raise SyntaxError('bad syntax')", encoding="utf-8")

    bundle = load_assignment_plugins(tmp_path)
    assert bundle.feedback_hooks == []


def test_check_runtime_failure_does_not_abort_batch(tmp_path: Path) -> None:
    """A check that raises at runtime should be skipped, not abort the report."""
    checks_dir = tmp_path / "checks"
    checks_dir.mkdir()
    (checks_dir / "failing_check.py").write_text(
        "def register_checks():\n"
        "    def bad(check, ctx): raise ValueError('runtime boom')\n"
        "    return {'exploding_check': bad}\n",
        encoding="utf-8",
    )
    (tmp_path / "rubric.yaml").write_text(
        "assignment_id: fail-test\npoints_possible: 10\nsubmission_types:\n  - txt\n"
        "checks:\n  - id: boom\n    type: exploding_check\n    points: 10\n",
        encoding="utf-8",
    )
    submission = tmp_path / "sub.txt"
    submission.write_text("hello world", encoding="utf-8")

    report = build_report(str(tmp_path), str(submission), str(tmp_path / "reports"))
    # Check was skipped, so no results recorded
    assert report.total_score == 0


def test_feedback_hook_failure_does_not_abort_report(tmp_path: Path) -> None:
    """A feedback hook that raises should be caught, not abort report generation."""
    feedback_dir = tmp_path / "feedback"
    feedback_dir.mkdir()
    (feedback_dir / "bad_hook.py").write_text(
        "def register_feedback():\n"
        "    def hook(report): raise RuntimeError('hook boom')\n"
        "    return [hook]\n",
        encoding="utf-8",
    )
    (tmp_path / "rubric.yaml").write_text(
        "assignment_id: hook-fail-test\npoints_possible: 5\nsubmission_types:\n  - txt\n"
        "checks:\n  - id: wc\n    type: word_count\n    min: 1\n    points: 5\n",
        encoding="utf-8",
    )
    submission = tmp_path / "sub.txt"
    submission.write_text("hello world", encoding="utf-8")

    # Should not raise
    report = build_report(str(tmp_path), str(submission), str(tmp_path / "reports"))
    assert report.total_score == 5


# ---------------------------------------------------------------------------
# Plugin registration patterns
# ---------------------------------------------------------------------------


def test_register_checks_function_takes_priority(tmp_path: Path) -> None:
    """register_checks() return value should override check_ prefix convention."""
    checks_dir = tmp_path / "checks"
    checks_dir.mkdir()
    (checks_dir / "both.py").write_text(
        "from grader.models import Check, CheckResult\n\n"
        "def check_fallback(check, ctx):\n"
        "    return CheckResult(id=check.id, type=check.type, passed=True, earned_points=1,\n"
        "                       possible_points=1, feedback='fallback')\n\n"
        "def register_checks():\n"
        "    return {'my_check': lambda c, ctx: None}\n",
        encoding="utf-8",
    )
    bundle = load_assignment_plugins(tmp_path)
    assert "my_check" in bundle.check_handlers
    # The check_ prefix function is NOT registered when register_checks() exists
    assert "fallback" not in bundle.check_handlers


def test_check_prefix_convention_without_register_function(tmp_path: Path) -> None:
    """check_* functions should be auto-registered when register_checks is absent."""
    checks_dir = tmp_path / "checks"
    checks_dir.mkdir()
    (checks_dir / "auto.py").write_text(
        "from grader.models import Check, CheckResult\n\n"
        "def check_auto_type(check, ctx):\n"
        "    return CheckResult(id=check.id, type=check.type, passed=True,\n"
        "                       earned_points=0, possible_points=0, feedback='ok')\n",
        encoding="utf-8",
    )
    bundle = load_assignment_plugins(tmp_path)
    assert "auto_type" in bundle.check_handlers
