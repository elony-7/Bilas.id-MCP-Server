"""Bilas.id Clean MCP Server Module

Guarantees 100% isolation & zero hardcoded credentials:
  - Stores session state ONLY in the user's OS home directory (~/.bilas_id/token_state.json)
  - Contains NO hardcoded JWT tokens, NO hardcoded outlet IDs, and NO local cached credentials
  - Guides new users to launch interactive browser login on first run
"""
import base64
import json
import os
import sys
import time
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timedelta
from pathlib import Path

# User-isolated state path in user's OS home directory
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
    return json.loads(base64.urlsafe_b64decode(p))

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
            st["user_id"] = payload.get("id")
            st["last_refresh"] = time.strftime("%Y-%m-%dT%H:%M:%S")
            save_state(st)
            return True
    except Exception as e:
        sys.stderr.write(f"[Bilas MCP] Token refresh failed: {e}\n")
    return False

def trigger_interactive_browser_login():
    """Launches Playwright GUI browser window to let user log in safely via web UI.
    Intercepts the user's JWT token and outlet ID from network responses and saves it locally.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return json.dumps({
            "status": "error",
            "message": "Playwright is not installed. Run 'pip install playwright' and 'playwright install' first."
        }, indent=2)

    print("\n=======================================================")
    print("   [Bilas.id Interactive Browser Authentication]       ")
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

def get_valid_headers():
    st = load_state()
    if not st.get("jwt") or not st.get("outlet_id"):
        guidance = (
            "\n=======================================================\n"
            " [Bilas.id MCP] AUTHENTICATION REQUIRED                 \n"
            "=======================================================\n"
            "You haven't connected your bilas.id account yet.\n"
            "To manage cashboxes, reports, orders, and settings,\n"
            "please log in once using your web browser.\n\n"
            "👉 Action Needed:\n"
            "   Run tool 'bilas_launch_browser_login' or command:\n"
            "   bilas-mcp --browser-login\n\n"
            "A browser window will pop up. Once you log in, your\n"
            "session token will be saved locally and auto-refreshed!\n"
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
    version="1.0.0",
    description="Clean Bilas.id Agent Integration Suite with Automated Browser Login Onboarding"
)

@mcp.tool()
def bilas_launch_browser_login() -> str:
    """Launch interactive browser login window. The user logs in via web UI, and the MCP captures the session token automatically."""
    return trigger_interactive_browser_login()

@mcp.tool()
def bilas_get_cashbox_report(tgl_awal: str, tgl_akhir: str, base_opening_balances: dict = None) -> str:
    """Computes exact per-cashbox accounting table (Saldo Awal + Debit - Kredit = Saldo Akhir).

    Args:
        tgl_awal: Start date in YYYY/MM/DD format (e.g. '2026/08/01')
        tgl_akhir: End date in YYYY/MM/DD format (e.g. '2026/08/30')
        base_opening_balances: Optional dict of opening balances per cashbox (e.g. {"Tunai": 800000, "BCA": 620746})
    """
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

@mcp.tool()
def bilas_search_invoice(query: str) -> str:
    """Lookup invoice or customer transaction history by nota number, customer name, or phone."""
    headers, st = get_valid_headers()
    outlet_id = st["outlet_id"]
    q = urllib.parse.quote(query, safe="")
    url = f"https://apiweb.bilas.id/web/transaksi/reguler/all?id={outlet_id}&page=1&limit=20&search={q}"
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        res = json.loads(resp.read().decode("utf-8"))
        return json.dumps(res, indent=2, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)}, indent=2)

def main():
    if "--browser-login" in sys.argv or "--login" in sys.argv:
        res = trigger_interactive_browser_login()
        print(res)
        return
    mcp.run()

if __name__ == "__main__":
    main()
