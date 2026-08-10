"""Logging via loguru: one sink, one contract, stdlib intercepted.

- get_logger("api.auth") gives a namespaced logger; per-namespace levels come
  from LOG_LEVELS ("db.query=DEBUG,api.auth=DEBUG"), everything else LOG_LEVEL.
- LOG_JSON=true emits one flat JSON object per line (the logging contract shared
  with the Nuxt side) for Loki/Alloy; false keeps human-readable dev output.
- A patch() scrubber redacts Iranian mobile numbers and OTP/token-like values
  from every record before any sink sees it.
- Sinks write to stderr only: containers ship stdout/stderr to the collector;
  rotation/retention is the log driver's job, not the app's.

Call setup_logging() once at startup (see app/main.py).
"""

import json
import logging
import re
import sys
import traceback

from loguru import logger

from app.core.config import settings

# --- per-module levels ----------------------------------------------------------

_LEVEL_NO = {"TRACE": 5, "DEBUG": 10, "INFO": 20, "SUCCESS": 25, "WARNING": 30,
             "ERROR": 40, "CRITICAL": 50}


def _module_levels() -> dict[str, int]:
    out: dict[str, int] = {}
    for pair in settings.log_levels.split(","):
        if "=" in pair:
            mod, _, lvl = pair.strip().partition("=")
            out[mod] = _LEVEL_NO.get(lvl.strip().upper(), 20)
    return out


def _level_filter(record) -> bool:
    """Namespace level override: longest matching prefix of `module` wins."""
    levels = _module_levels()
    if not levels:
        return True
    mod = record["extra"].get("module", "")
    best = None
    for prefix, lvl in levels.items():
        if mod == prefix or mod.startswith(prefix + "."):
            if best is None or len(prefix) > best[0]:
                best = (len(prefix), lvl)
    if best is None:
        return True
    return record["level"].no >= best[1]


def get_logger(module: str):
    """Module-scoped logger, e.g. get_logger("db.query"). The `module` value is
    the namespace used for filtering, dashboards, and grep."""
    return logger.bind(module=module)


# --- redaction ------------------------------------------------------------------

# Iranian mobile numbers (09xxxxxxxxx, optionally +98) and bare 5-6 digit codes
# following the word کد / code (OTP bodies). Deny-list on the rendered message —
# the cheap net under the real rule: don't log secrets in the first place.
_PHONE_RE = re.compile(r"(?:\+?98|0)9\d{2}(\d{4})(\d{3})")
_OTP_RE = re.compile(r"((?:کد|code)\D{0,24})\d{4,8}", re.IGNORECASE)
_SENSITIVE_KEYS = {"password", "token", "authorization", "cookie", "secret",
                   "code_hash", "otp", "api_key"}


def _scrub_text(text: str) -> str:
    text = _PHONE_RE.sub(lambda m: m.group(0)[:4] + "****" + m.group(2), text)
    return _OTP_RE.sub(r"\g<1>******", text)


def _scrub(record) -> None:
    record["message"] = _scrub_text(record["message"])
    extra = record["extra"]
    for k in list(extra):
        if k.lower() in _SENSITIVE_KEYS:
            extra[k] = "[redacted]"
        elif isinstance(extra[k], str):
            extra[k] = _scrub_text(extra[k])


# --- JSON sink (the logging contract) -------------------------------------------

_CONTEXT_FIELDS = ("request_id", "user_id", "event", "duration_ms", "status_code")


def _json_line(record) -> str:
    extra = record["extra"]
    doc = {
        "timestamp": record["time"].isoformat(),
        "level": record["level"].name,
        "service": settings.log_service,
        "env": settings.app_env,
        "module": extra.get("module", record["name"]),
        "message": record["message"],
        "pid": record["process"].id,
    }
    for f in _CONTEXT_FIELDS:
        if extra.get(f) is not None:
            doc[f] = extra[f]
    # Anything else bound via .bind()/contextualize() rides along as-is.
    for k, v in extra.items():
        if k not in doc and k not in ("module",) and not k.startswith("_"):
            doc[k] = v
    if record["exception"]:
        exc = record["exception"]
        doc["error"] = {
            "type": exc.type.__name__ if exc.type else None,
            "message": str(exc.value) if exc.value else None,
            "stack": "".join(
                traceback.format_exception(exc.type, exc.value, exc.traceback)
            )[-4000:],
        }
    return json.dumps(doc, ensure_ascii=False, default=str)


def _json_sink_format(record) -> str:
    # Stash the rendered line so the format string stays trivial and safe.
    record["extra"]["_json"] = _json_line(record)
    return "{extra[_json]}\n"


_HUMAN_FORMAT = (
    "<green>{time:HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | "
    "<cyan>{extra[module]}</cyan> | {message}"
)


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
        logger.opt(depth=depth, exception=record.exc_info).bind(
            module=f"stdlib.{record.name.split('.')[0]}"
        ).log(level, record.getMessage())


def setup_logging() -> None:
    logger.remove()
    # Default module for logs emitted via the bare `logger` (legacy call sites).
    logger.configure(extra={"module": "app"}, patcher=_scrub)
    if settings.log_json:
        logger.add(
            sys.stderr,
            level=settings.log_level,
            format=_json_sink_format,
            filter=_level_filter,
            enqueue=True,  # non-blocking off the event loop; per-worker safe
            backtrace=False,
            diagnose=False,
        )
    else:
        logger.add(
            sys.stderr,
            level=settings.log_level,
            format=_HUMAN_FORMAT,
            filter=_level_filter,
            backtrace=False,
            diagnose=False,
        )
    # Route the root logger + noisy named loggers through loguru.
    logging.basicConfig(handlers=[_InterceptHandler()], level=0, force=True)
    for name in ("uvicorn", "uvicorn.access", "uvicorn.error", "sqlalchemy.engine"):
        lg = logging.getLogger(name)
        lg.handlers = [_InterceptHandler()]
        lg.propagate = False
