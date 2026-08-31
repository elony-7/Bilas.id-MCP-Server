"""Bilas.id MCP Server — MCP Resources.

Resources expose read-only data that clients can discover and subscribe to.
Unlike tools, resources use URI-based addressing and are meant for reference
data that doesn't require explicit agent invocation.
"""
import json

import httpx

from .constants import APIWEB_BASE
from .auth import get_valid_headers


def register_resources(mcp):
    """Register all MCP Resources on the given MCPServer instance."""

    @mcp.resource("bilas://outlet/profile", name="outlet_profile",
                  description="Current outlet business profile (name, address, hours, tariffs, subscription)")
    async def get_outlet_profile_resource():
        headers, st = await get_valid_headers()
        outlet_id = st["outlet_id"]
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    f"{APIWEB_BASE}/web/outlet/profil",
                    params={"id": outlet_id},
                    headers=headers,
                )
                return resp.text
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})

    @mcp.resource("bilas://machines/list", name="machine_list",
                  description="IoT-connected laundry machines (washers, dryers) with status and pulse counters")
    async def get_machines_resource():
        headers, st = await get_valid_headers()
        outlet_id = st["outlet_id"]
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    f"{APIWEB_BASE}/web/mqtt/machine/list",
                    params={"id": outlet_id},
                    headers=headers,
                )
                return resp.text
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})

    @mcp.resource("bilas://production/summary", name="production_summary",
                  description="Real-time production pipeline stage counters (antrian, proses, siap ambil, etc.)")
    async def get_production_summary_resource():
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
            return json.dumps({"production_counters": counters})
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})

    @mcp.resource("bilas://financial/categories", name="financial_categories",
                  description="Configured expense and income categories for this outlet")
    async def get_financial_categories_resource():
        headers, st = await get_valid_headers()
        outlet_id = st["outlet_id"]
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    f"{APIWEB_BASE}/web/keuangan/kategori",
                    params={"id": outlet_id},
                    headers=headers,
                )
                return resp.text
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})
