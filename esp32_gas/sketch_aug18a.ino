#include <Arduino.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>

#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>

#include <ESP32Servo.h>


// ======================================================
// GPIO 설정
// ======================================================

#define MQ_PIN       2

#define LED_GREEN     3
#define LED_ORANGE    4
#define LED_RED       5

// 부저
#define BUZZER_PIN    10

// I2C LCD
#define LCD_SDA       6
#define LCD_SCL       7

// 서보모터
#define SERVO_PIN     21

// 팬
#define FAN_PIN       20


// ======================================================
// LCD 설정
// ======================================================

#define LCD_ADDRESS   0x27

// 16x2 LCD
LiquidCrystal_I2C lcd(
  LCD_ADDRESS,
  16,
  2
);


// ======================================================
// 서보모터 설정
// ======================================================

Servo myServo;

// 정상/주의 상태 서보 위치
#define SERVO_NORMAL_ANGLE   0

// 위험 상태 서보 위치
#define SERVO_DANGER_ANGLE   90


// ======================================================
// MQ 임계값
// ======================================================

#define THRESHOLD_NORMAL   500
#define THRESHOLD_WARNING  1000


// ======================================================
// DANGER 알람 설정
// ======================================================

// DANGER 상태 진입 여부
bool dangerActive = false;

// 현재 부저/빨간 LED 상태
// true  = ON
// false = OFF
bool dangerOutputState = false;

// 마지막 상태 변경 시간
unsigned long dangerPreviousMillis = 0;

// ON 시간 = 1초
const unsigned long DANGER_ON_TIME = 1000;

// OFF 시간 = 0.5초
const unsigned long DANGER_OFF_TIME = 500;


// ======================================================
// BLE UUID
// ======================================================

#define SERVICE_UUID \
  "4fafc201-1fb5-459e-8fcc-c5c9c331914b"

#define CHARACTERISTIC_UUID \
  "beb5483e-36e1-4688-b7f5-ea07361b26a8"


// ======================================================
// BLE 변수
// ======================================================

BLECharacteristic *pCharacteristic;

bool deviceConnected = false;


// ======================================================
// BLE 연결 Callback
// ======================================================

class MyServerCallbacks : public BLEServerCallbacks {

  void onConnect(BLEServer *pServer) {

    deviceConnected = true;

    Serial.println("[BLE] Device Connected");
  }


  void onDisconnect(BLEServer *pServer) {

    deviceConnected = false;

    Serial.println("[BLE] Device Disconnected");

    pServer->getAdvertising()->start();
  }
};


// ======================================================
// BLE 메시지 전송
// ======================================================

void sendBLEMessage(
  String status,
  int sensorValue,
  bool motor
) {

  String message =
    "STATUS=" + status +
    ",MQ=" + String(sensorValue) +
    ",MOTOR=" + String(motor ? 1 : 0);


  if (deviceConnected) {

    pCharacteristic->setValue(
      message.c_str()
    );

    pCharacteristic->notify();
  }
}


// ======================================================
// LCD 표시
// ======================================================

void updateLCD(
  int mqValue,
  String status
) {

  lcd.clear();


  // ------------------------------------------
  // 1번째 줄
  // ------------------------------------------

  lcd.setCursor(0, 0);

  lcd.print("MQ: ");
  lcd.print(mqValue);


  // ------------------------------------------
  // 2번째 줄
  // ------------------------------------------

  lcd.setCursor(0, 1);

  lcd.print(status);
}


// ======================================================
// 정상 상태
// ======================================================

void setNormal() {

  // DANGER 알람 종료
  dangerActive = false;
  dangerOutputState = false;

  digitalWrite(
    BUZZER_PIN,
    LOW
  );


  // LED
  digitalWrite(LED_GREEN, HIGH);
  digitalWrite(LED_ORANGE, LOW);
  digitalWrite(LED_RED, LOW);


  // 서보모터 0도
  myServo.write(
    SERVO_NORMAL_ANGLE
  );


  // 팬 OFF
  digitalWrite(
    FAN_PIN,
    LOW
  );
}


// ======================================================
// 주의 상태
// ======================================================

void setWarning() {

  // DANGER 알람 종료
  dangerActive = false;
  dangerOutputState = false;

  digitalWrite(
    BUZZER_PIN,
    LOW
  );


  // LED
  digitalWrite(LED_GREEN, LOW);
  digitalWrite(LED_ORANGE, HIGH);
  digitalWrite(LED_RED, LOW);


  // 서보모터 0도
  myServo.write(
    SERVO_NORMAL_ANGLE
  );


  // 팬 OFF
  digitalWrite(
    FAN_PIN,
    LOW
  );
}


