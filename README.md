# Bilas.id MCP Server (v1.9.14)

Comprehensive Model Context Protocol (MCP) server for integrating AI Agents with the **bilas.id** POS & Laundry Management Platform.

---

## 🚀 2-Step Automated OAuth Bridge

The MCP server guarantees **100% session state isolation**. Zero hardcoded credentials or JWT tokens exist in the codebase. User authentication is stored exclusively in `~/.bilas_id/token_state.json` on the user's local machine.

### 🌐 How the 2-Step OAuth Bridge Works (`--remote-bridge` / `bilas_start_remote_auth_bridge`)

When running on headless cloud servers or local machines without terminal popups:

1. **Step 1 (Login)**: Click **"1. Open Bilas.id Login Web Page"** to log in using Google SSO or password on the official Bilas web app.
2. **Step 2 (Instant Auto-Grab)**: Click **"⚡ 2. Auto-Grab Token & Authorize Agent"** (or use the 1-click bookmarklet). The portal reads `extendedToken` directly from browser storage and securely posts it to `127.0.0.1:8765`.
3. **Auto-Outlet Resolution**: The server automatically queries the user's outlet business profile to fetch their active `outlet_id` without manual entry.

---


### ⚡ Direct CLI Token Onboarding (`--token`)

Agents or automation scripts can save session credentials directly without opening a browser:

```bash
# Pass JWT token directly (outlet_id is auto-resolved via profile API)
bilas-mcp --token "eyJhbGci..."

# Pass both JWT token and Outlet ID
bilas-mcp --token "eyJhbGci..." --outlet "2cvnOPoOgK9uZBQCc40c"
```

## 🛠️ Complete Feature & Tool Suite

### 1. 🔐 Auth & Onboarding Tools
- `bilas_launch_browser_login`: Opens interactive Playwright GUI browser window.
- `bilas_start_remote_auth_bridge`: Starts 2-Step Automated OAuth Bridge HTTP server on `127.0.0.1:8765`.
- `bilas_set_manual_credentials`: Manually saves JWT token and Outlet ID.

### 2. 📊 Financials & Cashbox Accounting
- `bilas_get_cashbox_report`: Computes exact 5-Column per-cashbox accounting matrix (`Saldo Awal + Debit - Kredit = Saldo Akhir`).
- `bilas_get_financial_categories`: Lists all operational expense & income categories.
- `bilas_add_expense`: Records new operational expense (*Pengeluaran*) entries (e.g. *Selisih Kurang*, *Biaya Listrik*).
- `bilas_delete_expense`: Soft-deletes erroneous financial records by `keuanganId`.

### 3. 🧾 Orders & Production Pipeline
- `bilas_get_order_details`: Fetches full line-by-line item breakdown (*Detail Layanan*, package name, service item, weight/quantity in Kg/Satuan, unit price, total price, perfume, notes, and photos).
- `bilas_list_orders_by_status`: Queries and filters active orders directly by production stage (*Antrian*, *Proses*, *Setrika*, *Siap Ambil*, *Selesai*, or `all`).
- `bilas_update_order_status`: Updates selected production items forward and verifies persistence by re-fetching the order.
- `bilas_revert_item_stage`: Corrects one detail item backward to an earlier production stage using the dashboard Koreksi/Riwayat payload, then verifies persistence.
- `bilas_create_order`: Creates new regular laundry transactions with customer information, service items, and payment method.
- `bilas_search_invoice`: Look up customer orders by Nota Number (`TRX/...`), Customer Name, or Phone Number with pagination.
- `bilas_get_production_summary`: Fetches real-time production stage counters (*Antrian*, *Proses*, *Siap Ambil*, *Siap Antar*, *Konfirmasi*, *Validasi*).
- `bilas_list_customers`: Lists and searches customer profiles with lifetime order counts and spend summary.

### 4. 🤖 IoT Smart Machines
- `bilas_list_machines`: Returns real-time status and pulse metrics for connected washers and dryers.

### 5. ⚙️ Outlet Profile & Settings
- `bilas_get_outlet_profile`: Fetches business details, address, location coordinates, and store configurations.

### 6. 📈 Dashboard Reports (read-only)
- `bilas_get_ringkasan_outlet` — Outlet summary (Ringkasan Outlet).
- `bilas_get_pendapatan_transaksi` — Transaction income / Omzet (Pendapatan Transaksi).
- `bilas_get_topup_paket` — Topup Paket income.
- `bilas_get_topup_deposit` — Topup Deposit / e-money income.
- `bilas_get_self_service_income` — Self-service income.
- `bilas_get_other_income` — Other income.
- `bilas_get_piutang` — Kasbon & Piutang report.
- `bilas_get_pembulatan` — Pembulatan (rounding) report.
- `bilas_get_merchant_fees` — Biaya Layanan / merchant fees.

### 7. 👥 Pelanggan (read-only)
- `bilas_get_customer_growth` — Customer growth (Pertumbuhan Pelanggan).
- `bilas_get_top_customers` — Top customers by spend.
- `bilas_get_package_quota` — Remaining package quota per customer.
- `bilas_get_deposit_balance` — Customer deposit / e-money balances.
- `bilas_get_kasbon_history` — Customer kasbon history.

All dashboard report tools:
- Accept `tgl_awal` and `tgl_akhir` in `YYYY/MM/DD` format.
- Validate date format and ordering locally before any network call.
- Return the raw Bilas response and a `normalized_metadata` block with the
  source endpoint, period, request_id, outlet_id, and HTTP status.

---

## 📦 Installation & Setup

```bash
pip install git+https://github.com/elony-7/Bilas.id-MCP-Server.git
playwright install
```
