# Bilas.id MCP Server

Model Context Protocol (MCP) server for integrating AI Agents with **bilas.id** POS & reporting platform.

## Features
- **5-Column Cashbox Accounting Reports**: Saldo Awal + Debit - Kredit = Saldo Akhir
- **Expense & Income Management**: Create, edit, and soft-delete financial entries
- **Order & Invoice Lookup**: Search by nota number (TRX/...), customer name, or phone number
- **IoT Machine Control & Metrics**: Connected washers and dryers list
- **Automated Zero-Password Onboarding**: Intercepts web browser login securely and auto-refreshes tokens every 7 days indefinitely

## Installation & Setup

### 1. Install via pip
```bash
pip install bilas-id-mcp
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

## First Time Use (Unauthenticated User Flow)
When any tool is called for the first time, the server will detect that no session is active and prompt:
> 🔒 **Authentication Required**: Run tool `bilas_launch_browser_login` or run `bilas-mcp --browser-login`.

A browser window opens to `https://web.bilas.id/login`. Once you log in via Google, OTP, or Password, the MCP intercepts your session token and stores it **locally** on your machine. Token auto-refreshes every 7 days!
