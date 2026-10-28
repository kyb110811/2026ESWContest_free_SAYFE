# ESP32-C3 Excavator GPIO Controller

BLE 명령을 수신하여 ESP32-C3의 GPIO 4개를 동시에 제어하는 굴착기 제어용 펌웨어입니다. SAYFE 시스템에서 위험 이벤트가 발생하면 지정된 GPIO를 활성화하고, `reset` 명령을 받으면 비활성화합니다.

> **안전 주의:** 이 코드는 예제 수준의 GPIO 제어 펌웨어입니다. 실제 굴착기의 구동 제한·비상 정지 등 안전 기능에 그대로 사용해서는 안 됩니다. BLE 연결이 끊겨도 현재 GPIO 상태가 유지되며, 통신 타임아웃·인증·워치독·안전 상태 검증이 구현되어 있지 않습니다. 실제 장비 적용 시 별도의 검증된 안전 회로와 독립적인 비상 정지 수단이 필요합니다.

## 1. 주요 기능

- BLE GATT 서버로 동작하며 `ESP32C3_EXCAVATOR`라는 이름으로 광고합니다.
- `excavator_danger` 수신 시 GPIO 2, 3, 4, 5를 모두 `HIGH`로 설정합니다.
- `reset` 수신 시 해당 GPIO를 모두 `LOW`로 설정합니다.
- BLE 연결 및 해제, 명령 수신 상태를 시리얼 모니터(115200 bps)에 출력합니다.
- BLE 연결이 해제되면 광고를 다시 시작합니다.

## 2. 하드웨어 및 GPIO 설정

| 구분 | ESP32-C3 GPIO | 초기 상태 | `excavator_danger` | `reset` |
| --- | --- | --- | --- | --- |
| GPIO_1 | GPIO2 | LOW | HIGH | LOW |
| GPIO_2 | GPIO3 | LOW | HIGH | LOW |
| GPIO_3 | GPIO4 | LOW | HIGH | LOW |
| GPIO_4 | GPIO5 | LOW | HIGH | LOW |

`HIGH`/`LOW`는 **ESP32-C3 출력의 논리 레벨**이며, 실제 연결된 릴레이 또는 구동 회로의 ON/OFF 동작과 반드시 일치하지는 않습니다. 특히 Active-LOW 릴레이 모듈이라면 동작이 반대일 수 있습니다.

**주의 사항**

- 출력 핀에 모터, 솔레노이드, 릴레이 코일 등을 직접 연결하지 마세요. 적절한 구동 회로, 절연 및 보호 회로를 사용하세요.
- 사용하는 ESP32-C3 보드의 실제 핀 배치와 부팅 시 GPIO 제약 사항을 확인하세요. 특히 **GPIO2는 부트 스트래핑과 관련된 핀**이므로 외부 회로가 부팅 상태를 방해하지 않도록 주의해야 합니다.
- 전원 투입 직후부터 펌웨어의 `setup()`이 실행되기 전까지 외부 회로가 안전한 상태를 유지하도록 설계해야 합니다.

## 3. BLE 설정

| 항목 | 값 |
| --- | --- |
| 장치 이름 | `ESP32C3_EXCAVATOR` |
| Service UUID | `7f4a1001-8c21-4b7d-9a31-123456789001` |
| Characteristic UUID | `7f4a1002-8c21-4b7d-9a31-123456789002` |
| Characteristic 속성 | READ, WRITE, NOTIFY |
| 초기 Characteristic 값 | `READY` |

BLE 클라이언트(예: Jetson 또는 스마트폰)가 해당 Characteristic에 **UTF-8 텍스트 문자열**을 작성하면 명령을 처리합니다. 수신 문자열의 앞뒤 공백은 `trim()`으로 제거합니다. 명령은 **대소문자를 구분**합니다.

## 4. BLE 명령어

| 전송 문자열 | 수행 동작 |
| --- | --- |
| `excavator_danger` | 4개 GPIO 모두 HIGH |
| `reset` | 4개 GPIO 모두 LOW |
| 그 외 문자열 | `UNKNOWN` 로그만 출력, GPIO 상태 변경 없음 |

**동작 흐름**

```text
Jetson / BLE Client
       |
       | BLE Write: "excavator_danger"
       v
ESP32-C3 (BLE GATT Server)
       |
       +--> GPIO2 = HIGH
       +--> GPIO3 = HIGH
       +--> GPIO4 = HIGH
       +--> GPIO5 = HIGH

BLE Write: "reset"
       |
       v
GPIO2 / GPIO3 / GPIO4 / GPIO5 = LOW
```

## 5. 개발 환경 및 업로드

