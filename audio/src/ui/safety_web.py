from flask import Flask, jsonify, request
from pathlib import Path
import csv
import os
import signal
import subprocess
import sys
import time

app = Flask(__name__)

ROOT = Path(
    os.getenv(
        "SAYFE_PROJECT_ROOT",
        str(Path(__file__).resolve().parents[2]),
    )
).resolve()
LOG_CSV = ROOT / "output" / "realtime_safe_path" / "safe_path_log.csv"

state = {
    "running": False,
    "languages": ["ko", "zh", "vi"],
}

broadcast_process = None


HTML = r"""
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<title>SAY:FE Safety Broadcast</title>


<style>
:root {
    --bg: #eef1f5;
    --card: #ffffff;
    --text: #111318;
    --muted: #6d7786;
    --accent: #5a78a6;
    --accent-soft: #8ea6c6;
    --accent-pale: #eef3f8;
    --line: #9db1cd;
    --border: #e1e6ec;
    --danger: #d9534f;
    --success: #27ae60;
}

* {
    box-sizing: border-box;
}

body {
    margin: 0;
    background: var(--bg);
    font-family:
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        "Noto Sans KR",
        Arial,
        sans-serif;
    color: var(--text);
}

.container {
    width: 980px;
    max-width: calc(100% - 40px);
    margin: 28px auto 48px;
}

.header {
    margin: 0 0 28px;
    padding: 0;
}

.sayfe-header-image {
    display: block;
    width: 100%;
    max-width: 100%;
    height: auto;
    object-fit: contain;
    object-position: left center;
    margin: 0 0 18px;
    padding: 0;
    border: 0;
}

.hero-title {
    font-size: 28px;
    font-weight: 600;
    line-height: 1.5;
    letter-spacing: -1.1px;
    margin-top: 0;
}

.card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 28px 32px;
    margin-bottom: 18px;
    box-shadow: 0 3px 14px rgba(23, 38, 56, 0.045);
}

.status {
    text-align: center;
    padding: 30px 32px;
}

.status-dot {
    display: inline-block;
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: var(--success);
    margin-right: 8px;
}

.status-title {
    font-size: 20px;
    font-weight: 800;
    letter-spacing: 0.2px;
}

.status-message {
    margin-top: 8px;
    color: var(--muted);
    font-size: 14px;
}

.section-title {
    font-size: 15px;
    font-weight: 800;
    margin-bottom: 18px;
    letter-spacing: -0.2px;
}

.languages {
    display: flex;
    gap: 12px;
    margin-bottom: 22px;
}

.language {
    flex: 1;
    border: 1.5px solid #bfc9d6;
    border-radius: 10px;
    padding: 16px;
    cursor: pointer;
    text-align: center;
    transition: 0.15s ease;
    user-select: none;
    background: #ffffff;
}

.language:hover {
    border-color: var(--accent);
    background: #f8fafc;
}

.language.selected {
    border: 2px solid var(--accent);
    background: var(--accent-pale);
    color: var(--accent);
}

.language input {
    display: none;
}

.language-name {
    font-size: 16px;
    font-weight: 750;
}

.start-button {
    width: 100%;
    height: 54px;
    border: 0;
    border-radius: 9px;
    background: var(--accent);
    color: white;
    font-size: 16px;
    font-weight: 800;
    cursor: pointer;
    transition: 0.15s ease;
}

.start-button:hover {
    background: #48658e;
}

.start-button.running {
    background: var(--danger);
}

.start-button.running:hover {
    background: #c74642;
}

.label {
    font-size: 13px;
    color: var(--muted);
    margin-bottom: 10px;
    font-weight: 650;
}

.main-text {
    font-size: 21px;
    line-height: 1.6;
    min-height: 34px;
    word-break: keep-all;
}

.translation-block + .translation-block {
    border-top: 1px solid #e7ebf0;
    margin-top: 22px;
    padding-top: 22px;
}

.language-label {
    font-size: 14px;
    font-weight: 800;
    color: var(--accent);
    margin-bottom: 8px;
}

.translation {
    font-size: 18px;
    line-height: 1.6;
}

.bottom {
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.latency-label {
    font-size: 13px;
    color: var(--muted);
    font-weight: 650;
}

.latency {
    font-size: 22px;
    font-weight: 800;
    margin-top: 4px;
}

.history-button {
    border: 1.5px solid #c6d0dc;
    color: var(--accent);
    background: white;
    padding: 10px 16px;
    border-radius: 8px;
    cursor: pointer;
    font-weight: 750;
}

.history-button:hover {
    background: var(--accent-pale);
    border-color: var(--accent);
}

.hidden {
    display: none;
}

.history {
    margin-top: 20px;
    border-top: 1px solid #e7ebf0;
    padding-top: 18px;
}

.history-item {
    padding: 13px 0;
    border-bottom: 1px solid #eef1f4;
}

.history-time {
    font-size: 12px;
    color: #8b94a1;
}

.history-text {
    margin-top: 5px;
    font-size: 14px;
}

@media (max-width: 650px) {
    .container {
        max-width: calc(100% - 24px);
        margin-top: 18px;
    }

    .hero-title {
        font-size: 22px;
    }

    .languages {
        flex-direction: column;
    }

    .card {
        padding: 22px;
    }
}

</style>

</head>

<body>

<div class="container">

    <div class="header">
        <img
            src="/static/sayfe_header.png"
            class="sayfe-header-image"
            alt="SAY:FE - 모두의 안전을, 각자의 언어로."
        >

        <div class="hero-title">
            <div>Edge AI 기반 건설현장</div>
            <div>실시간 다국어 안전소통 및 위험대응 시스템</div>
        </div>
    </div>


<div class="card status">
        <div class="status-title">
            <span class="status-dot" id="statusDot"></span>
            <span id="statusTitle">READY</span>
        </div>

        <div class="status-message" id="statusMessage">
            안전방송 시스템 준비 완료
        </div>
    </div>


    <div class="card">

        <div class="section-title">
            송출 언어
        </div>

        <div class="languages">

            <label class="language selected" id="box-ko">
                <input type="checkbox" id="lang-ko" checked>
                <div class="language-name">KOREAN</div>
            </label>

            <label class="language selected" id="box-zh">
                <input type="checkbox" id="lang-zh" checked>
                <div class="language-name">CHINESE</div>
            </label>

            <label class="language selected" id="box-vi">
                <input type="checkbox" id="lang-vi" checked>
                <div class="language-name">VIETNAMESE</div>
            </label>

        </div>

        <button
            class="start-button"
            id="startButton"
            onclick="toggleBroadcast()"
        >
            ▶ 방송 시작
        </button>

    </div>


    <div class="card">

        <div class="label">
            관리자 안전지시
        </div>

        <div class="main-text" id="koreanText">
            송출을 시작하고 한국어로 안전지시를 말씀해주세요.
        </div>

    </div>


    <div class="card" id="translationCard">

        <div class="section-title">
            다국어 송출 결과
        </div>

        <div class="translation-block" id="zhBlock">
            <div class="language-label">CHINESE</div>
            <div class="translation" id="zhText">-</div>
        </div>

        <div class="translation-block" id="viBlock">
            <div class="language-label">VIETNAMESE</div>
            <div class="translation" id="viText">-</div>
        </div>

    </div>


    <div class="card">

        <div class="bottom">

            <div>
                <div class="latency-label">
                    전체 응답 시간
                </div>

                <div class="latency" id="latency">
                    -
                </div>
            </div>

            <button
                class="history-button"
                onclick="toggleHistory()"
            >
                송출 이력
            </button>

        </div>

        <div class="history hidden" id="history"></div>

    </div>

</div>


<script>

let running = false;
let historyOpen = false;


function setBroadcastUi(isRunning) {

    const button = document.getElementById("startButton");
    running = isRunning;

    button.innerText = isRunning ? "■ 방송 종료" : "▶ 방송 시작";
    button.classList.toggle("running", isRunning);

    document.getElementById("statusTitle").innerText =
        isRunning ? "ON AIR" : "READY";

    document.getElementById("statusMessage").innerText = isRunning
        ? "관리자의 안전지시를 기다리고 있습니다."
        : "안전방송 시스템 준비 완료";

    ["ko", "zh", "vi"].forEach(lang => {
        document.getElementById("lang-" + lang).disabled = isRunning;
    });
}


function updateLanguageStyle(lang) {

    const checkbox =
        document.getElementById("lang-" + lang);

    const box =
        document.getElementById("box-" + lang);

    if (checkbox.checked) {
        box.classList.add("selected");
    } else {
        box.classList.remove("selected");
    }
}


["ko", "zh", "vi"].forEach(lang => {

    document
        .getElementById("lang-" + lang)
        .addEventListener("change", () => {

            updateLanguageStyle(lang);
            updateTranslationVisibility();

        });
});


function updateTranslationVisibility() {

    const zh =
        document.getElementById("lang-zh").checked;

    const vi =
        document.getElementById("lang-vi").checked;

    document
        .getElementById("zhBlock")
        .classList.toggle("hidden", !zh);

    document
        .getElementById("viBlock")
        .classList.toggle("hidden", !vi);

    document
        .getElementById("translationCard")
        .classList.toggle(
            "hidden",
            !zh && !vi
        );
}


async function toggleBroadcast() {

    const button =
        document.getElementById("startButton");

    if (!running) {

        const languages = [];

        if (document.getElementById("lang-ko").checked)
            languages.push("ko");

        if (document.getElementById("lang-zh").checked)
            languages.push("zh");

        if (document.getElementById("lang-vi").checked)
            languages.push("vi");

        if (languages.length === 0) {
            alert("방송할 언어를 하나 이상 선택해주세요.");
            return;
        }

        const response = await fetch(
            "/api/start",
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    languages: languages
                })
            }
        );

        const data = await response.json();

        if (!data.ok) {
            alert(data.error || "시작할 수 없습니다.");
            return;
        }

        setBroadcastUi(true);

    } else {

        const response = await fetch(
            "/api/stop",
            {method: "POST"}
        );

        const data = await response.json();
        if (!data.ok) {
            alert(data.error || "방송을 종료할 수 없습니다.");
            return;
        }
        setBroadcastUi(false);
    }
}


async function refreshState() {

    try {

        const response =
            await fetch("/api/state");

        const data =
            await response.json();

        // The server owns process truth.  If the controller exits because of
        // an ALSA/VAD/worker error, immediately clear the local ON AIR state.
        setBroadcastUi(Boolean(data.running));

        if (data.latest) {

            document.getElementById(
                "koreanText"
            ).innerText =
                data.latest.stt_raw || "-";

            document.getElementById(
                "zhText"
            ).innerText =
                data.latest.zh || "-";

            document.getElementById(
                "viText"
            ).innerText =
                data.latest.vi || "-";

            const total =
                data.latest.post_utterance_total_sec;

            document.getElementById(
                "latency"
            ).innerText =
                total
                ? Number(total).toFixed(2) + " s"
                : "-";
        }

    } catch (error) {
        console.log(error);
    }
}


async function toggleHistory() {

    historyOpen = !historyOpen;

    const area =
        document.getElementById("history");

    if (!historyOpen) {
        area.classList.add("hidden");
        return;
    }

    const response =
        await fetch("/api/history");

    const data =
        await response.json();

    area.innerHTML = "";

    data.rows.forEach(row => {

        const item =
            document.createElement("div");

        item.className = "history-item";

        item.innerHTML =
            '<div class="history-time">' +
            (row.timestamp || "") +
            '</div>' +
            '<div class="history-text">' +
            (row.stt_raw || "") +
            '</div>';

        area.appendChild(item);
    });

    if (data.rows.length === 0) {
        area.innerHTML =
            '<div class="history-text">' +
            '저장된 송출 이력이 없습니다.' +
            '</div>';
    }

    area.classList.remove("hidden");
}


setInterval(
    refreshState,
    1000
);

updateTranslationVisibility();

</script>

</body>
</html>
"""


