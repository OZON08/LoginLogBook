import json
from pathlib import Path

from scripts.build_dashboards import render_dashboard


def test_render_replaces_placeholders(tmp_path: Path):
    template = {"title": "@@grafana.betrieb.dashtitle@@",
                "panels": [{"title": "@@grafana.betrieb.total@@"}]}
    locale = {"grafana.betrieb.dashtitle": "LoginLogBook – Betrieb",
              "grafana.betrieb.total": "Logins gesamt"}
    out = render_dashboard(template, locale)
    assert out["title"] == "LoginLogBook – Betrieb"
    assert out["panels"][0]["title"] == "Logins gesamt"
    assert "@@" not in json.dumps(out)


def test_render_missing_key_raises(tmp_path: Path):
    template = {"title": "@@grafana.unknown@@"}
    import pytest
    with pytest.raises(KeyError):
        render_dashboard(template, {})


def test_render_escapes_special_characters(tmp_path: Path):
    # A translation containing " or \ must not corrupt the JSON output.
    template = {"title": "@@k@@"}
    out = render_dashboard(template, {"k": 'A "quoted" \\ value'})
    assert out["title"] == 'A "quoted" \\ value'
