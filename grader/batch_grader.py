"""batch_grader.py – Production batch grading for entire submission directories.

Discovers all supported submission files under a directory, grades each
independently (never aborting the batch on individual failures), and writes:

- Per-submission reports under ``<output_dir>/<assignment_id>/<stem>/``
- ``gradebook.csv``   – one row per submission
- ``summary.json``    – aggregate statistics
- ``instructor_summary.md`` – human-readable dashboard report
"""

from __future__ import annotations

import csv
import json
import logging
import statistics
from pathlib import Path

from grader.main import build_report
from grader.models import GradeReport
from grader.rubric_loader import load_rubric

logger = logging.getLogger(__name__)

# Submission file extensions supported by the grader.
SUPPORTED_EXTENSIONS: frozenset[str] = frozenset(
    {"txt", "docx", "pdf", "zip", "pptx", "xlsx"}
)

GRADEBOOK_COLUMNS = [
    "submission_name",
    "assignment_id",
    "auto_score",
    "auto_points_possible",
    "manual_points_available",
    "final_points_possible",
    "passed_checks",
    "failed_checks",
    "manual_checks",
    "status",
    "error_message",
    "report_path",
]


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------


def discover_submissions(submission_dir: str | Path) -> list[Path]:
    """Recursively find all supported submission files under *submission_dir*."""
    root = Path(submission_dir)
    found: list[Path] = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.suffix.lstrip(".").lower() in SUPPORTED_EXTENSIONS:
            found.append(path)
    return found


# ---------------------------------------------------------------------------
# Per-submission grading
# ---------------------------------------------------------------------------


def _auto_possible(report: GradeReport) -> float:
    return sum(r.possible_points for r in [*report.passed_checks, *report.failed_checks])


def _manual_possible(report: GradeReport) -> float:
    return sum(r.possible_points for r in report.manual_review_items)


def _grade_one(
    assignment: str,
    submission_path: Path,
    output_dir: Path,
) -> dict:
    """Grade a single submission and return a gradebook row dict."""
    row: dict = {col: "" for col in GRADEBOOK_COLUMNS}
    row["submission_name"] = submission_path.name
    row["report_path"] = str(output_dir)

    try:
        report = build_report(str(assignment), str(submission_path), str(output_dir))
        row["assignment_id"] = report.assignment_id
        row["auto_score"] = report.total_score
        row["auto_points_possible"] = _auto_possible(report)
        row["manual_points_available"] = _manual_possible(report)
        row["final_points_possible"] = report.points_possible
        row["passed_checks"] = len(report.passed_checks)
        row["failed_checks"] = len(report.failed_checks)
        row["manual_checks"] = len(report.manual_review_items)
        row["status"] = "success"
        row["error_message"] = ""
    except Exception as exc:
        logger.exception("Failed to grade submission: %s", submission_path)
        row["status"] = "error"
        row["error_message"] = str(exc)

    return row


# ---------------------------------------------------------------------------
# Gradebook + summary
# ---------------------------------------------------------------------------


def _write_gradebook(rows: list[dict], out_dir: Path) -> Path:
    path = out_dir / "gradebook.csv"
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=GRADEBOOK_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return path


def _write_summary(rows: list[dict], out_dir: Path) -> Path:
    successful = [r for r in rows if r["status"] == "success"]
    failed = [r for r in rows if r["status"] != "success"]
    scores = [float(r["auto_score"]) for r in successful if r["auto_score"] != ""]
    auto_possibles = [float(r["auto_points_possible"]) for r in successful if r["auto_points_possible"] != ""]

    def _pass_rate() -> float:
        if not successful or not auto_possibles:
            return 0.0
        passing = sum(
            1 for r, ap in zip(successful, auto_possibles)
            if ap > 0 and float(r["auto_score"]) / ap >= 0.6
        )
        return round(passing / len(successful), 4) if successful else 0.0

    summary = {
        "total_submissions": len(rows),
        "successful_submissions": len(successful),
        "failed_submissions": len(failed),
        "average_auto_score": round(statistics.mean(scores), 2) if scores else None,
        "median_auto_score": round(statistics.median(scores), 2) if scores else None,
        "highest_auto_score": max(scores) if scores else None,
        "lowest_auto_score": min(scores) if scores else None,
        "pass_rate": _pass_rate(),
    }
    path = out_dir / "summary.json"
    path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Instructor summary dashboard
# ---------------------------------------------------------------------------


