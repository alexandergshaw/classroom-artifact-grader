from pathlib import Path

from grader.main import build_report
from grader.plugin_loader import load_assignment_plugins


def test_plugin_loader_discovers_assignment_plugins() -> None:
    plugins = load_assignment_plugins(Path("assignments/example-assignment"))
    assert "contains_student_name" in plugins.check_handlers
    assert plugins.validators
    assert plugins.feedback_hooks


def test_assignment_specific_check_is_executed(tmp_path: Path) -> None:
    submission = tmp_path / "student.txt"
    submission.write_text("alex wrote about deterministic grading", encoding="utf-8")

    report = build_report("assignments/example-assignment", str(submission), str(tmp_path / "reports"))
    assert report.total_score == 20
    assert report.instructor_notes
