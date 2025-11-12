# MPU6050 Serial Data Logger
# Reads compact data from Arduino serial and logs to CSV with Arduino timestamps

import serial
import csv
import re
from datetime import datetime

port = '/dev/cu.usbmodem11201'  # Change to your Arduino port
baud_rate = 250000
max_retries = 3

# Prompt for test or official run
print("Type 0 for test run, or 1 for official run: ")
choice = input().strip()
if choice == '1':
    csv_filename = f'MPU_OfficialRun_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
else:
    csv_filename = f'MPU_TestRun_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'

print(f"Logging to: {csv_filename}")

# Open CSV file
csv_file = open(csv_filename, 'w', newline='')
csv_writer = csv.writer(csv_file)
csv_writer.writerow(['time_s', 'accel_x', 'accel_y', 'accel_z', 'angle_x', 'angle_y', 'angle_z'])

# Open serial connection
try:
    ser = serial.Serial(port, baud_rate, timeout=1)
except Exception as e:
    print(f"Failed to open serial port {port}: {e}")
    exit(1)

import time
time.sleep(2)

# Parse compact single-line format: ts ax ay az gx gy gz
data_pattern = re.compile(r'(\d+)\s+([-+]?\d+\.?\d*)\s+([-+]?\d+\.?\d*)\s+([-+]?\d+\.?\d*)\s+([-+]?\d+\.?\d*)\s+([-+]?\d+\.?\d*)\s+([-+]?\d+\.?\d*)')

sample_count = 0
arduino_start_time = None

try:
    print("Logging data (Ctrl+C to stop)...")
    while True:
        line = ser.readline().decode(errors='ignore').strip()
        if not line:
            continue

        # Parse compact data line: timestamp ax ay az gx gy gz
        match = data_pattern.search(line)
        if match:
            ts_micros, ax_val, ay_val, az_val, gx_val, gy_val, gz_val = match.groups()
            ts_micros = int(ts_micros)
            
            # Initialize reference time on first sample
            if arduino_start_time is None:
                arduino_start_time = ts_micros
                print(f"Started logging at Arduino timestamp: {arduino_start_time} micros")
            
            # Convert Arduino microseconds to seconds, relative to first sample
            t = (ts_micros - arduino_start_time) / 1_000_000.0
            
            # Write to CSV
            csv_writer.writerow([t, ax_val, ay_val, az_val, gx_val, gy_val, gz_val])
            sample_count += 1

except KeyboardInterrupt:
    print(f'\nStopping... Total samples logged: {sample_count}')
finally:
    csv_file.close()
    ser.close()
    print(f"Data saved to: {csv_filename}")
