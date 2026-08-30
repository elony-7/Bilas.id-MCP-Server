"""Behavior tests for the dashboard cashbox report tools.

Credentials and live network traffic stay out of this suite. Date-validation
cases document the input contract the tool should enforce before a request.
"""
import asyncio
import json
import re
import urllib.error
import urllib.request
import uuid

import pytest

from bilas_id_mcp import server


class FakeResponse:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode("utf-8")

    def read(self):
        return self.payload


def install_credentials(monkeypatch):
    """Provide non-secret request credentials without touching user state."""
    monkeypatch.setattr(
        server,
        "get_valid_headers",
        lambda: ({"Authorization": "Bearer test-token", "x-outlet-id": "outlet-test"}, {"outlet_id": "outlet-test"}),
    )


def decode_request_body(request):
    return json.loads(request.data.decode("utf-8"))


# Verifies date-range request construction, endpoint selection, and normalization.
class TestDashboardReport:
    def test_report_posts_dashboard_date_range_and_normalizes_rows(self, monkeypatch):
        install_credentials(monkeypatch)
        calls = []
        api_response = {
            "value": "1",
            "result2": [
                {"cashbox": "Tunai", "saldo_sebelum": "125000", "total_debit": 30000, "total_kredit": None, "saldo_sesudah": "155000"},
                {"cashbox": "BCA", "saldo_sebelum": 0, "total_debit": "2000", "total_kredit": "500", "saldo_sesudah": 1500},
            ],
        }

        def fake_urlopen(request, timeout):
            calls.append((request, timeout))
            return FakeResponse(api_response)

        monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
        result = json.loads(server.bilas_get_cashbox_report("2026/08/01", "2026/08/30"))

        assert result["status"] == "success"
        assert result["rows"] == [
            {"cashbox": "Tunai", "saldo_awal": 125000, "debit": 30000, "kredit": 0, "saldo_akhir": 155000},
            {"cashbox": "BCA", "saldo_awal": 0, "debit": 2000, "kredit": 500, "saldo_akhir": 1500},
        ]
        assert result["summary"] == {"cashbox": "TOTAL", "saldo_awal": 125000, "debit": 32000, "kredit": 500, "saldo_akhir": 156500}

        request, timeout = calls[0]
        assert request.full_url == server.ARUSKAS_NERACA_URL
        assert request.method == "POST"
        assert request.get_header("Authorization") == "Bearer test-token"
        assert request.get_header("X-outlet-id") == "outlet-test"
        assert timeout == 60
        body = decode_request_body(request)
        assert body["id"] == "outlet-test"
        assert body["tgl_awal"] == "2026/08/01"
        assert body["tgl_akhir"] == "2026/08/30"
        assert re.fullmatch(r"[0-9a-f-]{36}", body["req_id"])
        uuid.UUID(body["req_id"])

    # Verifies malformed and impossible ranges are rejected before network access.
    @pytest.mark.parametrize(
        ("start", "end"),
        [("2026-08-01", "2026/08/30"), ("2026/8/01", "2026/08/30"), ("2026/02/30", "2026/03/01"), ("2026/09/01", "2026/08/30"), ("", "2026/08/30")],
    )
    def test_report_rejects_invalid_date_ranges_without_request(self, monkeypatch, start, end):
        install_credentials(monkeypatch)
        calls = []
        monkeypatch.setattr(urllib.request, "urlopen", lambda *args, **kwargs: calls.append(args) or FakeResponse({}))

        result = json.loads(server.bilas_get_cashbox_report(start, end))

        assert result["status"] == "error"
        assert "date" in result["message"].lower()
        assert calls == []

    # Verifies transport failures are converted to the tool's JSON error contract.
    def test_report_returns_json_error_when_dashboard_request_fails(self, monkeypatch):
        install_credentials(monkeypatch)

        def raise_network_error(*args, **kwargs):
            raise urllib.error.URLError("dashboard unavailable")

        monkeypatch.setattr(urllib.request, "urlopen", raise_network_error)
        result = json.loads(server.bilas_get_cashbox_report("2026/08/01", "2026/08/30"))

        assert result == {"status": "error", "message": "<urlopen error dashboard unavailable>"}

    # Verifies the convenience tool maps the same endpoint output into its public shape.
    def test_live_cashbox_tool_maps_report_result(self, monkeypatch):
        expected = {"status": "success", "tgl_awal": "2026/08/01", "tgl_akhir": "2026/08/30", "rows": [{"cashbox": "Tunai", "saldo_awal": 10, "debit": 4, "kredit": 1, "saldo_akhir": 13}], "summary": {"cashbox": "TOTAL", "saldo_awal": 10, "debit": 4, "kredit": 1, "saldo_akhir": 13}, "api_response": {"result2": []}}
        monkeypatch.setattr(server, "bilas_get_cashbox_report", lambda start, end: json.dumps(expected))

        result = json.loads(server.bilas_get_live_cashbox_balances("2026/08/01", "2026/08/30"))

        assert result == {"status": "success", "period": {"start": "2026/08/01", "end": "2026/08/30"}, "cashbox_balances": expected["rows"], "overall_summary": expected["summary"], "source": server.ARUSKAS_NERACA_URL}


# Verifies both dashboard report functions are exposed through MCP registration.
def test_dashboard_report_tools_are_registered():
    tools = asyncio.run(server.mcp.list_tools())
    names = {tool.name for tool in tools}
    assert {"bilas_get_cashbox_report", "bilas_get_live_cashbox_balances"} <= names


# Verifies the Ringkasan Outlet summary block surfaces the KPI numbers the
# dashboard Transaksi and Keuangan cards read.
def test_ringkasan_summarizer_extracts_kpi_block():
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
    summary = server._summarize_ringkasan(api)
    assert summary is not None
    assert summary["kiloan"] == 723.76
    assert summary["satuan"] == 72
    assert summary["trxmasuk"] == 113
    assert summary["omzet"] == 7693360
    assert summary["graph"][0]["tanggal"] == "01/08/2026"


def test_ringkasan_summarizer_handles_empty_response():
    assert server._summarize_ringkasan({"value": 1, "result": []}) is None
    assert server._summarize_ringkasan({}) is None
