"""Coverage for the two bits of infra the app never exercises under test:
the stdlib->loguru bridge (custom log levels) and the real get_db() generator
(the app uses a dependency override, so the real one is otherwise never run)."""

import logging

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

import app.core.db as db_mod
from app.core.logging import _InterceptHandler


def _record(levelname: str) -> logging.LogRecord:
    rec = logging.LogRecord("t", logging.INFO, __file__, 1, "hello", None, None)
    rec.levelname = levelname
    return rec


def test_intercept_handler_known_level_does_not_raise():
    _InterceptHandler().emit(_record("WARNING"))


def test_intercept_handler_unknown_level_falls_back_to_numeric():
    # loguru doesn't know this level name -> ValueError -> numeric levelno path.
    _InterceptHandler().emit(_record("TOTALLY_CUSTOM"))


def test_intercept_handler_through_stdlib_walks_frames():
    # Emitting via the real logging machinery means currentframe() starts inside
    # logging/__init__.py, so the frame-walk loop actually advances.
    lg = logging.getLogger("didar_intercept_probe")
    lg.handlers = [_InterceptHandler()]
    lg.propagate = False
    lg.setLevel(logging.INFO)
    lg.warning("through stdlib")  # must not raise


@pytest.mark.asyncio(loop_scope="session")
async def test_get_db_yields_and_closes_a_session(_sessionmaker, monkeypatch):
    # Point the real get_db at the test sessionmaker and drive the generator by
    # hand (the app overrides get_db, so these lines are otherwise uncovered).
    monkeypatch.setattr(db_mod, "SessionLocal", _sessionmaker)
    gen = db_mod.get_db()
    session = await gen.__anext__()
    assert isinstance(session, AsyncSession)
    await gen.aclose()  # runs the `async with` cleanup
