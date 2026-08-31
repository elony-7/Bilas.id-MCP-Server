"""Tests for bilas_id_mcp.server — MCP server instantiation and registration."""
import asyncio
import pytest

from bilas_id_mcp.server import mcp
from bilas_id_mcp.constants import VERSION


def test_server_name():
    assert mcp.name == "bilas-id-mcp"


def test_server_version():
    assert mcp.version == VERSION


def test_server_description_mentions_auth():
    assert "token_state.json" in mcp.description


@pytest.mark.asyncio
async def test_tool_count():
    tools = await mcp.list_tools()
    assert len(tools) == 30


@pytest.mark.asyncio
async def test_no_duplicate_tools():
    tools = await mcp.list_tools()
    names = [t.name for t in tools]
    assert len(names) == len(set(names)), f"Duplicate tool names found: {[n for n in names if names.count(n) > 1]}"


@pytest.mark.asyncio
async def test_resource_count():
    resources = await mcp.list_resources()
    assert len(resources) == 4


@pytest.mark.asyncio
async def test_prompt_count():
    prompts = await mcp.list_prompts()
    assert len(prompts) == 5


@pytest.mark.asyncio
async def test_all_tools_have_descriptions():
    tools = await mcp.list_tools()
    for t in tools:
        assert t.description, f"Tool {t.name} has no description"


@pytest.mark.asyncio
async def test_all_tools_have_input_schema():
    tools = await mcp.list_tools()
    for t in tools:
        assert t.input_schema is not None, f"Tool {t.name} has no input schema"


@pytest.mark.asyncio
async def test_expected_tool_names():
    """Verify the exact set of tool names matches expectations."""
    tools = await mcp.list_tools()
    names = {t.name for t in tools}
    expected = {
        # Auth
        "bilas_launch_browser_login",
        "bilas_set_manual_credentials",
        # Financial reports
        "bilas_get_ringkasan_outlet",
        "bilas_get_pendapatan_transaksi",
        "bilas_get_topup_paket",
        "bilas_get_topup_deposit",
        "bilas_get_self_service_income",
        "bilas_get_other_income",
        "bilas_get_piutang",
        "bilas_get_pembulatan",
        "bilas_get_merchant_fees",
        "bilas_get_customer_growth",
        "bilas_get_top_customers",
        "bilas_get_package_quota",
        "bilas_get_deposit_balance",
        "bilas_get_kasbon_history",
        # Cashbox & expenses
        "bilas_get_cashbox_report",
        "bilas_get_financial_categories",
        "bilas_add_expense",
        "bilas_delete_expense",
        # Transactions & production
        "bilas_search_invoice",
        "bilas_get_production_summary",
        "bilas_update_order_status",
        "bilas_revert_item_stage",
        # Orders
        "bilas_create_order",
        "bilas_get_order_details",
        "bilas_list_orders_by_status",
        # Infrastructure
        "bilas_list_machines",
        "bilas_get_outlet_profile",
        # Customers
        "bilas_list_customers",
    }
    assert names == expected, f"Missing: {expected - names}, Extra: {names - expected}"


@pytest.mark.asyncio
async def test_no_hardcoded_date_defaults():
    """Verify no tool has hardcoded 2026 dates in its default parameters."""
    tools = await mcp.list_tools()
    for t in tools:
        schema = t.input_schema
        if "properties" in schema:
            for prop_name, prop_def in schema["properties"].items():
                if "default" in prop_def:
                    default_val = str(prop_def["default"])
                    assert "2026" not in default_val, (
                        f"Tool {t.name}.{prop_name} has hardcoded 2026 date default: {default_val}"
                    )
