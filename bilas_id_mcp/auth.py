"""Bilas.id MCP Server — authentication, token management, and OAuth onboarding."""
import base64
import http.server
import json
import os
import sys
import time
import urllib.parse

import httpx

from .constants import APP_TOKENS, CONFIG_DIR, STATE_FILE, APIWEB_BASE


def ensure_config_dir():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load_state():
    """Load credentials from env vars (priority) or the state file."""
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
            "source": "environment_variables",
        }

    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"jwt": "", "outlet_id": "", "exp": None, "last_refresh": None}


def save_state(st):
    """Persist credentials to the state file, normalising outlet_id if it's a JSON blob."""
    ensure_config_dir()
    if st.get("outlet_id"):
        out_raw = str(st["outlet_id"]).strip()
        if out_raw.startswith("{") and out_raw.endswith("}"):
            try:
                out_obj = json.loads(out_raw)
                st["outlet_id"] = out_obj.get("id") or out_raw
            except Exception:
                pass
    STATE_FILE.write_text(json.dumps(st, indent=2, ensure_ascii=False), encoding="utf-8")


def jwt_decode_payload(jwt_str):
    """Decode the payload section of a JWT without verification."""
    if not jwt_str or "." not in jwt_str:
        return {}
    p = jwt_str.split(".")[1]
    p += "=" * (-len(p) % 4)
    try:
        return json.loads(base64.urlsafe_b64decode(p))
    except Exception:
        return {}


async def refresh_jwt_token(st):
    """Attempt to refresh an expired JWT. Returns True on success."""
    if not st.get("jwt"):
        return False
    headers = dict(APP_TOKENS)
    headers["Authorization"] = "Bearer " + st["jwt"]
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{APIWEB_BASE}/web/user/auth/refresh-token",
                headers=headers,
                json={},
            )
            d = resp.json()
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


async def get_valid_headers():
    """Return (headers, state) with a valid, refreshed JWT."""
    st = load_state()
    if st.get("jwt") and st.get("exp"):
        try:
            exp_ts = int(st["exp"])
            # Refresh if within 10 minutes of expiry
            if exp_ts - time.time() < 600:
                await refresh_jwt_token(st)
                st = load_state()
        except (TypeError, ValueError):
            pass

    h = dict(APP_TOKENS)
    h["Authorization"] = "Bearer " + st["jwt"]
    h["x-outlet-id"] = st["outlet_id"]
    return h, st


async def save_manual_credentials(jwt_token: str, outlet_id: str = "") -> str:
    """Save a JWT and optional outlet_id to the state file. Auto-resolves outlet if missing."""
    if not jwt_token or not jwt_token.strip():
        return json.dumps({"status": "error", "message": "JWT token cannot be empty."}, indent=2)

    payload = jwt_decode_payload(jwt_token)
    user_id = payload.get("id", "")
    exp = payload.get("exp")

    st = {
        "jwt": jwt_token.strip(),
        "outlet_id": outlet_id.strip() if outlet_id else "",
        "user_id": user_id,
        "exp": exp,
        "last_refresh": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "source": "manual_cli",
    }

    # Auto-resolve outlet_id from profile if not provided
    if not st["outlet_id"] and user_id:
        try:
            headers = dict(APP_TOKENS)
            headers["Authorization"] = "Bearer " + jwt_token.strip()
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(f"{APIWEB_BASE}/web/user/auth/profile", headers=headers)
                profile = resp.json()
            result = profile.get("result", {})
            outlets = result.get("outlet", [])
            if isinstance(outlets, list) and outlets:
                st["outlet_id"] = outlets[0].get("id", "")
            elif isinstance(result.get("outlet_id"), str):
                st["outlet_id"] = result["outlet_id"]
        except Exception:
            pass

    save_state(st)
    return json.dumps({
        "status": "success",
        "message": "Credentials saved successfully.",
        "outlet_id": st["outlet_id"],
        "user_id": user_id,
        "exp": exp,
        "saved_to": str(STATE_FILE),
    }, indent=2)