def _write_instructor_summary(rows: list[dict], assignment_id: str, out_dir: Path) -> Path:
    successful = [r for r in rows if r["status"] == "success"]
    failed_rows = [r for r in rows if r["status"] != "success"]
    scores = [float(r["auto_score"]) for r in successful if r["auto_score"] != ""]

    avg = round(statistics.mean(scores), 2) if scores else "N/A"
    med = round(statistics.median(scores), 2) if scores else "N/A"
    high = max(scores) if scores else "N/A"
    low = min(scores) if scores else "N/A"

    lines: list[str] = [
        "# Assignment Summary",
        "",
        f"**Assignment:** {assignment_id}",
        "",
        f"- Total submissions: {len(rows)}",
        f"- Successful: {len(successful)}",
        f"- Failed (error): {len(failed_rows)}",
        f"- Average score: {avg}",
        f"- Median score: {med}",
        f"- Highest score: {high}",
        f"- Lowest score: {low}",
        "",
    ]

    # Common failed checks
    failed_check_counts: dict[str, int] = {}
    manual_review_submissions: list[str] = []
    warning_submissions: list[str] = []

    for r in successful:
        fc = int(r.get("failed_checks") or 0)
        if fc > 0:
            # We don't have check-level detail in gradebook rows; use submission-level
            failed_check_counts[r["submission_name"]] = fc
        mc = int(r.get("manual_checks") or 0)
        if mc > 0:
            manual_review_submissions.append(r["submission_name"])

    # Load individual report JSONs to gather check-level failure counts
    check_failure_counts: dict[str, int] = {}
    for r in successful:
        report_path = Path(r["report_path"]) / "report.json"
        if report_path.exists():
            try:
                data = json.loads(report_path.read_text(encoding="utf-8"))
                for fc in data.get("failed_checks", []):
                    ct = fc.get("type", "unknown")
                    check_failure_counts[ct] = check_failure_counts.get(ct, 0) + 1
            except Exception:
                warning_submissions.append(r["submission_name"])

    lines.append("## Common Failed Checks")
    lines.append("")
    if check_failure_counts:
        sorted_failures = sorted(check_failure_counts.items(), key=lambda x: x[1], reverse=True)
        for i, (check_type, count) in enumerate(sorted_failures, start=1):
            lines.append(f"{i}. {check_type} ({count} failure{'s' if count != 1 else ''})")
    else:
        lines.append("_No failed checks recorded._")
    lines.append("")

    lines.append("## Manual Review Required")
    lines.append("")
    if manual_review_submissions:
        for name in manual_review_submissions:
            lines.append(f"- {name}")
    else:
        lines.append("_No submissions require manual review._")
    lines.append("")

    lines.append("## Grading Warnings")
    lines.append("")
    all_warnings = warning_submissions + [r["submission_name"] for r in failed_rows]
    if all_warnings:
        for name in all_warnings:
            matching = next((r for r in rows if r["submission_name"] == name), {})
            err = matching.get("error_message", "")
            if err:
                lines.append(f"- {name}: {err}")
            else:
                lines.append(f"- {name}: extraction or report read failure")
    else:
        lines.append("_No grading warnings._")
    lines.append("")

    path = out_dir / "instructor_summary.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def run_batch(assignment: str, submission_dir: str, output_dir: str) -> list[dict]:
    """Grade all submissions in *submission_dir* and write batch reports.

    Returns the list of gradebook row dicts.
    """
    assignment_path = Path(assignment)
    rubric = load_rubric(assignment_path)
    assignment_id = rubric.assignment_id

    submissions = discover_submissions(submission_dir)
    if not submissions:
        logger.warning("No supported submissions found in %s", submission_dir)

    batch_out = Path(output_dir) / assignment_id
    batch_out.mkdir(parents=True, exist_ok=True)

    rows: list[dict] = []
    for sub_path in submissions:
        stem = sub_path.stem
        sub_out = batch_out / stem
        sub_out.mkdir(parents=True, exist_ok=True)
        logger.info("Grading %s → %s", sub_path.name, sub_out)
        row = _grade_one(assignment_path, sub_path, sub_out)
        rows.append(row)

    _write_gradebook(rows, batch_out)
    _write_summary(rows, batch_out)
    _write_instructor_summary(rows, assignment_id, batch_out)

    logger.info(
        "Batch complete: %d/%d succeeded. Reports in %s",
        sum(1 for r in rows if r["status"] == "success"),
        len(rows),
        batch_out,
    )
    return rows
