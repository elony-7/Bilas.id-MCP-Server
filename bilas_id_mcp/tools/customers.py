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
    """Unique customer analysis and Pertumbuhan Pelanggan (New vs. Returning) for any date range.
    Accurately counts every customer who had transactions (active, completed, or picked up)
    by combining server-side top customer reports, active pipeline orders, and customer registry.

    Answers:
    1. Total unique customers who ordered in the period
    2. Pelanggan Baru (New customers registered in this period)
    3. Pelanggan Lama (Returning customers registered prior to this period)
    4. Total all-time registered customers
    5. Itemized breakdown per customer (spend, orders, phone, statuses, registration date)

    READ-ONLY. Credentials auto-loaded from ~/.bilas_id/token_state.json.

    Args:
        tgl_awal: Start date in YYYY/MM/DD format (e.g. '2026/08/01')
        tgl_akhir: End date in YYYY/MM/DD format (e.g. '2026/08/31')
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

    def add_customer(name, phone, amount, status, order_id=None, no_nota=None):
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
                "orders": [],
            }
        c = customers[key]
        c["tx_count"] += 1
        try:
            c["total_amount"] += int(amount or 0)
        except (ValueError, TypeError):
            pass
        if status:
            c["statuses"].add(str(status))
        if no_nota or order_id:
            c["orders"].append({
                "no_nota": no_nota or "-",
                "order_id": order_id or "-",
                "status": status or "-",
                "amount": int(amount or 0),
            })
        if not c["phone"] and phone:
            c["phone"] = str(phone).strip()

    def order_in_range(order):
        wp = str(order.get("waktu_pesan", ""))
        if not wp:
            return False
        date_part = wp[:10].replace("-", "/")
        return start_str <= date_part <= end_str

    # 1. Primary Source: top_customers report (comprehensive server-side monthly aggregation)
    try:
        top_result = await post_report("top_customers", tgl_awal, tgl_akhir)
        if top_result.get("status") == "success":
            top_list = top_result.get("api_response", {}).get("result", [])
            if isinstance(top_list, list):
                for row in top_list:
                    cust_name = row.get("nama", "")
                    cust_phone = row.get("hp", "")
                    details = row.get("detail", [])
                    if details:
                        for item in details:
                            add_customer(
                                name=cust_name or item.get("nama_pelanggan", ""),
                                phone=cust_phone or item.get("hp", ""),
                                amount=item.get("total_harga", 0) or item.get("total_tagihan", 0),
                                status=item.get("status_pengerjaan", ""),
                                order_id=item.get("id", ""),
                                no_nota=item.get("no_nota", ""),
                            )
                    else:
                        add_customer(
                            name=cust_name,
                            phone=cust_phone,
                            amount=row.get("total_harga", 0) or row.get("total_tagihan", 0),
                            status="Completed",
                            order_id=row.get("id", ""),
                        )
    except Exception:
        pass

    # 2. Secondary Source: Active in-flight orders (/all) to capture unclosed recent transactions
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
                cust_key = normalize_name(o.get("nama_pelanggan", ""))
                existing_orders = [ord_item.get("order_id") for ord_item in customers.get(cust_key, {}).get("orders", [])]
                if o.get("id") not in existing_orders:
                    add_customer(
                        name=o.get("nama_pelanggan", ""),
                        phone=o.get("hp", ""),
                        amount=o.get("total_tagihan", 0) or o.get("total_harga", 0),
                        status=o.get("status_pengerjaan", ""),
                        order_id=o.get("id", ""),
                        no_nota=o.get("no_nota", ""),
                    )
    except Exception:
        pass

    # 3. Enrich & Classify from customer profile registry (/web/pelanggan/list)
    all_registered_list = []
    registered_lookup = {}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{APIWEB_BASE}/web/pelanggan/list",
                headers=headers,
                json={"id": outlet_id},
            )
            raw_res = resp.json()
        all_registered_list = raw_res.get("result", [])
        for c in all_registered_list:
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

    # Calculate Pelanggan Baru vs Pelanggan Lama metrics
    new_customers_count = 0
    returning_customers_count = 0

    output_list = []
    for key, data in sorted(customers.items(), key=lambda x: x[1]["total_amount"], reverse=True):
        reg = registered_lookup.get(key)
        reg_at = reg.get("registered_at") if reg else None
        reg_norm = reg_at[:10].replace("-", "/") if reg_at else ""

        if reg_norm and reg_norm >= start_str:
            is_new = True
            customer_type = "Baru (New)"
            new_customers_count += 1
        else:
            is_new = False
            customer_type = "Lama (Returning)"
            returning_customers_count += 1

        entry = {
            "name": data["name"],
            "phone": data["phone"] or (reg.get("phone") if reg else "-"),
            "customer_type": customer_type,
            "is_new": is_new,
            "transaction_count": data["tx_count"],
            "total_amount": data["total_amount"],
            "order_statuses": sorted(data["statuses"]),
            "is_registered": bool(reg),
            "customer_id": reg.get("customer_id") if reg else "-",
            "registered_at": reg_at or "-",
        }
        output_list.append(entry)

    paged_customers = output_list[:limit]

    return json.dumps({
        "status": "success",
        "period": {"tgl_awal": start_str, "tgl_akhir": end_str},
        "summary": {
            "total_transacting_customers": len(customers),
            "pelanggan_baru_count": new_customers_count,
            "pelanggan_lama_count": returning_customers_count,
            "all_time_registered_customers": len(all_registered_list),
        },
        "returned_count": len(paged_customers),
        "customers": paged_customers,
        "data_sources": [
            "toppelanggan (server-side monthly transacting aggregation)",
            "/web/transaksi/reguler/all (active pipeline verification)",
            "/web/pelanggan/list (registered profile & tgl_register enrichment)",
        ],
    }, indent=2, ensure_ascii=False)