// ======================================================
// 위험 상태
// ======================================================

void setDanger() {

  // 정상/주의 LED OFF
  digitalWrite(
    LED_GREEN,
    LOW
  );

  digitalWrite(
    LED_ORANGE,
    LOW
  );


  // ------------------------------------------
  // DANGER 상태에 처음 진입했을 때
  // ------------------------------------------

  if (!dangerActive) {

    dangerActive = true;

    // 처음에는 바로 ON
    dangerOutputState = true;

    dangerPreviousMillis = millis();


    // 빨간 LED ON
    digitalWrite(
      LED_RED,
      HIGH
    );


    // 부저 ON
    digitalWrite(
      BUZZER_PIN,
      HIGH
    );
  }


  // ------------------------------------------
  // 서보모터 90도
  // ------------------------------------------

  myServo.write(
    SERVO_DANGER_ANGLE
  );


  // ------------------------------------------
  // 팬 ON
  // ------------------------------------------

  digitalWrite(
    FAN_PIN,
    HIGH
  );
}


// ======================================================
// DANGER 부저 + 빨간 LED 제어
// ======================================================
//
// ON  : 1초
// OFF : 0.5초
// ON  : 1초
// OFF : 0.5초
// 계속 반복
//
// millis()를 사용하기 때문에 delay()로
// 프로그램 전체를 멈추지 않음
// ======================================================

void updateDangerAlarm() {

  // DANGER 상태가 아니면 실행하지 않음
  if (!dangerActive) {
    return;
  }


  unsigned long currentMillis = millis();


  // 현재 상태에 따른 시간 설정
  unsigned long interval;


  if (dangerOutputState) {

    // 현재 ON 상태
    interval = DANGER_ON_TIME;

  }
  else {

    // 현재 OFF 상태
    interval = DANGER_OFF_TIME;
  }


  // 시간이 지나면 상태 변경
  if (
    currentMillis - dangerPreviousMillis
    >= interval
  ) {

    dangerPreviousMillis = currentMillis;


    // ON <-> OFF 전환
    dangerOutputState = !dangerOutputState;


    // 빨간 LED
    digitalWrite(
      LED_RED,
      dangerOutputState
        ? HIGH
        : LOW
    );


    // 부저
    digitalWrite(
      BUZZER_PIN,
      dangerOutputState
        ? HIGH
        : LOW
    );
  }
}


// ======================================================
// Setup
// ======================================================

