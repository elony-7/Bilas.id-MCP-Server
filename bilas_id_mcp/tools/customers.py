"""Bilas.id MCP Server — customer management tools."""
import json

import httpx

from ..server import mcp
from ..constants import APIWEB_BASE
from ..auth import get_valid_headers
from ..helpers import validate_report_dates, post_report


@mcp.tool()
async def bilas_list_customers(
    search_query: str = "",
    limit: int = 20,
    registered_after: str = "",
    registered_before: str = "",
) -> str:
    """List and search registered customer profiles (Fast native directory with name, phone, email, gender, registration date).

    Args:
        search_query: Optional search filter by name, phone, or email
        limit: Max results to return (default: 20)
        registered_after: Optional. Only include customers registered on or after this date (YYYY/MM/DD)
        registered_before: Optional. Only include customers registered on or before this date (YYYY/MM/DD)"""
    headers, st = await get_valid_headers()
    outlet_id = st.get("outlet_id", "")

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{APIWEB_BASE}/web/pelanggan/list",
                headers=headers,
                json={"id": outlet_id},
            )
            raw_res = resp.json()
        customer_list = raw_res.get("result", [])

        # Filter if search_query is provided
        q = search_query.strip().lower()
        if q:
            filtered = [
                c for c in customer_list
                if q in str(c.get("nama", "")).lower()
                or q in str(c.get("hp", "")).lower()
                or q in str(c.get("email", "")).lower()
            ]
        else:
            filtered = customer_list

        # Date filter on tgl_register
        if registered_after or registered_before:
            try:
                start_str, end_str = validate_report_dates(
                    registered_after or "2000/01/01",
                    registered_before or "2099/12/31",
                )
            except ValueError as exc:
                return json.dumps({"status": "error", "message": str(exc)}, indent=2, ensure_ascii=False)

            def reg_in_range(c):
                reg = str(c.get("tgl_register", ""))
                if not reg:
                    return False
                date_part = reg[:10].replace("-", "/")
                return start_str <= date_part <= end_str

            filtered = [c for c in filtered if reg_in_range(c)]

        simplified = []
        for c in filtered[:limit]:
            simplified.append({
                "customer_id": c.get("id"),
                "name": c.get("nama"),
                "phone": c.get("hp"),
                "email": c.get("email") or "-",
                "gender": c.get("gender") or "-",
                "registered_at": c.get("tgl_register"),
                "address": c.get("alamat") or "-",
            })

        return json.dumps({
            "status": "success",
            "total_registered": len(customer_list),
            "matched_count": len(filtered),
            "customers": simplified,
        }, indent=2, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)}, indent=2)


