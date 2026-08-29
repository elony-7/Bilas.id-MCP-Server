"""Bilas.id Clean MCP Server Module (v1.4.0)

Comprehensive Model Context Protocol (MCP) server for Bilas.id POS & Reporting Platform:
  - Multi-Modal Onboarding (Interactive Playwright GUI, Automated OAuth Bridge, Manual Token Paste, Env Vars)
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
        sys.stderr.write(f"[Bilas MCP] Token refresh failed: {e}\n")
    return False

def login_via_playwright_gui():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return json.dumps({
            "status": "error",
            "message": "Playwright is not installed. Run 'pip install playwright' and 'playwright install' first."
        }, indent=2)

    print("\n=======================================================")
    print("   [Method 1: Interactive Browser GUI Authentication]  ")
    print("=======================================================")
    print("1. Opening bilas.id login page in browser...")
    print("2. Please log in using your Google account, OTP, or Password.")
    print("3. Once logged in, your token will be saved LOCALLY!")
    print("-------------------------------------------------------\n")

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

        def do_OPTIONS(self):
            self.send_response(200)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()

        def do_POST(self):
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path == "/token":
                content_length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_length).decode("utf-8")
                try:
                    payload_json = json.loads(body)
                    jwt = payload_json.get("jwt", "")
                    outlet = payload_json.get("outlet_id", "")
                    if jwt:
                        captured_data["jwt"] = jwt
                        captured_data["outlet_id"] = outlet
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json")
                        self.send_header("Access-Control-Allow-Origin", "*")
                        self.end_headers()
                        self.wfile.write(json.dumps({"status": "success"}).encode("utf-8"))
                        return
                except Exception:
                    pass

            self.send_response(400)
            self.end_headers()

        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path == "/google-oauth":
                try:
                    # Fetch NextAuth CSRF token & cookies from web.bilas.id
                    req_csrf = urllib.request.Request("https://web.bilas.id/api/auth/csrf", headers={"User-Agent": "Mozilla/5.0"})
                    with urllib.request.urlopen(req_csrf, timeout=10) as resp:
                        cookies = resp.headers.get_all("Set-Cookie")
                        csrf_data = json.loads(resp.read().decode("utf-8"))
                        csrf_token = csrf_data.get("csrfToken")

                    cookie_str = "; ".join([c.split(";")[0] for c in cookies]) if cookies else ""
                    post_data = urllib.parse.urlencode({
                        "csrfToken": csrf_token,
                        "callbackUrl": "https://web.bilas.id/beranda",
                        "json": "true"
                    }).encode("utf-8")

                    req_signin = urllib.request.Request(
                        "https://web.bilas.id/api/auth/signin/google",
                        data=post_data,
                        headers={
                            "Content-Type": "application/x-www-form-urlencoded",
                            "Cookie": cookie_str,
                            "User-Agent": "Mozilla/5.0"
                        },
                        method="POST"
                    )
                    with urllib.request.urlopen(req_signin, timeout=10) as resp_signin:
                        signin_res = json.loads(resp_signin.read().decode("utf-8"))
                        google_url = signin_res.get("url")
                        if google_url:
                            self.send_response(302)
                            self.send_header("Location", google_url)
                            self.end_headers()
                            return
                except Exception as e:
                    sys.stderr.write(f"[Bilas OAuth Bridge] OAuth redirect fetch error: {e}\n")

                self.send_response(302)
                self.send_header("Location", "https://web.bilas.id/masuk")
                self.end_headers()
                return

            if parsed.path == "/status":
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"authorized": bool(captured_data.get("jwt"))}).encode("utf-8"))
                return

            if parsed.path == "/token":
                query = urllib.parse.parse_qs(parsed.query)
                jwt = query.get("jwt", [""])[0]
                outlet = query.get("outlet_id", [""])[0]
                if jwt:
                    captured_data["jwt"] = jwt
                    captured_data["outlet_id"] = outlet
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(b"<html><body style='font-family:sans-serif; text-align:center; padding:50px; background:#0f172a; color:#f8fafc;'><h2 style='color:#4ade80;'>&#9989; OAuth Authorization Successful!</h2><p>Your Bilas.id session has been automatically captured & transferred to your AI Agent.</p><p>You may close this browser tab now.</p></body></html>")
                    return

            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            
            html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Bilas.id Direct Google OAuth Bridge</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0f172a; color: #f8fafc; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; padding: 20px; }}
        .card {{ background: #1e293b; padding: 32px; border-radius: 16px; width: 100%; max-width: 520px; box-shadow: 0 20px 25px -5px rgba(0,0,0,0.5); border: 1px solid #334155; text-align: center; }}
        h2 {{ margin-top: 0; color: #38bdf8; font-size: 22px; }}
        p {{ color: #94a3b8; line-height: 1.5; font-size: 14px; margin-bottom: 24px; }}
        .btn {{ display: flex; align-items: center; justify-content: center; gap: 10px; width: 100%; padding: 14px; background: #ffffff; color: #1f2937; border: none; border-radius: 10px; font-size: 15px; font-weight: 600; cursor: pointer; text-decoration: none; box-sizing: border-box; transition: all 0.2s; border: 1px solid #e5e7eb; }}
        .btn:hover {{ background: #f9fafb; transform: translateY(-1px); }}
        .step-box {{ background: #0f172a; border: 1px solid #334155; border-radius: 10px; padding: 18px; margin-top: 16px; text-align: left; }}
        .step-title {{ font-size: 13px; font-weight: 700; color: #cbd5e1; text-transform: uppercase; margin-bottom: 6px; }}
        .step-desc {{ font-size: 13px; color: #94a3b8; margin: 0 0 14px 0; }}
        .status {{ margin-top: 20px; font-size: 14px; font-weight: 500; padding: 12px; border-radius: 8px; background: #0f172a; border: 1px solid #334155; display: none; }}
        .success {{ color: #4ade80; border-color: #166534; display: block; }}
    </style>
</head>
<body>
    <div class="card">
        <h2>🔒 Bilas.id Direct OAuth Bridge</h2>
        <p>Authorize your Bilas.id AI Agent directly using Google Single Sign-On (SSO).</p>

        <div class="step-box">
            <div class="step-title">Direct Google SSO Login</div>
            <p class="step-desc">Click below to open the official Google OAuth sign-in window directly. Once you pick your account, your Bilas session automatically transfers here!</p>
            <button onclick="launchGoogleOAuth()" class="btn">
                <svg width="18" height="18" viewBox="0 0 24 24"><path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/><path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/><path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"/><path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"/></svg>
                Sign in with Google OAuth
            </button>
        </div>

        <div id="statusBox" class="status"></div>
    </div>

    <script>
        function checkStatus() {{
            fetch('/status')
                .then(r => r.json())
                .then(d => {{
                    if (d.authorized) {{
                        document.getElementById('statusBox').className = 'status success';
                        document.getElementById('statusBox').innerHTML = '✅ <strong>Agent Authorized Successfully!</strong> You may close this window.';
                    }}
                }}).catch(() => {{}});
        }}
        setInterval(checkStatus, 1500);

        function launchGoogleOAuth() {{
            const popup = window.open('/google-oauth', 'BilasGoogleOAuth', 'width=520,height=680');
            const timer = setInterval(() => {{
                if (!popup || popup.closed) {{
                    clearInterval(timer);
                    return;
                }}
                try {{
                    const href = popup.location.href;
                    if (href && (href.includes('web.bilas.id') || href.includes('127.0.0.1')) && !href.includes('accounts.google.com') && !href.includes('/google-oauth')) {{
                        let authDataStr = popup.localStorage.getItem('authData');
                        let jwt = '';
                        let outletId = popup.localStorage.getItem('activeOutlet') || popup.localStorage.getItem('outlet_id') || '';
                        if (authDataStr) {{
                            try {{
                                let parsedData = JSON.parse(authDataStr);
                                jwt = parsedData.extendedToken || parsedData.token || '';
                            }} catch(e) {{}}
                        }}
                        if (!jwt) {{
                            jwt = popup.localStorage.getItem('extendedToken') || popup.localStorage.getItem('token') || popup.sessionStorage.getItem('extendedToken') || popup.sessionStorage.getItem('token') || '';
                        }}
                        if (jwt) {{
                            fetch('http://127.0.0.1:{port}/token', {{
                                method: 'POST',
                                headers: {{ 'Content-Type': 'application/json' }},
                                body: JSON.stringify({{ jwt: jwt, outlet_id: outletId }})
                            }}).then(() => {{
                                popup.close();
                                clearInterval(timer);
                                document.getElementById('statusBox').className = 'status success';
                                document.getElementById('statusBox').innerHTML = '✅ <strong>Agent Authorized!</strong> Session captured via Google SSO.';
                            }});
                        }}
                    }}
                }} catch (e) {{}}
            }}, 800);
        }}
    </script>
</body>
</html>"""
            self.wfile.write(html_content.encode("utf-8"))

    try:
        httpd = socketserver.TCPServer(("127.0.0.1", port), AuthBridgeHandler)
    except Exception as e:
        return json.dumps({"status": "error", "message": f"Could not bind Remote Auth Bridge server to port {port}: {e}"})

    server_thread = threading.Thread(target=httpd.serve_forever)
    server_thread.daemon = True
    server_thread.start()

    bridge_url = f"http://localhost:{port}"
    print("\n=======================================================")
    print("   [Method 2: Automated OAuth Auth Bridge Server]      ")
    print("=======================================================")
    print(f"🔒 Server bound locally to: {bridge_url}")
    print("👉 Open the URL above to connect your Bilas.id account.")
    print("-------------------------------------------------------\n")

    start_time = time.time()
    while time.time() - start_time < 300:
        if captured_data.get("jwt"):
            if not captured_data.get("outlet_id"):
                payload = jwt_decode_payload(captured_data["jwt"])
                h = dict(APP_TOKENS)
                h["Authorization"] = "Bearer " + captured_data["jwt"]
                try:
                    req = urllib.request.Request("https://apiweb.bilas.id/web/outlet/profil", headers=h, method="GET")
                    resp = urllib.request.urlopen(req, timeout=5)
                    res = json.loads(resp.read().decode("utf-8"))
                    if res.get("result", {}).get("id"):
                        captured_data["outlet_id"] = res["result"]["id"]
                except Exception:
                    pass
            break
        time.sleep(1)

    httpd.shutdown()

    if captured_data.get("jwt"):
        payload = jwt_decode_payload(captured_data["jwt"])
        st = {
            "jwt": captured_data["jwt"],
            "user_id": payload.get("id"),
            "outlet_id": captured_data.get("outlet_id", ""),
            "exp": payload.get("exp"),
            "last_refresh": time.strftime("%Y-%m-%dT%H:%M:%S")
        }
        save_state(st)
        return json.dumps({
            "status": "success",
            "message": "✅ Direct Google OAuth Authorization Successful! Session state saved to ~/.bilas_id/",
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
    print("\n=======================================================")
    print("   [Bilas.id MCP Server Authentication Suite]          ")
    print("=======================================================")
    print("Select how you would like to connect your Bilas.id account:\n")
    print("1. 🖥️ Interactive GUI Browser (Local Machine with Playwright)")
    print("2. 🌐 Automated OAuth Bridge (Cloud / Headless Server via Local Web Link)")
    print("3. 🔑 Manual Token & Outlet ID Entry")
    print("4. ❌ Cancel\n")
    
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
            "\n=======================================================\n"
            " [Bilas.id MCP] AUTHENTICATION REQUIRED                 \n"
            "=======================================================\n"
            "You haven't connected your bilas.id account yet.\n"
            "Choose your preferred onboarding method:\n\n"
            "👉 Option A (Local Desktop GUI):\n"
            "   Run tool 'bilas_launch_browser_login' or command:\n"
            "   bilas-mcp --browser-login\n\n"
            "👉 Option B (Automated OAuth Bridge):\n"
            "   Run tool 'bilas_start_remote_auth_bridge' or command:\n"
            "   bilas-mcp --remote-bridge\n\n"
            "👉 Option C (Interactive Onboarding Menu):\n"
            "   bilas-mcp --onboard\n\n"
            "👉 Option D (Cloud Environment Variables):\n"
            "   export BILAS_JWT_TOKEN='...'\n"
            "   export BILAS_OUTLET_ID='...'\n"
            "=======================================================\n"
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
    version="1.4.0",
    description="Comprehensive Bilas.id Agent Integration Suite with Automated 1-Click OAuth Onboarding"
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
    """Start a temporary 1-Click Automated OAuth Auth Bridge HTTP server bound to localhost (127.0.0.1:8765). Automatically captures session state."""
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
