"""Bilas.id MCP Server — tool registration.

Import all tool modules so their @mcp.tool() decorators fire on server startup.
"""
from . import auth_tools, financials, transactions, customers, orders, infrastructure  # noqa: F401
