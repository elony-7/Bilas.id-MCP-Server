"""Bilas.id MCP Server — financial reports, cashbox accounting, and expense management."""
import json
import uuid

import httpx

from ..server import mcp
from ..constants import ARUSKAS_NERACA_URL, APIWEB_BASE
from ..auth import get_valid_headers, jwt_decode_payload
from ..helpers import validate_report_dates, post_report, report_tool, summarize_ringkasan


# ── Ringkasan Outlet (special handling for summary extraction) ─────────────

@mcp.tool()
async def bilas_get_ringkasan_outlet(tgl_awal: str, tgl_akhir: str) -> str:
    """Ringkasan Outlet summary report; dates use YYYY/MM/DD.

    Returns the per-outlet KPI summary block (omzet, pendapatan, kiloan in KG,
    satuan in pieces, meter, trxmasuk, trxemoney, etc.) at the top of the
    response so the dashboard's Keuangan and Transaksi KPI cards can be read
    without walking the raw payload. The full Bilas response is preserved
    under `api_response` for traceability.
    """
    try:
        result = await post_report("ringkasan_outlet", tgl_awal, tgl_akhir)
    except (PermissionError, ValueError) as exc:
        result = {"status": "error", "message": str(exc)}
    if result.get("status") == "success":
        summary = summarize_ringkasan(result.get("api_response", {}))
        if summary:
            result = {"status": "success", "summary": summary, **result}
    return json.dumps(result, indent=2, ensure_ascii=False)


# ── Standard report tools (thin wrappers over report_tool) ────────────────

@mcp.tool()
async def bilas_get_pendapatan_transaksi(tgl_awal: str, tgl_akhir: str) -> str:
    """Read-only Pendapatan Transaksi/Omzet report; dates use YYYY/MM/DD. Returns raw response and metadata."""
    return await report_tool("pendapatan_transaksi", tgl_awal, tgl_akhir)


@mcp.tool()
async def bilas_get_topup_paket(tgl_awal: str, tgl_akhir: str) -> str:
    """Read-only Topup Paket report; dates use YYYY/MM/DD. Returns raw response and metadata."""
    return await report_tool("topup_paket", tgl_awal, tgl_akhir)


@mcp.tool()
async def bilas_get_topup_deposit(tgl_awal: str, tgl_akhir: str) -> str:
    """Read-only Topup Deposit report; dates use YYYY/MM/DD. Returns raw response and metadata."""
    return await report_tool("topup_deposit", tgl_awal, tgl_akhir)


@mcp.tool()
async def bilas_get_self_service_income(tgl_awal: str, tgl_akhir: str) -> str:
    """Read-only Self-service income report; dates use YYYY/MM/DD. Returns raw response and metadata."""
    return await report_tool("self_service_income", tgl_awal, tgl_akhir)


@mcp.tool()
async def bilas_get_other_income(tgl_awal: str, tgl_akhir: str) -> str:
    """Read-only Other income report; dates use YYYY/MM/DD. Returns raw response and metadata."""
    return await report_tool("other_income", tgl_awal, tgl_akhir)


@mcp.tool()
async def bilas_get_piutang(tgl_awal: str, tgl_akhir: str) -> str:
    """Read-only Piutang report; dates use YYYY/MM/DD. Returns raw response and metadata."""
    return await report_tool("piutang", tgl_awal, tgl_akhir)


@mcp.tool()
async def bilas_get_pembulatan(tgl_awal: str, tgl_akhir: str) -> str:
    """Read-only Pembulatan report; dates use YYYY/MM/DD. Returns raw response and metadata."""
    return await report_tool("pembulatan", tgl_awal, tgl_akhir)


@mcp.tool()
async def bilas_get_merchant_fees(tgl_awal: str, tgl_akhir: str) -> str:
    """Read-only Merchant fees report; dates use YYYY/MM/DD. Returns raw response and metadata."""
    return await report_tool("merchant_fees", tgl_awal, tgl_akhir)


@mcp.tool()
async def bilas_get_customer_growth(tgl_awal: str, tgl_akhir: str) -> str:
    """Read-only Customer growth report; dates use YYYY/MM/DD. Returns raw response and metadata."""
    return await report_tool("customer_growth", tgl_awal, tgl_akhir)


@mcp.tool()
async def bilas_get_top_customers(tgl_awal: str, tgl_akhir: str) -> str:
    """Read-only Top customers report; dates use YYYY/MM/DD. Returns raw response and metadata."""
    return await report_tool("top_customers", tgl_awal, tgl_akhir)


@mcp.tool()
async def bilas_get_package_quota(tgl_awal: str, tgl_akhir: str) -> str:
    """Read-only Package quota report; dates use YYYY/MM/DD. Returns raw response and metadata."""
    return await report_tool("package_quota", tgl_awal, tgl_akhir)


@mcp.tool()
async def bilas_get_deposit_balance(tgl_awal: str, tgl_akhir: str) -> str:
    """Read-only Deposit balance report; dates use YYYY/MM/DD. Returns raw response and metadata."""
    return await report_tool("deposit_balance", tgl_awal, tgl_akhir)


@mcp.tool()
async def bilas_get_kasbon_history(tgl_awal: str, tgl_akhir: str) -> str:
    """Read-only Kasbon history report; dates use YYYY/MM/DD. Returns raw response and metadata."""
    return await report_tool("kasbon_history", tgl_awal, tgl_akhir)


# ── Cashbox accounting ────────────────────────────────────────────────────

