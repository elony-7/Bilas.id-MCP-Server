"""Behavior tests for the dashboard cashbox report tools.

Credentials and live network traffic stay out of this suite. Date-validation
cases document the input contract the tool should enforce before a request.
"""
import asyncio
import contextlib
import io
import json
import sys

import pytest

from bilas_id_mcp.helpers import validate_report_dates, summarize_ringkasan
from bilas_id_mcp.constants import ARUSKAS_NERACA_URL


# ── Date validation (sync, no network) ────────────────────────────────────

class TestDateValidation:
    @pytest.mark.parametrize(
        ("start", "end"),
        [
            ("2026-08-01", "2026/08/30"),
            ("2026/8/01", "2026/08/30"),
            ("2026/02/30", "2026/03/01"),
            ("2026/09/01", "2026/08/30"),
            ("", "2026/08/30"),
        ],
    )
    def test_rejects_invalid_date_ranges(self, start, end):
        with pytest.raises(ValueError, match="date"):
            validate_report_dates(start, end)

    def test_accepts_valid_range(self):
        start, end = validate_report_dates("2026/08/01", "2026/08/30")
        assert start == "2026/08/01"
        assert end == "2026/08/30"


# ── Ringkasan summarizer (sync, no network) ───────────────────────────────

class TestRingkasanSummarizer:
    def test_extracts_kpi_block(self):
        api = {
            "value": 1,
            "message": "Success",
            "result": [
                {
                    "semua": [
                        {
                            "omzet": 7693360, "pendapatan": 7307280, "kiloan": 723.76,
                            "satuan": 72, "meter": 16.2, "trxmasuk": 113, "trxbatal": 16,
                            "graph": [{"tanggal": "01/08/2026", "omzet": 0}],
                        }
                    ]
                }
            ],
        }
        summary = summarize_ringkasan(api)
        assert summary is not None
        assert summary["kiloan"] == 723.76
        assert summary["satuan"] == 72
        assert summary["trxmasuk"] == 113
        assert summary["omzet"] == 7693360
        assert summary["graph"][0]["tanggal"] == "01/08/2026"

    def test_handles_empty_response(self):
        assert summarize_ringkasan({"value": 1, "result": []}) is None
        assert summarize_ringkasan({}) is None


# ── CLI help text ─────────────────────────────────────────────────────────

def test_update_flag_appears_in_help():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        sys.argv = ["bilas-mcp", "--help"]
        from bilas_id_mcp.server import main
        main()
    out = buf.getvalue()
    assert "bilas-mcp --update" in out
    assert "Update to latest version" in out


def test_update_from_github_prints_success(monkeypatch):
    import subprocess as _subprocess
    from bilas_id_mcp.cli import _update_from_github

    fake = type("R", (), {
        "returncode": 0,
        "stdout": "Successfully installed bilas-id-mcp-1.9.99\n",
        "stderr": "",
    })()
    monkeypatch.setattr(_subprocess, "run", lambda *a, **k: fake)

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        _update_from_github()
    out = buf.getvalue()
    assert "Successfully installed" in out
    assert "1.9.99" in out


# ── Removed tool ──────────────────────────────────────────────────────────

def test_live_cashbox_balances_removed():
    """bilas_get_live_cashbox_balances was a thin wrapper with hardcoded dates — removed."""
    from bilas_id_mcp.server import mcp
    tools = asyncio.run(mcp.list_tools())
    names = {t.name for t in tools}
    assert "bilas_get_live_cashbox_balances" not in names


def test_remote_auth_bridge_removed():
    """bilas_start_remote_auth_bridge was a duplicate of bilas_launch_browser_login — removed."""
    from bilas_id_mcp.server import mcp
    tools = asyncio.run(mcp.list_tools())
    names = {t.name for t in tools}
    assert "bilas_start_remote_auth_bridge" not in names
