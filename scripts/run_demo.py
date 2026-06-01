"""run_demo.py – End-to-end demo for the classroom-artifact-grader pipeline.

Grades all three demo submissions against the demo-assignment rubric, writes
JSON + Markdown reports under ``reports/demo/<stem>/``, and prints a summary
table to stdout.

Usage::

    python scripts/run_demo.py

Manual-review checks (``type: manual``) are never awarded automatically, so
the automated score is shown as *earned / automated_possible* (i.e. the 30
manual-review points are excluded from both the numerator and the denominator
of the displayed score).
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import NamedTuple

# Configure logging before importing grader modules so the root-logger level
# set here takes precedence over the one in grader.main.
logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Allow running from the repository root without installing the package.
sys.path.insert(0, str(Path(__file__).parent.parent))

from grader.main import build_report  # noqa: E402
from grader.models import GradeReport  # noqa: E402

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).parent.parent
ASSIGNMENT_DIR = REPO_ROOT / "assignments" / "demo-assignment"
SUBMISSIONS_DIR = REPO_ROOT / "submissions"
REPORTS_BASE_DIR = REPO_ROOT / "reports" / "demo"
TEMPLATE_PATH = REPO_ROOT / "templates" / "report_template.md"

DEMO_SUBMISSIONS: list[str] = [
    "excellent_submission.docx",
    "passing_submission.docx",
    "failing_submission.docx",
]


# ---------------------------------------------------------------------------
# Helper types
# ---------------------------------------------------------------------------


class DemoResult(NamedTuple):
    """Summary of one graded submission."""

    submission_name: str
    automated_score: float
    automated_possible: float
    report: GradeReport


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------


def _automated_possible(report: GradeReport) -> float:
    """Return the total points available from automated (non-manual) checks."""
    automated = [
        *report.passed_checks,
        *report.failed_checks,
    ]
    return sum(r.possible_points for r in automated)


def grade_submission(submission_path: Path, output_dir: Path) -> GradeReport:
    """Run the grader on *submission_path* and store reports in *output_dir*.

    Parameters
    ----------
    submission_path:
        Absolute path to the submission file.
    output_dir:
        Directory where ``report.json`` and ``report.md`` will be written.

    Returns
    -------
    GradeReport
        The completed grade report (also written to disk by the grader).
    """
    logger.info("Grading %s → %s", submission_path.name, output_dir)
    return build_report(
        assignment=str(ASSIGNMENT_DIR),
        submission=str(submission_path),
        output_dir=str(output_dir),
    )


def run_demo() -> list[DemoResult]:
    """Grade all demo submissions and return a list of :class:`DemoResult` objects.

    Submissions are expected to exist under ``submissions/`` in the repository
    root.  Reports are written under ``reports/demo/<submission_stem>/``.

    Returns
    -------
    list[DemoResult]
        One entry per submission, in the order defined by :data:`DEMO_SUBMISSIONS`.
    """
    results: list[DemoResult] = []
    for filename in DEMO_SUBMISSIONS:
        submission_path = SUBMISSIONS_DIR / filename
        if not submission_path.exists():
            logger.error("Submission not found, skipping: %s", submission_path)
            continue

        stem = submission_path.stem
        output_dir = REPORTS_BASE_DIR / stem
        output_dir.mkdir(parents=True, exist_ok=True)

        try:
            report = grade_submission(submission_path, output_dir)
        except Exception:
            logger.exception("Failed to grade %s", filename)
            continue

        auto_possible = _automated_possible(report)
        auto_score = sum(r.earned_points for r in report.passed_checks)

        results.append(
            DemoResult(
                submission_name=filename,
                automated_score=auto_score,
                automated_possible=auto_possible,
                report=report,
            )
        )
        logger.info(
            "Graded %s: %.0f / %.0f automated", filename, auto_score, auto_possible
        )

    return results


def print_summary(results: list[DemoResult]) -> None:
    """Print a formatted summary table to stdout.

    Manual-review points are excluded from both the numerator and denominator
    because they can only be awarded by an instructor after reading the
    submission.

    Parameters
    ----------
    results:
        The list of :class:`DemoResult` objects returned by :func:`run_demo`.
    """
    col_width = 35
    header = f"{'Submission':<{col_width}} {'Score (automated)'}"
    separator = "-" * (col_width + 25)

    print()
    print(header)
    print(separator)
    for r in results:
        score_str = f"{r.automated_score:.0f}/{r.automated_possible:.0f}"
        print(f"{r.submission_name:<{col_width}} {score_str}")
    print()
    print(
        "Note: 30 manual-review points are excluded from the score above.\n"
        "      An instructor must award those points after reviewing each submission."
    )
    print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Grade all demo submissions and display a summary table."""
    print(f"Assignment : {ASSIGNMENT_DIR}")
    print(f"Submissions: {SUBMISSIONS_DIR}")
    print(f"Reports    : {REPORTS_BASE_DIR}")

    results = run_demo()

    if not results:
        print("\nNo submissions were graded successfully.", file=sys.stderr)
        sys.exit(1)

    print_summary(results)

    for r in results:
        stem = Path(r.submission_name).stem
        json_path = REPORTS_BASE_DIR / stem / "report.json"
        md_path = REPORTS_BASE_DIR / stem / "report.md"
        print(f"  {r.submission_name}: {json_path}  |  {md_path}")
    print()


if __name__ == "__main__":
    main()
