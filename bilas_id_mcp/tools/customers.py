"""Bilas.id MCP Server — customer management tools."""
import json

import httpx

from ..server import mcp
from ..constants import APIWEB_BASE
from ..auth import get_valid_headers


@mcp.tool()
async def bilas_list_customers(search_query: str = "", limit: int = 20) -> str:
    """List and search registered customer profiles (Fast native directory with name, phone, email, gender, registration date)."""
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
