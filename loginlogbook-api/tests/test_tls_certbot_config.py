"""Structural configuration tests for TLS bootstrap + optional certbot."""
import contextlib
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


def test_acme_location_before_https_redirect():
    conf = _NGINX_CONF.read_text(encoding="utf-8")
    acme = conf.find("/.well-known/acme-challenge/")
    redirect = conf.find("return 301 https://")
    assert acme != -1, "ACME challenge location missing"
    assert redirect != -1, "HTTPS redirect missing"
    assert acme < redirect, "ACME location must come before the HTTPS redirect"


def _has_docker() -> bool:
    return shutil.which("docker") is not None


@contextlib.contextmanager
def _ensure_env():
    """`docker compose config` needs the env_file (.env) to exist. Create a
    throwaway one from .env.example when the repo has no local .env."""
    env_path = _ROOT / ".env"
    created = False
    if not env_path.exists():
        env_path.write_text(_ENV_EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
        created = True
    try:
        yield
    finally:
        if created:
            env_path.unlink()


def test_certbot_service_profile_gated():
    assert _services()["certbot"]["profiles"] == ["certbot"]


def test_certbot_image_pinned():
    assert _services()["certbot"]["image"] == "certbot/certbot:v5.7.0"


def test_deploy_hook_script_executable():
    script = _SCRIPTS / "deploy-hook.sh"
    assert script.exists()
    assert os.access(script, os.X_OK)


def test_nginx_has_reload_loop():
    assert "nginx -s reload" in _services()["nginx"]["command"]


def test_letsencrypt_named_volume():
    assert "letsencrypt" in _compose()["volumes"]


@pytest.mark.skipif(not _has_docker(), reason="docker not available")
def test_compose_config_hides_certbot_without_profile():
    env = {**os.environ, "TLS_DOMAIN": "example.com", "CERTBOT_EMAIL": "a@b.c"}
    with _ensure_env():
        r = subprocess.run(
            ["docker", "compose", "-f", str(_COMPOSE), "config"],
            capture_output=True, text=True, cwd=_ROOT, env=env,
        )
    assert r.returncode == 0, r.stderr
    cfg = yaml.safe_load(r.stdout)
    assert "certbot" not in cfg["services"]


@pytest.mark.skipif(not _has_docker(), reason="docker not available")
def test_compose_config_shows_certbot_with_profile():
    env = {**os.environ, "TLS_DOMAIN": "example.com", "CERTBOT_EMAIL": "a@b.c"}
    with _ensure_env():
        r = subprocess.run(
            ["docker", "compose", "-f", str(_COMPOSE), "--profile", "certbot", "config"],
            capture_output=True, text=True, cwd=_ROOT, env=env,
        )
    assert r.returncode == 0, r.stderr
    cfg = yaml.safe_load(r.stdout)
    assert "certbot" in cfg["services"]


def test_env_example_has_certbot_email():
    assert "CERTBOT_EMAIL" in _ENV_EXAMPLE.read_text(encoding="utf-8")


def test_init_letsencrypt_executable_and_complete():
    script = _SCRIPTS / "init-letsencrypt.sh"
    assert script.exists()
    assert os.access(script, os.X_OK)
    body = script.read_text(encoding="utf-8")
    assert "certonly" in body
    assert "--webroot" in body
    assert "--deploy-hook" in body
    assert "--staging" in body


def test_readme_documents_https():
    readme = (_ROOT.parent / "README.md").read_text(encoding="utf-8")
    assert "HTTPS & Zertifikate" in readme
