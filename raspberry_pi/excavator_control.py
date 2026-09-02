
import argparse
import json
import logging
import socket
import threading
from typing import Any


# ============================================================
# 설정
# ============================================================

PINS = [2, 3, 4, 14]

# 굴착기 정지 대상 이벤트
VISION_EVENT = "WORKER_NEAR_MOVING_EXCAVATOR"

# 이벤트 발생 시 실행할 동작
FAST_PATH_EVENT = "WORKER_IN_EQUIPMENT_ZONE"


# ============================================================
# Logging
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

LOGGER = logging.getLogger(__name__)


# ============================================================
# GPIO
# ============================================================

import RPi.GPIO as GPIO

GPIO.setmode(GPIO.BCM)

# 처음에는 제어 가능 상태
# GPIO 2는 반전이므로 HIGH
GPIO.setup(2, GPIO.OUT, initial=GPIO.HIGH)

# GPIO 3, 4, 14는 LOW
for pin in [3, 4, 14]:
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


# ============================================================
# JSON Decoder
# ============================================================

class NewlineJsonDecoder:
    """
    Bluetooth RFCOMM stream에서
    \\n 기준으로 JSON 메시지를 분리한다.
    """

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


# ============================================================
# Event 처리
# ============================================================

def dispatch_vision_event(
    data: dict[str, Any]
) -> bool:

    event = data.get("event")

    print(
        "[EVENT]",
        json.dumps(
            data,
            ensure_ascii=False
        )
    )

    # --------------------------------------------------------
    # 굴착기 근처 작업자 감지
    # --------------------------------------------------------

    if event == VISION_EVENT:

        print(
            f"[TARGET EVENT] {VISION_EVENT}"
        )

        print(
            f"[EVENT MAP] "
            f"{VISION_EVENT} -> {FAST_PATH_EVENT}"
        )

        # 굴착기 제어 불가능 상태
        all_off()

        return True


    # --------------------------------------------------------
    # 다른 이벤트
    # --------------------------------------------------------

    print(
        f"[INFO] 다른 이벤트: {event}"
    )

    return False


# ============================================================
# Bluetooth RFCOMM Listener
# ============================================================

class BluetoothEventListener:

    def __init__(
        self,
        channel: int = 1
    ):

        self.channel = channel

        self._stop_event = threading.Event()

        self._thread = None

        self._server = None


    # --------------------------------------------------------
    # 시작
    # --------------------------------------------------------

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


    # --------------------------------------------------------
    # 종료
    # --------------------------------------------------------

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


    # --------------------------------------------------------
    # RFCOMM 서버
    # --------------------------------------------------------

    def _run(self):

        server = None

        try:

            server = socket.socket(
                socket.AF_BLUETOOTH,
                socket.SOCK_STREAM,
                socket.BTPROTO_RFCOMM
            )

            self._server = server

            # 첫 번째 잘 동작하는 코드와 동일한 방식
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


            # ------------------------------------------------
            # 연결 대기
            # ------------------------------------------------

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


    # --------------------------------------------------------
    # Client 데이터 수신
    # --------------------------------------------------------

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


            # ------------------------------------------------
            # 연결 종료
            # ------------------------------------------------

            if not chunk:

                return


            # 디버깅용 RAW 데이터
            print(
                "[BT RAW]",
                repr(chunk)
            )


            # ------------------------------------------------
            # JSON 처리
            # ------------------------------------------------

            for data in decoder.feed(chunk):

                print(
                    "[JSON RX]",
                    json.dumps(
                        data,
                        ensure_ascii=False
                    )
                )


                event = data.get("event")


                # --------------------------------------------
                # 대상 이벤트
                # --------------------------------------------

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


                # --------------------------------------------
                # 다른 이벤트
                # --------------------------------------------

                else:

                    dispatch_vision_event(
                        data
                    )


        # ----------------------------------------------------
        # 연결 종료
        # ----------------------------------------------------

        if event_active:

            print(
                "[EVENT END] "
                "Bluetooth 연결 종료"
            )

            # 이벤트 종료 → 다시 제어 가능
            all_on()


# ============================================================
# Main
# ============================================================

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


    # 프로그램 시작 시 제어 가능 상태
    all_on()


    listener = BluetoothEventListener(
        channel=args.channel
    )


    try:

        listener.start()

        # 메인 스레드를 계속 유지
        while True:

            threading.Event().wait(1)


    except KeyboardInterrupt:

        print()
        print(
            "[SYSTEM] 프로그램 종료"
        )


    finally:

        listener.stop()

        # 종료 시 안전하게 제어 가능 상태
        all_on()

        GPIO.cleanup()

        print(
            "[GPIO] cleanup 완료"
        )


# ============================================================
# 실행
# ============================================================

if __name__ == "__main__":

    main()