def read_latest():
    if not LOG_CSV.exists():
        return None

    try:
        with LOG_CSV.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as f:
            rows = list(csv.DictReader(f))

        if not rows:
            return None

        return rows[-1]

    except Exception:
        return None


def read_history(limit=10):
    if not LOG_CSV.exists():
        return []

    try:
        with LOG_CSV.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as f:
            rows = list(csv.DictReader(f))

        return list(reversed(rows[-limit:]))

    except Exception:
        return []


@app.route("/")
def index():
    return HTML


@app.route("/api/state")
def api_state():
   
    if (
        broadcast_process is not None
        and broadcast_process.poll() is not None
    ):
        state["running"] = False

    return jsonify({
        "running": state["running"],
        "languages": state["languages"],
        "latest": read_latest(),
    })


def stop_broadcast_process() -> None:
    """Stop the controller session and every inherited worker/aplay child."""
    global broadcast_process

    process = broadcast_process
    broadcast_process = None
    if process is None or process.poll() is not None:
        return

    try:
        process_group = os.getpgid(process.pid)
        os.killpg(process_group, signal.SIGINT)
        try:
            process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            os.killpg(process_group, signal.SIGTERM)
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                os.killpg(process_group, signal.SIGKILL)
                process.wait(timeout=3)
    except ProcessLookupError:
        pass


