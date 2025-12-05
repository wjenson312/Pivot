#include "Wire.h"
#include <MPU6050_light.h>

#define TCA_ADDR 0x70  // Default I2C address of the TCA9548A multiplexer

MPU6050 mpu1(Wire);  // IMU on channel 0
MPU6050 mpu2(Wire);  // IMU on channel 1

long timer = 0;

// Function to select multiplexer channel
void tcaSelect(uint8_t channel) {
  if (channel > 7) return;
  Wire.beginTransmission(TCA_ADDR);
  Wire.write(1 << channel);  // send byte with only the selected channel high
  Wire.endTransmission();
}

void setup() {
  Serial.begin(250000);  // Match Python baud rate
  while (!Serial);
  delay(2000);

  Wire.begin();

  // Initialize MPU1 on channel 0
  tcaSelect(0);
  byte status1 = mpu1.begin();
  Serial.print(F("MPU1 status: "));
  Serial.println(status1);
  while (status1 != 0) { }

  Serial.println(F("Calculating offsets for MPU1, do not move"));
  delay(1000);
  mpu1.calcOffsets(true, true);
  Serial.println("Done MPU1!\n");

  // Initialize MPU2 on channel 1
  tcaSelect(1);
  byte status2 = mpu2.begin();
  Serial.print(F("MPU2 status: "));
  Serial.println(status2);
  while (status2 != 0) { }

  Serial.println(F("Calculating offsets for MPU2, do not move"));
  delay(1000);
  mpu2.calcOffsets(true, true);
  Serial.println("Done MPU2!\n");
}

void loop() {
  unsigned long currentMicros = micros();

  if (millis() - timer > 10) {  // 100 Hz refresh rate

    // Read MPU1
    tcaSelect(0);
    mpu1.update();

    // Read MPU2
    tcaSelect(1);
    mpu2.update();

    // Print a single line: ts ax1 ay1 az1 gx1 gy1 gz1 ax2 ay2 az2 gx2 gy2 gz2
    Serial.print(currentMicros);

    // MPU1 data
    Serial.print(" ");
    Serial.print(mpu1.getAccX(), 3);
    Serial.print(" ");
    Serial.print(mpu1.getAccY(), 3);
    Serial.print(" ");
    Serial.print(mpu1.getAccZ(), 3);
    Serial.print(" ");
    Serial.print(mpu1.getAngleX(), 2);
    Serial.print(" ");
    Serial.print(mpu1.getAngleY(), 2);
    Serial.print(" ");
    Serial.print(mpu1.getAngleZ(), 2);

    // MPU2 data
    Serial.print(" ");
    Serial.print(mpu2.getAccX(), 3);
    Serial.print(" ");
    Serial.print(mpu2.getAccY(), 3);
    Serial.print(" ");
    Serial.print(mpu2.getAccZ(), 3);
    Serial.print(" ");
    Serial.print(mpu2.getAngleX(), 2);
    Serial.print(" ");
    Serial.print(mpu2.getAngleY(), 2);
    Serial.print(" ");
    Serial.println(mpu2.getAngleZ(), 2);

    timer = millis();
  }
}