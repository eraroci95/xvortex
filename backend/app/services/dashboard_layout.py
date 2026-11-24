"""Dashboard widget order and visibility. Stored as {"widgets": [{"id": ..., "visible": ...}]}."""
from typing import Any

WIDGET_IDS = ("loans", "paper", "market", "transactions", "news", "alerts")


def default_layout() -> list[dict[str, Any]]:
    return [{"id": i, "visible": True} for i in WIDGET_IDS]


def normalize_layout(stored: Any) -> list[dict[str, Any]]:
    """Read a stored layout tolerantly: drop unknown ids, add widgets introduced since it was saved."""
    items = stored.get("widgets", []) if isinstance(stored, dict) else []
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for item in items if isinstance(items, list) else []:
        wid = item.get("id") if isinstance(item, dict) else None
        if wid in WIDGET_IDS and wid not in seen:
            seen.add(wid)
            out.append({"id": wid, "visible": bool(item.get("visible", True))})
    out.extend({"id": i, "visible": True} for i in WIDGET_IDS if i not in seen)
    return out


def validate_layout(widgets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Strict check for saves: every known widget exactly once."""
    ids = [w["id"] for w in widgets]
    unknown = sorted(set(ids) - set(WIDGET_IDS))
    if unknown:
        raise ValueError(f"Unknown widget: {unknown[0]}")
    if len(ids) != len(set(ids)):
        raise ValueError("Each widget can appear only once.")
    missing = [i for i in WIDGET_IDS if i not in ids]
    if missing:
        raise ValueError(f"Missing widget: {missing[0]}")
    return [{"id": w["id"], "visible": bool(w["visible"])} for w in widgets]
