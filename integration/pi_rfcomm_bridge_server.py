import json
import os
import subprocess
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

PI_MAC = "DC:A6:32:7F:85:01"
DEV = "/dev/rfcomm0"
PORT = 8765

rfcomm_proc = None

def ensure_rfcomm():
    global rfcomm_proc

    if os.path.exists(DEV):
        return True

    rfcomm_proc = subprocess.Popen(
        ["rfcomm", "connect", "0", PI_MAC, "1"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    for _ in range(50):
        if os.path.exists(DEV):
            return True
        time.sleep(0.1)

    return False

def send_to_pi(event):
    if not ensure_rfcomm():
        raise RuntimeError("RFCOMM connection failed")

    payload = json.dumps(event, ensure_ascii=False) + "\n"

    with open(DEV, "w", buffering=1) as f:
        f.write(payload)
        f.flush()

class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/event":
            self.send_response(404)
            self.end_headers()
            return

        try:
            n = int(self.headers.get("Content-Length", "0"))
            event = json.loads(self.rfile.read(n))
            send_to_pi(event)

            body = b'{"ok":true,"status":"SENT"}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

            print("[PI BRIDGE] EVENT SENT:", event.get("event"), flush=True)

        except Exception as e:
            body = json.dumps({"ok": False, "error": str(e)}).encode()
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

            print("[PI BRIDGE] ERROR:", repr(e), flush=True)

    def log_message(self, *args):
        pass

print(f"[PI BRIDGE] listening on 127.0.0.1:{PORT}", flush=True)
HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
