# Vision Heartbeat integration

## Current deployment state

Both `config.json` and `config.example.json` have `heartbeat.enabled=false`.
The existing running application was not stopped or restarted. No connection to
the audio Jetson or equipment was made during implementation or tests.
The new code takes effect on a future approved application start, not by editing
the files of the running process.

Original files and the supplied reference were copied and SHA-256 verified before
editing, at `backups/heartbeat_20261031T160936+0900/`. `SHA256.json` identifies each
original source and hash. Protected camera/detector/risk/web/state files remain
unchanged. `server_jetson.py` must not be imported or run.

## Protocol and process lifecycle

`vision_heartbeat.py` contains the sender and dual-camera observer only. There is
no import-time socket, receiver service, output-path calculation, equipment command,
or risk event. The destination is `192.168.100.2:8766`, with a 1 second target
cadence, a 0.5 second connection/send timeout, and a 2.5 second component timeout.

Frames are UTF-8 JSON followed by `\n`: `protocol_version=1`,
`type="VISION_HEARTBEAT"`, `node_id`, UUID `boot_id`, positive increasing `seq`,
ISO wall-clock `sent_at`, `health`, `vision.cameras`, and `control_command=null`.
The receiver needs no ACK. Reconnection preserves boot ID and sequence; failed
attempts may leave sequence gaps. A newly created sender generates a new UUID.

`main.py` configures the observer before starting the pipeline, starts its separate
sender after the pipeline starts, and stops it before pipeline cleanup. This is
independent of the web-enabled flag. With Heartbeat disabled, it creates neither
an observer nor a sender. Warmup is not counted as live-camera inference progress.
Initial missing frames/results are reported as unhealthy, not fabricated as ready.

The sender uses monotonic deadlines and skips missed slots without catch-up bursts.
This avoids adding transmission time to every interval, but is not a hard realtime
guarantee under OS scheduling, network or CPU stalls. Network calls and all retries
stay in the sender worker. Its socket has bounded timeouts; stop interrupts active
sockets and the interval wait. Repeated identical send errors are logged once until
the error changes or transmission succeeds. `last_error` and `sent_count` are local
sender diagnostics; they are not equipment ACKs.

## Health semantics

The observer reads each real camera's capture count, successful read timestamp,
error, open/stop flags and worker state under the camera lock, with a bounded 10ms
lock wait. A live thread alone is insufficient. Capture timestamps are OpenCV read
return times; this does not detect a camera returning identical frozen image pixels.
The existing 1 second observation/risk staleness policy is not changed.

Only a successful `detector.detect()` return updates that camera's inference
completion timestamp, count and source frame sequence. The timestamp comes from
the detector's local `inference_end_ns`. An actual detector exception sets a fault
without refreshing that timestamp or count; the next success clears it. A later
ground/risk/publication error does not get relabeled as a detector exception.

Both cameras must be fresh and free of capture errors for `health.camera_ok=true`.
Both cameras must have fresh successful inference and no detector errors for
`health.inference_ok=true`. Aggregate ages are the oldest per-camera ages, or null
if one camera has no usable timestamp. `health.frame_seq` is the sum of successful
inference counts, not a camera capture sequence. FPS is successful YOLO returns in
the recent two-second window. `inference_ms` is the latest successful detector
inference-duration metric. `vision.cameras` preserves the individual values.
The supplied audio receiver keeps the payload in memory but its status JSON
publisher exposes aggregate health only, not the nested `vision.cameras` object.
Displaying per-camera detail there would require a separate audio-side change;
the sender already includes it on the wire.

Per-camera `inference_reason` distinguishes `DETECTOR_ERROR`, `INPUT_UNAVAILABLE`,
`NO_SUCCESSFUL_INFERENCE`, and `INFERENCE_PROGRESS_STALE`. When capture stops, the
corresponding inference eventually becomes stale too; `INPUT_UNAVAILABLE` identifies
the missing input without claiming the YOLO engine itself failed. A stale progress
reason with fresh input identifies missing inference progress, not its root cause:
model, scheduling and downstream backpressure may need separate diagnosis.

