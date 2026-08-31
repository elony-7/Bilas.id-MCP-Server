"""Bilas.id MCP Server — MCP Prompts.

Prompts provide reusable prompt templates that clients can discover and invoke.
Each prompt returns a structured message sequence that guides the agent through
a common Bilas.id workflow.
"""


def register_prompts(mcp):
    """Register all MCP Prompts on the given MCPServer instance."""

    @mcp.prompt(name="daily_summary",
                description="Generate a daily business summary for a given date range")
    def daily_summary_prompt(start_date: str = "", end_date: str = "") -> str:
        """Produce a prompt that asks the agent to pull and summarise today's business KPIs."""
        date_clause = ""
        if start_date and end_date:
            date_clause = f" for the period {start_date} to {end_date}"
        elif start_date:
            date_clause = f" for {start_date}"
        else:
            date_clause = " for today"

        return (
            f"Pull the Ringkasan Outlet report{date_clause} using bilas_get_ringkasan_outlet. "
            f"Then pull the Cashbox report for the same period using bilas_get_cashbox_report. "
            f"Summarise: total omzet, total pendapatan, total pengeluaran, net profit (pendapatan - pengeluaran), "
            f"number of transactions (trxmasuk), kiloan weight, and each cashbox's closing balance. "
            f"Flag any cashbox where saldo_akhir is negative. "
            f"Present the summary as a clean bullet-point list."
        )

    @mcp.prompt(name="check_production",
                description="Check the current production pipeline and list orders by stage")
    def check_production_prompt() -> str:
        return (
            "Check the production pipeline using bilas_get_production_summary to get stage counters. "
            "Then list orders at each active stage (Antrian, Proses, Setrika) using bilas_list_orders_by_status. "
            "Report: how many orders are at each stage, which orders have been waiting longest, "
            "and whether any orders appear stuck (waktu_antrian more than 4 hours ago without progress). "
            "Present as a production dashboard summary."
        )

    @mcp.prompt(name="expense_report",
                description="Review expenses for a date range with category breakdown")
    def expense_report_prompt(start_date: str = "", end_date: str = "") -> str:
        date_clause = f" from {start_date} to {end_date}" if start_date and end_date else ""
        return (
            f"Pull the Ringkasan Outlet report{date_clause} to get total pengeluaran. "
            f"Then pull the financial categories using bilas_get_financial_categories to understand available categories. "
            f"Present the total expenses, and if the ringkasan data includes category breakdowns, "
            f"show the top 5 expense categories by amount. "
            f"Flag any unusually large single expenses (>Rp 1,000,000)."
        )

    @mcp.prompt(name="customer_lookup",
                description="Look up a customer's orders and account details")
    def customer_lookup_prompt(customer_name: str = "") -> str:
        name_clause = f" named '{customer_name}'" if customer_name else ""
        return (
            f"Search for customer{name_clause} using bilas_list_customers. "
            f"Then search their orders using bilas_search_invoice with their name or phone number. "
            f"Summarise: customer profile (name, phone, registration date), "
            f"total orders found, most recent order status, "
            f"any outstanding payments (status_pembayaran: Belum Lunas), "
            f"and total lifetime spend if calculable from order history."
        )

    @mcp.prompt(name="cashbox_reconciliation",
                description="Reconcile cashbox balances for a date range")
    def cashbox_reconciliation_prompt(start_date: str = "", end_date: str = "") -> str:
        date_clause = f" for {start_date} to {end_date}" if start_date and end_date else ""
        return (
            f"Pull the cashbox report{date_clause} using bilas_get_cashbox_report. "
            f"For each cashbox, show: saldo_awal (opening), debit (money in), kredit (money out), "
            f"saldo_akhir (closing). Verify that saldo_awal + debit - kredit = saldo_akhir for each row. "
            f"Flag any cashbox where the formula doesn't hold or where saldo_akhir is negative. "
            f"Present as a reconciliation table."
        )
