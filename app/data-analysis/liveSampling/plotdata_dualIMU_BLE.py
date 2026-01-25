#!/usr/bin/env python3
"""
Real-time BLE plotter for dual MPU6050.

Connects to an MKR1010 BLE peripheral advertising IMU data,
reads the characteristic notifications, and plots two subplots (one per IMU).

Expected BLE data line format (space-separated):
 ts ax1 ay1 az1 gx1 gy1 gz1 ax2 ay2 az2 gx2 gy2 gz2

Dependencies: bleak, matplotlib
"""

import asyncio
import time
from collections import deque
import matplotlib.pyplot as plt
from bleak import BleakClient, BleakScanner

# BLE device info (must match Arduino sketch)
DEVICE_NAME = "MKR1010_MPU"
SERVICE_UUID = "180D"
CHARACTERISTIC_UUID = "2A37"
TARGET_ADDRESS = "4D7B2416-F159-E284-3A2A-34D5A2603212"

# Plotting / data config
MAX_POINTS = 1000
UPDATE_EVERY = 5  # update plot every N samples

# Data buffers
xs = deque(maxlen=MAX_POINTS)
data = {
    'imu1_ax': deque(maxlen=MAX_POINTS),
    'imu1_ay': deque(maxlen=MAX_POINTS),
    'imu1_az': deque(maxlen=MAX_POINTS),
    'imu1_gx': deque(maxlen=MAX_POINTS),
    'imu1_gy': deque(maxlen=MAX_POINTS),
    'imu1_gz': deque(maxlen=MAX_POINTS),
    'imu2_ax': deque(maxlen=MAX_POINTS),
    'imu2_ay': deque(maxlen=MAX_POINTS),
    'imu2_az': deque(maxlen=MAX_POINTS),
    'imu2_gx': deque(maxlen=MAX_POINTS),
    'imu2_gy': deque(maxlen=MAX_POINTS),
    'imu2_gz': deque(maxlen=MAX_POINTS),
}

first_ts = None
count = 0
last_status = time.time()


def parse_line(raw):
    """Parse a BLE data line into (ts_micro, values)"""
    if not raw:
        return None, None
    parts = [p for p in raw.strip().split() if p.strip() != '']
    if len(parts) < 13:
        return None, None
    try:
        ts = int(parts[0])
        vals = [float(v) for v in parts[1:13]]
        return ts, vals
    except Exception:
        return None, None


def setup_plot():
    plt.ion()
    fig, axes = plt.subplots(4, 1, sharex=True, figsize=(12, 9))
    ax_acc1, ax_gyro1, ax_acc2, ax_gyro2 = axes

    colors = ['r', 'g', 'b']
    acc_labels = ['ax', 'ay', 'az']
    gyr_labels = ['gx', 'gy', 'gz']

    lines_acc1, lines_gyr1, lines_acc2, lines_gyr2 = [], [], [], []

    for i, lab in enumerate(acc_labels):
        l, = ax_acc1.plot([], [], label=f"IMU1_{lab}", color=colors[i])
        lines_acc1.append(l)
    for i, lab in enumerate(gyr_labels):
        l, = ax_gyro1.plot([], [], label=f"IMU1_{lab}", color=colors[i])
        lines_gyr1.append(l)

    for i, lab in enumerate(acc_labels):
        l, = ax_acc2.plot([], [], label=f"IMU2_{lab}", color=colors[i])
        lines_acc2.append(l)
    for i, lab in enumerate(gyr_labels):
        l, = ax_gyro2.plot([], [], label=f"IMU2_{lab}", color=colors[i])
        lines_gyr2.append(l)

    ax_acc1.set_ylabel('IMU1 Acc (g)')
    ax_gyro1.set_ylabel('IMU1 Gyro (deg)')
    ax_acc2.set_ylabel('IMU2 Acc (g)')
    ax_gyro2.set_ylabel('IMU2 Gyro (deg)')
    ax_gyro2.set_xlabel('Arduino time (s)')

    for ax in axes:
        ax.legend(loc='upper right')
        ax.grid(True)

    return fig, ax_acc1, ax_gyro1, ax_acc2, ax_gyro2, lines_acc1, lines_gyr1, lines_acc2, lines_gyr2


