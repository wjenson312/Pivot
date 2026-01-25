"""
BLE microSD data downloader for MKR 1010.

- Requests a CSV file stored on the device SD card
- Receives it over BLE in chunks
- Saves locally as a CSV file
"""

import asyncio
import time
from datetime import datetime
from bleak import BleakClient, BleakScanner

# =======================
# BLE CONFIGURATION
# =======================

SERVICE_UUID = "180D"

CONTROL_CHAR_UUID = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"   # WRITE
SD_TRANSFER_CHAR_UUID = "yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy"  # NOTIFY

TARGET_ADDRESS = "4D7B2416-F159-E284-3A2A-34D5A2603212"

# File to request from SD card
REMOTE_FILENAME = "run_0003.csv"

# =======================
# GLOBAL STATE
# =======================

recv_buffer = bytearray()
transfer_complete = False
start_time = None


def handle_sd_notification(sender, data):
    """Handle incoming SD data chunks."""
    global recv_buffer, transfer_complete

    if data == b"EOF":
        transfer_complete = True
        print("✅ Transfer complete signal received")
        return

    recv_buffer.extend(data)

    if len(recv_buffer) % 4096 < len(data):
        print(f"📥 Received {len(recv_buffer)} bytes...")


async def main():
    global transfer_complete, start_time

    print("🔍 Scanning for BLE devices...")
    devices = await BleakScanner.discover()

    found = False
    for d in devices:
        if d.address == TARGET_ADDRESS:
            found = True
            break

    if not found:
        print("❌ Device not found")
        return

    print(f"🔗 Connecting to {TARGET_ADDRESS}...")
    async with BleakClient(TARGET_ADDRESS) as client:
        print("✅ Connected")

        await client.start_notify(
            SD_TRANSFER_CHAR_UUID,
            handle_sd_notification
        )

        cmd = f"GET {REMOTE_FILENAME}"
        print(f"📤 Requesting file: {REMOTE_FILENAME}")
        start_time = time.time()

        await client.write_gatt_char(
            CONTROL_CHAR_UUID,
            cmd.encode("utf-8")
        )

        # Wait for EOF
        while not transfer_complete:
            await asyncio.sleep(0.1)

        await client.stop_notify(SD_TRANSFER_CHAR_UUID)

    elapsed = time.time() - start_time
    print(f"⏱ Transfer time: {elapsed:.2f} s")

    # =======================
    # SAVE FILE LOCALLY
    # =======================

    out_name = f"SD_SYNC_{REMOTE_FILENAME}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    out_name = out_name.replace(".csv", "") + ".csv"

    with open(out_name, "wb") as f:
        f.write(recv_buffer)

    print(f"💾 Saved CSV → {out_name}")
    print(f"📊 Total bytes: {len(recv_buffer)}")


if __name__ == "__main__":
    asyncio.run(main())