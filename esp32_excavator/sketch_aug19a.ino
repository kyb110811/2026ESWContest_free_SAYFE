#include <Arduino.h>

#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>


#define GPIO_1  2
#define GPIO_2  3
#define GPIO_3  4
#define GPIO_4  5


#define SERVICE_UUID \
  "7f4a1001-8c21-4b7d-9a31-123456789001"

#define CHARACTERISTIC_UUID \
  "7f4a1002-8c21-4b7d-9a31-123456789002"


BLECharacteristic *pCharacteristic;

bool deviceConnected = false;


void gpioAllOn() {

  digitalWrite(GPIO_1, HIGH);
  digitalWrite(GPIO_2, HIGH);
  digitalWrite(GPIO_3, HIGH);
  digitalWrite(GPIO_4, HIGH);

  Serial.println("[GPIO] ALL ON");
}

void gpioAllOff() {

  digitalWrite(GPIO_1, LOW);
  digitalWrite(GPIO_2, LOW);
  digitalWrite(GPIO_3, LOW);
  digitalWrite(GPIO_4, LOW);

  Serial.println("[GPIO] ALL OFF");
}

class MyServerCallbacks : public BLEServerCallbacks {

  void onConnect(BLEServer *pServer) {

    deviceConnected = true;

    Serial.println();
    Serial.println("[BLE] Device Connected");
  }


  void onDisconnect(BLEServer *pServer) {

    deviceConnected = false;

    Serial.println();
    Serial.println("[BLE] Device Disconnected");

    // 다시 Advertising
    pServer->getAdvertising()->start();

    Serial.println("[BLE] Advertising Restarted");
  }
};

class MyCharacteristicCallbacks
  : public BLECharacteristicCallbacks {

  void onWrite(BLECharacteristic *pCharacteristic) {

    String message =
      pCharacteristic->getValue().c_str();

    message.trim();

    Serial.println();
    Serial.println("==============================");
    Serial.print("[BLE RX] ");
    Serial.println(message);
    Serial.println("==============================");

    if (message == "excavator_danger") {

      Serial.println("[EVENT] EXCAVATOR DANGER");

      gpioAllOn();
    }

    else if (message == "reset") {

      Serial.println("[EVENT] RESET");

      gpioAllOff();
    }


    else {

      Serial.print("[EVENT] UNKNOWN: ");
      Serial.println(message);
    }
  }
};

void setup() {

  Serial.begin(115200);

  delay(1000);


  Serial.println();
  Serial.println("==============================");
  Serial.println("EXCAVATOR GPIO CONTROLLER");
  Serial.println("==============================");


  pinMode(GPIO_1, OUTPUT);
  pinMode(GPIO_2, OUTPUT);
  pinMode(GPIO_3, OUTPUT);
  pinMode(GPIO_4, OUTPUT);


  gpioAllOff();

  BLEDevice::init("ESP32C3_EXCAVATOR");

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
      BLECharacteristic::PROPERTY_WRITE |
      BLECharacteristic::PROPERTY_NOTIFY

    );

  pCharacteristic->setCallbacks(
    new MyCharacteristicCallbacks()
  );


  pCharacteristic->addDescriptor(
    new BLE2902()
  );

  pCharacteristic->setValue(
    "READY"
  );

  pService->start();

  BLEAdvertising *pAdvertising =
    BLEDevice::getAdvertising();

  pAdvertising->addServiceUUID(
    SERVICE_UUID
  );

  pAdvertising->setScanResponse(true);


  BLEDevice::startAdvertising();


  Serial.println();
  Serial.println("[BLE] Ready");
  Serial.println("[BLE] Name : ESP32C3_EXCAVATOR");
  Serial.println();
  Serial.println("Waiting for BLE event...");
  Serial.println();
}


void loop() {
  delay(10);
}
