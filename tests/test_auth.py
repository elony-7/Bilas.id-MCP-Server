"""Tests for bilas_id_mcp.auth — JWT decoding, state management, credential saving."""
import json
import base64
import tempfile
from pathlib import Path
from unittest.mock import patch, AsyncMock

import pytest

from bilas_id_mcp.auth import (
    jwt_decode_payload,
    load_state,
    save_state,
    ensure_config_dir,
)


# ── jwt_decode_payload ────────────────────────────────────────────────────

def _make_jwt(payload_dict):
    """Build a minimal JWT string (header.payload.signature) for testing."""
    header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256"}).encode()).rstrip(b"=").decode()
    payload = base64.urlsafe_b64encode(json.dumps(payload_dict).encode()).rstrip(b"=").decode()
    return f"{header}.{payload}.fakesig"


def test_jwt_decode_valid():
    jwt = _make_jwt({"id": "user123", "exp": 1700000000})
    result = jwt_decode_payload(jwt)
    assert result["id"] == "user123"
    assert result["exp"] == 1700000000


def test_jwt_decode_empty():
    assert jwt_decode_payload("") == {}
    assert jwt_decode_payload(None) == {}


def test_jwt_decode_no_dots():
    assert jwt_decode_payload("notajwt") == {}


def test_jwt_decode_invalid_base64():
    assert jwt_decode_payload("a.b.c") == {}


# ── load_state / save_state ───────────────────────────────────────────────

def test_save_and_load_state(tmp_path):
    """Round-trip: save a state dict, load it back."""
    state_file = tmp_path / "token_state.json"
    with patch("bilas_id_mcp.auth.CONFIG_DIR", tmp_path), \
         patch("bilas_id_mcp.auth.STATE_FILE", state_file):
        test_state = {"jwt": "test.jwt.token", "outlet_id": "outlet_1", "exp": 1700000000}
        save_state(test_state)
        loaded = load_state()
        assert loaded["jwt"] == "test.jwt.token"
        assert loaded["outlet_id"] == "outlet_1"


def test_save_state_normalises_json_outlet(tmp_path):
    """If outlet_id is a JSON blob like {"id":"xxx"}, extract the id."""
    state_file = tmp_path / "token_state.json"
    with patch("bilas_id_mcp.auth.CONFIG_DIR", tmp_path), \
         patch("bilas_id_mcp.auth.STATE_FILE", state_file):
        test_state = {"jwt": "t", "outlet_id": '{"id":"extracted_id"}'}
        save_state(test_state)
        loaded = load_state()
        assert loaded["outlet_id"] == "extracted_id"


def test_load_state_returns_default_when_no_file(tmp_path):
    state_file = tmp_path / "nonexistent.json"
    with patch("bilas_id_mcp.auth.CONFIG_DIR", tmp_path), \
         patch("bilas_id_mcp.auth.STATE_FILE", state_file):
        loaded = load_state()
        assert loaded["jwt"] == ""
        assert loaded["outlet_id"] == ""


def test_load_state_prefers_env_vars(tmp_path):
    state_file = tmp_path / "token_state.json"
    jwt = _make_jwt({"id": "env_user", "exp": 1700000000})
    with patch("bilas_id_mcp.auth.CONFIG_DIR", tmp_path), \
         patch("bilas_id_mcp.auth.STATE_FILE", state_file), \
         patch.dict("os.environ", {"BILAS_JWT_TOKEN": jwt, "BILAS_OUTLET_ID": "env_outlet"}):
        loaded = load_state()
        assert loaded["jwt"] == jwt
        assert loaded["outlet_id"] == "env_outlet"
        assert loaded["source"] == "environment_variables"


# ── save_manual_credentials ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_save_manual_credentials_rejects_empty():
    from bilas_id_mcp.auth import save_manual_credentials
    result = json.loads(await save_manual_credentials(""))
    assert result["status"] == "error"


@pytest.mark.asyncio
async def test_save_manual_credentials_saves(tmp_path):
    from bilas_id_mcp.auth import save_manual_credentials
    state_file = tmp_path / "token_state.json"
    jwt = _make_jwt({"id": "u1", "exp": 1700000000})
    with patch("bilas_id_mcp.auth.CONFIG_DIR", tmp_path), \
         patch("bilas_id_mcp.auth.STATE_FILE", state_file):
        result = json.loads(await save_manual_credentials(jwt, "outlet_abc"))
        assert result["status"] == "success"
        assert result["outlet_id"] == "outlet_abc"