@mcp.tool()
async def bilas_get_cashbox_report(tgl_awal: str, tgl_akhir: str) -> str:
    """Return the dashboard Cashbox-tab table for a date range.

    Bilas calculates each cashbox's range-specific opening and closing balance
    server-side. This uses ``aruskasneraca`` rather than reconstructing rows
    from transaction-level Arus Kas data.

    The dashboard's full request body (``pemilik``, ``user``, ``mode``, ``tipe``,
    ``send_data``) is required — sending the minimal body silently zeroes out
    the stored opening baseline that the dashboard Cashbox tab shows.
    """
    try:
        start, end = validate_report_dates(tgl_awal, tgl_akhir)
    except ValueError as exc:
        return json.dumps({"status": "error", "message": str(exc)}, indent=2, ensure_ascii=False)

    headers, st = await get_valid_headers()
    outlet_id = st["outlet_id"]
    user_id = st.get("user_id", "")
    body = {
        "req_id": str(uuid.uuid4()),
        "tgl_awal": start, "tgl_akhir": end,
        "id": outlet_id, "pemilik": user_id,
        "dibuat_tgl": "2024-01-01T00:00:00.000Z",
        "send_data": False, "tipe": "semua",
        "user": f"web-{user_id}", "mode": "all list",
    }

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(ARUSKAS_NERACA_URL, headers=headers, json=body)
            response = resp.json()
        rows = response.get("result2", [])
        normalized = []
        for row in rows:
            normalized.append({
                "cashbox": row.get("cashbox", ""),
                "saldo_awal": int(row.get("saldo_sebelum", 0) or 0),
                "debit": int(row.get("total_debit", 0) or 0),
                "kredit": int(row.get("total_kredit", 0) or 0),
                "saldo_akhir": int(row.get("saldo_sesudah", 0) or 0),
            })
        total = {
            "cashbox": "TOTAL",
            "saldo_awal": sum(r["saldo_awal"] for r in normalized),
            "debit": sum(r["debit"] for r in normalized),
            "kredit": sum(r["kredit"] for r in normalized),
            "saldo_akhir": sum(r["saldo_akhir"] for r in normalized),
        }
        return json.dumps({
            "status": "success", "tgl_awal": start, "tgl_akhir": end,
            "rows": normalized, "summary": total, "api_response": response,
        }, indent=2, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)}, indent=2, ensure_ascii=False)


# ── Financial categories ──────────────────────────────────────────────────

@mcp.tool()
async def bilas_get_financial_categories() -> str:
    """List all financial categories (pengeluaran/pemasukan) configured for this outlet.
    Returns category names, types, and active status. Use these exact category names when calling bilas_add_expense.
    READ-ONLY. Credentials auto-loaded from ~/.bilas_id/token_state.json."""
    headers, st = await get_valid_headers()
    outlet_id = st["outlet_id"]
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{APIWEB_BASE}/web/keuangan/kategori",
                params={"id": outlet_id},
                headers=headers,
            )
            return json.dumps(resp.json(), indent=2, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)}, indent=2)


# ── Expense management (write operations) ─────────────────────────────────

@mcp.tool()
async def bilas_add_expense(cashbox: str, category: str, amount: int, description: str, date_mm_dd_yyyy: str) -> str:
    """Record a new operational expense (Pengeluaran) in the outlet financial ledger.
    WRITE OPERATION — use with care. Verify category names via bilas_get_financial_categories first.
    Credentials auto-loaded from ~/.bilas_id/token_state.json.

    Args:
        cashbox: Payment method exactly as configured (e.g. "Tunai", "BCA", "QRIS", "Dana")
        category: Expense category exactly as returned by bilas_get_financial_categories (e.g. "Biaya Listrik")
        amount: Amount in Rupiah as integer (e.g. 50000 for Rp50,000)
        description: Human-readable note (e.g. "Bayar listrik bulan Agustus")
        date_mm_dd_yyyy: Transaction date in MM/DD/YYYY format (e.g. "08/30/2026")"""
    headers, st = await get_valid_headers()
    outlet_id = st["outlet_id"]
    user_id = st.get("user_id") or jwt_decode_payload(st.get("jwt")).get("id")

    payload = {
        "id": outlet_id,
        "zone": "Asia/Jakarta",
        "dibuat_tgl": date_mm_dd_yyyy,
        "dataKeuangan": {
            "waktu": date_mm_dd_yyyy,
            "cashbox": cashbox,
            "kategori": category,
            "jumlah": amount,
            "keterangan": description,
            "jenis": "Pengeluaran",
            "id_operator": user_id,
        },
    }
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{APIWEB_BASE}/web/keuangan/koreksi-keuangan/create",
                headers=headers,
                json=payload,
            )
            return json.dumps(resp.json(), indent=2, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)}, indent=2)


@mcp.tool()
async def bilas_delete_expense(keuangan_id: str, date_mm_dd_yyyy: str) -> str:
    """Soft-delete a financial record by its keuanganId.
    WRITE OPERATION — use with care. The keuanganId is found in bilas_add_expense responses or the web dashboard.
    Credentials auto-loaded from ~/.bilas_id/token_state.json.

    Args:
        keuangan_id: Firestore document ID of the financial entry to delete
        date_mm_dd_yyyy: Date of the entry in MM/DD/YYYY format"""
    headers, st = await get_valid_headers()
    outlet_id = st["outlet_id"]
    payload = {
        "id": outlet_id,
        "outletId": outlet_id,
        "zone": "Asia/Jakarta",
        "dibuat_tgl": date_mm_dd_yyyy,
        "keuanganId": keuangan_id,
    }
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.put(
                f"{APIWEB_BASE}/web/keuangan/koreksi-keuangan/delete",
                headers=headers,
                json=payload,
            )
            return json.dumps(resp.json(), indent=2, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)}, indent=2)
