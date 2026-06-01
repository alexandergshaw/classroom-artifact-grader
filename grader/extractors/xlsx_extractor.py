from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def extract_xlsx(path: str | Path) -> str:
    logger.warning("XLSX extractor is placeholder-only and not yet implemented.")
    # TODO: implement robust deterministic XLSX extraction.
    return ""
