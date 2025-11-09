import serial
import time
import re
import matplotlib.pyplot as plt
from collections import deque

# Configure the serial connection
port = 'COM3'  # Replace with your Arduino's COM port
baud_rate = 9600
max_points = 200; # amount of data points to display on graph
ser = serial.Serial(port, baud_rate, timeout=1)

time.sleep(2)  # Allow time for the serial connection to establish

# Initialize deques to store time and acceleration data
time_vals = deque(maxlen=max_points)
accel_x = deque(maxlen=max_points)
accel_y = deque(maxlen=max_points)
accel_z = deque(maxlen=max_points);

start_time = time.time()

# Set up the plot
plt.ion()
fig, ax = plt.subplots()
lineX, = ax.plot([], [], label='Acc X')
lineY, = ax.plot([], [], label='Acc Y')
lineZ, = ax.plot([], [], label='Acc Z')
ax.legend()
ax.set_xlabel("Time (s)")
ax.set_ylabel("Acceleration")
ax.set_title("Accelerometer Readings vs Time")

# Regular expression pattern to match accelerometer data
accel_pattern = re.compile(r"ACCELERO\s+X:\s*([-+]?\d*\.?\d+)\s*Y:\s*([-+]?\d*\.?\d+)\s*Z:\s*([-+]?\d*\.?\d+)")

try:
    while True:
        line = ser.readline().decode(errors='ignore').strip()
        if not line:
            continue

        # match accelerometer line
        match = accel_pattern.search(line)
        if match:
            ax_val, ay_val, az_val = map(float, match.groups())
            t = time.time() - start_time

            # append new data
            time_vals.append(t)
            accel_x.append(ax_val)
            accel_y.append(ay_val)
            accel_z.append(az_val)

            # update plot
            lineX.set_data(time_vals, accel_x)
            lineY.set_data(time_vals, accel_y)
            lineZ.set_data(time_vals, accel_z)

            # adjust axes
            ax.relim()
            ax.autoscale_view()
            plt.pause(0.01)

except KeyboardInterrupt:
    print("Exiting...")

finally:
    ser.close()
