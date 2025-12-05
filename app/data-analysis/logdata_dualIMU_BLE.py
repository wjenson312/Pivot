"""
BLE receiver for dual-IMU data broadcast from MKR 1010 over BLE.
Reads compact CSV-style lines from the BLE characteristic and writes them to a CSV file.

Expected BLE data line format (same as Serial version):
 ts a1x a1y a1z g1x g1y g1z a2x a2y a2z g2x g2y g2z
"""

import asyncio
import csv
import time
from datetime import datetime
from bleak import BleakClient, BleakScanner

# UUIDs from the Arduino sketch
SERVICE_UUID = "180D"         # Service UUID
CHARACTERISTIC_UUID = "2A37"  # Characteristic UUID

# Name of the BLE device (as advertised in Arduino sketch)
DEVICE_NAME = "MKR1010_MPU"

# Output CSV file
out_fname = f"MPU_BothIMUs_BLE_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
csv_file = open(out_fname, 'w', newline='')
csv_writer = csv.writer(csv_file)
header = ['arduino_time_s', 'receive_time_s',
          'imu1_acc_x','imu1_acc_y','imu1_acc_z','imu1_gx','imu1_gy','imu1_gz',
          'imu2_acc_x','imu2_acc_y','imu2_acc_z','imu2_gx','imu2_gy','imu2_gz']
csv_writer.writerow(header)

first_ts = None
count = 0
last_print = time.time()

def handle_notification(sender, data):
    """Callback for BLE notifications"""
    global first_ts, count, last_print

    try:
        line = data.decode('utf-8').strip()
        if not line:
            return

        parts = [p for p in line.replace('\t', ' ').split() if p.strip() != '']
        if len(parts) < 13:
            return  # skip incomplete lines

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

        # print status every second
        if time.time() - last_print > 1.0:
            print(f"Logged {count} samples")
            last_print = time.time()

    except Exception as e:
        print(f"Error parsing BLE data: {line} -> {e}")

async def main():
    print("Scanning for BLE devices...")
    devices = await BleakScanner.discover()
    target = None
    for d in devices:
        if DEVICE_NAME in d.name:
            target = d
            break

    if target is None:
        print(f"Device '{DEVICE_NAME}' not found. Make sure it is advertising.")
        return

    print(f"Connecting to {target.name} [{target.address}]...")
    async with BleakClient(target.address) as client:
        print("Connected. Subscribing to notifications...")
        await client.start_notify(CHARACTERISTIC_UUID, handle_notification)

        print("Receiving data... (Ctrl+C to stop)")
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping...")
        finally:
            await client.stop_notify(CHARACTERISTIC_UUID)

    csv_file.close()
    print(f"Saved {count} rows to {out_fname}")

if __name__ == "__main__":
    asyncio.run(main())