def login_via_system_default_browser(port=8765):
    """Launch the system browser with an OAuth bridge on 127.0.0.1:port.

    The browser opens a local page that guides the user through login.
    A bookmarklet transfers the JWT from web.bilas.id back to the local server.
    """
    captured_data = {"jwt": "", "outlet_id": ""}

    class SystemBrowserHandler(http.server.BaseHTTPRequestHandler):
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
            if parsed.path == "/callback":
                query = urllib.parse.parse_qs(parsed.query)
                jwt = query.get("jwt", [""])[0]
                outlet = query.get("outlet_id", [""])[0]
                if jwt:
                    captured_data["jwt"] = jwt
                    captured_data["outlet_id"] = outlet
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(
                        "<html><body style='font-family:sans-serif;text-align:center;padding:50px;"
                        "background:#0f172a;color:#4ade80;'><h2>✅ Bilas Agent Authorized!</h2>"
                        "<p>Session token transferred. You may close this tab.</p>"
                        "<script>setTimeout(() => window.close(), 2000);</script></body></html>".encode("utf-8")
                    )
                    return
            if parsed.path == "/status":
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"authorized": bool(captured_data.get("jwt"))}).encode("utf-8"))
                return

            # Serve the onboarding HTML page
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(_ONBOARDING_HTML.encode("utf-8"))

    import socketserver
    import webbrowser
    import threading

    # Try to reuse the port; if it's already open with a valid token, skip
    try:
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            s.connect(("127.0.0.1", port))
            s.sendall(b"GET /status HTTP/1.0\r\n\r\n")
            data = s.recv(4096).decode()
            if '"authorized": true' in data:
                return json.dumps({
                    "status": "already_authorized",
                    "message": "A Bilas auth bridge is already running and authorized on this port.",
                }, indent=2)
    except Exception:
        pass

    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(("127.0.0.1", port), SystemBrowserHandler)
    server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    server_thread.start()

    try:
        webbrowser.open(f"http://127.0.0.1:{port}")
    except Exception:
        pass

    # Wait for token (up to 5 minutes)
    deadline = time.time() + 300
    while time.time() < deadline and not captured_data["jwt"]:
        time.sleep(0.5)

    httpd.shutdown()

    if captured_data["jwt"]:
        st = {
            "jwt": captured_data["jwt"],
            "outlet_id": captured_data["outlet_id"],
            "exp": jwt_decode_payload(captured_data["jwt"]).get("exp"),
            "last_refresh": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "source": "browser_oauth_bridge",
        }
        save_state(st)
        return json.dumps({
            "status": "success",
            "message": "Authenticated via browser OAuth bridge.",
            "outlet_id": st["outlet_id"],
            "saved_to": str(STATE_FILE),
        }, indent=2)
    else:
        return json.dumps({
            "status": "timeout",
            "message": "No token received within 5 minutes. Try again or use bilas_set_manual_credentials().",
        }, indent=2)


def interactive_onboarding_menu():
    """Interactive CLI onboarding — presents a menu of auth options."""
    import subprocess

    print(
        "\n  🔒 Bilas.id MCP — Interactive Onboarding\n"
        "  ─────────────────────────────────────────\n"
        "  1) Browser OAuth bridge (recommended)\n"
        "  2) Paste JWT token manually\n"
        "  3) Show credentials file location\n"
        "  4) Exit\n"
    )
    choice = input("  Select [1-4]: ").strip()

    if choice == "1":
        return login_via_system_default_browser()
    elif choice == "2":
        jwt = input("  Paste your full JWT token: ").strip()
        outlet = input("  Outlet ID (leave blank to auto-resolve): ").strip()
        # save_manual_credentials is async, but this menu is sync — run inline
        import asyncio
        return asyncio.get_event_loop().run_until_complete(save_manual_credentials(jwt, outlet))
    elif choice == "3":
        return json.dumps({"credentials_file": str(STATE_FILE)}, indent=2)
    else:
        return json.dumps({"status": "cancelled"})


