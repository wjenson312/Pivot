
# Simple dual-plot live graph for Arduino serial data
import serial
import time
import matplotlib.pyplot as plt
import re

port = '/dev/cu.usbmodem11201'  # Change to your Arduino port before running test
baud_rate = 250000 # Increased for 500Hz sensor data (was 9600)
max_points = 200
update_every_n = 10  # Only redraw plot every N samples for better performance at 500Hz

ser = serial.Serial(port, baud_rate, timeout=1)
time.sleep(2)

accel_x, accel_y, accel_z = [], [], []
angle_x, angle_y, angle_z = [], [], []
time_vals = []
start_time = time.time()
last_angle = [None, None, None]
plot_update_count = 0
sample_count = 0  # Track total samples received

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
plt.pause(0.1)  # let the GUI initialize so the window appears promptly

# Parse compact single-line format: ts ax ay az gx gy gz
data_pattern = re.compile(r'(\d+)\s+([-+]?\d+\.?\d*)\s+([-+]?\d+\.?\d*)\s+([-+]?\d+\.?\d*)\s+([-+]?\d+\.?\d*)\s+([-+]?\d+\.?\d*)\s+([-+]?\d+\.?\d*)')

try:
    arduino_start_time = None  # Will store the first Arduino timestamp
    
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
            
            # Convert Arduino microseconds to seconds, relative to first sample
            t = (ts_micros - arduino_start_time) / 1_000_000.0
            
            accel_x.append(float(ax_val))
            accel_y.append(float(ay_val))
            accel_z.append(float(az_val))
            angle_x.append(float(gx_val))
            angle_y.append(float(gy_val))
            angle_z.append(float(gz_val))
            time_vals.append(t)
            sample_count += 1
            
            # Keep only max_points
            if len(time_vals) > max_points:
                time_vals = time_vals[-max_points:]
                accel_x = accel_x[-max_points:]
                accel_y = accel_y[-max_points:]
                accel_z = accel_z[-max_points:]
                angle_x = angle_x[-max_points:]
                angle_y = angle_y[-max_points:]
                angle_z = angle_z[-max_points:]
        # Update plots only if all arrays have matching lengths
        if time_vals and accel_x and angle_x and len(time_vals) == len(accel_x) == len(angle_x):
            plot_update_count += 1
            # Only redraw every N samples to improve performance at 100Hz
            if plot_update_count >= update_every_n:
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

                plt.draw()
                plt.pause(0.001)  # process GUI events after drawing
                plot_update_count = 0

except KeyboardInterrupt:
    print(f'\nExiting... Received {sample_count} samples')
finally:
    ser.close()
