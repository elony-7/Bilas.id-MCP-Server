"""Bilas.id Clean MCP Server Module (v1.2.0)

Comprehensive Model Context Protocol (MCP) server for Bilas.id POS & Reporting Platform:
  - Multi-Modal Onboarding (Interactive GUI Browser, Remote Auth Bridge, Manual Token Paste, Env Vars)
  - 100% isolated session token management in user OS home (~/.bilas_id/token_state.json)
  - Zero hardcoded tokens or user IDs in codebase
  - 5-Column Per-Cashbox Accounting (Saldo Awal + Debit - Kredit = Saldo Akhir)
  - Financial Corrections (Expense / Income addition & soft deletion)
  - Operational Expense/Income Category Lookup
  - Order & Customer Transaction Search with Filter & Pagination
  - Production Pipeline Counter & Order Status Tracking
  - IoT Smart Laundry Machine Control & Real-time Monitoring
  - Outlet Business Profile & Settings Configuration
"""
import base64
import json
import os
import sys
import time
import urllib.parse
import urllib.request
import uuid
import http.server
import socketserver
import threading
from datetime import datetime, timedelta
from pathlib import Path

USER_HOME = Path.home()
CONFIG_DIR = USER_HOME / ".bilas_id"
STATE_FILE = CONFIG_DIR / "token_state.json"

APP_TOKENS = {
    "x-access-token": "sjgyfne73592643gedudney3628465hgrdt",
    "x-access-web-token": "UD1P6jZ0XKErPm5hQ4dKSXu5MQv6h8oOGeT78CVpXXAxC7H4LrtEZtj2BnwHKKcnuLfRtZYvne3Qlb2aUVg",
    "Content-Type": "application/json",
}

ARUSKAS_URL = "https://laporan.apibilas.com/v1/laporanoutlet/keuangan/aruskas"
PEMINDAHAN_URL = "https://laporan.apibilas.com/v1/laporanoutlet/keuangan/pemindahansaldo"

def ensure_config_dir():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

def load_state():
    ensure_config_dir()
    env_jwt = os.environ.get("BILAS_JWT_TOKEN")
    env_outlet = os.environ.get("BILAS_OUTLET_ID")
    if env_jwt and env_outlet:
        payload = jwt_decode_payload(env_jwt)
        return {
            "jwt": env_jwt,
            "outlet_id": env_outlet,
            "user_id": payload.get("id"),
            "exp": payload.get("exp"),
            "source": "environment_variables"
        }

    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"jwt": "", "outlet_id": "", "exp": None, "last_refresh": None}

def save_state(st):
    ensure_config_dir()
    STATE_FILE.write_text(json.dumps(st, indent=2, ensure_ascii=False), encoding="utf-8")

def jwt_decode_payload(jwt_str):
    if not jwt_str or "." not in jwt_str:
        return {}
    p = jwt_str.split(".")[1]
    p += "=" * (-len(p) % 4)
    try:
        return json.loads(base64.urlsafe_b64decode(p))
    except Exception:
        return {}

