"""Tests for bilas_id_mcp.cli — help text and CLI structure."""
from bilas_id_mcp.cli import _print_help
from bilas_id_mcp.constants import VERSION


def test_help_text_contains_version(capsys):
    _print_help()
    captured = capsys.readouterr()
    assert VERSION in captured.out


def test_help_text_lists_all_commands(capsys):
    _print_help()
    captured = capsys.readouterr()
    for cmd in ["--token", "--update", "--onboard", "--browser-login", "--help"]:
        assert cmd in captured.out, f"Help text missing command: {cmd}"


def test_help_text_lists_key_tools(capsys):
    _print_help()
    captured = capsys.readouterr()
    key_tools = [
        "bilas_get_ringkasan_outlet",
        "bilas_get_cashbox_report",
        "bilas_search_invoice",
        "bilas_update_order_status",
        "bilas_list_machines",
        "bilas_get_outlet_profile",
        "bilas_add_expense",
        "bilas_list_customers",
    ]
    for tool in key_tools:
        assert tool in captured.out, f"Help text missing tool: {tool}"


def test_help_text_lists_resources(capsys):
    _print_help()
    captured = capsys.readouterr()
    assert "bilas://outlet/profile" in captured.out
    assert "bilas://machines/list" in captured.out


def test_help_text_lists_prompts(capsys):
    _print_help()
    captured = capsys.readouterr()
    assert "daily_summary" in captured.out
    assert "check_production" in captured.out
