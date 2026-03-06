import logging
import sys

import structlog

from app.core.config import settings


def setup_logging(level: str | None = None) -> None:
    effective_level = (level or settings.LOG_LEVEL).upper()
    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)
    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, effective_level, logging.INFO)),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
        processors=[
            structlog.stdlib.add_log_level,
            timestamper,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
    )
    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, effective_level, logging.INFO),
        handlers=[logging.StreamHandler(sys.stdout)],
    )
