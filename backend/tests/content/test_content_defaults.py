"""Unit tests for the landing content defaults — specifically the group builder
used by migration 0007's backfill. Pure functions, no DB."""

from app.core.content_defaults import (
    SECTION_LABELS,
    default_content,
    groups_from_category_rows,
)


def test_default_content_has_all_sections():
    c = default_content()
    assert set(c) == {"sections", "promo", "hero", "trust", "groups", "faq", "footer"}
    assert c["groups"] == []  # fresh landing has no product groups


def test_groups_from_empty_rows_is_empty():
    assert groups_from_category_rows([]) == []


def test_groups_preserve_first_seen_category_order_and_ids():
    rows = [
        ("p1", "luxury"),
        ("p2", "daily"),
        ("p3", "luxury"),   # second luxury id joins the existing group
        ("p4", "daily"),
    ]
    groups = groups_from_category_rows(rows)

    # one group per distinct category, in first-seen order (luxury before daily)
    assert [g["title"] for g in groups] == [
        SECTION_LABELS["luxury"]["title"],
        SECTION_LABELS["daily"]["title"],
    ]
    assert groups[0]["product_ids"] == ["p1", "p3"]
    assert groups[1]["product_ids"] == ["p2", "p4"]
    # label fields are carried through from SECTION_LABELS
    assert groups[0]["eyebrow"] == SECTION_LABELS["luxury"]["eyebrow"]


def test_groups_unknown_category_gets_fallback_label():
    groups = groups_from_category_rows([("p1", "mystery")])
    assert groups[0]["title"] == "mystery"       # falls back to the raw category
    assert groups[0]["eyebrow"] == ""
    assert groups[0]["product_ids"] == ["p1"]


def test_groups_stringify_non_str_ids():
    # ids may arrive as UUIDs from the DB rows; they must be stringified.
    import uuid

    pid = uuid.uuid4()
    groups = groups_from_category_rows([(pid, "daily")])
    assert groups[0]["product_ids"] == [str(pid)]
