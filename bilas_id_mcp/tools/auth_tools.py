"""Bilas.id MCP Server — authentication & credential tools."""
import json

from ..server import mcp
from ..auth import login_via_system_default_browser, save_manual_credentials


@mcp.tool()
async def bilas_launch_browser_login() -> str:
    """Open Bilas.id login page in the system default browser with a local HTTP bridge on 127.0.0.1:8765.
    The user logs in via their normal browser (Google OAuth compatible), then uses the provided
    bookmarklet to transfer the session token to this MCP server.
    Token is saved to ~/.bilas_id/token_state.json. DO NOT save tokens to any other file.
    All other tools auto-read credentials from that state file.
    Equivalent CLI: bilas-mcp --browser-login"""
    return login_via_system_default_browser()


@mcp.tool()
async def bilas_set_manual_credentials(jwt_token: str, outlet_id: str = "") -> str:
    """Save a JWT token and optional Outlet ID into ~/.bilas_id/token_state.json.
    If outlet_id is omitted or empty, the server auto-resolves it via the user's Bilas.id profile API.
    DO NOT write tokens to .txt, .env, or any other file manually. NEVER truncate JWT tokens with ellipsis.
    Equivalent CLI: bilas-mcp --token <FULL_JWT_TOKEN> [--outlet <outlet_id>]

    Args:
        jwt_token: The COMPLETE JWT string from Bilas.id (e.g. eyJhbGciOiJIUzI1NiIs...). Must NOT be truncated.
        outlet_id: Firestore outlet document ID (e.g. outlet_abc123). Optional if already configured in ~/.bilas_id/token_state.json."""
    return await save_manual_credentials(jwt_token, outlet_id)