@app.route("/api/history")
def api_history():
    return jsonify({
        "rows": read_history(10)
    })


@app.route("/api/start", methods=["POST"])
def api_start():
    global broadcast_process

    if broadcast_process is not None and broadcast_process.poll() is None:
        return jsonify({
            "ok": False,
            "error": "이미 방송이 실행 중입니다.",
        }), 400

    data = request.get_json(silent=True) or {}

    languages = data.get(
        "languages",
        ["ko", "zh", "vi"],
    )

    valid = [
        lang
        for lang in languages
        if lang in ("ko", "zh", "vi")
    ]

    if not valid:
        return jsonify({
            "ok": False,
            "error": "송출 언어를 선택해주세요.",
        }), 400

    env = os.environ.copy()

    env["SAYFE_LANGUAGES"] = ",".join(valid)
    env["TOKENIZERS_PARALLELISM"] = "false"
    env["CONSTRUCTION_SAFETY_TRANSLATION_DEVICE"] = "cuda"
    env["PYTHONPATH"] = str(ROOT)

    command = [
        sys.executable,
        str(ROOT / "scripts" / "ui_mic_controller.py"),
    ]

    try:
        broadcast_process = subprocess.Popen(
            command,
            cwd=str(ROOT),
            env=env,
            start_new_session=True,
        )

        state["running"] = True
        state["languages"] = valid

        print()
        print("=" * 60)
        print("SAY:FE BROADCAST START")
        print("LANGUAGES:", valid)
        print("PID:", broadcast_process.pid)
        print("=" * 60)

        return jsonify({
            "ok": True,
            "languages": valid,
            "pid": broadcast_process.pid,
        })

    except Exception as exc:
        broadcast_process = None
        state["running"] = False

        return jsonify({
            "ok": False,
            "error": str(exc),
        }), 500

@app.route("/api/stop", methods=["POST"])
def api_stop():
    stop_broadcast_process()

    state["running"] = False

    print()
    print("=" * 60)
    print("SAY:FE BROADCAST STOP")
    print("=" * 60)

    return jsonify({
        "ok": True
    })


if __name__ == "__main__":

    print("=" * 60)
    print("SAY:FE Safety Broadcast UI")
    print("http://0.0.0.0:5000")
    print("=" * 60)

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False,
        threaded=True,
    )
