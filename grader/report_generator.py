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
        "## Feedback\n{{feedback}}\n\n"
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


def _render_feedback(messages: list[str]) -> str:
    if not messages:
        return "- No automated feedback."
    return "\n".join(f"- {m}" for m in messages)


def _render_review_form(report: GradeReport) -> str:
    auto_score = report.total_score
    auto_possible = sum(r.possible_points for r in [*report.passed_checks, *report.failed_checks])
    manual_possible = sum(r.possible_points for r in report.manual_review_items)

    lines: list[str] = [
        "# Instructor Review Form",
        "",
        f"**Assignment:** {report.assignment_id}",
        f"**Submission:** {report.submission_path}",
        "",
        "---",
        "",
        "## Auto Score Summary",
        "",
        f"- Auto score: {auto_score} / {auto_possible}",
        f"- Manual review points available: {manual_possible}",
        f"- Final points possible: {report.points_possible}",
        "",
        "---",
        "",
        "## Rubric Breakdown",
        "",
        "### Passed Checks",
        "",
        _render_check_list(report.passed_checks),
        "",
        "### Failed Checks",
        "",
        _render_check_list(report.failed_checks),
        "",
    ]

    if report.feedback:
        lines += [
            "### Automated Feedback",
            "",
            _render_feedback(report.feedback),
            "",
        ]

    if report.manual_review_items:
        lines += [
            "---",
            "",
            "## Manual Review Sections",
            "",
        ]
        for item in report.manual_review_items:
            lines += [
                f"### {item.id}",
                "",
                f"- **Criterion:** {item.id}",
                f"- **Points possible:** {item.possible_points}",
                "- **Points awarded:** ___",
                "- **Notes:** ___",
                "",
            ]

    lines += [
        "---",
        "",
        "## Instructor Notes",
        "",
        report.instructor_notes or "_(Add instructor notes here)_",
        "",
        "---",
        "",
        "## Final Score",
        "",
        f"- Auto score: {auto_score}",
        "- Manual points awarded: ___",
        "- **Final score: ___ / " + str(report.points_possible) + "**",
        "",
    ]
    return "\n".join(lines)


def write_report(report: GradeReport, output_dir: str | Path, template_path: str | Path) -> tuple[Path, Path, Path]:
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
        .replace("{{feedback}}", _render_feedback(report.feedback))
        .replace("{{manual_review_items}}", _render_check_list(report.manual_review_items))
        .replace("{{instructor_notes}}", report.instructor_notes or "")
    )
    md_path = out_dir / "report.md"
    md_path.write_text(markdown, encoding="utf-8")

    review_form = _render_review_form(report)
    review_path = out_dir / "review_form.md"
    review_path.write_text(review_form, encoding="utf-8")

    return json_path, md_path, review_path

