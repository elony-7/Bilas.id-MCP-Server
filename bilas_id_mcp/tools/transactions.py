"""Bilas.id MCP Server — transaction search, production pipeline, and order status tools."""
import json
import time
import urllib.parse

import httpx

from ..server import mcp
from ..constants import APIWEB_BASE
from ..auth import get_valid_headers, jwt_decode_payload
from ..helpers import fetch_order_detail, verify_production_items, production_response, validate_report_dates


@mcp.tool()
async def bilas_search_invoice(
    query: str = "",
    page: int = 1,
    limit: int = 20,
    tgl_awal: str = "",
    tgl_akhir: str = "",
) -> str:
    """Search customer orders/invoices by nota number, customer name, or phone number.
    Searches BOTH active orders (Antrian/Proses/Siap Ambil) AND completed/picked-up
    history (riwayat), so orders at any stage are found. Pass empty query for recent orders.
    READ-ONLY. Credentials auto-loaded from ~/.bilas_id/token_state.json.

    Args:
        query: Search term — nota number (TRX/...), customer name, or phone. Empty string = all recent.
        page: Page number for pagination (default: 1)
        limit: Results per page (default: 20, max recommended: 50)
        tgl_awal: Optional start date filter in YYYY/MM/DD format. Orders before this date are excluded.
        tgl_akhir: Optional end date filter in YYYY/MM/DD format. Orders after this date are excluded."""
    headers, st = await get_valid_headers()
    outlet_id = st["outlet_id"]
    q = urllib.parse.quote(query, safe="")

    all_orders = []
    seen_ids = set()

    # 1. Active orders (/all) — has server-side search
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{APIWEB_BASE}/web/transaksi/reguler/all",
                params={"id": outlet_id, "page": 1, "limit": 200, "search": q},
                headers=headers,
            )
            res = resp.json()
        for o in res.get("result", {}).get("list", []):
            oid = o.get("id")
            if oid and oid not in seen_ids:
                seen_ids.add(oid)
                all_orders.append(o)
    except Exception:
        pass

    # 2. Completed/history orders (/riwayat) — no server-side search, filter client-side
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
            ql = query.strip().lower()
            for o in history:
                oid = o.get("id")
                if oid in seen_ids:
                    continue
                if ql:
                    match = (
                        ql in str(o.get("no_nota", "")).lower()
                        or ql in str(o.get("nama_pelanggan", "")).lower()
                        or ql in str(o.get("hp", "")).lower()
                    )
                    if not match:
                        continue
                seen_ids.add(oid)
                all_orders.append(o)
    except Exception:
        pass

    # Date filtering (client-side, applied after merge)
    if tgl_awal or tgl_akhir:
        try:
            start_str, end_str = validate_report_dates(
                tgl_awal or "2000/01/01",
                tgl_akhir or "2099/12/31",
            )
        except ValueError as exc:
            return json.dumps({"status": "error", "message": str(exc)}, indent=2, ensure_ascii=False)

        def in_range(order):
            wp = str(order.get("waktu_pesan", ""))
            if not wp:
                return False
            date_part = wp[:10].replace("-", "/")
            return start_str <= date_part <= end_str

        all_orders = [o for o in all_orders if in_range(o)]

    # Sort by waktu_pesan descending (most recent first)
    all_orders.sort(key=lambda o: o.get("waktu_pesan", ""), reverse=True)

    # Paginate
    total = len(all_orders)
    start = (page - 1) * limit
    page_orders = all_orders[start: start + limit]

    return json.dumps({
        "value": "1",
        "message": "Success",
        "result": {"list": page_orders},
        "pagination": {
            "total": total, "page": page, "limit": limit,
            "total_pages": (total + limit - 1) // limit if limit else 1,
        },
        "source_endpoints": [
            "/web/transaksi/reguler/all (active orders)",
            "/web/transaksi/reguler/riwayat (completed history)",
        ],
    }, indent=2, ensure_ascii=False)


@mcp.tool()
async def bilas_get_production_summary() -> str:
    """Get real-time production pipeline stage counters for the outlet.
    Returns counts: antrian (queued), proses (in progress), siap ambil (ready pickup),
    siap antar (ready delivery), konfirmasi, validasi, penjemputan.
    READ-ONLY. Credentials auto-loaded from ~/.bilas_id/token_state.json."""
    headers, st = await get_valid_headers()
    outlet_id = st["outlet_id"]
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{APIWEB_BASE}/web/transaksi/reguler/all",
                params={"id": outlet_id, "page": 1, "limit": 1},
                headers=headers,
            )
            res = resp.json()
        counters = res.get("result", {}).get("counter", {})
        return json.dumps({"status": "success", "production_counters": counters}, indent=2, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)}, indent=2)


