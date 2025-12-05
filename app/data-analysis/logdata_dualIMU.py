"""
Serial receiver for dual-IMU data printed from the Arduino.
Reads compact CSV lines from the serial monitor and writes them to a CSV file.

Expected serial line format (compact CSV):
 ts,a1x,a1y,a1z,g1x,g1y,g1z,a2x,a2y,a2z,g2x,g2y,g2z

Example usage:
  python app/data-analysis/logdata_bothIMUs.py

"""

import serial
import csv
import time
from datetime import datetime

# Configuration
DEFAULT_PORTS = ['/dev/cu.usbmodem101', '/dev/cu.usbmodem14201', '/dev/ttyACM0', '/dev/ttyUSB0', 'COM3']
baud_rate = 250000

# Ask user for serial port (default suggestions shown)
print("Enter serial port to read from (press Enter to try defaults):")
for p in DEFAULT_PORTS:
    print(f"  {p}")
port = input().strip()
if not port:
    # pick the first existing default (best effort) else the first default
    import os
    port = next((p for p in DEFAULT_PORTS if os.path.exists(p)), DEFAULT_PORTS[0])

print(f"Opening serial port: {port} @ {baud_rate} baud")
try:
    ser = serial.Serial(port, baud_rate, timeout=1)
except Exception as e:
    print(f"Failed to open serial port {port}: {e}")
    raise

time.sleep(2)

# Output CSV file
out_fname = f"MPU_BothIMUs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
print(f"Logging to {out_fname}")
csv_file = open(out_fname, 'w', newline='')
csv_writer = csv.writer(csv_file)
header = ['arduino_time_s', 'receive_time_s',
          'imu1_acc_x','imu1_acc_y','imu1_acc_z','imu1_gx','imu1_gy','imu1_gz',
          'imu2_acc_x','imu2_acc_y','imu2_acc_z','imu2_gx','imu2_gy','imu2_gz']
csv_writer.writerow(header)

first_ts = None
count = 0
last_print = time.time()

print('Reading serial lines (Ctrl+C to stop)...')
try:
    while True:
        raw = ser.readline().decode('utf-8', errors='ignore').strip()
        if not raw:
            continue

        parts = [p.strip() for p in raw.replace('\t', ',').split(',') if p.strip()!='']
        # If split by commas didn't give enough fields, try splitting by whitespace
        if len(parts) < 13:
            parts = [p for p in raw.split() if p.strip()!='']

        if len(parts) >= 13:
            try:
                arduino_ts = int(parts[0])
                if first_ts is None:
                    first_ts = arduino_ts
                arduino_ts_s = (arduino_ts - first_ts) / 1_000_000.0
                vals = [float(v) for v in parts[1:13]]
                imu1 = vals[0:6]
                imu2 = vals[6:12]
                receive_ts = time.time()
                row = [arduino_ts_s, receive_ts]
                row.extend(imu1)
                row.extend(imu2)
                csv_writer.writerow(row)
                count += 1
            except Exception as e:
                print(f"Parse error for line: {raw}  -> {e}")
                continue
        else:
            print(f"Unrecognized serial line: {raw}")

        if time.time() - last_print > 1.0:
            print(f"Logged {count} samples")
            last_print = time.time()

except KeyboardInterrupt:
    print('\nStopping...')
finally:
    csv_file.close()
    ser.close()
    print(f"Saved {count} rows to {out_fname}")
