#!/usr/bin/env python3
"""
Real-time plotter for dual MPU6050 over serial.

Reads lines printed by `collectdata_dualIMU.ino` and plots two subplots (one per IMU).
Expected serial line format (space- or comma-separated):
 ts ax1 ay1 az1 gx1 gy1 gz1 ax2 ay2 az2 gx2 gy2 gz2

Run:
  python app/data-analysis/plotdata_dualIMU.py --port /dev/ttyUSB0

Dependencies: pyserial, matplotlib
"""

import argparse
import os
import sys
import time
from collections import deque

try:
    import serial
except Exception as e:
    print("pyserial is required (pip install pyserial)")
    raise

import matplotlib.pyplot as plt


def choose_default_port():
    defaults = ['/dev/cu.usbmodem101', '/dev/cu.usbmodem14201', '/dev/ttyACM0', '/dev/ttyUSB0', 'COM3']
    for p in defaults:
        if os.path.exists(p):
            return p
    return defaults[0]


def parse_line(raw):
    """Parse a raw serial line into (ts_micro, vals_list) or (None, None) on failure.
    Accepts either comma-separated or whitespace-separated values.
    """
    if not raw:
        return None, None
    # Normalize tabs to spaces, prefer comma split if comma present
    if ',' in raw:
        parts = [p.strip() for p in raw.replace('\t', ',').split(',') if p.strip()!='']
    else:
        parts = [p for p in raw.split() if p.strip()!='']

    if len(parts) < 13:
        return None, None

    try:
        ts = int(parts[0])
        vals = [float(v) for v in parts[1:13]]
        return ts, vals
    except Exception:
        return None, None