@mcp.tool()
async def bilas_update_order_status(
    transaction_id: str,
    status_pengerjaan: str,
    item_index: int = 0,
    item_name: str = "",
    operator_name: str = "Ele",
    machine_name: str = "",
    notes: str = "",
) -> str:
    """Update order or specific item production stage (Antrian, Pencucian, Pengeringan, Setrika, Siap Ambil, Selesai).
    Uses /web/transaksi/produksi/update endpoint with the full order object (dataTransaksi).
    Supports multi-service orders: specify `item_index` (1, 2...) or `item_name` to update a specific line item,
    or leave empty (0 / "") to update all applicable items in the order.
    Returns the API response; stage transitions are logged server-side by Bilas.
    """
    headers, st = await get_valid_headers()
    outlet_id = st.get("outlet_id", "")
    user_id = st.get("user_id") or jwt_decode_payload(st.get("jwt")).get("id")

    # 1. Fetch current order details
    try:
        raw_order = await fetch_order_detail(transaction_id, headers)
    except Exception:
        raw_order = {}

    target_stage = status_pengerjaan.strip()
    stage_norm = target_stage.lower()
    now_ts = time.strftime("%Y-%m-%dT%H:%M:%S.000+07:00")

    items = raw_order.get("detail", [])
    if not items:
        return json.dumps({"status": "error", "message": "Order not found or has no detail items"}, indent=2)

    updated_items = []
    expected_items = []
    target_url = f"{APIWEB_BASE}/web/transaksi/produksi/update"

    # Map stage name to the field prefix used in the detail item
    stage_to_field = {
        "cuci": ("dicuci", "waktu_cuci"),
        "pencucian": ("dicuci", "waktu_cuci"),
        "kering": ("dikeringkan", "waktu_kering"),
        "pengeringan": ("dikeringkan", "waktu_kering"),
        "setrika": ("disetrika", "waktu_setrika"),
        "ironing": ("disetrika", "waktu_setrika"),
        "ambil": ("diambilkan", "waktu_diambil"),
        "siap ambil": ("diambilkan", "waktu_diambil"),
        "selesai": ("diselesaikan", "waktu_selesai"),
        "finish": ("diselesaikan", "waktu_selesai"),
    }

    operator_field, time_field = stage_to_field.get(stage_norm, (None, None))
    if stage_norm in ("cuci", "pencucian"):
        target_stage = "Cuci"
    elif stage_norm in ("kering", "pengeringan"):
        target_stage = "Pengeringan"
    elif stage_norm in ("setrika", "ironing"):
        target_stage = "Setrika"
    elif stage_norm in ("ambil", "siap ambil"):
        target_stage = "Siap Ambil"
    elif stage_norm in ("selesai", "finish"):
        target_stage = "Selesai"

    for idx, item in enumerate(items, 1):
        # Filter if item_index or item_name specified
        if item_index > 0 and idx != item_index:
            continue
        if item_name and item_name.lower() not in (item.get("nama_layanan", "") + " " + item.get("nama_paket", "")).lower():
            continue

        joblist = str(item.get("joblist", "111"))
        nama_l = item.get("nama_layanan", "")
        nama_p = item.get("nama_paket", "")
        item_title = (nama_l + " " + nama_p).strip() or "Item #" + str(idx)

        # Check if requested stage applies to this item workflow
        if operator_field and "setrika" in stage_norm and joblist.endswith("0"):
            updated_items.append({
                "item_index": idx,
                "item_name": item_title,
                "status": "skipped",
                "message": "Service does not have an ironing step (joblist: " + joblist + "). Skipped.",
            })
            continue

        # Mutate the item in-place for the update
        if operator_field:
            item[operator_field] = user_id
            item[operator_field + "_nama"] = operator_name
        if time_field:
            item[time_field] = now_ts

        # Clear stations after the requested destination
        station_fields = [
            ("dicuci", "dicuci_nama"),
            ("dikeringkan", "dikeringkan_nama"),
            ("disetrika", "disetrika_nama"),
            ("diselesaikan", "diselesaikan_nama"),
            ("diambilkan", "diambilkan_nama"),
        ]
        destination_position = {
            "cuci": 1, "pencucian": 1, "kering": 2, "pengeringan": 2,
            "setrika": 3, "ironing": 3, "selesai": 4, "finish": 4,
            "ambil": 5, "siap ambil": 5,
        }.get(stage_norm)
        if destination_position:
            for position, (value_key, name_key) in enumerate(station_fields, 1):
                if position > destination_position:
                    item[value_key] = ""
                    item[name_key] = ""

        item["proses"] = target_stage
        item["keterangan"] = notes or item.get("keterangan", "")
        if machine_name:
            item["mesin"] = machine_name
        expected_items.append({
            "item_index": idx, "item_name": item_title,
            "uid": item.get("uid") or item.get("original_uid"),
            "target_stage": target_stage,
        })

    raw_order["update_date"] = now_ts

    attempted_items = [x for x in expected_items]
    if not attempted_items:
        return json.dumps({
            "status": "error",
            "message": "No applicable detail items were selected for update.",
            "items_targeted": updated_items,
        }, indent=2, ensure_ascii=False)

    api_responses = []
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            for expected in attempted_items:
                item = items[expected["item_index"] - 1]
                payload = {
                    "uid": expected.get("uid"),
                    "id_transaksi": transaction_id,
                    "id_paket": item.get("id_paket", ""),
                    "id_layanan": item.get("id_layanan", ""),
                    "proses": target_stage,
                    "dicuci": item.get("dicuci", ""),
                    "dicuci_nama": item.get("dicuci_nama", ""),
                    "dikeringkan": item.get("dikeringkan", ""),
                    "dikeringkan_nama": item.get("dikeringkan_nama", ""),
                    "disetrika": item.get("disetrika", ""),
                    "disetrika_nama": item.get("disetrika_nama", ""),
                    "diselesaikan": item.get("diselesaikan", ""),
                    "diselesaikan_nama": item.get("diselesaikan_nama", ""),
                    "diambilkan": item.get("diambilkan", ""),
                    "diambilkan_nama": item.get("diambilkan_nama", ""),
                    "waktu_cuci": now_ts if stage_norm in ("cuci", "pencucian") else "",
                    "waktu_kering": now_ts if stage_norm in ("kering", "pengeringan") else "",
                    "waktu_setrika": now_ts if stage_norm in ("setrika", "ironing") else "",
                    "waktu_selesai": now_ts if stage_norm in ("selesai", "finish") else "",
                    "waktu_diambil": now_ts if stage_norm in ("ambil", "siap ambil") else "",
                }
                resp = await client.post(target_url, headers=headers, json=payload)
                api_responses.append(production_response(resp.text))

        try:
            verified_order = await fetch_order_detail(transaction_id, headers)
            verification = verify_production_items(verified_order, attempted_items)
        except Exception as e:
            return json.dumps({
                "status": "verification_failed", "transaction_id": transaction_id,
                "target_stage": target_stage, "api_response": api_responses,
                "items_targeted": updated_items,
                "message": "API acknowledged the update, but verification failed: " + str(e),
            }, indent=2)

        persisted = sum(1 for row in verification if row["persisted"])
        final_status = "success" if persisted == len(verification) else "not_persisted" if persisted == 0 else "partial"
        return json.dumps({
            "status": final_status,
            "transaction_id": transaction_id,
            "target_stage": target_stage,
            "endpoint": target_url,
            "api_response": api_responses,
            "items_targeted": updated_items,
            "verification": verification,
            "note": "Success means the selected detail item was re-fetched and persisted.",
        }, indent=2, ensure_ascii=False)
    except httpx.HTTPStatusError as e:
        err_body = e.response.text
        try:
            parsed_err = json.loads(err_body)
        except Exception:
            parsed_err = err_body
        return json.dumps({
            "status": "error", "transaction_id": transaction_id,
            "target_stage": target_stage, "http_code": e.response.status_code,
            "error": parsed_err, "items_targeted": updated_items,
        }, indent=2, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e), "items_targeted": updated_items}, indent=2, ensure_ascii=False)


