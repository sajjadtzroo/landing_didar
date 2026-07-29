"""Logging via loguru. One stderr sink; stdlib logging (uvicorn, sqlalchemy,
asyncpg, ...) is redirected into loguru so the whole app shares one format.

Call setup_logging() once at startup (see app/main.py).
"""

import logging
import sys

from loguru import logger

from app.core.config import settings


class _InterceptHandler(logging.Handler):
    # ponytail: the standard stdlib->loguru bridge from the loguru docs. Without
    # it, uvicorn/3rd-party libs log through stdlib and print in a second format.
    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1
        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def setup_logging() -> None:
    logger.remove()
    logger.add(sys.stderr, level=settings.log_level, backtrace=False, diagnose=False)
    # Route the root logger + noisy named loggers through loguru.
    logging.basicConfig(handlers=[_InterceptHandler()], level=0, force=True)
    for name in ("uvicorn", "uvicorn.access", "uvicorn.error", "sqlalchemy.engine"):
        lg = logging.getLogger(name)
        lg.handlers = [_InterceptHandler()]
        lg.propagate = False
