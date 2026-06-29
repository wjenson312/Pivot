# Data Baseline — what the CSVs actually support (CRITIC reference)

## What we have
- 2 IMUs (imu1, imu2): each acc_x/y/z (g, gravity~1.0) + gx/gy/gz (deg/s OR fused Euler deg — see below).
- NO magnetometer, NO calibration/bias, NO anthropometry (mass/segment length/COM), NO load-cell ground truth.
- ~60Hz nominal but IRREGULAR dt (0.0169/0.017/0.018 s). Must integrate/sum with actual dt.
- arduino_time_s vs receive_time_s diverge (BLE jitter) -> use arduino_time_s.

## Trials: Anterior_Rotation_RL (273), Posterior_Rotation_RL (237), Tibial_Translation_RL (437),
## Jump_RL (215). Plus MPU_BothIMUs (941), MPU_TestRun (1097).

## RED FLAGS
1. FROZEN/STALE ACCEL: Anterior_Rotation_RL & Jump_RL start with many identical repeated rows
   = "frozen IMU after BLE init" bug (commit 657b146). Trials likely PRE-DATE fix. Detect/flag/drop.
2. FEMUR vs TIBIA mapping NOT in data (only imu1/imu2). Configurable + flagged, not assumed.
3. NO TORQUE: no Nm possible. Only relative kinematic indices honest.
4. GYRO DRIFT on integration; differencing cancels only COMMON-MODE. Stay in rate space.
5. SHORT TRIALS 4-7s: per-rep ok, NOT session-cumulative load.
6. COLUMN SEMANTICS AMBIGUITY (from Researcher caveat #2 — ELEVATED to RED): imuN_g* columns may be
   fused Euler ANGLES (deg) in collectdata_dualIMU_BLE.ino vs true GYRO RATES (deg/s) in bluetoothSync.ino.
   If the rotation CSVs actually contain ANGLES, then "rate" method differencing them yields a relative
   ANGLE, not rate, and any cumulative sum is meaningless. MUST verify per-file before any math.
