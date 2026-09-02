from __future__ import annotations

import json
import logging
import os
import socket
import threading
from collections.abc import Callable
from typing import Any


LOGGER = logging.getLogger(__name__)
VISION_EVENT = "WORKER_NEAR_MOVING_EXCAVATOR"
FAST_PATH_EVENT = "WORKER_IN_EQUIPMENT_ZONE"


class NewlineJsonDecoder:

    def __init__(self) -> None:
        self._buffer = b""

    def feed(self, chunk: bytes) -> list[dict[str, Any]]:
        self._buffer += chunk
        messages: list[dict[str, Any]] = []

        while b"\n" in self._buffer:
            line, self._buffer = self._buffer.split(b"\n", 1)
            if not line.strip():
                continue
            try:
                data = json.loads(line.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                LOGGER.warning("[SAY:FE BT] malformed JSON ignored: %s", exc)
                continue
            if not isinstance(data, dict):
                LOGGER.warning("[SAY:FE BT] non-object JSON ignored")
                continue
            messages.append(data)

        return messages


def dispatch_vision_event(
    data: dict[str, Any],
    trigger: Callable[[str], object] | None = None,
) -> bool:
  
    if data.get("event") != VISION_EVENT:
        return False

    if trigger is None:
      
        from src.safety.fast_path import trigger_fast_path

        trigger = trigger_fast_path

    LOGGER.warning("[SAY:FE BT] %s -> %s", VISION_EVENT, FAST_PATH_EVENT)
    trigger(FAST_PATH_EVENT)
    return True


class BluetoothEventListener:
    
    def __init__(
        self,
        channel: int = 1,
        on_event: Callable[[dict[str, Any]], object] = dispatch_vision_event,
    ) -> None:
        self.channel = channel
        self._on_event = on_event
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._server: socket.socket | None = None

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._thread = threading.Thread(
            target=self._run,
            name="sayfe-bluetooth-rfcomm",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        server = self._server
        if server is not None:
            try:
                server.close()
            except OSError:
                pass
        if self._thread is not None:
            self._thread.join(timeout=2)

    def _run(self) -> None:
        server: socket.socket | None = None
        try:
            server = socket.socket(
                socket.AF_BLUETOOTH,
                socket.SOCK_STREAM,
                socket.BTPROTO_RFCOMM,
            )
            self._server = server
            server.settimeout(0.5)
            server.bind((socket.BDADDR_ANY, self.channel))
            server.listen(1)
            LOGGER.warning("[SAY:FE BT] RFCOMM listening on channel %d", self.channel)

            while not self._stop_event.is_set():
                try:
                    client, address = server.accept()
                except socket.timeout:
                    continue
                except OSError:
                    if self._stop_event.is_set():
                        break
                    raise

                LOGGER.warning("[SAY:FE BT] client connected: %s", address)
                try:
                    self._receive_client(client)
                except Exception:
                    LOGGER.exception("[SAY:FE BT] client receive error; accepting again")
                finally:
                    try:
                        client.close()
                    except OSError:
                        pass
                    LOGGER.warning("[SAY:FE BT] client disconnected")
        except Exception:
           
            LOGGER.exception("[SAY:FE BT] listener unavailable; Safe Path continues")
        finally:
            if server is not None:
                try:
                    server.close()
                except OSError:
                    pass
            self._server = None

    def _receive_client(self, client: socket.socket) -> None:
        decoder = NewlineJsonDecoder()
        client.settimeout(0.5)
        while not self._stop_event.is_set():
            try:
                chunk = client.recv(4096)
            except socket.timeout:
                continue
            if not chunk:
                return
            for data in decoder.feed(chunk):
                LOGGER.warning("[SAY:FE BT] JSON RX: %s", data)
                try:
                    self._on_event(data)
                except Exception:
                    LOGGER.exception("[SAY:FE BT] event handling failed; listener continues")


def start_bluetooth_event_listener() -> BluetoothEventListener | None:
    enabled = os.environ.get("SAYFE_BT_ENABLED", "1").strip().lower()
    if enabled in {"0", "false", "no", "off"}:
        LOGGER.warning("[SAY:FE BT] listener disabled by SAYFE_BT_ENABLED")
        return None

    raw_channel = os.environ.get("SAYFE_BT_CHANNEL", "1")
    try:
        channel = int(raw_channel)
        if channel < 1 or channel > 30:
            raise ValueError
    except ValueError:
        LOGGER.warning("[SAY:FE BT] invalid channel %r; using 1", raw_channel)
        channel = 1

    listener = BluetoothEventListener(channel=channel)
    listener.start()
    return listener