def main():
    parser = argparse.ArgumentParser(description='Plot dual-IMU data from serial')
    parser.add_argument('--port', '-p', help='Serial port (e.g. /dev/ttyACM0). If omitted, a sensible default is tried.')
    parser.add_argument('--baud', type=int, default=250000, help='Serial baud rate (default 250000)')
    parser.add_argument('--max-points', type=int, default=1000, help='Max points to keep in rolling window')
    parser.add_argument('--update-every', type=int, default=5, help='Update plot every N samples')
    parser.add_argument('--timeout', type=float, default=1.0, help='Serial read timeout (seconds)')
    args = parser.parse_args()

    port = args.port or choose_default_port()
    baud = args.baud
    max_points = args.max_points
    update_every = max(1, args.update_every)

    print(f"Opening serial port {port} @ {baud} baud")
    try:
        ser = serial.Serial(port, baud, timeout=args.timeout)
    except Exception as e:
        print(f"Failed to open {port}: {e}")
        sys.exit(1)

    time.sleep(2.0)  # allow Arduino to reset

    # Data buffers
    xs = deque(maxlen=max_points)
    data = {
        'imu1_ax': deque(maxlen=max_points),
        'imu1_ay': deque(maxlen=max_points),
        'imu1_az': deque(maxlen=max_points),
        'imu1_gx': deque(maxlen=max_points),
        'imu1_gy': deque(maxlen=max_points),
        'imu1_gz': deque(maxlen=max_points),
        'imu2_ax': deque(maxlen=max_points),
        'imu2_ay': deque(maxlen=max_points),
        'imu2_az': deque(maxlen=max_points),
        'imu2_gx': deque(maxlen=max_points),
        'imu2_gy': deque(maxlen=max_points),
        'imu2_gz': deque(maxlen=max_points),
    }

    # Setup matplotlib: four stacked plots
    plt.ion()
    fig, axes = plt.subplots(4, 1, sharex=True, figsize=(12, 9))
    ax_acc1, ax_gyro1, ax_acc2, ax_gyro2 = axes

    colors = ['r', 'g', 'b']
    acc_labels = ['ax', 'ay', 'az']
    gyr_labels = ['gx', 'gy', 'gz']

    # Lines: three accel and three gyro per IMU
    lines_acc1 = []
    lines_gyr1 = []
    lines_acc2 = []
    lines_gyr2 = []

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

    ax_acc1.legend(loc='upper right')
    ax_gyro1.legend(loc='upper right')
    ax_acc2.legend(loc='upper right')
    ax_gyro2.legend(loc='upper right')

    ax_acc1.grid(True)
    ax_gyro1.grid(True)
    ax_acc2.grid(True)
    ax_gyro2.grid(True)

    first_ts = None
    count = 0
    last_status = time.time()

    print('Starting read/plot loop. Press Ctrl+C to stop.')
    try:
        while True:
            raw = ser.readline().decode('utf-8', errors='ignore').strip()
            if not raw:
                continue

            ts, vals = parse_line(raw)
            if ts is None:
                # Could not parse - print once per second
                if time.time() - last_status > 1.0:
                    print(f"Unrecognized line: {raw}")
                    last_status = time.time()
                continue

            if first_ts is None:
                first_ts = ts

            t_s = (ts - first_ts) / 1_000_000.0
            xs.append(t_s)

            # vals: [a1x,a1y,a1z,g1x,g1y,g1z,a2x,a2y,a2z,g2x,g2y,g2z]
            data['imu1_ax'].append(vals[0])
            data['imu1_ay'].append(vals[1])
            data['imu1_az'].append(vals[2])
            data['imu1_gx'].append(vals[3])
            data['imu1_gy'].append(vals[4])
            data['imu1_gz'].append(vals[5])

            data['imu2_ax'].append(vals[6])
            data['imu2_ay'].append(vals[7])
            data['imu2_az'].append(vals[8])
            data['imu2_gx'].append(vals[9])
            data['imu2_gy'].append(vals[10])
            data['imu2_gz'].append(vals[11])

            count += 1

            # Periodic plotting update (batched)
            if count % update_every == 0 and len(xs) > 0:
                x = list(xs)

                # IMU1 accel
                for i, key in enumerate(['imu1_ax', 'imu1_ay', 'imu1_az']):
                    y = list(data[key])
                    x_tail = x[-len(y):] if len(y) != len(x) and len(y) > 0 else x
                    if len(x_tail) > 0:
                        lines_acc1[i].set_data(x_tail, y)

                # IMU1 gyro
                for i, key in enumerate(['imu1_gx', 'imu1_gy', 'imu1_gz']):
                    y = list(data[key])
                    x_tail = x[-len(y):] if len(y) != len(x) and len(y) > 0 else x
                    if len(x_tail) > 0:
                        lines_gyr1[i].set_data(x_tail, y)

                # IMU2 accel
                for i, key in enumerate(['imu2_ax', 'imu2_ay', 'imu2_az']):
                    y = list(data[key])
                    x_tail = x[-len(y):] if len(y) != len(x) and len(y) > 0 else x
                    if len(x_tail) > 0:
                        lines_acc2[i].set_data(x_tail, y)

                # IMU2 gyro
                for i, key in enumerate(['imu2_gx', 'imu2_gy', 'imu2_gz']):
                    y = list(data[key])
                    x_tail = x[-len(y):] if len(y) != len(x) and len(y) > 0 else x
                    if len(x_tail) > 0:
                        lines_gyr2[i].set_data(x_tail, y)

                # adjust axes
                try:
                    xmin, xmax = x[0], x[-1]
                    for ax in (ax_acc1, ax_gyro1, ax_acc2, ax_gyro2):
                        ax.set_xlim(xmin, xmax)
                        ax.relim()
                        ax.autoscale_view(True, True, True)
                except Exception:
                    pass

                fig.canvas.draw_idle()
                plt.pause(0.001)

            # periodic status
            if time.time() - last_status > 1.0:
                print(f"Samples: {count}, buffer: {len(xs)}")
                last_status = time.time()

    except KeyboardInterrupt:
        print('\nInterrupted by user')
    finally:
        ser.close()
        print('Serial closed. Exiting.')


if __name__ == '__main__':
    main()