1. Arduino IDE에 ESP32 보드 패키지를 설치합니다.
2. 사용하는 ESP32-C3 보드에 맞는 보드와 포트를 선택합니다. XIAO ESP32-C3라면 해당 보드 항목을 선택합니다.
3. 제공된 소스코드를 `.ino` 파일에 저장합니다.
4. `BLEDevice.h`, `BLEServer.h`, `BLEUtils.h`, `BLE2902.h`를 제공하는 **사용 중인 ESP32 Arduino 코어의 BLE 라이브러리**가 사용 가능한지 확인합니다. 코어 버전에 따라 API 호환성 차이가 있을 수 있습니다.
5. 보드에 업로드한 뒤 시리얼 모니터를 **115200 baud**로 엽니다.

정상 실행 시 다음과 유사한 메시지가 출력됩니다.

```text
EXCAVATOR GPIO CONTROLLER
[GPIO] ALL OFF
[BLE] Ready
[BLE] Name : ESP32C3_EXCAVATOR
Waiting for BLE event...
```

## 6. 테스트 방법

1. 스마트폰의 nRF Connect와 같은 BLE GATT 클라이언트를 실행합니다.
2. `ESP32C3_EXCAVATOR` 장치를 찾아 연결합니다.
3. Service UUID `7f4a1001-8c21-4b7d-9a31-123456789001`을 확인합니다.
4. Characteristic UUID `7f4a1002-8c21-4b7d-9a31-123456789002`에 **텍스트(UTF-8)** 로 `excavator_danger`를 Write합니다.
5. GPIO2/3/4/5가 HIGH로 변경되는지 확인합니다.
6. 같은 Characteristic에 `reset`을 Write하여 모두 LOW가 되는지 확인합니다.

예상 시리얼 출력:

```text
[BLE] Device Connected
==============================
[BLE RX] excavator_danger
==============================
[EVENT] EXCAVATOR DANGER
[GPIO] ALL ON

==============================
[BLE RX] reset
==============================
[EVENT] RESET
[GPIO] ALL OFF
```

## 7. 코드 구조

| 함수 또는 클래스 | 역할 |
| --- | --- |
| `gpioAllOn()` | GPIO2/3/4/5를 HIGH로 설정 |
| `gpioAllOff()` | GPIO2/3/4/5를 LOW로 설정 |
| `MyServerCallbacks::onConnect()` | BLE 연결 상태 및 로그 갱신 |
| `MyServerCallbacks::onDisconnect()` | BLE 연결 해제 로그 출력 후 광고 재시작 |
| `MyCharacteristicCallbacks::onWrite()` | 수신 명령을 분석하여 GPIO 제어 |
| `setup()` | GPIO 초기화 및 BLE 서버 구성 |
| `loop()` | 별도 작업 없이 10 ms 지연 반복 |

## 8. 현재 구현의 동작 및 제한 사항

- 전원을 켜고 `setup()`이 정상적으로 실행되면 모든 GPIO를 LOW로 초기화합니다.
- `excavator_danger`를 받은 후에는 `reset`이 수신되거나 장치가 재시작될 때까지 HIGH가 유지됩니다.
- **BLE 연결 해제 시 GPIO를 자동으로 LOW 또는 HIGH로 전환하지 않습니다.** 마지막 상태가 유지됩니다.
- BLE 클라이언트 인증·암호화 강제 및 명령 발신자 검증 로직이 없습니다.
- 연결 이상 감지용 heartbeat, 타임아웃, Watchdog 및 명령 수신 확인(ACK) 프로토콜은 구현되어 있지 않습니다.
- Characteristic은 NOTIFY 속성을 제공하지만, 현재 코드에는 `notify()` 호출이 없어 상태 알림을 능동적으로 전송하지 않습니다.
- `deviceConnected` 변수는 연결 상태를 기록하지만 `loop()`에서 활용하지 않습니다.

## 9. 실제 장비 적용 전에 권장하는 보완 사항

- **안전 상태 정의:** 위험 감지, 통신 단절, 재부팅, 전원 장애 시 장비가 어떻게 반응해야 하는지 별도로 정의합니다.
- **연결 감시:** Jetson ↔ ESP32-C3 heartbeat와 타임아웃, 통신 단절 시 독립적인 안전 동작을 설계합니다.
- **권한 통제:** 페어링·암호화·인증 및 유효한 제어 명령 검증을 추가합니다.
- **출력 피드백:** GPIO 명령뿐 아니라 실제 릴레이/구동 회로의 상태를 확인합니다.
- **안전 검증:** 장비 제조사 요구사항 및 적용 안전 표준에 맞춰 위험 분석과 하드웨어 시험을 진행합니다.

---

**프로젝트:** SAYFE — BLE 기반 굴착기 GPIO 제어 모듈  
**대상:** ESP32-C3  
**통신:** BLE GATT  
**시리얼 속도:** 115200 bps
