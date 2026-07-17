## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).

## Sprachen (i18n)

Feste UI-Texte liegen in JSON-Locale-Dateien. Aktive Sprache = serverseitig (`/data/settings.json`), umschaltbar in der Admin-UI. Neue Sprache `xx`:
1. `xx.json` je Verzeichnis aus `de.json` kopieren und übersetzen: `loginlogbook-client/app/locales/`, `loginlogbook-api/app/locales/{admin,api,grafana}/`.
2. Client/Admin/API: fertig (`xx` erscheint automatisch im Admin-Umschalter).
3. Grafana: `uv run python -m scripts.build_dashboards --lang xx` + `docker compose restart grafana`.

Key-Parität (jede Sprachdatei hat dieselben Keys wie `de.json`) wird per Test erzwungen (`test_locale_parity.py` in beiden Komponenten).
