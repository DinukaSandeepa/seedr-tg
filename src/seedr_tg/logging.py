from __future__ import annotations

import logging


def configure_logging(level: str) -> None:
    resolved_level = getattr(logging, level, logging.INFO)
    logging.basicConfig(
        level=resolved_level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    # Keep app logs visible while suppressing per-request noise from HTTP clients.
    if resolved_level >= logging.INFO:
        logging.getLogger("httpx").setLevel(logging.WARNING)
