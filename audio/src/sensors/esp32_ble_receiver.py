"""Restartable ESP32-C3 BLE gas receiver for the SAY:FE GPU worker."""

from __future__ import annotations

import asyncio
import os
import re
import threading
from collections.abc import Callable


DEVICE_NAME = "ESP32C3_MQ"
DEFAULT_MAC = "80:F1:B2:64:32:02"
SERVICE_UUID = "4fafc201-1fb5-459e-8fcc-c5c9c331914b"
CHARACTERISTIC_UUID = "beb5483e-36e1-4688-b7f5-ea07361b26a8"
DEFAULT_THRESHOLD = 1000
RETRY_SECONDS = 5.0
MQ_PATTERN = re.compile(r"(?:^|,)\s*MQ\s*=\s*(-?\d+)")


def parse_mq(data: bytes | str) -> int | None:
    """Extract an MQ integer from one ESP32 notification."""
    message = (
        data.decode("utf-8", errors="ignore")
        if isinstance(data, bytes)
        else data
    )
    match = MQ_PATTERN.search(message)
    return int(match.group(1)) if match else None


class GasThresholdLatch:
    """Fire once above threshold, then re-arm at or below it."""

    def __init__(
        self,
        threshold: int = DEFAULT_THRESHOLD,
        on_danger: Callable[[int], object] | None = None,
    ) -> None:
        self.threshold = threshold
        self.on_danger = on_danger
        self._armed = True

    def update(self, mq: int) -> bool:
        if mq > self.threshold:
            if not self._armed:
                return False
            self._armed = False
            print(f"[SAY:FE GAS] MQ={mq} > {self.threshold}", flush=True)
            if self.on_danger is not None:
                try:
                    self.on_danger(mq)
                except Exception as error:
                    # One audio-path failure must not kill BLE reconnect/notify.
                    print(
                        f"[SAY:FE GAS] GAS_DANGER trigger failed ({error})",
                        flush=True,
                    )
            return True

        if not self._armed:
            self._armed = True
            print(f"[SAY:FE GAS] MQ={mq} re-armed", flush=True)
        return False


class Esp32BleGasReceiver:
    """Run Bleak in a daemon thread and reconnect without blocking Safe Path."""

    def __init__(
        self,
        on_danger: Callable[[int], object],
        mac: str = DEFAULT_MAC,
        threshold: int = DEFAULT_THRESHOLD,
        retry_seconds: float = RETRY_SECONDS,
    ) -> None:
        self.mac = mac
        self.threshold = threshold
        self.retry_seconds = retry_seconds
        self._latch = GasThresholdLatch(threshold, on_danger)
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._thread = threading.Thread(
            target=self._thread_main,
            name="sayfe-esp32-gas-ble",
            daemon=True,
        )
        self._thread.start()
        print("[SAY:FE GAS] BLE receiver started", flush=True)
        print(
            f"[SAY:FE GAS] target={self.mac} threshold={self.threshold}",
            flush=True,
        )

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=3.0)

    def _thread_main(self) -> None:
        try:
            asyncio.run(self._run())
        except Exception as error:
            print(
                f"[SAY:FE GAS] ESP32 unavailable; system continues ({error})",
                flush=True,
            )

    async def _run(self) -> None:
        try:
            from bleak import BleakClient
        except ImportError as error:
            print(
                f"[SAY:FE GAS] ESP32 unavailable; system continues ({error})",
                flush=True,
            )
            return

        first_attempt = True
        while not self._stop_event.is_set():
            disconnected = asyncio.Event()

            def on_disconnect(_client: object) -> None:
                disconnected.set()

            try:
                async with BleakClient(
                    self.mac,
                    disconnected_callback=on_disconnect,
                    timeout=10.0,
                ) as client:
                    first_attempt = False
                    print(f"[SAY:FE GAS] connected {DEVICE_NAME}", flush=True)
                    await client.start_notify(
                        CHARACTERISTIC_UUID,
                        self._notification_handler,
                    )
                    while (
                        not self._stop_event.is_set()
                        and client.is_connected
                        and not disconnected.is_set()
                    ):
                        await asyncio.sleep(0.5)
                    if client.is_connected:
                        await client.stop_notify(CHARACTERISTIC_UUID)
            except Exception as error:
                if first_attempt:
                    print(
                        "[SAY:FE GAS] ESP32 unavailable; system continues "
                        f"({error})",
                        flush=True,
                    )
                    first_attempt = False

            if not self._stop_event.is_set():
                print("[SAY:FE GAS] disconnected; retrying", flush=True)
                await self._wait_for_retry()

    async def _wait_for_retry(self) -> None:
        waited = 0.0
        while waited < self.retry_seconds and not self._stop_event.is_set():
            interval = min(0.5, self.retry_seconds - waited)
            await asyncio.sleep(interval)
            waited += interval

    def _notification_handler(self, _sender: object, data: bytearray) -> None:
        mq = parse_mq(bytes(data))
        if mq is not None:
            self._latch.update(mq)


def _enabled_from_environment() -> bool:
    return os.environ.get("SAYFE_GAS_ENABLED", "1").strip().lower() not in {
        "0", "false", "no", "off",
    }


def start_esp32_ble_gas_receiver(
    on_danger: Callable[[int], object],
) -> Esp32BleGasReceiver | None:
    """Start the optional receiver; invalid configuration cannot stop startup."""
    if not _enabled_from_environment():
        print("[SAY:FE GAS] BLE receiver disabled", flush=True)
        return None

    mac = os.environ.get("SAYFE_GAS_MAC", DEFAULT_MAC).strip() or DEFAULT_MAC
    raw_threshold = os.environ.get("SAYFE_GAS_THRESHOLD", str(DEFAULT_THRESHOLD))
    try:
        threshold = int(raw_threshold)
    except ValueError:
        print(
            f"[SAY:FE GAS] invalid threshold {raw_threshold!r}; "
            f"using {DEFAULT_THRESHOLD}",
            flush=True,
        )
        threshold = DEFAULT_THRESHOLD

    receiver = Esp32BleGasReceiver(on_danger, mac=mac, threshold=threshold)
    receiver.start()
    return receiver


async def main() -> None:
    """Compatibility entry point for manually observing threshold crossings."""
    receiver = Esp32BleGasReceiver(
        lambda mq: print(f"[SAY:FE GAS] danger callback MQ={mq}", flush=True)
    )
    receiver.start()
    try:
        while True:
            await asyncio.sleep(1)
    finally:
        receiver.stop()


if __name__ == "__main__":
    asyncio.run(main())
