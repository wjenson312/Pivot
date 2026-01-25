#include <Wire.h>
#include <MPU6050_light.h>
#include <ArduinoBLE.h>

#define TCA_ADDR 0x70

MPU6050 mpu1(Wire);
MPU6050 mpu2(Wire);

long timer = 0;

// --- Multiplexer select function ---
void tcaSelect(uint8_t channel) {
  if (channel > 7) return;
  Wire.beginTransmission(TCA_ADDR);
  Wire.write(1 << channel);
  Wire.endTransmission();
}

// --- BLE setup ---
BLEService imuService("180D");                 // custom service UUID
BLECharacteristic imuCharacteristic("2A37", BLERead | BLENotify, 100); // 100-byte buffer

void setup() {
  Serial.begin(115200);
  while (!Serial);  // wait for Serial Monitor

  Wire.begin();

  // Initialize MPU1
  tcaSelect(0);
  byte status1 = mpu1.begin();
  if (status1 != 0) Serial.println("MPU1 init failed!");
  mpu1.calcOffsets(true, true);

  // Initialize MPU2
  tcaSelect(1);
  byte status2 = mpu2.begin();
  if (status2 != 0) Serial.println("MPU2 init failed!");
  mpu2.calcOffsets(true, true);

  // Initialize BLE
  if (!BLE.begin()) {
    Serial.println("Failed to initialize BLE!");
    while (1);
  }

  BLE.setLocalName("MKR1010_MPU");
  BLE.setDeviceName("MKR1010_MPU");
  BLE.setAdvertisedService(imuService);
  imuService.addCharacteristic(imuCharacteristic);
  BLE.addService(imuService);
  imuCharacteristic.setValue("0"); // initialize characteristic

  if (BLE.advertise()) {
    Serial.println("BLE advertising started");
  } else {
    Serial.println("BLE advertising failed");
  }
}

void loop() {
  BLE.poll();  // handle BLE events

  if (millis() - timer > 10) { // ~100 Hz
    // Update MPU1
    tcaSelect(0); mpu1.update();
    // Update MPU2
    tcaSelect(1); mpu2.update();

    // Prepare data string
    String dataStr = String(micros()) + " " +
                     String(mpu1.getAccX(), 3) + " " + String(mpu1.getAccY(), 3) + " " + String(mpu1.getAccZ(), 3) + " " +
                     String(mpu1.getAngleX(), 2) + " " + String(mpu1.getAngleY(), 2) + " " + String(mpu1.getAngleZ(), 2) + " " +
                     String(mpu2.getAccX(), 3) + " " + String(mpu2.getAccY(), 3) + " " + String(mpu2.getAccZ(), 3) + " " +
                     String(mpu2.getAngleX(), 2) + " " + String(mpu2.getAngleY(), 2) + " " + String(mpu2.getAngleZ(), 2);

    // Send data over BLE
    imuCharacteristic.setValue(dataStr.c_str()); // automatically notifies subscribed clients

    timer = millis();
  }
}
