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
  delayMicroseconds(100);  // let channel switch settle before next I2C transaction
}

// --- BLE setup ---
BLEService imuService("180D");                 // custom service UUID
BLECharacteristic imuCharacteristic("2A37", BLERead | BLENotify, 120); // 120-byte buffer — 100 was too tight for worst-case extreme readings (106 chars), causing silent truncation

void setup() {
  Serial.begin(115200);
  // No while(!Serial) — sketch must run standalone without USB

  Wire.begin();
  Wire.setClock(100000);  // 100 kHz — more resilient to bus disruption from BLE SPI activity

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
  if (millis() - timer > 10) {  // ~100 Hz
    timer = millis();

    // I2C reads first — no BLE SPI activity during this window
    unsigned long ts = micros();
    tcaSelect(0); mpu1.update();
    tcaSelect(1); mpu2.update();

    // Build packet into fixed buffer — no heap allocation
    char buf[120];
    snprintf(buf, sizeof(buf),
      "%lu %.3f %.3f %.3f %.2f %.2f %.2f %.3f %.3f %.3f %.2f %.2f %.2f",
      ts,
      mpu1.getAccX(), mpu1.getAccY(), mpu1.getAccZ(),
      mpu1.getAngleX(), mpu1.getAngleY(), mpu1.getAngleZ(),
      mpu2.getAccX(), mpu2.getAccY(), mpu2.getAccZ(),
      mpu2.getAngleX(), mpu2.getAngleY(), mpu2.getAngleZ());

    // BLE operations after I2C is complete
    BLE.poll();
    imuCharacteristic.setValue((uint8_t*)buf, strlen(buf));
  } else {
    BLE.poll();  // keep BLE alive between sensor reads
  }
}
