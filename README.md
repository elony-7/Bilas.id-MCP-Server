# Bilas.id MCP Server (v1.4.0)

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
- `bilas_search_invoice`: Look up customer orders by Nota Number (`TRX/...`), Customer Name, or Phone Number with pagination.
- `bilas_get_production_summary`: Fetches real-time production stage counters (*Antrian*, *Proses*, *Siap Ambil*, *Siap Antar*, *Konfirmasi*, *Validasi*).

### 4. 🤖 IoT Smart Machines
- `bilas_list_machines`: Returns real-time status and pulse metrics for connected washers and dryers.

### 5. ⚙️ Outlet Profile & Settings
- `bilas_get_outlet_profile`: Fetches business details, address, location coordinates, and store configurations.

---

## 📦 Installation & Setup

```bash
pip install git+https://github.com/elony-7/Bilas.id-MCP-Server.git
playwright install
```
