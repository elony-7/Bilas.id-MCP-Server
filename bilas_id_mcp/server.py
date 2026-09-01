"""Bilas.id MCP Server — entry point.

Creates the MCPServer instance, registers all tools/resources/prompts,
and provides the CLI entry point for ``bilas-mcp``.

Architecture:
  constants.py  — API URLs, config paths, version string
  auth.py       — JWT management, OAuth bridge, credential persistence
  helpers.py    — shared authenticated HTTP helpers, report processing
  tools/        — MCP tool definitions (auth, financials, transactions, customers, orders, infrastructure)
  resources.py  — MCP Resources (outlet profile, machines, production, categories)
  prompts.py    — MCP Prompts (daily summary, production check, expense report, etc.)
  cli.py        — CLI argument parsing (--token, --browser-login, --update, --help)
  server.py     — this file: MCPServer instantiation and module wiring
"""
from mcp.server.mcpserver import MCPServer

from .constants import VERSION

# The MCPServer instance must exist before tool modules are imported,
# because they import `mcp` from this module and decorate with @mcp.tool().
mcp = MCPServer(
    name="bilas-id-mcp",
    version=VERSION,
    description=(
        f"Bilas.id MCP Server v{VERSION} — AI Agent integration for Bilas.id POS & Laundry Management.\n"
        "AUTHENTICATION: All tools auto-read credentials from ~/.bilas_id/token_state.json.\n"
        "To authenticate: run CLI 'bilas-mcp --token <FULL_JWT>' or call tool bilas_set_manual_credentials().\n"
        "NEVER save tokens to .txt/.env/local files manually. NEVER truncate JWT strings with '...' or ellipsis.\n"
        "Token refresh is automatic. Outlet ID is auto-resolved if not provided.\n"
        "Available CLI commands: bilas-mcp --token <JWT> [--outlet <ID>] | --onboard | --browser-login\n"
        "\n"
        "TOOLS (34):\n"
        "  Auth:     bilas_launch_browser_login, bilas_set_manual_credentials\n"
        "  Reports:  bilas_get_ringkasan_outlet, bilas_get_pendapatan_transaksi, bilas_get_pengeluaran_transaksi,\n"
        "            bilas_get_topup_paket, bilas_get_topup_deposit, bilas_get_self_service_income,\n"
        "            bilas_get_other_income, bilas_get_piutang, bilas_get_pembulatan, bilas_get_merchant_fees,\n"
        "            bilas_get_customer_growth, bilas_get_top_customers, bilas_get_package_quota,\n"
        "            bilas_get_deposit_balance, bilas_get_kasbon_history\n"
        "  Finance:  bilas_get_cashbox_report, bilas_get_financial_categories,\n"
        "            bilas_add_expense, bilas_add_income, bilas_update_expense, bilas_delete_expense\n"
        "  Orders:   bilas_search_invoice, bilas_get_order_details, bilas_create_order,\n"
        "            bilas_list_orders_by_status\n"
        "  Prod:     bilas_get_production_summary, bilas_update_order_status, bilas_revert_item_stage\n"
        "  Infra:    bilas_get_outlet_profile, bilas_list_machines\n"
        "  Customers: bilas_list_customers, bilas_get_unique_customers\n"
        "\n"
        "RESOURCES: bilas://outlet/profile, bilas://machines/list, bilas://production/summary,\n"
        "           bilas://financial/categories\n"
        "\n"
        "PROMPTS: daily_summary, check_production, expense_report, customer_lookup, cashbox_reconciliation"
    ),
)

# Import tool modules — their @mcp.tool() decorators register on import.
from . import tools  # noqa: E402, F401

# Import and register resources and prompts.
from .resources import register_resources  # noqa: E402
from .prompts import register_prompts  # noqa: E402

register_resources(mcp)
register_prompts(mcp)


def main():
    """CLI entry point for ``bilas-mcp``."""
    from .cli import run_cli
    run_cli(mcp)
