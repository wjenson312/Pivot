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
// NON-BLOCKING FILE TRANSFER
// =======================
File xferFile;
bool xferActive = false;
File listRoot;
bool listActive = false;
unsigned long lastXferMs = 0;

// =======================
// MULTIPLEXER
// =======================
void tcaSelect(uint8_t ch) {
  Wire.beginTransmission(TCA_ADDR);
  Wire.write(1 << ch);
  Wire.endTransmission();
  delayMicroseconds(100);  // let channel switch settle before next I2C transaction
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

  if (cmd == "LIST") {
    // Kick off a non-blocking directory listing; chunks sent from loop()
    if (listActive) listRoot.close();
    listRoot = SD.open("/");
    listActive = true;
    return;
  }

  if (cmd.startsWith("GET ")) {
    // Kick off a non-blocking file transfer; chunks sent from loop()
    String filename = cmd.substring(4);
    if (xferActive) xferFile.close();
    xferFile = SD.open(filename);
    if (!xferFile) {
      sdChar.notify("ERR");
      return;
    }
    xferActive = true;
    return;
  }

  if (cmd.startsWith("DELETE ")) {
    String filename = cmd.substring(7);
    if (SD.exists(filename) && SD.remove(filename)) {
      sdChar.notify("DELETED");
    } else {
      sdChar.notify("ERR");
    }
    return;
  }
}

// =======================
// SETUP
// =======================
void setup() {
  Serial.begin(115200);
  Wire.begin();
  Wire.setClock(100000);  // 100 kHz — more resilient to bus disruption from BLE SPI activity
  pinMode(BUTTON_PIN, INPUT_PULLUP);

  // IMUs — delay between channels so multiplexer and bus are settled before calcOffsets
  tcaSelect(0); delay(10); mpu1.begin(); mpu1.calcOffsets();
  tcaSelect(1); delay(10); mpu2.begin(); mpu2.calcOffsets();

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
    // Send one LIST entry per 20ms tick (non-blocking)
    if (listActive && millis() - lastXferMs >= 20) {
      lastXferMs = millis();
      File entry = listRoot.openNextFile();
      if (!entry) {
        listRoot.close();
        listActive = false;
        sdChar.notify("EOF");
      } else {
        String name = entry.name();
        entry.close();
        if (name.startsWith("run_") && name.endsWith(".csv")) {
          String line = "/" + name + "\n";
          sdChar.notify((const uint8_t*)line.c_str(), line.length());
        }
      }
    }

    // Send one GET chunk per 20ms tick (non-blocking)
    if (xferActive && millis() - lastXferMs >= 20) {
      lastXferMs = millis();
      if (xferFile.available()) {
        uint8_t buf[180];
        int n = xferFile.read(buf, sizeof(buf));
        sdChar.notify(buf, n);
      } else {
        xferFile.close();
        xferActive = false;
        sdChar.notify("EOF");
      }
    }

    if (!BLE.connected()) {
      // Clean up any in-progress transfers on disconnect
      if (listActive) { listRoot.close(); listActive = false; }
      if (xferActive) { xferFile.close(); xferActive = false; }
      state = IDLE;
      BLE.stopAdvertise();
    }
  }
}

