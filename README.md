# Bilas.id MCP Server (v1.2.0)

Comprehensive Model Context Protocol (MCP) server for integrating AI Agents with the **bilas.id** POS & Laundry Management Platform.

---

## 🚀 Multi-Modal Authentication Suite (Headless & Desktop Support)

The MCP server guarantees **100% session state isolation**. Zero hardcoded credentials or JWT tokens exist in the codebase. User authentication is stored exclusively in `~/.bilas_id/token_state.json` on the user's local machine.

Users and Agents have 4 distinct onboarding options:

### 1. 🖥️ Interactive GUI Browser (`--browser-login`)
- Launches a local Playwright Chromium window opening `https://web.bilas.id/login`.
- Intercepts login response tokens and saves session state locally.
- **Best for:** Local desktop AI agents (Claude Code CLI, Claude Desktop).

### 2. 🌐 Remote Auth Bridge (`--remote-bridge`)
- Launches a lightweight local HTTP Auth Bridge server (`http://localhost:8765`).
- Displays a clean web link. The user opens the URL on their laptop/phone, logs in, and authorizes the cloud server.
- **Best for:** Headless cloud servers, VPS instances, remote Docker containers without display output (X11/GUI).

### 3. 🔑 Interactive Onboarding Menu (`--onboard`)
- Interactive CLI prompt presenting all authentication options upon running `bilas-mcp --onboard`.

### 4. 💻 Cloud Environment Variables
- Set `BILAS_JWT_TOKEN` and `BILAS_OUTLET_ID` in your server environment for headless automation.

---

## 🛠️ Complete Feature & Tool Suite

### 1. 🔐 Auth & Onboarding Tools
- `bilas_launch_browser_login`: Opens interactive GUI browser window to log in.
- `bilas_start_remote_auth_bridge`: Starts temporary Remote Auth Bridge HTTP server for cloud servers.
- `bilas_set_manual_credentials`: Manually saves JWT token and Outlet ID into local configuration.

### 2. 📊 Financials & Cashbox Accounting
- `bilas_get_cashbox_report`: Computes the exact 5-Column per-cashbox accounting matrix (`Saldo Awal + Debit - Kredit = Saldo Akhir`).
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

### 1. Install Package via Pip
```bash
pip install git+https://github.com/elony-7/Bilas.id-MCP-Server.git
playwright install
```

### 2. Add to Claude Code CLI
```bash
claude mcp add bilas-id -- bilas-mcp
```

### 3. Add to Claude Desktop (`claude_desktop_config.json`)
```json
{
  "mcpServers": {
    "bilas-id": {
      "command": "bilas-mcp"
    }
  }
}
```