# ── Onboarding HTML (served by the OAuth bridge) ──────────────────────────
_ONBOARDING_HTML = """<!DOCTYPE html>
<html>
<head>
    <title>Bilas.id Agent Onboarding</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0f172a; color: #f8fafc; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; padding: 20px; }
        .card { background: #1e293b; padding: 32px; border-radius: 16px; width: 100%; max-width: 560px; box-shadow: 0 20px 25px -5px rgba(0,0,0,0.5); border: 1px solid #334155; text-align: center; }
        h2 { margin-top: 0; color: #38bdf8; font-size: 22px; }
        p { color: #94a3b8; line-height: 1.5; font-size: 14px; margin-bottom: 20px; }
        .btn { display: block; width: 100%; padding: 14px; background: #0284c7; color: white; border: none; border-radius: 10px; font-size: 15px; font-weight: 600; cursor: pointer; text-decoration: none; box-sizing: border-box; transition: all 0.2s; text-align: center; margin-bottom: 12px; }
        .btn:hover { background: #0369a1; transform: translateY(-1px); }
        .btn-green { background: #16a34a; margin-top: 8px; }
        .btn-green:hover { background: #15803d; }
        .status { margin-top: 20px; font-size: 14px; font-weight: 500; padding: 14px; border-radius: 8px; background: #0f172a; border: 1px solid #334155; display: none; }
        .success { color: #4ade80; border-color: #166534; display: block; }
        .step-box { background: #0f172a; border: 1px solid #334155; border-radius: 10px; padding: 18px; margin-top: 16px; text-align: left; }
        .step-title { font-size: 13px; font-weight: 700; color: #cbd5e1; text-transform: uppercase; margin-bottom: 6px; }
        .step-desc { font-size: 13px; color: #94a3b8; margin: 0 0 12px 0; }
        input { width: 100%; padding: 12px; background: #1e293b; border: 1px solid #475569; color: white; border-radius: 8px; box-sizing: border-box; margin-top: 8px; font-size: 13px; }
        input:focus { border-color: #38bdf8; outline: none; }
    </style>
</head>
<body>
    <div class="card">
        <h2>🔒 Bilas.id Agent Onboarding</h2>
        <p>Log in using your system browser with 100% Google security compliance.</p>
        <div class="step-box">
            <div class="step-title">Step 1: Open Bilas Web Login Window</div>
            <p class="step-desc">Click below to open web.bilas.id in a connected window.</p>
            <button class="btn" onclick="openBilasWindow()">🌐 1. Open Bilas.id Window</button>
        </div>
        <div class="step-box">
            <div class="step-title">Step 2: 1-Click Bookmarklet Transfer</div>
            <p class="step-desc">Drag this green button to your browser Bookmarks Bar. After logging into <code>web.bilas.id</code>, click the bookmarklet to send your session token to the agent!</p>
            <a class="btn btn-green" style="display:inline-block; cursor:grab;" href="javascript:(function(){try{let a=localStorage.getItem('authData')||'{}';let b=JSON.parse(a);let t=b.extendedToken||b.token||localStorage.getItem('extendedToken')||localStorage.getItem('token')||'';let o=localStorage.getItem('activeOutlet')||localStorage.getItem('outlet_id')||'';if(t){let payload={jwt:t,outlet_id:o};if(navigator.clipboard){navigator.clipboard.writeText(JSON.stringify(payload)).catch(()=>{});}fetch('http://127.0.0.1:8765/token',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)}).then(r=>r.json()).then(d=>{alert('✅ Bilas.id Session Token & Outlet ID Transferred and Copied to Clipboard!');}).catch(e=>{alert('✅ Credentials JSON (JWT + Outlet ID) copied to clipboard! (Failed to send to 127.0.0.1:8765)');});}else{alert('❌ No Bilas.id session token found in this tab. Please log in first!');}}catch(e){alert('Error: '+e.message);}})();">🔖 Drag to Bookmarks Bar: Transfer Token to MCP</a>
            <p class="step-desc" style="margin-top:12px; margin-bottom:4px;">Or paste your <code>authData</code> / JWT token JSON below:</p>
            <input type="text" id="jwtInput" placeholder="Paste token or authData JSON here..." oninput="handlePaste(this.value)">
        </div>
        <div id="statusBox" class="status"></div>
    </div>
    <script>
        let bilasWin = null;
        function openBilasWindow() {
            bilasWin = window.open("https://web.bilas.id/masuk", "BilasAuthTab", "width=600,height=750");
            startPoller();
        }
        function startPoller() {
            let interval = setInterval(() => {
                if (!bilasWin || bilasWin.closed) { clearInterval(interval); return; }
                try {
                    let storage = bilasWin.localStorage;
                    let authStr = storage.getItem("authData") || "{}";
                    let authObj = JSON.parse(authStr);
                    let token = authObj.extendedToken || authObj.token || storage.getItem("extendedToken") || storage.getItem("token");
                    if (token) {
                        sendTokenToLocalServer(token, storage.getItem("activeOutlet") || "");
                        clearInterval(interval);
                    }
                } catch (e) {}
            }, 1000);
        }
        function sendTokenToLocalServer(jwt, outlet) {
            fetch("/token", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ jwt: jwt, outlet_id: outlet })
            }).then(r => r.json()).then(d => {
                if (d.status === "success") {
                    checkStatus();
                    if (bilasWin && !bilasWin.closed) bilasWin.close();
                }
            }).catch(e => {});
        }
        function checkStatus() {
            fetch("/status").then(r => r.json()).then(d => {
                let box = document.getElementById("statusBox");
                if (d.authorized) {
                    box.className = "status success";
                    box.textContent = "✅ Authorized! Token received. You can close this page.";
                    box.style.display = "block";
                }
            }).catch(() => {});
        }
        function handlePaste(val) {
            try {
                let obj = JSON.parse(val);
                let jwt = obj.extendedToken || obj.token || obj.jwt || "";
                let outlet = obj.activeOutlet || obj.outlet_id || "";
                if (jwt) sendTokenToLocalServer(jwt, outlet);
            } catch (e) {}
        }
        setInterval(checkStatus, 2000);
    </script>
</body>
</html>"""
