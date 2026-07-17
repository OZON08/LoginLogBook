"""Generate Grafana dashboards from templates + grafana locale files.

Usage: python -m scripts.build_dashboards [--lang de]
Replaces @@grafana.key@@ placeholders with the locale value. Writes 24h
variants to grafana/dashboards/ and 7d variants to grafana/dashboards-dev/.
"""
import argparse
import json
import re
from pathlib import Path

_ROOT = Path(__file__).parent.parent
_TEMPLATES = _ROOT / "grafana" / "templates"
_LOCALES = _ROOT / "app" / "locales" / "grafana"
_PROD = _ROOT / "grafana" / "dashboards"
_DEV = _ROOT / "grafana" / "dashboards-dev"
_PLACEHOLDER = re.compile(r"@@([a-z0-9._]+)@@")


def render_dashboard(template: dict, locale: dict) -> dict:
    def sub(m: re.Match) -> str:
        # KeyError on missing key = fail loud. Escape for the JSON string
        # context so a value with " or \ cannot corrupt the output.
        return json.dumps(locale[m.group(1)], ensure_ascii=False)[1:-1]
    text = _PLACEHOLDER.sub(sub, json.dumps(template, ensure_ascii=False))
    return json.loads(text)


def _load_locale(lang: str) -> dict:
    base = json.loads((_LOCALES / "de.json").read_text(encoding="utf-8"))
    if lang != "de":
        base = {**base, **json.loads((_LOCALES / f"{lang}.json").read_text(encoding="utf-8"))}
    return base


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", default="de")
    args = ap.parse_args()
    locale = _load_locale(args.lang)
    _PROD.mkdir(parents=True, exist_ok=True)
    _DEV.mkdir(parents=True, exist_ok=True)
    for tpl_path in sorted(_TEMPLATES.glob("*.json")):
        tpl = json.loads(tpl_path.read_text(encoding="utf-8"))
        rendered = render_dashboard(tpl, locale)
        rendered["time"] = {"from": "now-24h", "to": "now"}
        (_PROD / tpl_path.name).write_text(
            json.dumps(rendered, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        dev = render_dashboard(tpl, locale)
        dev["time"] = {"from": "now-7d", "to": "now"}
        (_DEV / tpl_path.name).write_text(
            json.dumps(dev, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"built {len(list(_TEMPLATES.glob('*.json')))} dashboards for lang={args.lang}")


if __name__ == "__main__":
    main()
