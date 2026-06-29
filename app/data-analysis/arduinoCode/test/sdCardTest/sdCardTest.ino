#include <SPI.h>
#include <SD.h>

const int chipSelect = 10;

void setup() {
  Serial.begin(115200);
  while (!Serial);

  Serial.println("Initializing SD card...");
  if (!SD.begin(chipSelect)) {
    Serial.println("SD.begin() failed — check card detect/init at SPI level.");
    return;
  }
  Serial.println("SD.begin() succeeded.");

  File root = SD.open("/");
  if (!root) {
    Serial.println("Could not open root directory — filesystem issue.");
    return;
  }
  Serial.println("Root directory opened OK. Listing files:");
  while (true) {
    File entry = root.openNextFile();
    if (!entry) break;
    Serial.println(entry.name());
    entry.close();
  }
}

void loop() {}
