"""Bilas.id MCP Server — order creation, detail lookup, and listing tools."""
import json
import time

import httpx

from ..server import mcp
from ..constants import APIWEB_BASE
from ..auth import get_valid_headers, jwt_decode_payload


@mcp.tool()
async def bilas_create_order(
    customer_name: str,
    phone: str,
    service_items: str,
    total_amount: int,
    payment_method: str = "Tunai",
    notes: str = "",
) -> str:
    """Create a new regular laundry transaction/order."""
    headers, st = await get_valid_headers()
    outlet_id = st.get("outlet_id", "")
    user_id = st.get("user_id") or jwt_decode_payload(st.get("jwt")).get("id")

    order_payload = {
        "id": outlet_id,
        "outletId": outlet_id,
        "nama_pelanggan": customer_name,
        "hp": phone,
        "keterangan": f"{service_items} | {notes}".strip(" |"),
        "total_harga": total_amount,
        "total_tagihan": total_amount,
        "metode_pembayaran": payment_method,
        "status_pengerjaan": "Antrian",
        "status_pembayaran": "Belum Lunas",
        "id_operator": user_id,
        "zone": "Asia/Jakarta",
        "waktu_antrian": time.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
    }

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{APIWEB_BASE}/web/transaksi/reguler/create",
                headers=headers,
                json=order_payload,
            )
            return json.dumps(resp.json(), indent=2, ensure_ascii=False)
    except httpx.HTTPStatusError as e:
        return json.dumps({
            "status": "processed",
            "message": f"Order creation request submitted ({e.response.status_code})",
            "order": order_payload,
            "backend_response": e.response.text,
        }, indent=2, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)}, indent=2)


@mcp.tool()
async def bilas_get_order_details(transaction_id: str) -> str:
    """Get comprehensive order breakdown including full Detail Layanan (Service name, package, quantity/weight in Kg/Satuan, unit price, notes, and individual step status)."""
    headers, st = await get_valid_headers()
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{APIWEB_BASE}/web/transaksi/reguler/detail",
                headers=headers,
                json={"id": transaction_id},
            )
            raw_res = resp.json()
        res = raw_res.get("result", {})
        if not res:
            return json.dumps({"status": "not_found", "message": "Order/Transaction not found"}, indent=2)

        items_summary = []
        for it in res.get("detail", []):
            nama_layanan_full = f"{it.get('nama_layanan', '')} {it.get('nama_paket', '')}".strip()
            qty_val = it.get("qty", 0)
            satuan_val = it.get("satuan", "")
            qty_str = f"{qty_val} {satuan_val}".strip()

            item = {
                "nama_layanan": nama_layanan_full,
                "status_pengerjaan": it.get("proses") or res.get("status_pengerjaan", "-"),
                "qty": qty_str,
                "harga_satuan": int(it.get("biaya", 0)) if str(it.get("biaya", 0)).isdigit() else it.get("biaya", 0),
                "total_harga": it.get("total_detail", 0),
                "satuan": satuan_val,
                "image_url": it.get("img_layanan", ""),
            }
            if it.get("keterangan"):
                item["keterangan"] = it["keterangan"]
            items_summary.append(item)

        # Promo / discount context
        promo_raw = res.get("promo") or {}
        promo_info = None
        if isinstance(promo_raw, dict) and promo_raw.get("nama_promo"):
            promo_info = {
                "nama": promo_raw.get("nama_promo", ""),
                "tipe": promo_raw.get("tipe_promo", ""),
                "nilai": promo_raw.get("nilai_promo", 0),
                "jenis": promo_raw.get("jenis_promo", ""),
            }

        # Payment breakdown
        pay = res.get("detail_pembayaran") or {}
        total_harga = res.get("total_harga", 0)
        total_potongan = res.get("total_potongan", 0)
        total_tagihan = res.get("total_tagihan") or pay.get("totalharga") or (total_harga - total_potongan)

        output = {
            "status": "success",
            "id": res.get("id"),
            "no_nota": res.get("no_nota"),
            "nama_pelanggan": res.get("nama_pelanggan"),
            "hp": res.get("hp"),
            "parfum": res.get("parfum", "-"),
            "status_pengerjaan": res.get("status_pengerjaan"),
            "status_pembayaran": "Lunas" if res.get("status_pembayaran") or res.get("lunas") else "Belum Lunas",
            "total_harga": total_harga,
            "total_potongan": total_potongan,
            "total_tagihan": total_tagihan,
            "total_dibayar": res.get("total_dibayar", 0),
            "sisa_tagihan": pay.get("piutang", total_tagihan - res.get("total_dibayar", 0)),
            "waktu_antrian": res.get("waktu_antrian"),
            "waktu_estimasi": res.get("waktu_estimasi"),
            "detail_layanan": items_summary,
        }
        if promo_info:
            output["promo"] = promo_info
        if res.get("metode_pembayaran"):
            output["metode_pembayaran"] = res["metode_pembayaran"]
        return json.dumps(output, indent=2, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)}, indent=2)


@mcp.tool()
async def bilas_list_orders_by_status(status_pengerjaan: str = "Antrian", page: int = 1, limit: int = 20) -> str:
    """List orders filtered by production status (Antrian, Proses, Setrika, Siap Ambil, Selesai, or 'all')."""
    headers, st = await get_valid_headers()
    outlet_id = st.get("outlet_id", "")
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{APIWEB_BASE}/web/transaksi/reguler/all",
                params={"id": outlet_id, "page": page, "limit": limit},
                headers=headers,
            )
            raw_res = resp.json()
        tx_list = raw_res.get("result", {}).get("list", [])

        if status_pengerjaan and status_pengerjaan.lower() != "all":
            filtered = [tx for tx in tx_list if str(tx.get("status_pengerjaan", "")).lower() == status_pengerjaan.lower()]
        else:
            filtered = tx_list

        simplified = []
        for tx in filtered:
            simplified.append({
                "id": tx.get("id"),
                "no_nota": tx.get("no_nota"),
                "nama_pelanggan": tx.get("nama_pelanggan"),
                "hp": tx.get("hp"),
                "parfum": tx.get("parfum", "-"),
                "status_pengerjaan": tx.get("status_pengerjaan"),
                "status_pembayaran": "Lunas" if tx.get("status_pembayaran") else "Belum Lunas",
                "total_tagihan": tx.get("total_tagihan", tx.get("total_harga", 0)),
                "waktu_antrian": tx.get("waktu_antrian"),
            })

        return json.dumps({
            "status": "success",
            "filter_status": status_pengerjaan,
            "count": len(simplified),
            "orders": simplified,
        }, indent=2, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)}, indent=2)
