
# Simple dual-plot live graph for Arduino serial data
import serial
import time
import matplotlib.pyplot as plt
import csv
import re
from datetime import datetime

port = '/dev/cu.usbmodem11201'  # Change to your Arduino port
baud_rate = 9600
max_points = 200

ser = serial.Serial(port, baud_rate, timeout=1)
time.sleep(2)

# Open CSV file for logging
csv_file = open(f'mpu_log_{datetime.now()}.csv', 'w', newline='')
csv_writer = csv.writer(csv_file)
csv_writer.writerow(['time', 'accel_x', 'accel_y', 'accel_z', 'angle_x', 'angle_y', 'angle_z'])

accel_x, accel_y, accel_z = [], [], []
angle_x, angle_y, angle_z = [], [], []
time_vals = []
start_time = time.time()
last_angle = [None, None, None]

plt.ion()
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 8))

# Acceleration plot
line_ax = ax1.plot([], [], label='X')[0]
line_ay = ax1.plot([], [], label='Y')[0]
line_az = ax1.plot([], [], label='Z')[0]
ax1.set_title('Acceleration')
ax1.set_xlabel('Time (s)')
ax1.set_ylabel('g')
ax1.legend()

# Angle plot
line_gx = ax2.plot([], [], label='X')[0]
line_gy = ax2.plot([], [], label='Y')[0]
line_gz = ax2.plot([], [], label='Z')[0]
ax2.set_title('Angle Tilt')
ax2.set_xlabel('Time (s)')
ax2.set_ylabel('Degrees')
ax2.legend()

plt.show(block=False)

# Regex patterns for parsing
accel_pattern = re.compile(r'ACCELERO\s+X:\s*([-+]?\d+\.?\d*)\s+Y:\s*([-+]?\d+\.?\d*)\s+Z:\s*([-+]?\d+\.?\d*)')
angle_pattern = re.compile(r'ANGLE\s+X:\s*([-+]?\d+\.?\d*)\s+Y:\s*([-+]?\d+\.?\d*)\s+Z:\s*([-+]?\d+\.?\d*)')

try:
    while True:
        line = ser.readline().decode(errors='ignore').strip()
        if not line:
            plt.pause(0.01)
            continue

        # Parse ACCELERO line
        accel_match = accel_pattern.search(line)
        if accel_match:
            ax_val, ay_val, az_val = map(float, accel_match.groups())
            accel_x.append(ax_val)
            accel_y.append(ay_val)
            accel_z.append(az_val)
            t = time.time() - start_time
            time_vals.append(t)
            # Keep only max_points
            if len(time_vals) > max_points:
                time_vals = time_vals[-max_points:]
                accel_x = accel_x[-max_points:]
                accel_y = accel_y[-max_points:]
                accel_z = accel_z[-max_points:]
            # Log to CSV (use last known angle values)
            ax_ang = last_angle[0] if last_angle[0] is not None else ''
            ay_ang = last_angle[1] if last_angle[1] is not None else ''
            az_ang = last_angle[2] if last_angle[2] is not None else ''
            csv_writer.writerow([t, ax_val, ay_val, az_val, ax_ang, ay_ang, az_ang])

        # Parse ANGLE line
        angle_match = angle_pattern.search(line)
        if angle_match:
            gx_val, gy_val, gz_val = map(float, angle_match.groups())
            angle_x.append(gx_val)
            angle_y.append(gy_val)
            angle_z.append(gz_val)
            # Keep only max_points
            if len(angle_x) > max_points:
                angle_x = angle_x[-max_points:]
                angle_y = angle_y[-max_points:]
                angle_z = angle_z[-max_points:]
            last_angle = [gx_val, gy_val, gz_val]

        # Update plots only if all arrays have matching lengths
        if time_vals and accel_x and angle_x and len(time_vals) == len(accel_x) == len(angle_x):
            line_ax.set_data(time_vals, accel_x)
            line_ay.set_data(time_vals, accel_y)
            line_az.set_data(time_vals, accel_z)
            ax1.relim()
            ax1.autoscale_view()

            line_gx.set_data(time_vals, angle_x)
            line_gy.set_data(time_vals, angle_y)
            line_gz.set_data(time_vals, angle_z)
            ax2.relim()
            ax2.autoscale_view()

            plt.pause(0.01)
            plt.draw()

except KeyboardInterrupt:
    print('Exiting...')
finally:
    ser.close()
    csv_file.close()
