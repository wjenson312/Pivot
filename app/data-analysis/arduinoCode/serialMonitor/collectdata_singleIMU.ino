#include "Wire.h"
#include <MPU6050_light.h>

MPU6050 mpu(Wire);

long timer = 0;

void setup() {
  Serial.begin(250000);  // Match Python baud rate for faster data transfer
  while(!Serial);
  delay(2000);

  Wire.begin();
  
  byte status = mpu.begin();
  Serial.print(F("MPU6050 status: "));
  Serial.println(status);
  while(status!=0){ } // stop everything if could not connect to MPU6050
  
  Serial.println(F("Calculating offsets, do not move MPU6050"));
  delay(1000);
  mpu.calcOffsets(true,true); // gyro and accelero
  Serial.println("Done!\n");
  
}

void loop() {
  mpu.update();

  if(millis() - timer > 10){ // print data every 10 ms (100Hz refresh rate)
    // Send single compact line: timestamp ax ay az gx gy gz
    unsigned long ts = micros();
    Serial.print(ts);
    Serial.print(" ");
    Serial.print(mpu.getAccX(), 3);
    Serial.print(" ");
    Serial.print(mpu.getAccY(), 3);
    Serial.print(" ");
    Serial.print(mpu.getAccZ(), 3);
    Serial.print(" ");
    Serial.print(mpu.getAngleX(), 2);
    Serial.print(" ");
    Serial.print(mpu.getAngleY(), 2);
    Serial.print(" ");
    Serial.println(mpu.getAngleZ(), 2);
    timer = millis();
  }

}

