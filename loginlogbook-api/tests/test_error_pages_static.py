from pathlib import Path

_ROOT = Path(__file__).parent.parent  # loginlogbook-api/
_ERRORS = _ROOT / "nginx" / "errors"


def test_all_error_pages_exist_and_are_self_contained():
    expected = {
        "50x.de.html": "Dienst nicht erreichbar",
        "50x.en.html": "Service unavailable",
        "429.de.html": "Zu viele Anfragen",
        "429.en.html": "Too many requests",
    }
    for name, marker in expected.items():
        html = (_ERRORS / name).read_text(encoding="utf-8")
        assert marker in html
        assert "data:image/svg+xml;base64," in html   # embedded logo
        assert "http://" not in html and "https://" not in html  # no external resources


def test_prod_nginx_config_wires_error_pages():
    conf = (_ROOT / "nginx" / "nginx.conf").read_text(encoding="utf-8")
    assert "map $http_accept_language $err_lang" in conf
    assert "limit_req_status 429;" in conf
    assert "error_page 502 503 504 @err5xx;" in conf
    assert "error_page 429 @err429;" in conf
    assert "location @err5xx" in conf and "location @err429" in conf


def test_dev_nginx_config_wires_5xx_error_page():
    conf = (_ROOT / "nginx" / "nginx.dev.conf").read_text(encoding="utf-8")
    assert "error_page 502 503 504 @err5xx;" in conf
    assert "location @err5xx" in conf
