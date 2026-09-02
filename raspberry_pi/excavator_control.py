
import argparse
import json
import logging
import socket
import threading
from typing import Any


PINS = [2, 3, 4, 14]


VISION_EVENT = "WORKER_NEAR_MOVING_EXCAVATOR"


FAST_PATH_EVENT = "WORKER_IN_EQUIPMENT_ZONE"


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

LOGGER = logging.getLogger(__name__)


import RPi.GPIO as GPIO

GPIO.setmode(GPIO.BCM)
for pin in [2, 3, 4, 14]:
    GPIO.setup(pin, GPIO.OUT, initial=GPIO.LOW)

def set_all(state):
    for pin in PINS:
        GPIO.output(pin, state)

def all_on():
    set_all(GPIO.HIGH)

    print(
        "[GPIO] ALL ON -> "
        "GPIO2=HIGH, "
        "GPIO3=HIGH, "
        "GPIO4=HIGH, "
        "GPIO14=HIGH"
    )

def all_off():
    set_all(GPIO.LOW)

    print(
        "[GPIO] ALL OFF -> "
        "GPIO2=LOW, "
        "GPIO3=LOW, "
        "GPIO4=LOW, "
        "GPIO14=LOW"
    )


def print_status():

    print("[GPIO STATUS]")

    for pin in PINS:

        state = GPIO.input(pin)

        print(
            f"  GPIO {pin}: "
            f"{'HIGH' if state else 'LOW'}"
        )


class NewlineJsonDecoder:
    def __init__(self):
        self._buffer = b""

    def feed(self, chunk: bytes) -> list[dict[str, Any]]:

        self._buffer += chunk

        messages = []

        while b"\n" in self._buffer:

            line, self._buffer = self._buffer.split(
                b"\n",
                1
            )

            if not line.strip():
                continue

            try:

                data = json.loads(
                    line.decode("utf-8")
                )

            except (
                UnicodeDecodeError,
                json.JSONDecodeError
            ) as exc:

                LOGGER.warning(
                    "[BT] malformed JSON ignored: %s",
                    exc
                )

                continue

            if not isinstance(data, dict):

                LOGGER.warning(
                    "[BT] non-object JSON ignored"
                )

                continue

            messages.append(data)

        return messages

def dispatch_vision_event(data: dict[str, Any]) -> bool:
    event = data.get("event")

    print(
        "[EVENT]",
        json.dumps(
            data,
            ensure_ascii=False
        )
    )

    if event == VISION_EVENT:
        print(
            f"[TARGET EVENT] {VISION_EVENT}"
        )
        print(
            f"[EVENT MAP] "
            f"{VISION_EVENT} -> {FAST_PATH_EVENT}"
        )
        all_off()
        return True
    return False


class BluetoothEventListener:

    def __init__(
        self,
        channel: int = 1
    ):

        self.channel = channel
        self._stop_event = threading.Event()
        self._thread = None
        self._server = None


    def start(self):

        if (
            self._thread is not None
            and self._thread.is_alive()
        ):
            return

        self._thread = threading.Thread(
            target=self._run,
            name="bluetooth-rfcomm",
            daemon=True
        )

        self._thread.start()


    def stop(self):

        self._stop_event.set()

        server = self._server

        if server is not None:

            try:
                server.close()

            except OSError:
                pass

        if self._thread is not None:

            self._thread.join(
                timeout=2
            )



    def _run(self):

        server = None

        try:

            server = socket.socket(
                socket.AF_BLUETOOTH,
                socket.SOCK_STREAM,
                socket.BTPROTO_RFCOMM
            )

            self._server = server

            server.settimeout(0.5)

            server.bind(
                (
                    socket.BDADDR_ANY,
                    self.channel
                )
            )

            server.listen(1)

            print(
                f"[BT RECEIVER] "
                f"waiting on RFCOMM channel "
                f"{self.channel}"
            )


            while not self._stop_event.is_set():

                try:

                    client, address = server.accept()

                except socket.timeout:

                    continue

                except OSError:

                    if self._stop_event.is_set():
                        break

                    raise


                print(
                    "[BT RECEIVER] connected:",
                    address
                )


                try:

                    self._receive_client(
                        client
                    )

                except Exception:

                    LOGGER.exception(
                        "[BT] client receive error"
                    )

                finally:

                    try:
                        client.close()

                    except OSError:
                        pass

                    print(
                        "[BT DISCONNECTED]"
                    )


        except Exception:

            LOGGER.exception(
                "[BT] listener unavailable"
            )


        finally:

            if server is not None:

                try:
                    server.close()

                except OSError:
                    pass

            self._server = None


    def _receive_client(
        self,
        client: socket.socket
    ):

        decoder = NewlineJsonDecoder()

        client.settimeout(0.5)

        event_active = False


        while not self._stop_event.is_set():

            try:

                chunk = client.recv(4096)

            except socket.timeout:

                continue

            if not chunk:

                return

            print(
                "[BT RAW]",
                repr(chunk)
            )

            for data in decoder.feed(chunk):

                print(
                    "[JSON RX]",
                    json.dumps(
                        data,
                        ensure_ascii=False
                    )
                )


                event = data.get("event")

                if event == VISION_EVENT:

                    if not event_active:

                        dispatch_vision_event(
                            data
                        )

                        event_active = True

                    else:

                        print(
                            "[INFO] "
                            "대상 이벤트가 이미 활성화되어 있음"
                        )

                else:

                    dispatch_vision_event(
                        data
                    )

        if event_active:

            print(
                "[EVENT END] "
                "Bluetooth 연결 종료"
            )

            # 이벤트 종료 → 다시 제어 가능
            all_on()


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--channel",
        type=int,
        default=1
    )

    args = parser.parse_args()


    print()
    print("==============================")
    print(" Raspberry Pi BT Event Receiver")
    print("==============================")

    print(
        f"RFCOMM Channel : {args.channel}"
    )

    print(
        f"Target Event   : {VISION_EVENT}"
    )

    print()

    all_on()

    listener = BluetoothEventListener(
        channel=args.channel
    )


    try:

        listener.start()

        while True:

            threading.Event().wait(1)


    except KeyboardInterrupt:

        print()
        print(
            "[SYSTEM] 프로그램 종료"
        )


    finally:

        listener.stop()

        all_on()

        GPIO.cleanup()

        print(
            "[GPIO] cleanup 완료"
        )


if __name__ == "__main__":

    main()