@mcp.tool()
async def bilas_get_unique_customers(tgl_awal: str, tgl_akhir: str, limit: int = 100) -> str:
    """Unique customer analysis for a date range. Aggregates customers from paid transactions,
    active orders, and completed history, then enriches with registered customer profiles.
    Returns deduplicated list with transaction count, total amount, and order statuses per customer.
    READ-ONLY. Credentials auto-loaded from ~/.bilas_id/token_state.json.

    Args:
        tgl_awal: Start date in YYYY/MM/DD format
        tgl_akhir: End date in YYYY/MM/DD format
        limit: Maximum unique customers to return (default: 100)"""
    try:
        start_str, end_str = validate_report_dates(tgl_awal, tgl_akhir)
    except ValueError as exc:
        return json.dumps({"status": "error", "message": str(exc)}, indent=2, ensure_ascii=False)

    headers, st = await get_valid_headers()
    outlet_id = st.get("outlet_id", "")

    customers = {}

    def normalize_name(name):
        return str(name or "").strip().lower()

    def add_customer(name, phone, amount, status, order_id):
        key = normalize_name(name)
        if not key:
            return
        if key not in customers:
            customers[key] = {
                "name": str(name).strip(),
                "phone": str(phone or "").strip(),
                "tx_count": 0,
                "total_amount": 0,
                "statuses": set(),
                "order_ids": [],
            }
        c = customers[key]
        c["tx_count"] += 1
        try:
            c["total_amount"] += int(amount or 0)
        except (ValueError, TypeError):
            pass
        if status:
            c["statuses"].add(str(status))
        if order_id:
            c["order_ids"].append(order_id)
        if not c["phone"] and phone:
            c["phone"] = str(phone).strip()

    def order_in_range(order):
        wp = str(order.get("waktu_pesan", ""))
        if not wp:
            return False
        date_part = wp[:10].replace("-", "/")
        return start_str <= date_part <= end_str

    # 1. Source: pendapatan_transaksi report (paid transactions)
    try:
        report_result = await post_report("pendapatan_transaksi", tgl_awal, tgl_akhir)
        if report_result.get("status") == "success":
            api_data = report_result.get("api_response", {})
            results = api_data.get("result", [])
            if isinstance(results, list):
                for row in results:
                    if isinstance(row, dict):
                        add_customer(
                            row.get("nama_pelanggan", ""),
                            row.get("hp", ""),
                            row.get("total_tagihan", 0) or row.get("total_harga", 0),
                            "Paid",
                            row.get("id", ""),
                        )
    except Exception:
        pass

    # 2. Source: Active orders (/all)
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(
                f"{APIWEB_BASE}/web/transaksi/reguler/all",
                params={"id": outlet_id, "page": 1, "limit": 500},
                headers=headers,
            )
            res = resp.json()
        for o in res.get("result", {}).get("list", []):
            if order_in_range(o):
                add_customer(
                    o.get("nama_pelanggan", ""),
                    o.get("hp", ""),
                    o.get("total_tagihan", 0) or o.get("total_harga", 0),
                    o.get("status_pengerjaan", ""),
                    o.get("id", ""),
                )
    except Exception:
        pass

    # 3. Source: Completed/history orders (/riwayat)
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(
                f"{APIWEB_BASE}/web/transaksi/reguler/riwayat",
                params={"id": outlet_id, "page": 1, "limit": 500},
                headers=headers,
            )
            res = resp.json()
        history = res.get("result", [])
        if isinstance(history, list):
            for o in history:
                if order_in_range(o):
                    add_customer(
                        o.get("nama_pelanggan", ""),
                        o.get("hp", ""),
                        o.get("total_tagihan", 0) or o.get("total_harga", 0),
                        o.get("status_pengerjaan", ""),
                        o.get("id", ""),
                    )
    except Exception:
        pass

    # 4. Enrich from customer registry
    registered_lookup = {}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{APIWEB_BASE}/web/pelanggan/list",
                headers=headers,
                json={"id": outlet_id},
            )
            raw_res = resp.json()
        for c in raw_res.get("result", []):
            key = normalize_name(c.get("nama", ""))
            if key:
                registered_lookup[key] = {
                    "customer_id": c.get("id"),
                    "registered_at": c.get("tgl_register"),
                    "email": c.get("email") or "-",
                    "phone": c.get("hp", ""),
                }
    except Exception:
        pass

    # Build output
    output_list = []
    for key, data in sorted(customers.items(), key=lambda x: x[1]["total_amount"], reverse=True):
        entry = {
            "name": data["name"],
            "phone": data["phone"],
            "transaction_count": data["tx_count"],
            "total_amount": data["total_amount"],
            "order_statuses": sorted(data["statuses"]),
        }
        reg = registered_lookup.get(key)
        if reg:
            entry["is_registered"] = True
            entry["customer_id"] = reg["customer_id"]
            entry["registered_at"] = reg["registered_at"]
            if not entry["phone"] and reg["phone"]:
                entry["phone"] = reg["phone"]
        else:
            entry["is_registered"] = False
        output_list.append(entry)

    output_list = output_list[:limit]

    return json.dumps({
        "status": "success",
        "period": {"tgl_awal": start_str, "tgl_akhir": end_str},
        "unique_customer_count": len(customers),
        "returned_count": len(output_list),
        "customers": output_list,
        "data_sources": [
            "pendapatan_transaksi (paid transaction report)",
            "/web/transaksi/reguler/all (active orders)",
            "/web/transaksi/reguler/riwayat (completed history)",
            "/web/pelanggan/list (customer registry enrichment)",
        ],
    }, indent=2, ensure_ascii=False)
