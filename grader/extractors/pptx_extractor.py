from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def extract_pptx(path: str | Path) -> str:
    logger.warning("PPTX extractor is placeholder-only and not yet implemented.")
    # TODO: implement robust deterministic PPTX extraction.
    return ""
