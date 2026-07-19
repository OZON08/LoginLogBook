"""Author-time generator for the static nginx error pages.

Run once and commit the output:  python build_error_pages.py
Produces 50x.<lang>.html and 429.<lang>.html with the LoginLogBook logo
embedded as a data: URI, so the pages are fully self-contained.
"""
import base64
from pathlib import Path

_HERE = Path(__file__).parent
_LOGO_PATH = _HERE.parent.parent / "app" / "static" / "loginlogbook-logo.svg"

_TEXTS = {
    ("50x", "de"): ("Dienst nicht erreichbar",
                    "Der Dienst ist vorübergehend nicht erreichbar. Bitte versuchen Sie es in Kürze erneut.",
                    "Erneut versuchen"),
    ("50x", "en"): ("Service unavailable",
                    "The service is temporarily unavailable. Please try again shortly.",
                    "Try again"),
    ("429", "de"): ("Zu viele Anfragen",
                    "Zu viele Anfragen in kurzer Zeit. Bitte warten Sie einen Moment.",
                    "Erneut versuchen"),
    ("429", "en"): ("Too many requests",
                    "Too many requests in a short time. Please wait a moment.",
                    "Try again"),
}


def _logo_data_uri() -> str:
    b64 = base64.b64encode(_LOGO_PATH.read_bytes()).decode("ascii")
    return f"data:image/svg+xml;base64,{b64}"


def _render(lang: str, title: str, message: str, retry: str, logo: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} – LoginLogBook</title>
<style>
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ background: #0F172A; font-family: "Segoe UI", system-ui, sans-serif;
  min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 1rem; }}
.card {{ background: #fff; border-radius: 12px; padding: 2.5rem 2rem; width: 100%;
  max-width: 480px; box-shadow: 0 24px 64px rgba(0,0,0,0.4); text-align: center; }}
.logo {{ height: 96px; margin-bottom: 1.25rem; }}
h1 {{ font-size: 1.25rem; font-weight: 700; color: #0F172A; margin-bottom: 0.75rem; }}
p {{ font-size: 0.9375rem; color: #475569; margin-bottom: 1.75rem; line-height: 1.6; }}
a {{ display: inline-block; background: #2563EB; color: #fff; text-decoration: none;
     font-weight: 600; font-size: 0.9375rem; padding: 0.625rem 1.5rem; border-radius: 8px; }}
a:hover {{ background: #1D4ED8; }}
</style>
</head>
<body>
<div class="card">
  <img class="logo" src="{logo}" alt="LoginLogBook">
  <h1>{title}</h1>
  <p>{message}</p>
  <a href="/">{retry}</a>
</div>
</body>
</html>"""


def main() -> None:
    logo = _logo_data_uri()
    for (page, lang), (title, message, retry) in _TEXTS.items():
        html = _render(lang, title, message, retry, logo)
        (_HERE / f"{page}.{lang}.html").write_text(html, encoding="utf-8")
    print(f"wrote {len(_TEXTS)} error pages to {_HERE}")


if __name__ == "__main__":
    main()
