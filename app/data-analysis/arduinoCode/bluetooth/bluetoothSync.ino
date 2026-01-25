#include <Wire.h>
#include <SPI.h>
#include <SD.h>
#include <MPU6050_light.h>
#include <ArduinoBLE.h>

#define TCA_ADDR 0x70
#define SD_CS_PIN 4
#define BUTTON_PIN 7

// =======================
// STATE MACHINE
// =======================
enum DeviceState {
  IDLE,
  RECORDING,
  BLE_SYNC
};

DeviceState state = IDLE;

// =======================
// IMUs
// =======================
MPU6050 mpu1(Wire);
MPU6050 mpu2(Wire);

// =======================
// BLE
// =======================
BLEService dataService("180D");
BLECharacteristic controlChar(
  "11111111-1111-1111-1111-111111111111",
  BLEWrite,
  40
);

BLECharacteristic sdChar(
  "22222222-2222-2222-2222-222222222222",
  BLENotify,
  180
);

// =======================
// SD
// =======================
File logFile;
uint16_t runIndex = 0;

// =======================
// TIMING
// =======================
unsigned long lastSampleMs = 0;
unsigned long buttonPressMs = 0;
bool buttonHeld = false;

// =======================
// MULTIPLEXER
// =======================
void tcaSelect(uint8_t ch) {
  Wire.beginTransmission(TCA_ADDR);
  Wire.write(1 << ch);
  Wire.endTransmission();
}

// =======================
// UTILITIES
// =======================
String nextRunFilename() {
  char name[20];
  sprintf(name, "/run_%04d.csv", runIndex++);
  return String(name);
}

// =======================
// BLE COMMAND HANDLER
// =======================
void handleControlWrite(BLEDevice central, BLECharacteristic characteristic) {
  String cmd = characteristic.value();
  cmd.trim();

  if (!cmd.startsWith("GET ")) return;

  String filename = cmd.substring(4);
  File f = SD.open(filename);

  if (!f) {
    sdChar.notify("ERR");
    return;
  }

  uint8_t buf[180];
  while (f.available()) {
    int n = f.read(buf, sizeof(buf));
    sdChar.notify(buf, n);
    delay(5);
  }

  sdChar.notify("EOF");
  f.close();
}

// =======================
// SETUP
// =======================
void setup() {
  Serial.begin(115200);
  Wire.begin();
  pinMode(BUTTON_PIN, INPUT_PULLUP);

  // IMUs
  tcaSelect(0); mpu1.begin(); mpu1.calcOffsets();
  tcaSelect(1); mpu2.begin(); mpu2.calcOffsets();

  // SD
  if (!SD.begin(SD_CS_PIN)) {
    Serial.println("SD init failed");
    while (1);
  }

  // BLE
  BLE.begin();
  BLE.setLocalName("MKR1010_MPU");
  BLE.setAdvertisedService(dataService);
  dataService.addCharacteristic(controlChar);
  dataService.addCharacteristic(sdChar);
  BLE.addService(dataService);

  controlChar.setEventHandler(BLEWritten, handleControlWrite);
}

// =======================
// LOOP
// =======================
void loop() {
  BLE.poll();

  // -----------------------
  // BUTTON HANDLING
  // -----------------------
  bool pressed = digitalRead(BUTTON_PIN) == LOW;

  if (pressed && !buttonHeld) {
    buttonHeld = true;
    buttonPressMs = millis();
  }

  if (!pressed && buttonHeld) {
    unsigned long held = millis() - buttonPressMs;
    buttonHeld = false;

    if (held > 2000) {
      state = BLE_SYNC;
      BLE.advertise();
    } else {
      if (state == RECORDING) {
        logFile.close();
        state = IDLE;
      } else if (state == IDLE) {
        String fname = nextRunFilename();
        logFile = SD.open(fname, FILE_WRITE);
        logFile.println("ts,ax1,ay1,az1,gx1,gy1,gz1,ax2,ay2,az2,gx2,gy2,gz2");
        state = RECORDING;
      }
    }
  }

  // -----------------------
  // RECORDING STATE
  // -----------------------
  if (state == RECORDING && millis() - lastSampleMs >= 10) {
    lastSampleMs = millis();

    tcaSelect(0); mpu1.update();
    tcaSelect(1); mpu2.update();

    logFile.print(micros()); logFile.print(",");
    logFile.print(mpu1.getAccX(),3); logFile.print(",");
    logFile.print(mpu1.getAccY(),3); logFile.print(",");
    logFile.print(mpu1.getAccZ(),3); logFile.print(",");
    logFile.print(mpu1.getGyroX(),3); logFile.print(",");
    logFile.print(mpu1.getGyroY(),3); logFile.print(",");
    logFile.print(mpu1.getGyroZ(),3); logFile.print(",");
    logFile.print(mpu2.getAccX(),3); logFile.print(",");
    logFile.print(mpu2.getAccY(),3); logFile.print(",");
    logFile.print(mpu2.getAccZ(),3); logFile.print(",");
    logFile.print(mpu2.getGyroX(),3); logFile.print(",");
    logFile.print(mpu2.getGyroY(),3); logFile.print(",");
    logFile.println(mpu2.getGyroZ(),3);
  }

  // -----------------------
  // BLE SYNC STATE
  // -----------------------
  if (state == BLE_SYNC) {
    // BLE callbacks do the work
    if (!BLE.connected()) {
      state = IDLE;
      BLE.stopAdvertise();
    }
  }
}

