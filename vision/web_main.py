import argparse
import json
import threading
import time

import cv2
from flask import Flask, Response, jsonify, render_template_string, request

from config import (
    DEFAULT_EQUIPMENT_STATE,
    LOG_PATH,
    PROXIMITY_MARGIN_RATIO,
    MOTION_START_THRESHOLD,
    MOTION_STOP_THRESHOLD,
    MOTION_PIXEL_THRESHOLD,
    MOTION_START_FRAMES,
    MOTION_STOP_FRAMES,
)
from detector import JetsonYOLODetector
from event_logic import HazardStateMachine
from event_sender import MultiBluetoothEventSender
from logger import CsvLogger
from proximity import expand_bbox, foot_point, point_in_bbox, normalized_distance_to_bbox
from runtime_state import RuntimeState
from motion_detector import EquipmentMotionDetector


HTML = r"""
<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Vision Safety Node</title>
<style>
:root{--bg:#0b1020;--p:#121a2c;--p2:#172136;--l:#273650;--t:#eef4ff;--m:#95a6bf;--ok:#58d68d;--w:#f5c464;--d:#ff6b6b}
*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%;overflow:hidden}body{background:var(--bg);color:var(--t);font-family:Arial,sans-serif}
.wrap{height:100vh;max-width:1600px;margin:auto;padding:8px 12px;display:flex;flex-direction:column;gap:7px}.top{height:42px;display:flex;align-items:center;justify-content:space-between}
h1{font-size:19px;margin:0}.sub{font-size:10px;color:var(--m)}.badge{border:1px solid var(--l);border-radius:999px;padding:6px 10px;font-size:11px;font-weight:900}
.grid{flex:1;min-height:0;display:grid;grid-template-columns:1.55fr .85fr;gap:8px}.card{background:var(--p);border:1px solid var(--l);border-radius:12px}
.video{padding:7px;display:flex;min-height:0}.video img{width:100%;height:100%;object-fit:contain;border-radius:8px;background:#000}
.side{padding:8px;display:flex;flex-direction:column;gap:6px;min-height:0}.lab{font-size:9px;letter-spacing:.12em;color:var(--m);font-weight:900}
.hero{display:flex;justify-content:space-between;background:var(--p2);padding:8px 10px;border-radius:9px}.state{font-size:24px;font-weight:900}.sm{font-size:9px;color:var(--m)}
.pipe{display:grid;grid-template-columns:repeat(4,1fr);gap:4px}.stage{background:var(--p2);border:1px solid var(--l);border-radius:8px;padding:6px;min-height:50px}.stage .n{font-size:8px;color:var(--m)}.stage .v{font-size:9px;font-weight:900;margin-top:4px}
.dot{display:inline-block;width:7px;height:7px;border-radius:50%;margin-right:4px;background:#607089}.ok{background:var(--ok)}.warn{background:var(--w)}.danger{background:var(--d)}
.rows{display:grid;grid-template-columns:1fr 1fr;gap:4px}.row{background:var(--p2);border:1px solid var(--l);border-radius:7px;padding:5px 7px;display:flex;justify-content:space-between}.row span{font-size:9px;color:var(--m)}.row b{font-size:9px}
.bt{display:grid;grid-template-columns:1fr 1fr;gap:4px}.btc{background:var(--p2);border:1px solid var(--l);border-radius:8px;padding:6px}.btnm{font-size:9px;color:var(--m)}.bts{font-size:13px;font-weight:900;margin:2px 0}.det{font-size:8px;color:var(--m);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.actions{display:grid;grid-template-columns:1fr 1fr 1.2fr;gap:4px}button{border:0;border-radius:7px;padding:7px;font-size:9px;font-weight:900;cursor:pointer}.run{background:#e25f5f;color:white}.reset{background:#f2c15d}.test{background:#7185ff;color:white}
.log{flex:1;min-height:80px;background:#0d1424;border:1px solid var(--l);border-radius:8px;padding:6px;overflow:auto;font:8px/1.45 Consolas,monospace}.lt{color:#71809a}.lok{color:var(--ok)}.ler{color:var(--d)}.lwr{color:var(--w)}
@media(max-width:1050px){html,body{overflow:auto}.wrap{height:auto}.grid{grid-template-columns:1fr}.video{height:55vh}}
</style></head><body><div class="wrap">
<div class="top"><div><h1>Vision Safety Node</h1><div class="sub">Detect → Proximity → Decide → Bluetooth Handoff</div></div><div id="badge" class="badge">SYSTEM READY</div></div>
<div class="grid"><div class="card video"><img src="/video_feed"></div><div class="card side">
<div class="lab">SAFETY DECISION</div><div class="hero"><div><div id="status" class="state">SAFE</div><div id="desc" class="sm">Monitoring</div></div><div style="text-align:right"><b id="equip">STOP</b><div class="sm">Equipment Motion</div></div></div>
<div class="lab">PROCESS PIPELINE</div><div class="pipe"><div class="stage"><div class="n">01 DETECT</div><div id="d1" class="v">WAIT</div></div><div class="stage"><div class="n">02 PROXIMITY</div><div id="d2" class="v">SAFE</div></div><div class="stage"><div class="n">03 DECIDE</div><div id="d3" class="v">SAFE</div></div><div class="stage"><div class="n">04 SEND</div><div id="d4" class="v">READY</div></div></div>
<div class="rows"><div class="row"><span>Person</span><b id="person">-</b></div><div class="row"><span>Excavator</span><b id="exc">-</b></div><div class="row"><span>Worker Near</span><b id="near">false</b></div><div class="row"><span>Inference</span><b id="inf">0 ms</b></div><div class="row"><span>FPS</span><b id="fps">0</b></div><div class="row"><span>Motion Score</span><b id="motionScore">0</b></div><div class="row"><span>BT total</span><b id="btm">-</b></div></div>
<div class="lab">BLUETOOTH DELIVERY</div><div class="bt"><div class="btc"><div class="btnm">Audio Jetson</div><div id="as" class="bts">READY</div><div id="ad" class="det">B4:8C:9D:34:D6:48</div></div><div class="btc"><div class="btnm">Raspberry Pi / Excavator</div><div id="ps" class="bts">READY</div><div id="pd" class="det">DC:A6:32:7F:85:01</div></div></div>
<div class="actions"><button id="eb" class="run" onclick="toggleE()">AUTO MOTION</button><button class="reset" onclick="resetS()">Manual Reset</button><button class="test" onclick="testE()">Send TEST EVENT</button></div>
<div class="lab">EVENT / DELIVERY LOG</div><div id="logs" class="log"></div>
</div></div></div>
<script>
const dot=c=>`<span class="dot ${c}"></span>`;
async function refresh(){let r=await fetch('/api/status'),s=await r.json(),danger=s.status==='DANGER';
status.textContent=s.status;status.style.color=danger?'var(--d)':'var(--ok)';equip.textContent=s.equipment_state;
desc.textContent=danger?'Hazard latched — manual reset required':(s.equipment_state==='RUNNING'?'Excavator moving — protection active':'Excavator stopped — monitoring');
person.textContent=s.person_detected?`DETECTED ${s.person_confidence}`:'NOT DETECTED';exc.textContent=s.excavator_detected?`DETECTED ${s.excavator_confidence}`:'NOT DETECTED';near.textContent=s.worker_near_excavator;inf.textContent=s.inference_ms+' ms';fps.textContent=s.fps;motionScore.textContent=s.motion_score;btm.textContent=s.bt_total_ms==null?'-':s.bt_total_ms+' ms';
let both=s.person_detected&&s.excavator_detected;d1.innerHTML=dot(both?'ok':'')+(both?'PERSON + EXCAVATOR':'MONITORING');d2.innerHTML=dot(s.worker_near_excavator?'warn':'ok')+(s.worker_near_excavator?'NEAR':'SAFE');d3.innerHTML=dot(danger?'danger':'ok')+(danger?'HAZARD':'SAFE');
let a=s.audio_bt_status,p=s.control_bt_status,good=x=>['ACKED','SENT'].includes(x),bad=x=>['FAILED','ERROR'].includes(x);d4.innerHTML=dot(bad(a)||bad(p)?'danger':(good(a)&&good(p)?'ok':''))+(good(a)&&good(p)?'DELIVERED':(bad(a)||bad(p)?'PARTIAL':'READY'));
as.textContent=a;ps.textContent=p;as.style.color=good(a)?'var(--ok)':bad(a)?'var(--d)':'var(--t)';ps.style.color=good(p)?'var(--ok)':bad(p)?'var(--d)':'var(--t)';
ad.textContent=s.audio_bt_error||('B4:8C:9D:34:D6:48'+(s.audio_send_ms!=null?' · '+s.audio_send_ms+' ms':''));pd.textContent=s.control_bt_error||('DC:A6:32:7F:85:01'+(s.control_send_ms!=null?' · '+s.control_send_ms+' ms':''));
logs.innerHTML=(s.event_logs||[]).map(x=>`<div class="${x.level==='ERROR'?'ler':x.level==='WARN'?'lwr':x.level==='OK'?'lok':''}"><span class="lt">[${x.time}]</span> ${x.message}</div>`).join('')||'<span class="lt">No event yet</span>';logs.scrollTop=logs.scrollHeight;
badge.textContent=danger?'HAZARD ACTIVE':'SYSTEM READY';badge.style.color=danger?'var(--d)':'var(--ok)';eb.textContent='AUTO MOTION'}
async function toggleE(){alert('v.6: 굴착기 RUNNING/STOP은 카메라 픽셀 움직임으로 자동 판단합니다.');}async function resetS(){let r=await fetch('/api/reset',{method:'POST'}),d=await r.json();if(!d.ok)alert(d.reason||'Reset blocked');refresh()}async function testE(){await fetch('/api/test/event',{method:'POST'});refresh()}
setInterval(refresh,500);refresh();
</script></body></html>
"""


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--camera", type=int, default=0)
    p.add_argument("--width", type=int, default=640)
    p.add_argument("--height", type=int, default=480)
    p.add_argument("--jpeg-quality", type=int, default=75)
    p.add_argument("--host", default="0.0.0.0")
    p.add_argument("--port", type=int, default=5000)

    p.add_argument("--audio-mac", default="B4:8C:9D:34:D6:48")
    p.add_argument("--pi-mac", default="DC:A6:32:7F:85:01")
    p.add_argument("--bt-channel", type=int, default=1)

    p.add_argument("--model", default="best_construction_v1.engine")
    p.add_argument("--imgsz", type=int, default=640)
    p.add_argument("--conf", type=float, default=0.30)
    p.add_argument("--device", default="0")
    return p.parse_args()


