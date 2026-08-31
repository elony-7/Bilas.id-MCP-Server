"""Bilas.id MCP Server — shared helpers for authenticated API calls and report processing."""
import json
import re
import uuid
from datetime import datetime

import httpx

from .constants import APP_TOKENS, REPORT_ENDPOINTS, APIWEB_BASE
from .auth import get_valid_headers


def validate_report_dates(tgl_awal: str, tgl_akhir: str):
    """Validate dashboard dates in YYYY/MM/DD format and ordering."""
    fmt = "%Y/%m/%d"
    pattern = re.compile(r"^\d{4}/\d{2}/\d{2}$")
    if not (pattern.match(str(tgl_awal)) and pattern.match(str(tgl_akhir))):
        raise ValueError("invalid date format: use YYYY/MM/DD (e.g. 2026/08/30)")
    try:
        start = datetime.strptime(str(tgl_awal), fmt)
        end = datetime.strptime(str(tgl_akhir), fmt)
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid date range: dates must be valid calendar dates in YYYY/MM/DD") from exc
    if start > end:
        raise ValueError("invalid date range: tgl_awal must not be later than tgl_akhir")
    return start.strftime(fmt), end.strftime(fmt)


async def post_report(report_name: str, tgl_awal: str, tgl_akhir: str):
    """POST an authenticated report request and return the normalised response.

    Uses the dashboard's full body shape (pemilik, user, mode, tipe, send_data)
    which the report endpoints require. The Ringkasan Outlet endpoint takes a
    different id shape — a JSON-encoded array of outlet descriptors.
    """
    start, end = validate_report_dates(tgl_awal, tgl_akhir)
    headers, state = await get_valid_headers()
    request_id = str(uuid.uuid4())
    outlet_id = state["outlet_id"]
    user_id = state.get("user_id", "")
    url = REPORT_ENDPOINTS[report_name]

    if report_name == "ringkasan_outlet":
        body = {
            "req_id": request_id,
            "tgl_awal": start, "tgl_akhir": end,
            "id": json.dumps([{"id_outlet": outlet_id, "dibuat_tgl": "2024-01-01T00:00:00.000Z"}]),
            "pemilik": user_id,
            "send_data": False, "tipe": "semua",
            "user": f"web-{user_id}", "mode": "all list",
        }
    else:
        body = {
            "req_id": request_id,
            "tgl_awal": start, "tgl_akhir": end,
            "id": outlet_id, "pemilik": user_id,
            "send_data": False, "tipe": "semua",
            "user": f"web-{user_id}", "mode": "all list",
        }

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(url, headers=headers, json=body)
            raw = resp.json()
            status_code = resp.status_code
        return {
            "status": "success",
            "api_response": raw,
            "normalized_metadata": {
                "report": report_name, "endpoint": url, "outlet_id": outlet_id,
                "period": {"tgl_awal": start, "tgl_akhir": end},
                "request_id": request_id, "http_status": status_code,
            },
        }
    except httpx.HTTPStatusError as exc:
        return {
            "status": "error", "message": "Bilas report request failed",
            "http_code": exc.response.status_code,
            "normalized_metadata": {"report": report_name, "endpoint": url, "request_id": request_id},
        }
    except (httpx.RequestError, TimeoutError, json.JSONDecodeError) as exc:
        return {
            "status": "error",
            "message": f"Bilas report could not be retrieved: {type(exc).__name__}: {exc}",
            "normalized_metadata": {"report": report_name, "endpoint": url, "request_id": request_id},
        }


async def report_tool(report_name, tgl_awal, tgl_akhir):
    """Thin wrapper that catches validation errors and serialises to JSON."""
    try:
        result = await post_report(report_name, tgl_awal, tgl_akhir)
    except (PermissionError, ValueError) as exc:
        result = {"status": "error", "message": str(exc)}
    return json.dumps(result, indent=2, ensure_ascii=False)


def summarize_ringkasan(api_response):
    """Pull the per-outlet summary block out of the Ringkasan Outlet response.

    The dashboard's Transaksi tab and many KPI cards read from this block.
    Keys surfaced: omzet, pendapatan, paket, pemasukan, pengeluaran, piutang,
    kasbon, penjualan, pembulatan, trxmasuk, trxpaket, trxbatal, satuan,
    meter, kiloan, emoney, trxemoney, trxpenjualan, trxpembelian, hutang,
    labarugi, selfservice, trxselfservice, biaya_merchant. The graph list
    is the daily Keuangan chart, kept verbatim.
    """
    summary_keys = {
        "omzet", "pendapatan", "paket", "pemasukan", "pengeluaran", "piutang",
        "kasbon", "penjualan", "pembulatan", "trxmasuk", "trxpaket", "trxbatal",
        "satuan", "meter", "kiloan", "emoney", "trxemoney", "trxpenjualan",
        "trxpembelian", "hutang", "labarugi", "selfservice", "trxselfservice",
        "biaya_merchant",
    }
    try:
        results = api_response.get("result") or []
    except AttributeError:
        return None
    if not results:
        return None
    first = results[0] if isinstance(results, list) else results
    if not isinstance(first, dict):
        return None

    candidates = []
    if "semua" in first:
        candidates.append(first["semua"])
    for k, v in first.items():
        if k == "semua":
            continue
        if isinstance(v, list) and v and isinstance(v[0], dict) and any(x in v[0] for x in summary_keys):
            candidates.append(v)
    for cand in candidates:
        if not cand:
            continue
        row = cand[0] if isinstance(cand, list) and cand else (cand if isinstance(cand, dict) else None)
        if not isinstance(row, dict):
            continue
        summary = {k: row[k] for k in summary_keys if k in row}
        summary["graph"] = row.get("graph", [])
        return summary
    return None


# ── Production pipeline helpers ────────────────────────────────────────────

def production_response(resp_text):
    """Parse a production update response that may be empty or 'undefined'."""
    raw = resp_text.strip()
    if not raw or raw == "undefined":
        return {"status": "success", "message": "Server acknowledged with empty body"}
    try:
        return json.loads(raw)
    except Exception:
        return {"status": "processed", "raw_response": raw}


async def fetch_order_detail(transaction_id, headers):
    """Fetch the full order detail for a transaction."""
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{APIWEB_BASE}/web/transaksi/reguler/detail",
            headers=headers,
            json={"id": transaction_id},
        )
        raw = resp.text.strip()
    if not raw or raw == "undefined":
        return {}
    return json.loads(raw).get("result", {}) or {}


def verify_production_items(order, expected_items):
    """Verify that production stage changes persisted for each expected item."""
    actual = (order or {}).get("detail", [])
    rows = []
    for expected in expected_items:
        found = next(
            (item for item in actual if expected.get("uid") and
             (item.get("uid") == expected["uid"] or item.get("original_uid") == expected["uid"])),
            None,
        )
        if found is None and 0 < expected["item_index"] <= len(actual):
            found = actual[expected["item_index"] - 1]
        observed = found.get("proses") if found else None
        rows.append({
            "item_index": expected["item_index"],
            "item_name": expected["item_name"],
            "uid": expected.get("uid"),
            "expected_stage": expected["target_stage"],
            "observed_stage": observed,
            "persisted": observed == expected["target_stage"],
        })
    return rows