async def main():

    print("Scanning for BLE devices...")
    devices = await BleakScanner.discover()

    found = False

    for dev in devices:
        print(f"Found BLE device: {dev.name} | {dev.address}")

        if dev.address == TARGET_ADDRESS:
            found = True
            break

    if not found:
        print(f"\n❌ Device with address {TARGET_ADDRESS} not found.")
        print("   → Turn device off/on")
        print("   → Turn Bluetooth off/on")
        print("   → Make sure no other program is connected")
        return

    print(f"\n🔗 Connecting to device at {TARGET_ADDRESS}...")

    async with BleakClient(TARGET_ADDRESS) as client:
        print("✅ Connected!")
        # Your notify + plotting code continues as-is below

        fig, ax_acc1, ax_gyro1, ax_acc2, ax_gyro2, lines_acc1, lines_gyr1, lines_acc2, lines_gyr2 = setup_plot()

        def handle_notification(sender, payload):
            global count, last_status, first_ts

            # Decode BLE bytes to string
            line = payload.decode('utf-8').strip()
            ts, vals = parse_line(line)
            if ts is None:
                return

            # Establish time zero
            if first_ts is None:
                first_ts = ts
            t_s = (ts - first_ts) / 1_000_000.0
            xs.append(t_s)

            # Store IMU1 values
            data['imu1_ax'].append(vals[0])
            data['imu1_ay'].append(vals[1])
            data['imu1_az'].append(vals[2])
            data['imu1_gx'].append(vals[3])
            data['imu1_gy'].append(vals[4])
            data['imu1_gz'].append(vals[5])

            # Store IMU2 values
            data['imu2_ax'].append(vals[6])
            data['imu2_ay'].append(vals[7])
            data['imu2_az'].append(vals[8])
            data['imu2_gx'].append(vals[9])
            data['imu2_gy'].append(vals[10])
            data['imu2_gz'].append(vals[11])

            count += 1

            # Update plot occasionally for efficiency
            if count % UPDATE_EVERY == 0 and len(xs) > 0:
                x = list(xs)

                # IMU1 accel
                for i, key in enumerate(['imu1_ax','imu1_ay','imu1_az']):
                    y = list(data[key])
                    lines_acc1[i].set_data(x[-len(y):], y)

                # IMU1 gyro
                for i, key in enumerate(['imu1_gx','imu1_gy','imu1_gz']):
                    y = list(data[key])
                    lines_gyr1[i].set_data(x[-len(y):], y)

                # IMU2 accel
                for i, key in enumerate(['imu2_ax','imu2_ay','imu2_az']):
                    y = list(data[key])
                    lines_acc2[i].set_data(x[-len(y):], y)

                # IMU2 gyro
                for i, key in enumerate(['imu2_gx','imu2_gy','imu2_gz']):
                    y = list(data[key])
                    lines_gyr2[i].set_data(x[-len(y):], y)

                # Refresh plot
                for ax in (ax_acc1, ax_gyro1, ax_acc2, ax_gyro2):
                    ax.relim()
                    ax.autoscale_view(True, True, True)

                fig.canvas.draw_idle()
                plt.pause(0.001)

            # Status print every second
            if time.time() - last_status > 1:
                print(f"Samples: {count}, buffer: {len(xs)}")
                last_status = time.time()

        await client.start_notify(CHARACTERISTIC_UUID, handle_notification)

        print("Receiving BLE data... Press Ctrl+C to stop.")
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("Interrupted by user.")
        finally:
            await client.stop_notify(CHARACTERISTIC_UUID)
            plt.ioff()
            plt.show()


if __name__ == '__main__':
    asyncio.run(main())
