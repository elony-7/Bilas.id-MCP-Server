"""Bilas.id MCP Server — IoT machines and outlet profile tools."""
import json

import httpx

from ..server import mcp
from ..constants import APIWEB_BASE
from ..auth import get_valid_headers


@mcp.tool()
async def bilas_list_machines() -> str:
    """List all IoT-connected laundry machines (washers and dryers) registered to this outlet.
    Returns machine IDs, names, product types, pulse counters, and status timestamps.
    READ-ONLY. Credentials auto-loaded from ~/.bilas_id/token_state.json."""
    headers, st = await get_valid_headers()
    outlet_id = st["outlet_id"]
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{APIWEB_BASE}/web/mqtt/machine/list",
                params={"id": outlet_id},
                headers=headers,
            )
            return json.dumps(resp.json(), indent=2, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)}, indent=2)


@mcp.tool()
async def bilas_get_outlet_profile() -> str:
    """Retrieve outlet business profile: name, address, city, province, phone, operating hours (jadwal),
    delivery tariffs (ongkir_tarif), printer/nota settings, subscription status, and location coordinates.
    READ-ONLY. Credentials auto-loaded from ~/.bilas_id/token_state.json."""
    headers, st = await get_valid_headers()
    outlet_id = st["outlet_id"]
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{APIWEB_BASE}/web/outlet/profil",
                params={"id": outlet_id},
                headers=headers,
            )
            return json.dumps(resp.json(), indent=2, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)}, indent=2)
