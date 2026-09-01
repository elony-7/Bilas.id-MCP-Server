# Bilas.id MCP Server (v1.9.25)

Comprehensive Model Context Protocol (MCP) server for integrating AI Agents with the **bilas.id** POS & Laundry Management Platform.

---

## 🚀 Authentication & Session Isolation

The MCP server guarantees **100% session state isolation**. Zero hardcoded credentials or JWT tokens exist in the codebase. User authentication is stored exclusively in `~/.bilas_id/token_state.json` on the user's local machine.

### 🌐 System Default Browser Login (`--browser-login` / `bilas_launch_browser_login`)

When running on local or remote developer environments:

1. **Step 1 (Open Browser)**: The server launches the system default browser to the official Bilas.id login page and opens a local bridge on `127.0.0.1:8765`.
2. **Step 2 (Login & Token Transfer)**: Log in using Google SSO or password. Use the 1-click bookmarklet or portal link to securely transfer `extendedToken` to the local bridge.
3. **Auto-Outlet Resolution**: The server automatically queries the user's outlet business profile to fetch their active `outlet_id` without requiring manual lookup.

### ⚡ Direct CLI Token Onboarding (`--token`)

Agents or automation scripts can save session credentials directly:

```bash
# Pass JWT token directly (outlet_id is auto-resolved via profile API)
bilas-mcp --token "eyJhbGci..."

# Pass both JWT token and explicit Outlet ID
bilas-mcp --token "eyJhbGci..." --outlet "outlet_abc123"
```

---

## 🛠️ Complete Feature & Tool Suite (34 Tools)

### 1. 🔐 Auth Tools
- `bilas_launch_browser_login`: Open system browser + local bridge on `127.0.0.1:8765` for 1-click bookmarklet token transfer (Google SSO compatible).
- `bilas_set_manual_credentials`: Save JWT token and optional Outlet ID into `~/.bilas_id/token_state.json`.

### 2. 📊 Financials, Cashbox & Ledger Mutation
- `bilas_get_cashbox_report`: Computes exact 5-Column per-cashbox accounting matrix (`Saldo Awal + Debit - Kredit = Saldo Akhir`) using server-side `aruskasneraca`.
- `bilas_get_financial_categories`: Lists all operational expense & income categories configured for this outlet.
- `bilas_add_expense`: Records new operational expense (*Pengeluaran*) entries (e.g. *Biaya Listrik*, *Beli Sabun*).
- `bilas_add_income`: Records new operational income (*Pemasukan*) entries directly into specified cashbox with category and date.
- `bilas_update_expense`: Directly updates an existing financial record by `keuanganId` without needing delete+re-add cycles.
- `bilas_delete_expense`: Soft-deletes a financial record by `keuanganId`.

### 3. 🧾 Orders & Production Pipeline
- `bilas_search_invoice`: Look up customer orders across active and completed history by Nota Number (`TRX/...`), Customer Name, or Phone Number with optional `tgl_awal` and `tgl_akhir` (`YYYY/MM/DD`) date filtering.
- `bilas_get_order_details`: Comprehensive order breakdown with line-by-line item breakdown (*Detail Layanan*, package name, service item, weight/quantity in Kg/Satuan, unit price, total price, perfume, notes, and photos).
- `bilas_create_order`: Creates new regular laundry transactions with customer information, service items, and payment method.
- `bilas_list_orders_by_status`: Queries and filters active orders directly by production stage (*Antrian*, *Proses*, *Setrika*, *Siap Ambil*, *Selesai*, or `all`).
- `bilas_get_production_summary`: Real-time pipeline stage counters (*Antrian*, *Proses*, *Siap Ambil*, *Siap Antar*, *Konfirmasi*, *Validasi*, *Penjemputan*).
- `bilas_update_order_status`: Advances order or specific line item to the next production stage.
- `bilas_revert_item_stage`: Moves exactly one detail item backward through Koreksi/Riwayat with persistence verification.

### 4. 👥 Customer Management & Analytics
- `bilas_list_customers`: Lists and searches registered customer profiles with optional `registered_after` and `registered_before` (`YYYY/MM/DD`) date filtering.
- `bilas_get_unique_customers`: Multi-source customer deduplication combining paid transactions (`pendapatan_transaksi`), active orders (`/all`), and completed history orders (`/riwayat`), enriched with customer registry profiles (ID, registration date, email, spend, and order statuses).

### 5. 🤖 IoT Smart Machines & Outlet Profile
- `bilas_list_machines`: Real-time status, product types, and pulse metrics for IoT connected washers and dryers.
- `bilas_get_outlet_profile`: Business profile details, address, operating hours, delivery tariffs, and coordinates.

### 6. 📈 Dashboard Financial & Growth Reports (15 Reports)
All reporting tools accept `tgl_awal` and `tgl_akhir` in `YYYY/MM/DD` format:
- `bilas_get_ringkasan_outlet`: Outlet KPI summary with parsed KPI block (`kiloan`, `satuan`, `meter`, `omzet`, `pendapatan`, `pengeluaran`, `labarugi`, `trxmasuk`, `trxbatal`, `graph`).
- `bilas_get_pendapatan_transaksi`: Transaction revenue / Omzet breakdown.
- `bilas_get_pengeluaran_transaksi`: Itemized transaction expense report.
- `bilas_get_topup_paket`: Package top-ups report.
- `bilas_get_topup_deposit`: Deposit / e-money top-ups report.
- `bilas_get_self_service_income`: Self-service machine revenue.
- `bilas_get_other_income`: Other miscellaneous revenue.
- `bilas_get_piutang`: Accounts receivable and unpaid customer balances.
- `bilas_get_pembulatan`: Rounding adjustments report.
- `bilas_get_merchant_fees`: Biaya Layanan / merchant transaction fees.
- `bilas_get_customer_growth`: Customer registration growth over time.
- `bilas_get_top_customers`: Top customer ranking by revenue.
- `bilas_get_package_quota`: Active customer package quota usage and balances.
- `bilas_get_deposit_balance`: Customer deposit account balances.
- `bilas_get_kasbon_history`: Customer credit / kasbon history.

---

## 📦 MCP Resources & Prompts

### Resources
- `bilas://outlet/profile` — Live outlet profile and operating configuration.
- `bilas://machines/list` — Real-time IoT washer and dryer statuses.
- `bilas://production/summary` — Real-time production stage counters.
- `bilas://financial/categories` — Active operational income and expense categories.

### Prompts
- `daily_summary` — Generates daily business KPI summary (Omzet, expenses, production stages).
- `check_production` — Audits the production pipeline and highlights bottlenecks.
- `expense_report` — Breaks down operational expenses by category.
- `customer_lookup` — Looks up customer details and purchase history.
- `cashbox_reconciliation` — Audits cashbox balances against physical cash counts.

---

## 📦 Installation & Setup

```bash
pip install git+https://github.com/elony-7/Bilas.id-MCP-Server.git
playwright install
```

### Self-Updating to Latest Version

```bash
bilas-mcp --update         # or --upgrade
```

The update command pulls and reinstalls the latest release directly from GitHub into your running Python environment.

---

## 🧪 Testing

Run the test suite:

```bash
pytest tests/ -v
```
