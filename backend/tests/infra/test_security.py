"""Unit tests for auth signing + hashing. Pure functions, no DB, no app."""

import runpy
import sys

import pytest

from app.core import security
from app.core.config import settings
from app.core.security import (
    hash_otp,
    hash_password,
    issue_customer_session,
    issue_session,
    read_customer_session,
    read_session,
    verify_otp,
    verify_password,
)


# ---- passwords ----
def test_verify_password_round_trip():
    h = hash_password("s3cret")
    assert verify_password("s3cret", h) is True
    assert verify_password("wrong", h) is False


def test_verify_password_empty_hash_is_false():
    # No admin hash configured => login must never succeed.
    assert verify_password("anything", "") is False


# ---- admin session cookie ----
def test_read_session_round_trip():
    token = issue_session("admin")
    assert read_session(token) == "admin"


@pytest.mark.parametrize("bad", [None, "", "not-a-token", issue_session("admin") + "x"])
def test_read_session_rejects_missing_or_tampered(bad):
    assert read_session(bad) is None


def test_read_session_rejects_expired(monkeypatch):
    token = issue_session("admin")
    monkeypatch.setattr(settings, "session_max_age", -1)  # already expired
    assert read_session(token) is None


# ---- customer session cookie (different salt) ----
def test_read_customer_session_round_trip():
    token = issue_customer_session("cust-1")
    assert read_customer_session(token) == "cust-1"


def test_session_families_do_not_cross():
    # An admin cookie must not validate as a customer cookie, and vice versa —
    # the salt separation is the whole point.
    assert read_customer_session(issue_session("admin")) is None
    assert read_session(issue_customer_session("cust-1")) is None


# ---- OTP hashing ----
def test_verify_otp_round_trip():
    h = hash_otp("123456")
    assert verify_otp("123456", h) is True
    assert verify_otp("000000", h) is False


def test_verify_otp_empty_hash_is_false():
    assert verify_otp("123456", "") is False


def test_verify_otp_malformed_hash_is_false():
    # A corrupt/garbage hash must be treated as "no match", not blow up.
    assert verify_otp("123456", "not-an-argon2-hash") is False


# ---- CLI entrypoint (python -m app.core.security <password>) ----
def test_cli_prints_a_hash(capsys, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["security", "mypw"])
    runpy.run_path(security.__file__, run_name="__main__")
    out = capsys.readouterr().out.strip()
    assert out.startswith("$argon2") and verify_password("mypw", out)


def test_cli_usage_error_exits_1(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["security"])  # missing the password arg
    with pytest.raises(SystemExit) as exc:
        runpy.run_path(security.__file__, run_name="__main__")
    assert exc.value.code == 1


# keep the module import referenced (runpy re-imports under __main__)
assert security.SESSION_COOKIE != security.CUSTOMER_COOKIE
