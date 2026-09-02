#include <Arduino.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>

#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>

#include <ESP32Servo.h>

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


#define LCD_ADDRESS   0x27

// 16x2 LCD
LiquidCrystal_I2C lcd(
  LCD_ADDRESS,
  16,
  2
);


Servo myServo;

#define SERVO_NORMAL_ANGLE   0
#define SERVO_DANGER_ANGLE   90

#define THRESHOLD_NORMAL   500
#define THRESHOLD_WARNING  1000

bool dangerActive = false;
bool dangerOutputState = false;
unsigned long dangerPreviousMillis = 0;

const unsigned long DANGER_ON_TIME = 1000;
const unsigned long DANGER_OFF_TIME = 500;


// BLE UUID
#define SERVICE_UUID \
  "4fafc201-1fb5-459e-8fcc-c5c9c331914b"

#define CHARACTERISTIC_UUID \
  "beb5483e-36e1-4688-b7f5-ea07361b26a8"


BLECharacteristic *pCharacteristic;

bool deviceConnected = false;

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

void updateLCD(
  int mqValue,
  String status
) {

  lcd.clear();

  lcd.setCursor(0, 0);

  lcd.print("MQ: ");
  lcd.print(mqValue);


  // ------------------------------------------
  // 2번째 줄
  // ------------------------------------------

  lcd.setCursor(0, 1);

  lcd.print(status);
}

void setNormal() {

  dangerActive = false;
  dangerOutputState = false;

  digitalWrite(
    BUZZER_PIN,
    LOW
  );


  digitalWrite(LED_GREEN, HIGH);
  digitalWrite(LED_ORANGE, LOW);
  digitalWrite(LED_RED, LOW);


  myServo.write(
    SERVO_NORMAL_ANGLE
  );


  digitalWrite(
    FAN_PIN,
    LOW
  );
}


void setWarning() {

  dangerActive = false;
  dangerOutputState = false;

  digitalWrite(
    BUZZER_PIN,
    LOW
  );


  digitalWrite(LED_GREEN, LOW);
  digitalWrite(LED_ORANGE, HIGH);
  digitalWrite(LED_RED, LOW);

  myServo.write(
    SERVO_NORMAL_ANGLE
  );

  digitalWrite(
    FAN_PIN,
    LOW
  );
}
=

void setDanger() {

  digitalWrite(
    LED_GREEN,
    LOW
  );

  digitalWrite(
    LED_ORANGE,
    LOW
  );


  if (!dangerActive) {

    dangerActive = true;
    dangerOutputState = true;
    dangerPreviousMillis = millis();

    digitalWrite(
      LED_RED,
      HIGH
    );


    digitalWrite(
      BUZZER_PIN,
      HIGH
    );
  }



  myServo.write(
    SERVO_DANGER_ANGLE
  );



  digitalWrite(
    FAN_PIN,
    HIGH
  );
}


void updateDangerAlarm() {

  if (!dangerActive) {
    return;
  }


  unsigned long currentMillis = millis();

  unsigned long interval;


  if (dangerOutputState) {
    interval = DANGER_ON_TIME;
  }
  else {
    interval = DANGER_OFF_TIME;
  }

  if (
    currentMillis - dangerPreviousMillis
    >= interval
  ) {

    dangerPreviousMillis = currentMillis;
    dangerOutputState = !dangerOutputState;

    digitalWrite(
      LED_RED,
      dangerOutputState
        ? HIGH
        : LOW
    );

    digitalWrite(
      BUZZER_PIN,
      dangerOutputState
        ? HIGH
        : LOW
    );
  }
}


void setup() {


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

  Serial.begin(115200);

  delay(1000);

  Serial.println("==============================");
  Serial.println("ESP32-C3 MQ Monitor");
  Serial.println("System Starting...");
  Serial.println("==============================");

  Wire.begin(
    LCD_SDA,
    LCD_SCL
  );


  lcd.init();

  lcd.backlight();

  lcd.clear();


  lcd.setCursor(0, 0);

  lcd.print(
    "MQ MONITOR"
  );

  lcd.setCursor(0, 1);

  lcd.print(
    "Starting..."
  );


  delay(2000);

  Serial.println(
    "[SERVO] Initializing..."
  );


  myServo.setPeriodHertz(50);

  myServo.attach(
    SERVO_PIN,
    500,
    2400
  );


  myServo.write(
    SERVO_NORMAL_ANGLE
  );


  Serial.println(
    "[SERVO] Ready"
  );

  Serial.println(
    "[SERVO] Position = 0"
  );


  analogReadResolution(12);


  BLEDevice::init(
    "ESP32C3_MQ"
  );


  BLEServer *pServer =
    BLEDevice::createServer();


  pServer->setCallbacks(
    new MyServerCallbacks()
  );


  BLEService *pService =
    pServer->createService(
      SERVICE_UUID
    );


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

  pService->start();

  BLEAdvertising *pAdvertising =
    BLEDevice::getAdvertising();


  pAdvertising->addServiceUUID(
    SERVICE_UUID
  );


  pAdvertising->setScanResponse(
    true
  );


  BLEDevice::startAdvertising();

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


void loop() {

  int mqValue =
    analogRead(MQ_PIN);

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


  else {

    setDanger();

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

  delay(1000);
}