class VisionWorker:
    def __init__(self, args, state):
        self.args = args
        self.state = state
        device = int(args.device) if str(args.device).isdigit() else args.device
        self.detector = JetsonYOLODetector(
            model_path=args.model,
            conf=args.conf,
            imgsz=args.imgsz,
            device=device,
        )
        self.hazard = HazardStateMachine()
        self.motion_detector = EquipmentMotionDetector(
            start_threshold=MOTION_START_THRESHOLD,
            stop_threshold=MOTION_STOP_THRESHOLD,
            pixel_threshold=MOTION_PIXEL_THRESHOLD,
            start_frames=MOTION_START_FRAMES,
            stop_frames=MOTION_STOP_FRAMES,
        )
        self.logger = CsvLogger(LOG_PATH)

        self.sender = MultiBluetoothEventSender(
            audio_mac=args.audio_mac,
            control_mac=args.pi_mac,
            channel=args.bt_channel,
        )

        self.stop_event = threading.Event()

    def run(self):
        cap = cv2.VideoCapture(self.args.camera, cv2.CAP_V4L2)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.args.width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.args.height)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        if not cap.isOpened():
            print("[ERROR] camera open failed")
            return

        with self.state.lock:
            self.state.camera_ok = True

        frame_idx = 0
        prev_time = time.perf_counter()

        while not self.stop_event.is_set():
            ok, frame = cap.read()
            if not ok:
                with self.state.lock:
                    self.state.camera_ok = False
                time.sleep(0.05)
                continue

            frame_idx += 1
            frame_start = time.perf_counter()

            with self.state.lock:
                person_enabled = self.state.person_enabled
                excavator_enabled = self.state.excavator_enabled

            self.detector.set_person_enabled(person_enabled)
            self.detector.set_excavator_enabled(excavator_enabled)

            infer_start = time.perf_counter()
            detections = self.detector.detect(frame)
            inference_ms = (time.perf_counter() - infer_start) * 1000.0

            persons = [d for d in detections if d.class_name == "person"]
            excavators = [d for d in detections if d.class_name == "excavator"]
            excavator = max(excavators, key=lambda d: d.confidence, default=None)

            equipment_state, motion_score, motion_pixel_ratio, motion_center_shift = (
                self.motion_detector.update(
                    frame,
                    excavator.bbox if excavator is not None else None,
                )
            )

            h, w = frame.shape[:2]
            dynamic_zone = None
            worker_near = False
            nearest_person = None
            nearest_proximity = None

            for d in detections:
                x1, y1, x2, y2 = d.bbox
                color = (0, 255, 0) if d.class_name == "person" else (255, 128, 0)
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                cv2.putText(
                    frame,
                    f"{d.class_name} {d.confidence:.2f}",
                    (x1, max(20, y1 - 8)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    color,
                    2,
                )

            if excavator is not None:
                dynamic_zone = expand_bbox(
                    excavator.bbox,
                    PROXIMITY_MARGIN_RATIO,
                    w,
                    h,
                )
                zx1, zy1, zx2, zy2 = dynamic_zone
                cv2.rectangle(frame, (zx1, zy1), (zx2, zy2), (0, 165, 255), 2)
                cv2.putText(
                    frame,
                    "AUTO PROXIMITY",
                    (zx1, max(22, zy1 - 8)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.60,
                    (0, 165, 255),
                    2,
                )

                for person in persons:
                    fp = foot_point(person.bbox)
                    cv2.circle(frame, fp, 6, (255, 255, 0), -1)

                    proximity = normalized_distance_to_bbox(fp, excavator.bbox)
                    is_near = point_in_bbox(fp, dynamic_zone)

                    if nearest_proximity is None or proximity < nearest_proximity:
                        nearest_proximity = proximity
                        nearest_person = person

                    if is_near:
                        worker_near = True

            person_conf = nearest_person.confidence if nearest_person else 0.0
            excavator_conf = excavator.confidence if excavator else 0.0
            confidence = (
                min(person_conf, excavator_conf)
                if nearest_person is not None and excavator is not None
                else 0.0
            )

            decision = self.hazard.update(
                worker_near_equipment=worker_near,
                equipment_state=equipment_state,
                confidence=confidence,
                person_confidence=person_conf,
                excavator_confidence=excavator_conf,
                proximity=nearest_proximity,
            )

            if decision.just_triggered and decision.event:
                self.state.add_log(f"HAZARD EVENT generated: {decision.event['event']}", "WARN")
                results=self.sender.send(decision.event)
                audio=results.get("audio",{}); control=results.get("control",{})
                with self.state.lock:
                    self.state.last_event=decision.event
                    self.state.last_event_time=int(time.time()*1000)
                    self.state.audio_bt_status=audio.get("status","FAILED")
                    self.state.control_bt_status=control.get("status","FAILED")
                    self.state.audio_bt_error=audio.get("error")
                    self.state.control_bt_error=control.get("error")
                    self.state.audio_send_ms=audio.get("send_ms")
                    self.state.control_send_ms=control.get("send_ms")
                    self.state.bt_total_ms=results.get("total_ms")
                self.state.add_log(f"Audio Jetson: {audio.get('status')} {audio.get('send_ms')} ms" if audio.get("ok") else f"Audio Jetson: FAILED - {audio.get('error')}", "OK" if audio.get("ok") else "ERROR")
                self.state.add_log(f"Raspberry Pi: {control.get('status')} {control.get('send_ms')} ms" if control.get("ok") else f"Raspberry Pi: FAILED - {control.get('error')}", "OK" if control.get("ok") else "ERROR")

            now = time.perf_counter()
            fps = 1.0 / max(now - prev_time, 1e-6)
            prev_time = now

            status_text = "DANGER" if decision.active else "SAFE"
            status_color = (0, 0, 255) if decision.active else (0, 255, 0)

            cv2.putText(
                frame,
                f"STATUS: {status_text}",
                (20, 35),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.9,
                status_color,
                2,
            )
            cv2.putText(
                frame,
                f"EQUIPMENT: {equipment_state}",
                (20, 70),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 255),
                2,
            )
            cv2.putText(
                frame,
                f"MOTION: {equipment_state} {motion_score:.3f}",
                (20, 103),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.60,
                (255, 255, 255),
                2,
            )
            cv2.putText(
                frame,
                f"NEAR: {str(worker_near).upper()}",
                (20, 132),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (255, 255, 255),
                2,
            )
            cv2.putText(
                frame,
                f"FPS: {fps:.1f}",
                (20, 161),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (255, 255, 255),
                2,
            )

            frame_ms = (time.perf_counter() - frame_start) * 1000.0

           
            person_bbox = nearest_person.bbox if nearest_person else None
            person_conf_log = nearest_person.confidence if nearest_person else None
            self.logger.write(
                frame_idx,
                person_bbox,
                person_conf_log,
                worker_near,
                equipment_state,
                decision.active,
                inference_ms,
                frame_ms,
            )

            ok_jpg, jpg = cv2.imencode(
                ".jpg",
                frame,
                [cv2.IMWRITE_JPEG_QUALITY, self.args.jpeg_quality],
            )

            if ok_jpg:
                with self.state.lock:
                    self.state.jpeg_frame = jpg.tobytes()
                    self.state.status = status_text
                    self.state.worker_in_zone = worker_near
                    self.state.fps = fps
                    self.state.inference_ms = inference_ms
                    self.state.frame_ms = frame_ms
                    self.state.camera_ok = True
                    self.state.reset_allowed = decision.reset_allowed
                    self.state.person_detected = bool(persons)
                    self.state.excavator_detected = bool(excavators)
                    self.state.person_confidence = max([p.confidence for p in persons], default=0.0)
                    self.state.excavator_confidence = excavator_conf
                    self.state.proximity = nearest_proximity
                    self.state.equipment_state = equipment_state
                    self.state.motion_score = motion_score
                    self.state.motion_pixel_ratio = motion_pixel_ratio
                    self.state.motion_center_shift = motion_center_shift
                    self.state.motion_source = "VISION_PIXEL"

        cap.release()


def make_app(state, worker):
    app = Flask(__name__)

    @app.get("/")
    def index():
        return render_template_string(HTML)

    @app.get("/video_feed")
    def video_feed():
        def generate():
            while True:
                with state.lock:
                    frame = state.jpeg_frame
                if frame is None:
                    time.sleep(0.05)
                    continue
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n"
                    + frame
                    + b"\r\n"
                )
                time.sleep(0.01)

        return Response(
            generate(),
            mimetype="multipart/x-mixed-replace; boundary=frame",
        )

    @app.get("/api/status")
    def api_status():
        return jsonify(state.snapshot())

    @app.post("/api/equipment/toggle")
    def api_toggle_equipment():
        return jsonify({
            "ok": False,
            "reason": "v.6 uses automatic vision motion detection.",
            "equipment_state": state.snapshot()["equipment_state"],
        }), 409

    @app.post("/api/equipment")
    def api_set_equipment():
        return jsonify({
            "ok": False,
            "reason": "v.6 equipment state is determined by visual motion.",
            "equipment_state": state.snapshot()["equipment_state"],
        }), 409

    @app.post("/api/reset")
    def api_reset():
        ok = worker.hazard.reset()
        if not ok:
            return jsonify({
                "ok": False,
                "reason": "Worker is still near excavator.",
            }), 409

        with state.lock:
            state.status = "SAFE"
            state.reset_allowed = False
            state.audio_bt_status = "READY"
            state.control_bt_status = "READY"
            state.audio_bt_error = None
            state.control_bt_error = None
        return jsonify({"ok": True})

    @app.post("/api/test/event")
    def api_test_event():
        event={"source":"VISION","event":"WORKER_NEAR_MOVING_EXCAVATOR","equipment":"EXCAVATOR_01",
               "equipment_state":state.snapshot()["equipment_state"],"confidence":1.0,
               "person_confidence":1.0,"excavator_confidence":1.0,"proximity":0.0,
               "test":True,"timestamp":int(time.time()*1000)}
        state.add_log("TEST EVENT generated / Bluetooth send started","WARN")
        results=worker.sender.send(event); audio=results.get("audio",{}); control=results.get("control",{})
        with state.lock:
            state.last_event=event; state.last_event_time=event["timestamp"]
            state.audio_bt_status=audio.get("status","FAILED"); state.control_bt_status=control.get("status","FAILED")
            state.audio_bt_error=audio.get("error"); state.control_bt_error=control.get("error")
            state.audio_send_ms=audio.get("send_ms"); state.control_send_ms=control.get("send_ms")
            state.bt_total_ms=results.get("total_ms")
        state.add_log(f"Audio Jetson: {audio.get('status')} {audio.get('send_ms')} ms" if audio.get("ok") else f"Audio Jetson: FAILED - {audio.get('error')}", "OK" if audio.get("ok") else "ERROR")
        state.add_log(f"Raspberry Pi: {control.get('status')} {control.get('send_ms')} ms" if control.get("ok") else f"Raspberry Pi: FAILED - {control.get('error')}", "OK" if control.get("ok") else "ERROR")
        state.add_log(f"Bluetooth handoff finished: {results.get('total_ms')} ms","INFO")
        return jsonify({"ok":bool(audio.get("ok") and control.get("ok")),"audio":audio,"control":control,"total_ms":results.get("total_ms")})

    @app.post("/api/test/person/toggle")
    def api_toggle_person():
        with state.lock:
            state.person_enabled = not state.person_enabled
            value = state.person_enabled
        return jsonify({"person_enabled": value})

    @app.post("/api/test/excavator/toggle")
    def api_toggle_excavator():
        with state.lock:
            state.excavator_enabled = not state.excavator_enabled
            value = state.excavator_enabled
        return jsonify({"excavator_enabled": value})

    return app


def main():
    args = parse_args()
    state = RuntimeState(DEFAULT_EQUIPMENT_STATE)
    worker = VisionWorker(args, state)

    t = threading.Thread(target=worker.run, daemon=True)
    t.start()

    app = make_app(state, worker)

    print(f"[WEB] http://<JETSON_IP>:{args.port}")
    print(f"[BT-AUDIO] {args.audio_mac} ch={args.bt_channel}")
    print(f"[BT-PI]    {args.pi_mac} ch={args.bt_channel}")

    try:
        app.run(
            host=args.host,
            port=args.port,
            threaded=True,
            debug=False,
            use_reloader=False,
        )
    finally:
        worker.stop_event.set()
        t.join(timeout=2)


if __name__ == "__main__":
    main()
