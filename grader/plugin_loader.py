from __future__ import annotations

import importlib.util
import logging
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Callable

from grader.models import Check, CheckResult, GradeReport, Rubric

logger = logging.getLogger(__name__)

CheckHandler = Callable[[Check, dict], CheckResult]
Validator = Callable[[Rubric], None]
FeedbackHook = Callable[[GradeReport], None]


@dataclass
class PluginBundle:
    check_handlers: dict[str, CheckHandler] = field(default_factory=dict)
    validators: list[Validator] = field(default_factory=list)
    feedback_hooks: list[FeedbackHook] = field(default_factory=list)


def _load_module(module_path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(f"assignment_plugin_{module_path.stem}", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load plugin module {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _iter_py_files(directory: Path) -> list[Path]:
    if not directory.exists() or not directory.is_dir():
        return []
    return sorted([p for p in directory.glob("*.py") if p.name != "__init__.py"])


def load_assignment_plugins(assignment_dir: str | Path) -> PluginBundle:
    assignment_path = Path(assignment_dir)
    bundle = PluginBundle()

    checks_dir = assignment_path / "checks"
    for file in _iter_py_files(checks_dir):
        module = _load_module(file)
        if hasattr(module, "register_checks"):
            registered = module.register_checks()
            bundle.check_handlers.update(registered)
        else:
            for attr_name in dir(module):
                if attr_name.startswith("check_"):
                    check_type = attr_name.removeprefix("check_")
                    func = getattr(module, attr_name)
                    if callable(func):
                        bundle.check_handlers[check_type] = func

    validators_dir = assignment_path / "validators"
    for file in _iter_py_files(validators_dir):
        module = _load_module(file)
        if hasattr(module, "register_validators"):
            bundle.validators.extend(module.register_validators())

    feedback_dir = assignment_path / "feedback"
    for file in _iter_py_files(feedback_dir):
        module = _load_module(file)
        if hasattr(module, "register_feedback"):
            bundle.feedback_hooks.extend(module.register_feedback())

    logger.info(
        "Loaded assignment plugins: %s checks, %s validators, %s feedback hooks",
        len(bundle.check_handlers),
        len(bundle.validators),
        len(bundle.feedback_hooks),
    )
    return bundle
