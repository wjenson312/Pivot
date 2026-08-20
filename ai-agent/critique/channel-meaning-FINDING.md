# CRITICAL FINDING — the trial CSV "gyro" columns are almost certainly Euler ANGLES (deg), not rates

Reviewed firmware + receiver 2026-06-19. This converts the "channel_meaning ambiguity"
from an unknown-to-auto-detect into a near-certain data-meaning error to correct.

## Evidence chain (firmware-level proof)
1. The BLE Arduino sketch `app/data-analysis/arduinoCode/bluetooth/collectdata_dualIMU_BLE.ino`
   (lines 75-81) transmits, per IMU:
   AccX, AccY, AccZ, **getAngleX, getAngleY, getAngleZ**  -> i.e. fused EULER ANGLES (deg).
   It does NOT transmit getGyroX/Y/Z.
2. The BLE receiver `app/data-analysis/liveSampling/logdata_dualIMU_BLE.py` (lines 28-33)
   writes header:
   arduino_time_s, receive_time_s, imu1_acc_{xyz}, **imu1_gx/gy/gz**, imu2_acc_{xyz}, **imu2_gx/gy/gz**
   It blindly labels packet positions 5-7 / 11-13 as "g*" REGARDLESS of content. The Arduino put
   ANGLES there. So the "_gx/_gy/_gz" name is a MISLABEL.
3. ALL cycle-1 trial CSVs (Anterior_/Posterior_Rotation_RL, Tibial_Translation_RL, Jump_RL) use this
   exact arduino_time_s/receive_time_s header -> they came from this BLE logger -> their _g* columns
   are EULER ANGLES (deg), not gyro rates.
4. Contrast: serial sketch `bluetooth/bluetoothSync.ino` (lines 184, 203-211) logs true getGyroX/Y/Z
   (deg/s) but writes a DIFFERENT header (`ts,ax1,ay1,az1,gx1,...`). None of the trial CSVs use that
   header, so the trials are NOT the gyro-rate path.

## Corroborating data behavior
- Trial frozen-start "g" values are large & stable (e.g. imu1: -30.05,-56.27,-49.32) = a resting
  ORIENTATION in degrees, NOT a plausible ~50 deg/s gyro bias.
- MPU_BothIMUs at rest shows small "g" (1.0,-3.26,-11.46) — but it's still the same BLE logger header,
  so also angles; the small values are just a near-zero starting Euler reference, not gyro rate.

## Why this is method-breaking (not just a flag)
- omega_rel = omega_tibia - omega_femur on ANGLE data yields a relative ANGLE (deg), not a rate (deg/s).
- The planned `cumulative_rotation_deg / active_window_s` would be summing ANGLES -> dimensionally wrong;
  the headline "rate-space deg/s" is then a misnomer.
- Euler angle channels WRAP at +/-180; differencing/summing across a wrap produces huge false spikes
  unless unwrapped. A peak detector would flag the wrap as the biggest "rotation."

## Required action (told Backend, Planner, Researcher)
- Backend: DEFAULT channel_meaning = euler_deg for all current trial CSVs (provenance = BLE logger),
  NOT auto-detected-as-rate. To get a true rate, DIFFERENTIATE the unwrapped angle w.r.t. arduino_time_s
  (flag lower-confidence, differentiation amplifies noise). Unwrap before any diff/sum.
- Better path actually available: since these are fused ANGLES, the RELATIVE KNEE ANGLE (omega->theta)
  is directly the cleaner signal and avoids gyro-drift integration entirely — the method could pivot to
  relative-angle ROM rather than rate, which the data actually supports better.
- Confirm with human tester which firmware/receiver produced each file (final ground truth).
