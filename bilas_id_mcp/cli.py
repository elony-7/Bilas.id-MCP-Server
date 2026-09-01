"""Bilas.id MCP Server — CLI argument parsing and self-update."""
import json
import subprocess
import sys
import textwrap

from .constants import VERSION


def _print_help():
    """Print the --help text with all current tools listed."""
    print(f"""
  Bilas.id MCP Server v{VERSION}
  ─────────────────────────────────────────────────────
  Usage:
    bilas-mcp                         Start MCP server (stdio transport)
    bilas-mcp --update                Update to latest version from GitHub
    bilas-mcp --token <JWT>            Save JWT token (outlet auto-resolved)
    bilas-mcp --token <JWT> --outlet <ID>  Save JWT + explicit outlet ID
    bilas-mcp --onboard                Interactive onboarding menu
    bilas-mcp --browser-login          Open system browser + bookmarklet bridge
    bilas-mcp --help                   Show this help

  Credentials:
    Saved to:  ~/.bilas_id/token_state.json
    All tools auto-read from that file. Token refresh is automatic.
    NEVER save tokens to .txt/.env or truncate JWT strings.

  Auth tools:
    bilas_launch_browser_login         Browser + bookmarklet bridge
    bilas_set_manual_credentials       Save JWT + outlet via MCP tool call

  Financial reports (15):
    bilas_get_ringkasan_outlet         Outlet KPI summary
    bilas_get_pendapatan_transaksi     Transaction revenue / omzet
    bilas_get_pengeluaran_transaksi    Transaction expenses
    bilas_get_topup_paket              Package top-ups
    bilas_get_topup_deposit            Deposit top-ups
    bilas_get_self_service_income      Self-service income
    bilas_get_other_income             Other income
    bilas_get_piutang                  Receivables
    bilas_get_pembulatan               Rounding adjustments
    bilas_get_merchant_fees            Merchant/payment fees
    bilas_get_customer_growth          Customer growth
    bilas_get_top_customers            Top customers by spend
    bilas_get_package_quota            Package quota usage
    bilas_get_deposit_balance          Deposit balances
    bilas_get_kasbon_history           Kasbon (credit) history

  Cashbox & expenses:
    bilas_get_cashbox_report           5-column cashbox accounting matrix
    bilas_get_financial_categories     Expense/income category list
    bilas_add_expense                  Record new expense entry
    bilas_add_income                   Record new income entry
    bilas_update_expense               Update existing financial entry
    bilas_delete_expense               Soft-delete a financial entry

  Orders & production:
    bilas_search_invoice               Search orders by nota/name/phone/date
    bilas_get_order_details            Full order breakdown with detail items
    bilas_create_order                 Create a new laundry order
    bilas_list_orders_by_status        List orders filtered by production stage
    bilas_get_production_summary       Production pipeline stage counters
    bilas_update_order_status          Advance order to next production stage
    bilas_revert_item_stage            Move item backward (Koreksi/Riwayat)

  Infrastructure:
    bilas_get_outlet_profile           Outlet business details & settings
    bilas_list_machines                IoT washer/dryer status

  Customers:
    bilas_list_customers               Search/list registered customer profiles
    bilas_get_unique_customers         Unique customer analysis by date range

  MCP Resources:
    bilas://outlet/profile             Outlet profile (auto-refreshed)
    bilas://machines/list              Machine list (auto-refreshed)
    bilas://production/summary         Production counters (auto-refreshed)
    bilas://financial/categories       Financial categories (auto-refreshed)

  MCP Prompts:
    daily_summary                      Daily business KPI summary
    check_production                   Production pipeline dashboard
    expense_report                     Expense breakdown by category
    customer_lookup                    Customer profile + order history
    cashbox_reconciliation             Cashbox balance reconciliation
  ─────────────────────────────────────────────────────
""")


def _update_from_github():
    """Pull and reinstall the latest bilas-id-mcp from the GitHub repository."""
    repo_url = "git+https://github.com/elony-7/Bilas.id-MCP-Server.git"
    print(textwrap.dedent(f"""\
        ╔══════════════════════════════════════════════════════════════╗
        ║  Updating bilas-id-mcp from GitHub...                      ║
        ║  Source: {repo_url:<48}  ║
        ╚══════════════════════════════════════════════════════════════╝
    """))

    python_exec = sys.executable or "python"
    cmd = [
        python_exec, "-m", "pip", "install",
        "--upgrade", "--force-reinstall", "--no-deps",
        repo_url,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        stdout = result.stdout or ""
        stderr = result.stderr or ""
        output = stdout + stderr

        installed_line = ""
        for line in output.splitlines():
            if "Successfully installed" in line:
                installed_line = line.strip()
                break

        if result.returncode == 0 and installed_line:
            print(f"  ✅  {installed_line}")
            print(f"  ℹ️  Run 'bilas-mcp --help' to see the updated version.")
        elif result.returncode == 0:
            print("  ✅  Already up to date — no newer version found on GitHub.")
        else:
            last_lines = "\n".join(output.splitlines()[-10:])
            print(f"  ❌  pip exited with code {result.returncode}")
            print(f"      {last_lines}")
    except FileNotFoundError:
        print("  ❌  Could not find Python/pip — make sure 'python -m pip' works.")
    except subprocess.TimeoutExpired:
        print("  ❌  pip timed out after 300 seconds — check your network connection.")
    except Exception as exc:
        print(f"  ❌  Update failed: {exc}")


def run_cli(mcp):
    """Parse CLI arguments and either run a command or start the MCP server."""
    # Show help
    if "--help" in sys.argv or "-h" in sys.argv:
        _print_help()
        return

    # Handle self-update
    if "--update" in sys.argv or "--upgrade" in sys.argv:
        _update_from_github()
        return

    # Handle direct CLI token passing: bilas-mcp --token <jwt_token> [--outlet <outlet_id>]
    if "--token" in sys.argv:
        try:
            idx = sys.argv.index("--token")
            jwt_val = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else ""
            outlet_val = ""
            if "--outlet" in sys.argv:
                oidx = sys.argv.index("--outlet")
                outlet_val = sys.argv[oidx + 1] if oidx + 1 < len(sys.argv) else ""

            if not jwt_val:
                print(json.dumps({"status": "error", "message": "❌ Missing token value after --token"}, indent=2))
                return

            import asyncio
            from .auth import save_manual_credentials
            res = asyncio.get_event_loop().run_until_complete(save_manual_credentials(jwt_val, outlet_val))
            print(res)
            return
        except Exception as e:
            print(json.dumps({"status": "error", "message": f"❌ Failed to parse CLI flags: {e}"}, indent=2))
            return

    if "--browser-login" in sys.argv:
        from .auth import login_via_system_default_browser
        res = login_via_system_default_browser()
        print(res)
        return
    elif "--remote-bridge" in sys.argv or "--google-sso" in sys.argv:
        from .auth import login_via_system_default_browser
        res = login_via_system_default_browser()
        print(res)
        return
    elif "--login" in sys.argv or "--onboard" in sys.argv:
        from .auth import interactive_onboarding_menu
        res = interactive_onboarding_menu()
        print(res)
        return

    # Default: start the MCP server over stdio
    mcp.run()
