"""Tests for bilas_id_mcp.helpers — date validation, summary extraction, production verification."""
import json
import pytest

from bilas_id_mcp.helpers import (
    validate_report_dates,
    summarize_ringkasan,
    verify_production_items,
    production_response,
)


# ── validate_report_dates ─────────────────────────────────────────────────

def test_validate_valid_dates():
    start, end = validate_report_dates("2026/08/01", "2026/08/31")
    assert start == "2026/08/01"
    assert end == "2026/08/31"


def test_validate_rejects_bad_format():
    with pytest.raises(ValueError, match="invalid date format"):
        validate_report_dates("08-01-2026", "08-31-2026")


def test_validate_rejects_reversed_range():
    with pytest.raises(ValueError, match="tgl_awal must not be later"):
        validate_report_dates("2026/08/31", "2026/08/01")


def test_validate_rejects_invalid_date():
    with pytest.raises(ValueError):
        validate_report_dates("2026/13/01", "2026/13/31")


def test_validate_same_date():
    start, end = validate_report_dates("2026/08/15", "2026/08/15")
    assert start == end


# ── summarize_ringkasan ───────────────────────────────────────────────────

def test_summarize_ringkasan_with_semua():
    api_response = {
        "result": [{
            "semua": [{
                "omzet": 1000000,
                "pendapatan": 800000,
                "kiloan": 50,
                "trxmasuk": 25,
                "graph": [{"date": "2026-08-01", "omzet": 500000}],
            }]
        }]
    }
    summary = summarize_ringkasan(api_response)
    assert summary is not None
    assert summary["omzet"] == 1000000
    assert summary["pendapatan"] == 800000
    assert len(summary["graph"]) == 1


def test_summarize_ringkasan_with_outlet_key():
    api_response = {
        "result": [{
            "outlet_123": [{
                "omzet": 500000,
                "pendapatan": 400000,
                "pengeluaran": 100000,
                "graph": [],
            }]
        }]
    }
    summary = summarize_ringkasan(api_response)
    assert summary is not None
    assert summary["omzet"] == 500000


def test_summarize_ringkasan_empty():
    assert summarize_ringkasan({}) is None
    assert summarize_ringkasan({"result": []}) is None
    assert summarize_ringkasan({"result": [{}]}) is None


def test_summarize_ringkasan_no_matching_keys():
    api_response = {"result": [{"semua": [{"unrelated": 1}]}]}
    # Returns a dict with only 'graph' when row has no matching summary keys
    result = summarize_ringkasan(api_response)
    assert result is not None
    assert "graph" in result
    assert len(result) == 1  # only graph, no summary keys


# ── verify_production_items ───────────────────────────────────────────────

def test_verify_production_items_persisted():
    order = {"detail": [{"uid": "u1", "proses": "Cuci"}]}
    expected = [{"item_index": 1, "item_name": "Cuci Biasa", "uid": "u1", "target_stage": "Cuci"}]
    result = verify_production_items(order, expected)
    assert len(result) == 1
    assert result[0]["persisted"] is True


def test_verify_production_items_not_persisted():
    order = {"detail": [{"uid": "u1", "proses": "Antrian"}]}
    expected = [{"item_index": 1, "item_name": "Cuci Biasa", "uid": "u1", "target_stage": "Cuci"}]
    result = verify_production_items(order, expected)
    assert result[0]["persisted"] is False


def test_verify_production_items_missing_item():
    order = {"detail": []}
    expected = [{"item_index": 1, "item_name": "X", "uid": "u1", "target_stage": "Cuci"}]
    result = verify_production_items(order, expected)
    assert result[0]["observed_stage"] is None
    assert result[0]["persisted"] is False


def test_verify_production_items_fallback_by_index():
    """When UID doesn't match, fall back to item_index."""
    order = {"detail": [{"uid": "other", "proses": "Setrika"}]}
    expected = [{"item_index": 1, "item_name": "X", "uid": "u1", "target_stage": "Setrika"}]
    result = verify_production_items(order, expected)
    assert result[0]["persisted"] is True


# ── production_response ───────────────────────────────────────────────────

def test_production_response_empty():
    result = production_response("")
    assert result["status"] == "success"


def test_production_response_undefined():
    result = production_response("undefined")
    assert result["status"] == "success"


def test_production_response_valid_json():
    result = production_response('{"status":"ok"}')
    assert result["status"] == "ok"


def test_production_response_raw_text():
    result = production_response("some raw text")
    assert result["status"] == "processed"
    assert result["raw_response"] == "some raw text"
