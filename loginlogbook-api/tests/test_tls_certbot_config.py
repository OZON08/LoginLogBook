"""Structural configuration tests for TLS bootstrap + optional certbot."""
import os
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

_ROOT = Path(__file__).resolve().parent.parent          # loginlogbook-api/
_COMPOSE = _ROOT / "docker-compose.yml"
_NGINX_CONF = _ROOT / "nginx" / "nginx.conf"
_ENV_EXAMPLE = _ROOT / ".env.example"
_SCRIPTS = _ROOT / "scripts"


def _compose() -> dict:
    return yaml.safe_load(_COMPOSE.read_text(encoding="utf-8"))


def _services() -> dict:
    return _compose()["services"]


def test_env_example_has_tls_domain():
    assert "TLS_DOMAIN" in _ENV_EXAMPLE.read_text(encoding="utf-8")


def test_certs_init_image_pinned():
    assert _services()["certs-init"]["image"] == "alpine/openssl:3.5.7"


def test_nginx_depends_on_certs_init_completed():
    dep = _services()["nginx"]["depends_on"]["certs-init"]
    assert dep["condition"] == "service_completed_successfully"


def test_certs_init_script_executable():
    script = _SCRIPTS / "certs-init.sh"
    assert script.exists()
    assert os.access(script, os.X_OK)
