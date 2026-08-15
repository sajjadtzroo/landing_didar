"""The logging contract's non-trivial parts: PII scrubbing and per-module
level filtering. If these break, secrets leak or logs vanish silently."""

from app.core.logging import _scrub_text


def test_iranian_mobile_is_masked():
    assert _scrub_text("sms to 09123456789 sent") == "sms to 0912****789 sent"
    assert _scrub_text("+989123456789") == "+989****789"


def test_otp_code_after_kod_is_masked():
    assert _scrub_text("کد ورود دیدار: 099019").endswith("******")
    assert _scrub_text("your code is 4321").endswith("******")


def test_plain_numbers_untouched():
    # order totals / ids must NOT be starred
    assert _scrub_text("order total 1250000 toman") == "order total 1250000 toman"


def test_module_level_filter(monkeypatch):
    from app.core import logging as applog

    monkeypatch.setattr(applog.settings, "log_levels", "db.query=WARNING")
    rec_info = {"extra": {"module": "db.query"}, "level": type("L", (), {"no": 20})()}
    rec_warn = {"extra": {"module": "db.query"}, "level": type("L", (), {"no": 30})()}
    rec_other = {"extra": {"module": "api.access"}, "level": type("L", (), {"no": 20})()}
    assert applog._level_filter(rec_info) is False  # INFO suppressed for db.query
    assert applog._level_filter(rec_warn) is True
    assert applog._level_filter(rec_other) is True  # other modules unaffected
