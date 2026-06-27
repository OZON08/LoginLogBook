"""Pure-logic tests for reason filtering — no PyQt6 required."""
from app.models import Reason


def _filter(reasons: list[Reason], query: str) -> list[Reason]:
    """Replicate the filter logic used by ReasonList.apply_filter."""
    q = query.strip().lower()
    if not q:
        return [r for r in reasons if r.active]
    return [r for r in reasons if r.active and q in r.label.lower()]


REASONS = [
    Reason(id="1", label="Wartung"),
    Reason(id="2", label="Deployment"),
    Reason(id="3", label="Incident"),
    Reason(id="4", label="Monitoring"),
    Reason(id="5", label="Wartungsarbeiten", active=False),
]


def test_empty_query_returns_all_active():
    result = _filter(REASONS, "")
    assert len(result) == 4
    assert all(r.active for r in result)


def test_filter_is_case_insensitive():
    result = _filter(REASONS, "WART")
    assert len(result) == 1
    assert result[0].label == "Wartung"


def test_filter_strips_whitespace():
    result = _filter(REASONS, "  deployment  ")
    assert len(result) == 1


def test_filter_excludes_inactive():
    result = _filter(REASONS, "Wartung")
    assert all(r.label != "Wartungsarbeiten" for r in result)


def test_no_match_returns_empty():
    assert _filter(REASONS, "xyzzy") == []