@mcp.tool()
async def bilas_revert_item_stage(
    transaction_id: str,
    status_pengerjaan: str,
    item_index: int = 0,
    item_name: str = "",
    operator_name: str = "Ele",
    notes: str = "",
) -> str:
    """Move exactly one detail item backward through Koreksi/Riwayat and verify persistence.
    Pass item_index or an unambiguous item_name. Forward destinations are rejected.
    """
    headers, st = await get_valid_headers()
    outlet_id = st.get("outlet_id", "")
    user_id = st.get("user_id") or jwt_decode_payload(st.get("jwt")).get("id")

    try:
        order = await fetch_order_detail(transaction_id, headers)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)}, indent=2)

    items = order.get("detail", [])
    needle = (item_name or "").strip().lower()
    selected = [
        (i, x) for i, x in enumerate(items, 1)
        if (not item_index or i == item_index)
        and (not needle or needle in ((x.get("nama_layanan", "") + " " + x.get("nama_paket", "")).lower()))
    ]
    if not item_index and not needle:
        return json.dumps({"status": "error", "message": "Pass item_index or item_name for a backward correction."}, indent=2)
    if not selected:
        return json.dumps({"status": "error", "message": "No matching detail item found."}, indent=2)
    if len(selected) > 1:
        return json.dumps({"status": "error", "message": "Item name matched multiple detail rows; use item_index."}, indent=2)

    idx, item = selected[0]
    names = {
        "antrian": ("Antrian", 0), "cuci": ("Cuci", 1), "pencucian": ("Cuci", 1),
        "kering": ("Pengeringan", 2), "pengeringan": ("Pengeringan", 2),
        "setrika": ("Setrika", 3), "ironing": ("Setrika", 3),
        "selesai": ("Selesai", 4), "packing": ("Selesai", 4),
    }
    target = names.get((status_pengerjaan or "").strip().lower())
    current = names.get(str(item.get("proses", "")).strip().lower())
    if not target or not current:
        return json.dumps({"status": "error", "message": "Use a recognized earlier stage: Antrian, Cuci, Pengeringan, Setrika, or Selesai."}, indent=2)
    if target[1] >= current[1]:
        return json.dumps({
            "status": "error",
            "message": "This tool only moves backward; use bilas_update_order_status for forward transitions.",
            "current_stage": current[0], "requested_stage": target[0],
        }, indent=2)

    uid = item.get("uid") or item.get("original_uid")
    now_ts = time.strftime("%Y-%m-%dT%H:%M:%S.000+07:00")
    payload = {
        "uid": uid,
        "id_transaksi": transaction_id,
        "id_paket": item.get("id_paket", ""),
        "id_layanan": item.get("id_layanan", ""),
        "proses": target[0],
        "dicuci": item.get("dicuci", ""),
        "dicuci_nama": item.get("dicuci_nama", ""),
        "dikeringkan": item.get("dikeringkan", ""),
        "dikeringkan_nama": item.get("dikeringkan_nama", ""),
        "disetrika": item.get("disetrika", ""),
        "disetrika_nama": item.get("disetrika_nama", ""),
        "diselesaikan": item.get("diselesaikan", ""),
        "diselesaikan_nama": item.get("diselesaikan_nama", ""),
        "diambilkan": item.get("diambilkan", ""),
        "diambilkan_nama": item.get("diambilkan_nama", ""),
        "waktu_cuci": item.get("waktu_cuci", ""),
        "waktu_kering": item.get("waktu_kering", ""),
        "waktu_setrika": item.get("waktu_setrika", ""),
        "waktu_selesai": item.get("waktu_selesai", ""),
        "waktu_diambil": item.get("waktu_diambil", ""),
    }

    target_url = f"{APIWEB_BASE}/web/transaksi/produksi/update"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(target_url, headers=headers, json=payload)
            api = production_response(resp.text)
        verification = verify_production_items(
            await fetch_order_detail(transaction_id, headers),
            [{"item_index": idx, "item_name": item.get("nama_layanan", ""), "uid": uid, "target_stage": target[0]}],
        )
        return json.dumps({
            "status": "success" if verification[0]["persisted"] else "not_persisted",
            "transaction_id": transaction_id,
            "from_stage": current[0],
            "target_stage": target[0],
            "api_response": api,
            "verification": verification,
        }, indent=2, ensure_ascii=False)
    except httpx.HTTPStatusError as e:
        return json.dumps({
            "status": "error", "http_code": e.response.status_code,
            "error": e.response.text,
        }, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)}, indent=2)
