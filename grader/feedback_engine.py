"""feedback_engine.py – Deterministic feedback generation from failed checks.

Loads feedback rules from ``templates/feedback_rules.yaml`` and, optionally,
from an assignment-specific override at
``assignments/<id>/feedback/feedback_rules.yaml``.

Rules map a check *type* to a human-readable failure message.  If no rule
exists for a given check type the engine falls back to the check's own
``feedback`` field.
"""

from __future__ import annotations

import logging
from pathlib import Path

import yaml

from grader.models import CheckResult

logger = logging.getLogger(__name__)

_DEFAULT_RULES_PATH = Path("templates/feedback_rules.yaml")


class FeedbackEngine:
    """Generate deduplicated feedback messages from failed :class:`CheckResult` objects."""

    def __init__(self, assignment_path: str | Path | None = None) -> None:
        self._rules: dict[str, str] = {}
        self._load_rules(_DEFAULT_RULES_PATH)
        if assignment_path is not None:
            override = Path(assignment_path) / "feedback" / "feedback_rules.yaml"
            self._load_rules(override)

    def _load_rules(self, path: Path) -> None:
        if not path.exists():
            return
        try:
            with path.open("r", encoding="utf-8") as fh:
                data = yaml.safe_load(fh) or {}
            for check_type, rule in data.items():
                if isinstance(rule, dict):
                    msg = rule.get("fail", "")
                else:
                    msg = str(rule)
                if msg:
                    self._rules[str(check_type)] = msg
        except Exception:
            logger.exception("Failed to load feedback rules from %s", path)

    def generate(self, failed_checks: list[CheckResult]) -> list[str]:
        """Return a deduplicated list of feedback messages for *failed_checks*."""
        seen: set[str] = set()
        messages: list[str] = []
        for result in failed_checks:
            msg = self._rules.get(result.type) or result.feedback
            if msg and msg not in seen:
                seen.add(msg)
                messages.append(msg)
        return messages
