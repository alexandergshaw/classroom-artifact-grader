from pathlib import Path

from grader.models import CheckResult, GradeReport
from grader.report_generator import write_report


def test_report_generation_writes_json_and_markdown(tmp_path: Path) -> None:
    report = GradeReport(
        assignment_id="a1",
        submission_path="submissions/student.txt",
        total_score=5,
        points_possible=10,
        passed_checks=[
            CheckResult(
                id="x",
                type="word_count",
                passed=True,
                earned_points=5,
                possible_points=5,
                feedback="ok",
            )
        ],
        failed_checks=[],
        manual_review_items=[],
        instructor_notes="",
    )

    json_path, md_path = write_report(report, tmp_path, Path("templates/report_template.md"))
    assert json_path.exists()
    assert md_path.exists()
    assert "Total Score: 5.0 / 10.0" in md_path.read_text(encoding="utf-8")
