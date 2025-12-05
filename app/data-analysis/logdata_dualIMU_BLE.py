"""
BLE receiver for dual-IMU data broadcast from MKR 1010 over BLE.
Reads compact CSV-style lines from the BLE characteristic and writes them to a CSV file.

Expected BLE data line format:
 ts a1x a1y a1z g1x g1y g1z a2x a2y a2z g2x g2y g2z
"""

import asyncio
import csv
import time
from datetime import datetime
from bleak import BleakClient, BleakScanner

# BLE UUIDs from the Arduino sketch
SERVICE_UUID = "180D"
CHARACTERISTIC_UUID = "2A37"

# Device identity
DEVICE_NAME = "MKR1010_MPU"   # Unused unless name begins working on macOS
TARGET_ADDRESS = "4D7B2416-F159-E284-3A2A-34D5A2603212"   # ← YOUR BOARD MAC

# Output CSV
out_fname = f"MPU_BothIMUs_BLE_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
csv_file = open(out_fname, 'w', newline='')
csv_writer = csv.writer(csv_file)

header = [
    'arduino_time_s', 'receive_time_s',
    'imu1_acc_x','imu1_acc_y','imu1_acc_z','imu1_gx','imu1_gy','imu1_gz',
    'imu2_acc_x','imu2_acc_y','imu2_acc_z','imu2_gx','imu2_gy','imu2_gz'
]
csv_writer.writerow(header)

first_ts = None
count = 0
last_print = time.time()


def handle_notification(sender, payload):
    """Receive IMU BLE stream and write rows to CSV."""
    global first_ts, count, last_print

    try:
        line = payload.decode('utf-8').strip()
        if not line:
            return

        parts = [p for p in line.replace('\t', ' ').split() if p.strip()]
        if len(parts) < 13:
            return

        arduino_ts = int(parts[0])
        if first_ts is None:
            first_ts = arduino_ts

        arduino_ts_s = (arduino_ts - first_ts) / 1_000_000.0
        vals = [float(v) for v in parts[1:13]]

        imu1 = vals[0:6]
        imu2 = vals[6:12]

        row = [arduino_ts_s, time.time(), *imu1, *imu2]
        csv_writer.writerow(row)
        count += 1

        if time.time() - last_print > 1:
            print(f"Logged {count} samples")
            last_print = time.time()

    except Exception as e:
        print(f"Error parsing BLE packet: {line} -> {e}")


async def main():

    print("Scanning for BLE devices...")
    devices = await BleakScanner.discover()

    found = False
    for dev in devices:
        print(f"Found device: {dev.name} | {dev.address}")   # Debug print
        if dev.address == TARGET_ADDRESS:                   # Address match = reliable
            found = True
            break

    if not found:
        print(f"\n❌ Could not find device at {TARGET_ADDRESS}")
        print("Check power, BLE advertising, and ensure no other device is connected.")
        return

    print(f"\n🔗 Connecting to device at {TARGET_ADDRESS}...")
    async with BleakClient(TARGET_ADDRESS) as client:
        print("✅ Connected. Subscribing to notifications...")
        await client.start_notify(CHARACTERISTIC_UUID, handle_notification)

        print("Receiving IMU data → logging to CSV (Ctrl+C to stop)")
        try:
            while True:
                await asyncio.sleep(1)

        except KeyboardInterrupt:
            print("\nStopping logger...")

        finally:
            await client.stop_notify(CHARACTERISTIC_UUID)
            csv_file.close()
            print(f"💾 Saved {count} rows to {out_fname}")


if __name__ == "__main__":
    asyncio.run(main())
