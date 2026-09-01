"""Tests for bilas_id_mcp.constants."""
from bilas_id_mcp.constants import (
    VERSION, CONFIG_DIR, STATE_FILE, APP_TOKENS,
    ARUSKAS_URL, ARUSKAS_NERACA_URL, REPORT_ENDPOINTS, APIWEB_BASE,
)


def test_version_format():
    """Version should be semver-like: X.Y.Z"""
    parts = VERSION.split(".")
    assert len(parts) == 3
    assert all(p.isdigit() for p in parts)


def test_config_paths():
    assert CONFIG_DIR.name == ".bilas_id"
    assert STATE_FILE.name == "token_state.json"
    assert STATE_FILE.parent == CONFIG_DIR


def test_app_tokens_have_defaults():
    assert "x-access-token" in APP_TOKENS
    assert "x-access-web-token" in APP_TOKENS
    assert APP_TOKENS["Content-Type"] == "application/json"
    # Defaults should be non-empty strings
    assert len(APP_TOKENS["x-access-token"]) > 0
    assert len(APP_TOKENS["x-access-web-token"]) > 0


def test_report_endpoints_count():
    assert len(REPORT_ENDPOINTS) == 15


def test_report_endpoints_are_urls():
    for name, url in REPORT_ENDPOINTS.items():
        assert url.startswith("https://"), f"{name} URL should be HTTPS"
        assert "apibilas" in url, f"{name} URL should be on apibilas domain"


def test_apiweb_base():
    assert APIWEB_BASE == "https://apiweb.bilas.id"


def test_aruskas_urls():
    assert ARUSKAS_URL.startswith("https://")
    assert ARUSKAS_NERACA_URL.startswith("https://")
