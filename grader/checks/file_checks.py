from __future__ import annotations

from pathlib import Path

from grader.models import Check, CheckResult


def file_exists(check: Check, base_path: Path) -> CheckResult:
    target = check.model_dump().get("path")
    path = base_path / str(target)
    passed = path.is_file()
    return CheckResult(
        id=check.id,
        type=check.type,
        passed=passed,
        earned_points=check.points if passed else 0,
        possible_points=check.points,
        feedback=("File exists." if passed else f"Missing required file: {target}"),
        evidence=str(path),
    )


def folder_exists(check: Check, base_path: Path) -> CheckResult:
    target = check.model_dump().get("path")
    path = base_path / str(target)
    passed = path.is_dir()
    return CheckResult(
        id=check.id,
        type=check.type,
        passed=passed,
        earned_points=check.points if passed else 0,
        possible_points=check.points,
        feedback=("Folder exists." if passed else f"Missing required folder: {target}"),
        evidence=str(path),
    )