void setup() {


  // ====================================================
  // GPIO 설정
  // ====================================================

  pinMode(
    LED_GREEN,
    OUTPUT
  );

  pinMode(
    LED_ORANGE,
    OUTPUT
  );

  pinMode(
    LED_RED,
    OUTPUT
  );

  pinMode(
    BUZZER_PIN,
    OUTPUT
  );

  pinMode(
    FAN_PIN,
    OUTPUT
  );


  // ====================================================
  // 초기 상태
  // ====================================================

  digitalWrite(
    LED_GREEN,
    LOW
  );

  digitalWrite(
    LED_ORANGE,
    LOW
  );

  digitalWrite(
    LED_RED,
    LOW
  );

  digitalWrite(
    BUZZER_PIN,
    LOW
  );

  digitalWrite(
    FAN_PIN,
    LOW
  );


  // ====================================================
  // Serial
  // ====================================================

  Serial.begin(115200);

  delay(1000);

  Serial.println("==============================");
  Serial.println("ESP32-C3 MQ Monitor");
  Serial.println("System Starting...");
  Serial.println("==============================");


  // ====================================================
  // I2C LCD 초기화
  // ====================================================

  // GPIO 6 = SDA
  // GPIO 7 = SCL

  Wire.begin(
    LCD_SDA,
    LCD_SCL
  );


  lcd.init();

  lcd.backlight();

  lcd.clear();


  // 시작 화면

  lcd.setCursor(0, 0);

  lcd.print(
    "MQ MONITOR"
  );

  lcd.setCursor(0, 1);

  lcd.print(
    "Starting..."
  );


  delay(2000);


  // ====================================================
  // 서보모터 초기화
  // ====================================================

  Serial.println(
    "[SERVO] Initializing..."
  );


  // ESP32 PWM 타이머에 서보 연결
  myServo.setPeriodHertz(50);


  // 서보 연결
  // 일반적인 SG90 기준

  myServo.attach(
    SERVO_PIN,
    500,
    2400
  );


  // 시작 위치 = 0도

  myServo.write(
    SERVO_NORMAL_ANGLE
  );


  Serial.println(
    "[SERVO] Ready"
  );

  Serial.println(
    "[SERVO] Position = 0"
  );


  // ====================================================
  // ADC 설정
  // ====================================================

  analogReadResolution(12);


  // ====================================================
  // BLE 초기화
  // ====================================================

  BLEDevice::init(
    "ESP32C3_MQ"
  );


  // ====================================================
  // BLE Server
  // ====================================================

  BLEServer *pServer =
    BLEDevice::createServer();


  pServer->setCallbacks(
    new MyServerCallbacks()
  );


  // ====================================================
  // BLE Service
  // ====================================================

  BLEService *pService =
    pServer->createService(
      SERVICE_UUID
    );


  // ====================================================
  // BLE Characteristic
  // ====================================================

  pCharacteristic =
    pService->createCharacteristic(

      CHARACTERISTIC_UUID,

      BLECharacteristic::PROPERTY_READ |
      BLECharacteristic::PROPERTY_NOTIFY

    );


  pCharacteristic->addDescriptor(
    new BLE2902()
  );


  pCharacteristic->setValue(
    "STATUS=START"
  );


  // ====================================================
  // BLE Service 시작
  // ====================================================

  pService->start();


  // ====================================================
  // BLE Advertising
  // ====================================================

  BLEAdvertising *pAdvertising =
    BLEDevice::getAdvertising();


  pAdvertising->addServiceUUID(
    SERVICE_UUID
  );


  pAdvertising->setScanResponse(
    true
  );


  BLEDevice::startAdvertising();


  // ====================================================
  // 시스템 준비 완료
  // ====================================================

  lcd.clear();

  lcd.setCursor(0, 0);

  lcd.print(
    "System Ready"
  );

  lcd.setCursor(0, 1);

  lcd.print(
    "MQ Starting"
  );


  Serial.println(
    "System Ready"
  );

  Serial.println(
    "MQ Monitoring Started"
  );


  delay(1000);
}


// ======================================================
// Loop
// ======================================================

void loop() {

  // ====================================================
  // MQ 센서값 읽기
  // ====================================================

  int mqValue =
    analogRead(MQ_PIN);


  // ====================================================
  // 정상
  // ====================================================

  if (
    mqValue <= THRESHOLD_NORMAL
  ) {

    setNormal();


    updateLCD(
      mqValue,
      "NORMAL"
    );


    sendBLEMessage(
      "NORMAL",
      mqValue,
      false
    );


    // Serial Monitor

    Serial.print(
      "[NORMAL] "
    );

    Serial.print(
      "MQ="
    );

    Serial.print(
      mqValue
    );

    Serial.println(
      " | SERVO=0 | FAN=OFF"
    );
  }


  // ====================================================
  // 주의
  // ====================================================

  else if (
    mqValue <= THRESHOLD_WARNING
  ) {

    setWarning();


    updateLCD(
      mqValue,
      "WARNING"
    );


    sendBLEMessage(
      "WARNING",
      mqValue,
      false
    );


    // Serial Monitor

    Serial.print(
      "[WARNING] "
    );

    Serial.print(
      "MQ="
    );

    Serial.print(
      mqValue
    );

    Serial.println(
      " | SERVO=0 | FAN=OFF"
    );
  }


  // ====================================================
  // 위험
  // ====================================================

  else {

    setDanger();


    // ------------------------------------------
    // 부저 + 빨간 LED 알람 업데이트
    // ------------------------------------------

    updateDangerAlarm();


    updateLCD(
      mqValue,
      "DANGER"
    );


    sendBLEMessage(
      "DANGER",
      mqValue,
      true
    );


    // Serial Monitor

    Serial.print(
      "[DANGER] "
    );

    Serial.print(
      "MQ="
    );

    Serial.print(
      mqValue
    );

    Serial.println(
      " | SERVO=90 | FAN=ON"
    );
  }


  // ====================================================
  // 짧은 대기
  // ====================================================
  //
  // 기존 delay(3000)은 제거했습니다.
  //
  // 50ms 정도만 쉬면서 계속 센서와 알람을 확인합니다.
  // ====================================================

  delay(1000);
}