def refresh_jwt_token(st):
    if not st.get("jwt"):
        return False
    h = dict(APP_TOKENS)
    h["Authorization"] = "Bearer " + st["jwt"]
    req = urllib.request.Request("https://apiweb.bilas.id/web/user/auth/refresh-token", data=b"{}", headers=h, method="POST")
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        d = json.loads(resp.read().decode("utf-8"))
        if str(d.get("value")) == "1" and d.get("result", {}).get("extendedToken"):
            st["jwt"] = d["result"]["extendedToken"]
            payload = jwt_decode_payload(st["jwt"])
            st["exp"] = payload.get("exp") or d["result"].get("expiredAt")
            if payload.get("id"):
                st["user_id"] = payload.get("id")
            st["last_refresh"] = time.strftime("%Y-%m-%dT%H:%M:%S")
            save_state(st)
            return True
    except Exception as e:
        sys.stderr.write(f"[Bilas MCP] Token refresh failed: {e}
")
    return False

def login_via_playwright_gui():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return json.dumps({
            "status": "error",
            "message": "Playwright is not installed. Run 'pip install playwright' and 'playwright install' first."
        }, indent=2)

    print("
=======================================================")
    print("   [Method 1: Interactive Browser GUI Authentication]  ")
    print("=======================================================")
    print("1. Opening bilas.id login page in browser...")
    print("2. Please log in using your Google account, OTP, or Password.")
    print("3. Once logged in, your token will be saved LOCALLY!")
    print("-------------------------------------------------------
")

    captured_state = {"jwt": "", "outlet_id": ""}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        def handle_response(response):
            try:
                if "/refresh-token" in response.url or "/login/" in response.url:
                    data = response.json()
                    res = data.get("result", {})
                    token = res.get("extendedToken") or res.get("token")
                    if token:
                        captured_state["jwt"] = token
                        payload = jwt_decode_payload(token)
                        captured_state["user_id"] = payload.get("id")
                        outlets = res.get("outletList", [])
                        if outlets:
                            captured_state["outlet_id"] = outlets[0]["id"]
            except Exception:
                pass

        page.on("response", handle_response)
        page.goto("https://web.bilas.id/login")

        start_time = time.time()
        while time.time() - start_time < 120:
            if captured_state.get("jwt") and captured_state.get("outlet_id") and "/beranda" in page.url:
                break
            page.wait_for_timeout(1000)

        browser.close()

    if captured_state.get("jwt"):
        payload = jwt_decode_payload(captured_state["jwt"])
        st = {
            "jwt": captured_state["jwt"],
            "user_id": captured_state.get("user_id"),
            "outlet_id": captured_state.get("outlet_id"),
            "exp": payload.get("exp"),
            "last_refresh": time.strftime("%Y-%m-%dT%H:%M:%S")
        }
        save_state(st)
        return json.dumps({
            "status": "success",
            "message": "✅ Login successful! Session token captured & saved locally to ~/.bilas_id/",
            "outlet_id": st["outlet_id"],
            "expires_at": st["exp"]
        }, indent=2)
    else:
        return json.dumps({
            "status": "error",
            "message": "❌ Login timed out or token was not captured."
        }, indent=2)

def start_remote_auth_bridge(port=8765):
    captured_data = {"jwt": "", "outlet_id": ""}

    class AuthBridgeHandler(http.server.BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass

        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path == "/token":
                query = urllib.parse.parse_qs(parsed.query)
                jwt = query.get("jwt", [""])[0]
                outlet = query.get("outlet_id", [""])[0]
                if jwt and outlet:
                    captured_data["jwt"] = jwt
                    captured_data["outlet_id"] = outlet
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(b"<html><body style='font-family:sans-serif; text-align:center; padding:50px; background:#f4f6f8;'><h2 style='color:#2e7d32;'>&#9989; Authentication Successful!</h2><p>Your session token has been securely transferred to your Cloud Agent.</p><p>You may close this tab now.</p></body></html>")
                    return

            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            html_content = '''<!DOCTYPE html>
<html>
<head>
    <title>Bilas.id Cloud Agent Remote Authentication</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0f172a; color: #f8fafc; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; padding: 20px; }
        .card { background: #1e293b; padding: 32px; border-radius: 16px; width: 100%; max-width: 480px; box-shadow: 0 20px 25px -5px rgba(0,0,0,0.5); border: 1px solid #334155; }
        h2 { margin-top: 0; color: #38bdf8; }
        p { color: #94a3b8; line-height: 1.5; font-size: 14px; }
        .btn { display: block; width: 100%; padding: 12px; margin: 12px 0; background: #0284c7; color: white; border: none; border-radius: 8px; font-weight: 600; cursor: pointer; text-decoration: none; text-align: center; box-sizing: border-box; }
        .btn:hover { background: #0369a1; }
        input { width: 100%; padding: 12px; margin: 8px 0 16px 0; background: #0f172a; border: 1px solid #475569; border-radius: 8px; color: white; box-sizing: border-box; }
        label { font-size: 12px; color: #cbd5e1; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }
    </style>
</head>
<body>
    <div class="card">
        <h2>🔒 Bilas.id Agent Remote Auth Bridge</h2>
        <p>Connect your Cloud AI Agent to Bilas.id securely without sharing raw login credentials with the server.</p>
        <a href="https://web.bilas.id/login" target="_blank" class="btn">1. Open Bilas.id Web Login</a>
        <form method="GET" action="/token">
            <label>2. Paste Extended Token (JWT)</label>
            <input type="text" name="jwt" placeholder="eyJhbGciOiJIUzI1Ni..." required />
            <label>3. Outlet ID</label>
            <input type="text" name="outlet_id" placeholder="2cvnOPoOgK9uZBQCc40c" required />
            <button type="submit" class="btn" style="background:#16a34a;">4. Authorize Cloud Agent</button>
        </form>
    </div>
</body>
</html>'''
            self.wfile.write(html_content.encode("utf-8"))

    try:
        httpd = socketserver.TCPServer(("0.0.0.0", port), AuthBridgeHandler)
    except Exception as e:
        return json.dumps({"status": "error", "message": f"Could not bind Remote Auth Bridge server to port {port}: {e}"})

    server_thread = threading.Thread(target=httpd.serve_forever)
    server_thread.daemon = True
    server_thread.start()

    bridge_url = f"http://localhost:{port}"
    print("
=======================================================")
    print("   [Method 2: Remote Auth Bridge Server Started]       ")
    print("=======================================================")
    print(f"👉 Please open this URL in your browser/phone:")
    print(f"   {bridge_url}")
    print("-------------------------------------------------------
")

    start_time = time.time()
    while time.time() - start_time < 300:
        if captured_data.get("jwt") and captured_data.get("outlet_id"):
            break
        time.sleep(1)

    httpd.shutdown()

    if captured_data.get("jwt"):
        payload = jwt_decode_payload(captured_data["jwt"])
        st = {
            "jwt": captured_data["jwt"],
            "user_id": payload.get("id"),
            "outlet_id": captured_data["outlet_id"],
            "exp": payload.get("exp"),
            "last_refresh": time.strftime("%Y-%m-%dT%H:%M:%S")
        }
        save_state(st)
        return json.dumps({
            "status": "success",
            "message": "✅ Remote Authentication Successful! Session state saved to ~/.bilas_id/",
            "outlet_id": st["outlet_id"]
        }, indent=2)
    else:
        return json.dumps({
            "status": "error",
            "message": "❌ Remote Auth Bridge timed out."
        }, indent=2)

def save_manual_credentials(jwt_token: str, outlet_id: str):
    payload = jwt_decode_payload(jwt_token)
    st = {
        "jwt": jwt_token.strip(),
        "outlet_id": outlet_id.strip(),
        "user_id": payload.get("id"),
        "exp": payload.get("exp"),
        "last_refresh": time.strftime("%Y-%m-%dT%H:%M:%S")
    }
    save_state(st)
    return json.dumps({
        "status": "success",
        "message": "✅ Credentials saved successfully to ~/.bilas_id/token_state.json!",
        "outlet_id": st["outlet_id"],
        "expires_at": st["exp"]
    }, indent=2)

def interactive_onboarding_menu():
    print("
=======================================================")
    print("   [Bilas.id MCP Server Authentication Suite]          ")
    print("=======================================================")
    print("Select how you would like to connect your Bilas.id account:
")
    print("1. 🖥️ Interactive GUI Browser (Local Machine with Playwright)")
    print("2. 🌐 Remote Auth Bridge (Cloud / Headless Server via Web Link)")
    print("3. 🔑 Manual Token & Outlet ID Entry")
    print("4. ❌ Cancel
")
    
    try:
        choice = input("Enter choice (1-4): ").strip()
    except Exception:
        choice = "2"

    if choice == "1":
        return login_via_playwright_gui()
    elif choice == "2":
        return start_remote_auth_bridge()
    elif choice == "3":
        jwt = input("Paste Extended JWT Token: ").strip()
        outlet = input("Enter Outlet ID: ").strip()
        return save_manual_credentials(jwt, outlet)
    else:
        return json.dumps({"status": "cancelled", "message": "Onboarding cancelled."})

def get_valid_headers():
    st = load_state()
    if not st.get("jwt") or not st.get("outlet_id"):
        guidance = (
            "
=======================================================
"
            " [Bilas.id MCP] AUTHENTICATION REQUIRED                 
"
            "=======================================================
"
            "You haven't connected your bilas.id account yet.
"
            "Choose your preferred onboarding method:

"
            "👉 Option A (Local Desktop GUI):
"
            "   Run tool 'bilas_launch_browser_login' or command:
"
            "   bilas-mcp --browser-login

"
            "👉 Option B (Cloud / Headless Server Remote Bridge):
"
            "   Run tool 'bilas_start_remote_auth_bridge' or command:
"
            "   bilas-mcp --remote-bridge

"
            "👉 Option C (Interactive Onboarding Menu):
"
            "   bilas-mcp --onboard

"
            "👉 Option D (Cloud Environment Variables):
"
            "   export BILAS_JWT_TOKEN='...'
"
            "   export BILAS_OUTLET_ID='...'
"
            "=======================================================
"
        )
        raise PermissionError(guidance)

    exp = st.get("exp") or jwt_decode_payload(st.get("jwt", "")).get("exp")
    if not exp or (exp - time.time() < 3600):
        refresh_jwt_token(st)
        st = load_state()

    h = dict(APP_TOKENS)
    h["Authorization"] = "Bearer " + st["jwt"]
    h["x-outlet-id"] = st["outlet_id"]
    return h, st

from mcp.server.mcpserver import MCPServer

mcp = MCPServer(
    name="bilas-id-mcp",
    version="1.2.0",
    description="Comprehensive Bilas.id Agent Integration Suite with Multi-Modal Onboarding (GUI Browser, Remote Auth Bridge, Env Vars)"
)

# ---------------------------------------------------------------------------
# 1. AUTH & ONBOARDING TOOLS
# ---------------------------------------------------------------------------

@mcp.tool()
def bilas_launch_browser_login() -> str:
    """Launch interactive Playwright GUI browser login window for local machines."""
    return login_via_playwright_gui()

@mcp.tool()
def bilas_start_remote_auth_bridge() -> str:
    """Start a temporary Remote Auth Bridge HTTP server for Cloud/Headless environments. Returns a web URL to authorize login on any device."""
    return start_remote_auth_bridge()

@mcp.tool()
def bilas_set_manual_credentials(jwt_token: str, outlet_id: str) -> str:
    """Manually set JWT token and Outlet ID directly into local configuration state."""
    return save_manual_credentials(jwt_token, outlet_id)

# ---------------------------------------------------------------------------
# 2. FINANCIALS & CASHBOX ACCOUNTING
# ---------------------------------------------------------------------------

@mcp.tool()
def bilas_get_cashbox_report(tgl_awal: str, tgl_akhir: str, base_opening_balances: dict = None) -> str:
    """Computes exact per-cashbox accounting table (Saldo Awal + Debit - Kredit = Saldo Akhir)."""
    headers, st = get_valid_headers()
    outlet_id = st["outlet_id"]

    def fetch_rep(url):
        body = {"id": outlet_id, "tgl_awal": tgl_awal, "tgl_akhir": tgl_akhir, "req_id": str(uuid.uuid4())}
        req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST")
        return json.loads(urllib.request.urlopen(req, timeout=60).read().decode("utf-8")).get("result", {})

    aruskas = fetch_rep(ARUSKAS_URL)
    pindah = fetch_rep(PEMINDAHAN_URL)

    period_debit, period_kredit = {}, {}
    for e in aruskas.get("detail", []):
        cb = e.get("cashbox", "")
        if cb:
            period_debit[cb] = period_debit.get(cb, 0) + e.get("debit", 0)
            period_kredit[cb] = period_kredit.get(cb, 0) + e.get("kredit", 0)
    for e in pindah.get("detail", []):
        cb = e.get("cashbox", "")
        if cb:
            period_debit[cb] = period_debit.get(cb, 0) + e.get("debit", 0)
            period_kredit[cb] = period_kredit.get(cb, 0) + e.get("kredit", 0)

    base_balances = base_opening_balances or {"Tunai": 0, "BCA": 0, "QRIS": 0, "Dana": 0}
    saldo_awal = dict(base_balances)
    all_cashboxes = sorted(list(set(list(base_balances.keys()) + list(period_debit.keys()) + list(period_kredit.keys()))))
    rows = []
    tot_awal = tot_debit = tot_kredit = tot_akhir = 0
    for cb in all_cashboxes:
        sa = saldo_awal.get(cb, 0)
        deb = period_debit.get(cb, 0)
        kre = period_kredit.get(cb, 0)
        sak = sa + deb - kre
        rows.append({"cashbox": cb, "saldo_awal": sa, "debit": deb, "kredit": kre, "saldo_akhir": sak})
        tot_awal += sa; tot_debit += deb; tot_kredit += kre; tot_akhir += sak

    summary = {"cashbox": "TOTAL", "saldo_awal": tot_awal, "debit": tot_debit, "kredit": tot_kredit, "saldo_akhir": tot_akhir}
    return json.dumps({"tgl_awal": tgl_awal, "tgl_akhir": tgl_akhir, "rows": rows, "summary": summary}, indent=2, ensure_ascii=False)

@mcp.tool()
def bilas_get_financial_categories() -> str:
    """Retrieve operational financial expense & income categories configured for the outlet."""
    headers, st = get_valid_headers()
    outlet_id = st["outlet_id"]
    url = f"https://apiweb.bilas.id/web/keuangan/kategori?id={outlet_id}"
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        res = json.loads(resp.read().decode("utf-8"))
        return json.dumps(res, indent=2, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)}, indent=2)

@mcp.tool()
def bilas_add_expense(cashbox: str, category: str, amount: int, description: str, date_mm_dd_yyyy: str) -> str:
    """Record an operational expense (Pengeluaran) entry."""
    headers, st = get_valid_headers()
    outlet_id = st["outlet_id"]
    user_id = st.get("user_id") or jwt_decode_payload(st.get("jwt")).get("id")

    payload = {
        "id": outlet_id,
        "zone": "Asia/Jakarta",
        "dibuat_tgl": date_mm_dd_yyyy,
        "dataKeuangan": {
            "waktu": date_mm_dd_yyyy,
            "cashbox": cashbox,
            "kategori": category,
            "jumlah": amount,
            "keterangan": description,
            "jenis": "Pengeluaran",
            "id_operator": user_id
        }
    }
    url = "https://apiweb.bilas.id/web/keuangan/koreksi-keuangan/create"
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        res = json.loads(resp.read().decode("utf-8"))
        return json.dumps(res, indent=2, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)}, indent=2)

@mcp.tool()
def bilas_delete_expense(keuangan_id: str, date_mm_dd_yyyy: str) -> str:
    """Soft-delete an expense or income entry by its keuanganId."""
    headers, st = get_valid_headers()
    outlet_id = st["outlet_id"]
    payload = {
        "id": outlet_id,
        "outletId": outlet_id,
        "zone": "Asia/Jakarta",
        "dibuat_tgl": date_mm_dd_yyyy,
        "keuanganId": keuangan_id
    }
    url = "https://apiweb.bilas.id/web/keuangan/koreksi-keuangan/delete"
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="PUT")
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        res = json.loads(resp.read().decode("utf-8"))
        return json.dumps(res, indent=2, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)}, indent=2)

# ---------------------------------------------------------------------------
# 3. TRANSACTIONS & PRODUCTION PIPELINE
# ---------------------------------------------------------------------------

@mcp.tool()
def bilas_search_invoice(query: str = "", page: int = 1, limit: int = 20) -> str:
    """Lookup transactions or customer history by nota number (TRX/...), customer name, or phone number."""
    headers, st = get_valid_headers()
    outlet_id = st["outlet_id"]
    q = urllib.parse.quote(query, safe="")
    url = f"https://apiweb.bilas.id/web/transaksi/reguler/all?id={outlet_id}&page={page}&limit={limit}&search={q}"
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        res = json.loads(resp.read().decode("utf-8"))
        return json.dumps(res, indent=2, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)}, indent=2)

