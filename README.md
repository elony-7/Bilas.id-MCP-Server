# Bilas.id MCP Server (v1.3.0)

Comprehensive Model Context Protocol (MCP) server for integrating AI Agents with the **bilas.id** POS & Laundry Management Platform.

---

## 🚀 1-Click OAuth & Multi-Modal Onboarding Suite

The MCP server guarantees **100% session state isolation**. Zero hardcoded credentials or JWT tokens exist in the codebase. User authentication is stored exclusively in `~/.bilas_id/token_state.json` on the user's local machine.

Users and Agents have 4 distinct onboarding options:

### 1. ⚡ 1-Click OAuth Remote Auth Bridge (`--remote-bridge`)
- Launches an interactive 1-Click OAuth Authorization server at `http://127.0.0.1:8765`.
- **Popup SSO Flow:** Clicking **"🔑 Connect & Authorize Bilas.id"** opens the Google / Bilas.id OAuth login popup window.
- **1-Click Auto-Grab Bookmarklet:** Includes a zero-paste bookmarklet button. Once logged in, clicking the bookmarklet instantly transfers your session token into the AI Agent's configuration file!
- **Automatic Outlet Resolution:** Once authorized, the server automatically queries the user's outlet business profile and extracts the active `outlet_id`.

### 2. 🖥️ Interactive Playwright GUI Browser (`--browser-login`)
- Launches a local Playwright Chromium window opening `https://web.bilas.id/login`.
- Intercepts login response tokens and saves session state locally.
- **Best for:** Local desktop AI agents (Claude Code CLI, Claude Desktop).

### 3. 🔑 Interactive Onboarding Menu (`--onboard`)
- Interactive CLI prompt presenting all authentication options upon running `bilas-mcp --onboard`.

### 4. 💻 Cloud Environment Variables
- Set `BILAS_JWT_TOKEN` and `BILAS_OUTLET_ID` in your server environment for headless automation.

---

## 🛠️ Complete Feature & Tool Suite

### 1. 🔐 Auth & Onboarding Tools
- `bilas_launch_browser_login`: Opens interactive Playwright GUI browser window.
- `bilas_start_remote_auth_bridge`: Starts 1-Click OAuth Auth Bridge HTTP server on `127.0.0.1:8765`.
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
