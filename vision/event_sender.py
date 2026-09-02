import json, socket, threading, time

class BluetoothRFCOMMEventSender:
    def __init__(self, mac, channel=1, name="BT", connect_timeout=1.5, ack_timeout=0.8, retries=1):
        self.mac=mac; self.channel=int(channel); self.name=name
        self.connect_timeout=connect_timeout; self.ack_timeout=ack_timeout; self.retries=retries

    def send(self, event):
        payload=(json.dumps(event, ensure_ascii=False)+"\n").encode()
        last_error=None
        for attempt in range(self.retries+1):
            s=socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
            try:
                s.settimeout(self.connect_timeout)
                s.connect((self.mac, self.channel))
                t0=time.perf_counter()
                s.sendall(payload)
                send_ms=round((time.perf_counter()-t0)*1000,1)
                try:
                    s.settimeout(self.ack_timeout)
                    ack=s.recv(64).decode(errors="ignore").strip().upper()
                    if ack.startswith("ACK"):
                        return {"ok":True,"status":"ACKED","error":None,"send_ms":send_ms}
                except Exception:
                    pass
                return {"ok":True,"status":"SENT","error":None,"send_ms":send_ms}
            except OSError as e:
                last_error=str(e)
                time.sleep(0.15)
            finally:
                try:s.close()
                except:pass
        return {"ok":False,"status":"FAILED","error":last_error,"send_ms":None}

class MultiBluetoothEventSender:
    def __init__(self, audio_mac, control_mac, channel=1):
        self.audio = BluetoothRFCOMMEventSender(audio_mac, channel, "BT-AUDIO")
        self.pi_bridge_url = "http://127.0.0.1:8765/event"

    def _send_pi_bridge(self, event):
        import urllib.request
        import urllib.error

        payload = json.dumps(event, ensure_ascii=False).encode()
        req = urllib.request.Request(
            self.pi_bridge_url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        t0 = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=4.0) as r:
                body = json.loads(r.read().decode())
            send_ms = round((time.perf_counter() - t0) * 1000, 1)

            if body.get("ok"):
                return {"ok": True, "status": body.get("status", "SENT"), "error": None, "send_ms": send_ms}

            return {"ok": False, "status": "FAILED", "error": body.get("error", "bridge failed"), "send_ms": None}

        except Exception as e:
            return {"ok": False, "status": "FAILED", "error": str(e), "send_ms": None}

    def send(self,event):
        results={}
        t0=time.perf_counter()

        results["audio"] = self.audio.send(event)
        results["control"] = self._send_pi_bridge(event)

        results["total_ms"] = round((time.perf_counter()-t0)*1000,1)
        return results