All component ages are computed on Vision. The receiver computes communication age
using its own clock. No monotonic timestamp is compared across devices or transmitted
as an absolute time for such comparisons. Health faults continue to be transmitted,
so DEVICE_FAULT remains distinct from COMM_LOST. Detection latency includes the
sender's sampling interval and receiver UI publication interval.

## Automated validation

Run with the existing environment, without launching `main.py`:

```bash
/home/hansungelec/venvs/sayfe_vision/bin/python -s -B -m unittest discover -s tests -v
```

The new tests substitute every TCP connection and use fake cameras, detector and
clock. The receiver decoder and status evaluator fixture in
`tests/fixtures/vision_heartbeat_receiver_v1.py` was extracted unchanged from the
supplied reference and compared by AST; its header records the original SHA-256.
It contains no receiver service, socket or file publisher. It verifies JSON-lines,
sequence/boot handling and NORMAL/DEVICE_FAULT/COMM_LOST/recovery transitions against
the actual supplied receiver logic. It does not establish network reachability or
prove that the running audio Jetson uses this exact source/configuration.

Validation completed on 2026-10-31: the full discovery run executed 242 tests,
with 240 passing and two JavaScript wrappers skipped because Node was not on PATH.
Both skipped wrappers were then rerun successfully with the existing VS Code Node
via `SAYFE_NODE`. No installation or environment change was needed. The new
Heartbeat suite contains 26 passing tests. Logs and final source hashes are saved
under `runs/heartbeat_validation_*/`.

## Future application procedure — do not execute automatically

1. On the actual host, identify the running Vision PID, command line, Python
   executable and original startup mechanism. Inspect existing TCP/RFCOMM/control
   services and logs read-only. Existing `audio_connected=false`,
   `control_connected=false` and UI "미연결" values are fixed declarations, not a
   measured connection check. A sandbox process/socket list cannot settle this.
2. Check the audio Jetson's actual receiver source/settings against the reference:
   bind address `192.168.100.2`, port `8766`, allowed peer `192.168.100.1`, and
   timeout 3.5 seconds. Find its status JSON from `SAYFE_VISION_STATUS_JSON` or its
   actual source-location default. Confirm no second sender owns its single client
   receive loop. Confirm routing gives this sender source IP `192.168.100.1`.
3. Check UI merging before deployment: this health channel intentionally omits risk
   status/events. The supplied receiver derives `hazard_latched=false` if no
   `vision.status="DANGER"` exists. That display value must not clear or override
   the existing RFCOMM hazard state or authorize control. No existing RFCOMM path
   is changed by this implementation.
4. After separate authorization for service interruption and actual Heartbeat
   activation, back up configuration again, set only `heartbeat.enabled=true`, and
   stop/start the existing application using its original mechanism. Do not run a
   second instance or use `server_jetson.py`. The original camera lock protection
   remains. This implementation has not performed this step.
5. Read the audio receiver status JSON/UI. `heartbeat_seq` and `heartbeat_count`
   should advance, `boot_id` should remain stable across TCP reconnects, and ages
   should stay fresh. No device command or audio danger event is needed to inspect
   health. Recovery/restart may leave `manual_reset_required` and `recovery_pending`
   set; Heartbeat does not authorize automatic reenable.

Expected receiver states:

| Condition | Status / details |
|---|---|
| Fresh capture and inference on both cameras | NORMAL; camera_ok=true; inference_ok=true |
| Capture error or stale capture | DEVICE_FAULT; CAMERA (possibly CAMERA+INFERENCE later) |
| Capture fresh, successful inference stale | DEVICE_FAULT; INFERENCE |
| No valid Heartbeat for more than 3.5 seconds | COMM_LOST; COMMUNICATION |
| Healthy communication recovers | NORMAL with manual recovery flags retained |

The receiver also times out if no first Heartbeat arrives. Its component/startup
faults latch manual confirmation flags. Do not auto-reset or fabricate a startup
grace period in the sender. Live cable removal, model stalls, deliberate missed
Heartbeats and application restart tests require a separately approved maintenance
window. The automated fake-clock tests already cover the state transitions.

Remaining live checks: deployed receiver/version and UI merge, physical interfaces
and routing, actual TCP reconnection and timing under Jetson load, full live startup/
shutdown, and any separately running audio/RFCOMM/equipment adapter. Heartbeat
availability alone is not proof that those control paths are connected or working.
