from app.services.dashboard_layout import WIDGET_IDS, default_layout, normalize_layout, validate_layout


def test_default_has_every_widget_visible():
    assert [w["id"] for w in default_layout()] == list(WIDGET_IDS)


def test_normalize_drops_unknown_dedupes_and_appends_new_widgets():
    stored = {"widgets": [{"id": "news", "visible": False}, {"id": "bogus"}, {"id": "news"}, {"id": "loans"}]}
    out = normalize_layout(stored)
    assert [w["id"] for w in out][:2] == ["news", "loans"]
    assert out[0]["visible"] is False
    assert sorted(w["id"] for w in out) == sorted(WIDGET_IDS)
    assert normalize_layout(None) == default_layout() and normalize_layout("junk") == default_layout()


def test_validate_requires_each_widget_exactly_once():
    ok = [{"id": i, "visible": True} for i in reversed(WIDGET_IDS)]
    assert [w["id"] for w in validate_layout(ok)] == list(reversed(WIDGET_IDS))
    for bad in (ok[:-1], ok + [ok[0]], [*ok[:-1], {"id": "x", "visible": True}]):
        try:
            validate_layout(bad)
        except ValueError:
            continue
        raise AssertionError("expected ValueError")