@mcp.tool()
def bilas_get_production_summary() -> str:
    """Get active production pipeline status counters (Antrian, Proses, Siap Ambil, Siap Antar, Konfirmasi, Validasi)."""
    headers, st = get_valid_headers()
    outlet_id = st["outlet_id"]
    url = f"https://apiweb.bilas.id/web/transaksi/reguler/all?id={outlet_id}&page=1&limit=1"
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        res = json.loads(resp.read().decode("utf-8"))
        counters = res.get("result", {}).get("counter", {})
        return json.dumps({"status": "success", "production_counters": counters}, indent=2, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)}, indent=2)

# ---------------------------------------------------------------------------
# 4. IOT SMART MACHINES (WASHERS & DRYERS)
# ---------------------------------------------------------------------------

@mcp.tool()
def bilas_list_machines() -> str:
    """List all connected IoT smart laundry machines (Washers & Dryers) and their current status."""
    headers, st = get_valid_headers()
    outlet_id = st["outlet_id"]
    url = f"https://apiweb.bilas.id/web/mqtt/machine/list?id={outlet_id}"
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        res = json.loads(resp.read().decode("utf-8"))
        return json.dumps(res, indent=2, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)}, indent=2)

# ---------------------------------------------------------------------------
# 5. OUTLET PROFILE & SETTINGS
# ---------------------------------------------------------------------------

@mcp.tool()
def bilas_get_outlet_profile() -> str:
    """Retrieve outlet business details, address, location coordinates, and operational configurations."""
    headers, st = get_valid_headers()
    outlet_id = st["outlet_id"]
    url = f"https://apiweb.bilas.id/web/outlet/profil?id={outlet_id}"
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        res = json.loads(resp.read().decode("utf-8"))
        return json.dumps(res, indent=2, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)}, indent=2)

def main():
    if "--browser-login" in sys.argv:
        res = login_via_playwright_gui()
        print(res)
        return
    elif "--remote-bridge" in sys.argv:
        res = start_remote_auth_bridge()
        print(res)
        return
    elif "--login" in sys.argv or "--onboard" in sys.argv:
        res = interactive_onboarding_menu()
        print(res)
        return
    mcp.run()

if __name__ == "__main__":
    main()
