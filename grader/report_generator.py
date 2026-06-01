from __future__ import annotations

from pathlib import Path

from grader.models import GradeReport


def _read_template(template_path: Path) -> str:
    if template_path.exists():
        return template_path.read_text(encoding="utf-8")
    return (
        "# Grading Report\n\n"
        "Assignment: {{assignment_id}}\n"
        "Submission: {{submission_path}}\n"
        "Total Score: {{total_score}} / {{points_possible}}\n\n"
        "## Passed checks\n{{passed_checks}}\n\n"
        "## Failed checks\n{{failed_checks}}\n\n"
        "## Manual review items\n{{manual_review_items}}\n\n"
        "## Instructor notes\n{{instructor_notes}}\n"
    )


def _render_check_list(items: list) -> str:
    if not items:
        return "- None"
    lines = []
    for item in items:
        lines.append(f"- {item.id}: {item.feedback} ({item.earned_points}/{item.possible_points})")
    return "\n".join(lines)


def write_report(report: GradeReport, output_dir: str | Path, template_path: str | Path) -> tuple[Path, Path]:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / "report.json"
    json_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")

    template = _read_template(Path(template_path))
    markdown = (
        template.replace("{{assignment_id}}", report.assignment_id)
        .replace("{{submission_path}}", report.submission_path)
        .replace("{{total_score}}", str(report.total_score))
        .replace("{{points_possible}}", str(report.points_possible))
        .replace("{{passed_checks}}", _render_check_list(report.passed_checks))
        .replace("{{failed_checks}}", _render_check_list(report.failed_checks))
        .replace("{{manual_review_items}}", _render_check_list(report.manual_review_items))
        .replace("{{instructor_notes}}", report.instructor_notes or "")
    )
    md_path = out_dir / "report.md"
    md_path.write_text(markdown, encoding="utf-8")
    return json_path, md_path
