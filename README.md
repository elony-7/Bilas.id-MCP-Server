# Bilas.id MCP Server (v1.1.0)

Comprehensive Model Context Protocol (MCP) server for integrating AI Agents with the **bilas.id** POS & Laundry Management Platform.

## Features & Tool Suite

### 1. 🔐 Auth & Zero-Password Onboarding
- `bilas_launch_browser_login`: Opens an interactive browser login window (`https://web.bilas.id/login`), captures session JWT token locally to `~/.bilas_id/token_state.json`, and auto-refreshes tokens every 7 days indefinitely.

### 2. 📊 Financials & Cashbox Accounting
- `bilas_get_cashbox_report`: Computes the exact 5-Column per-cashbox accounting matrix (Saldo Awal + Debit - Kredit = Saldo Akhir).
- `bilas_get_financial_categories`: Lists all configured operational expense and income categories.
- `bilas_add_expense`: Records new operational expense (*Pengeluaran*) entries (e.g. *Selisih Kurang*, *Biaya Listrik*).
- `bilas_delete_expense`: Soft-deletes erroneous financial records by `keuanganId`.

### 3. 🧾 Orders & Production Pipeline
- `bilas_search_invoice`: Look up customer orders by Nota Number (`TRX/...`), Customer Name, or Phone Number with pagination support.
- `bilas_get_production_summary`: Fetches real-time production stage counters (*Antrian*, *Proses*, *Siap Ambil*, *Siap Antar*, *Konfirmasi*, *Validasi*).

### 4. 🤖 IoT Smart Machines
- `bilas_list_machines`: Returns real-time status and pulse metrics for connected washers and dryers.

### 5. ⚙️ Outlet Profile & Settings
- `bilas_get_outlet_profile`: Fetches business details, address, coordinates, and store configurations.

---

## Installation & Setup

### 1. Install via Pip / Git
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

---

## Unauthenticated User Onboarding Flow

When any tool is called on a fresh installation, the server automatically detects that no local session exists and prompts:
> 🔒 **Authentication Required**: Please run tool `bilas_launch_browser_login` or run `bilas-mcp --browser-login`.

Once the user logs in via the browser popup, the session token is saved **locally** to `~/.bilas_id/token_state.json`. Zero session data is hardcoded or leaked into the package!
