from __future__ import annotations

import argparse
import logging
from pathlib import Path

from grader.checks.document_checks import heading_exists
from grader.checks.file_checks import file_exists, folder_exists
from grader.checks.text_checks import citation_count, regex_contains, required_terms, text_contains, word_count
from grader.extractors.docx_extractor import extract_docx
from grader.extractors.pdf_extractor import extract_pdf
from grader.extractors.pptx_extractor import extract_pptx
from grader.extractors.text_extractor import extract_text
from grader.extractors.url_extractor import extract_url
from grader.extractors.xlsx_extractor import extract_xlsx
from grader.extractors.zip_extractor import extract_zip
from grader.models import Check, CheckResult, GradeReport
from grader.plugin_loader import load_assignment_plugins
from grader.report_generator import write_report
from grader.rubric_loader import load_rubric

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def _submission_type(submission: str) -> str:
    lower = submission.lower()
    if lower.startswith("http://") or lower.startswith("https://"):
        return "url"
    ext = Path(submission).suffix.lower().lstrip(".")
    return ext


def _extract_submission(submission: str, submission_type: str) -> tuple[str, list[str], Path, object | None]:
    path = Path(submission)
    temp_handle = None

    if submission_type == "txt":
        return extract_text(path), [], path.parent, temp_handle
    if submission_type == "docx":
        text, headings = extract_docx(path)
        return text, headings, path.parent, temp_handle
    if submission_type == "pdf":
        return extract_pdf(path), [], path.parent, temp_handle
    if submission_type == "zip":
        temp_handle, extracted = extract_zip(path)
        text_chunks = [p.read_text(encoding="utf-8", errors="ignore") for p in extracted.rglob("*.txt")]
        return "\n".join(text_chunks), [], extracted, temp_handle
    if submission_type == "pptx":
        return extract_pptx(path), [], path.parent, temp_handle
    if submission_type == "xlsx":
        return extract_xlsx(path), [], path.parent, temp_handle
    if submission_type == "url":
        return extract_url(submission), [], Path("."), temp_handle
    raise ValueError(f"Unsupported submission type: {submission_type}")


def _manual_result(check: Check) -> CheckResult:
    return CheckResult(
        id=check.id,
        type=check.type,
        passed=False,
        earned_points=0,
        possible_points=check.points,
        feedback="Manual review required.",
        manual_review=True,
    )


def _run_core_check(check: Check, context: dict) -> CheckResult:
    text = context["text"]
    headings = context["headings"]
    base_path = context["base_path"]

    if check.type == "file_exists":
        return file_exists(check, base_path)
    if check.type == "folder_exists":
        return folder_exists(check, base_path)
    if check.type == "word_count":
        return word_count(check, text)
    if check.type == "heading_exists":
        return heading_exists(check, text, headings)
    if check.type == "required_terms":
        return required_terms(check, text)
    if check.type == "citation_count":
        return citation_count(check, text)
    if check.type == "regex_contains":
        return regex_contains(check, text)
    if check.type == "text_contains":
        return text_contains(check, text)
    if check.type == "manual":
        return _manual_result(check)
    raise ValueError(f"Unknown check type: {check.type}")


def build_report(assignment: str, submission: str, output_dir: str) -> GradeReport:
    assignment_path = Path(assignment)
    rubric = load_rubric(assignment_path)
    plugins = load_assignment_plugins(assignment_path)
    for validator in plugins.validators:
        validator(rubric)

    submission_type = _submission_type(submission)
    if rubric.submission_types and submission_type not in {s.lower() for s in rubric.submission_types}:
        raise ValueError(f"Submission type '{submission_type}' not allowed by rubric.")

    text, headings, base_path, temp_handle = _extract_submission(submission, submission_type)
    try:
        context = {"text": text, "headings": headings, "base_path": base_path, "submission": submission}
        results: list[CheckResult] = []
        for check in rubric.checks:
            if check.type in plugins.check_handlers:
                result = plugins.check_handlers[check.type](check, context)
            else:
                result = _run_core_check(check, context)
            results.append(result)

        manual_items = [r for r in results if r.manual_review]
        passed_checks = [r for r in results if r.passed and not r.manual_review]
        failed_checks = [r for r in results if not r.passed and not r.manual_review]

        report = GradeReport(
            assignment_id=rubric.assignment_id,
            submission_path=submission,
            total_score=sum(r.earned_points for r in results),
            points_possible=rubric.points_possible,
            passed_checks=passed_checks,
            failed_checks=failed_checks,
            manual_review_items=manual_items,
            instructor_notes="",
        )

        for hook in plugins.feedback_hooks:
            hook(report)

        write_report(report, output_dir, Path("templates/report_template.md"))
        return report
    finally:
        if temp_handle is not None:
            temp_handle.cleanup()


def main() -> None:
    parser = argparse.ArgumentParser(description="Rubric-driven classroom artifact grader")
    parser.add_argument("--assignment", required=True, help="Path to assignment directory containing rubric.yaml")
    parser.add_argument("--submission", required=True, help="Path or URL for submission")
    parser.add_argument("--output-dir", default="reports", help="Directory to write report outputs")
    args = parser.parse_args()

    report = build_report(args.assignment, args.submission, args.output_dir)
    logger.info("Grading complete: %.2f / %.2f", report.total_score, report.points_possible)


if __name__ == "__main__":
    main()
