# Method report — Relative Tibial-Femoral Knee Motion (cycle 1)

## What it measures (plain language)
Pivot has one motion sensor on the thigh (femur) and one on the shin (tibia).
When the knee bends or twists, the two sensors point in different directions.
By subtracting the thigh sensor's orientation from the shin sensor's
orientation we get the **relative knee angle** — how far the joint itself is
bent/rotated, separated from how the whole leg is oriented in space. We track
its **range of motion (ROM)** over a movement and roll it into a 0-100 **Knee
Motion / Load Index**: more and larger relative motion -> higher index. A faster,
larger relative motion means the joint and the surrounding tissue (incl. the
ACL) are being worked harder.

**This is a relative, qualitative signal — not a calibrated joint torque (no
newton-metres) and not an injury probability.** It says *more vs. less* and
*trending up vs. down*, not an absolute force.

## How it is derived from the two IMUs
1. **Channel meaning.** The real cycle-1 CSVs were produced by
   `collectdata_dualIMU_BLE.ino`, which sends fused **Euler angles** (deg). The
   BLE logger mislabels those columns `imuN_g*`, but they are angles, not gyro
   rates (firmware-traced; confirmed by Critic and Researcher). The module
   resolves this from file **provenance** (not a magnitude guess) and sets
   `channel_meaning="euler_deg"`. A magnitude heuristic runs only as a
   cross-check; disagreement is surfaced as `channel_meaning_confidence="low"`.
2. **Relative angle (primary).** Per axis, unwrap each segment's Euler angle
   across the +-180 deg discontinuity, then take `sign * (tibia - femur)` and
   baseline-zero to the quiet start. This relative angle is **drift-free** — it
   is a directly measured fused quantity, not an integral.
3. **ROM & index.** ROM = peak-to-peak of the dominant-axis relative angle.
   The 0-100 index normalises ROM to a 90 deg reference.
4. **Relative rate (secondary, lower-confidence).** The angle is differentiated
   w.r.t. actual `arduino_time_s` deltas (irregular ~17 ms, not assumed
   constant) to give deg/s. Differentiation amplifies noise, so it is flagged
   `rate_is_low_confidence=true`. For genuine gyro-rate files (from
   `bluetoothSync.ino`) the rate would instead be the direct difference and the
   primary signal.

## Limitations & honesty
- **Relative, not absolute.** Angular motion indexes how vigorously the joint
  is driven, not force. Calibrated load (Nm) needs inverse dynamics + ground
  reaction force — out of scope for two IMUs.
- **Femur/tibia mapping is UNVERIFIED.** Which IMU index is femur vs tibia is
  undocumented in the data (`imu1`=mux ch0, `imu2`=ch1). It is a configurable
  parameter (`femur_imu`, default 1) with a configurable `sign`, and is flagged
  `segment_assignment="UNVERIFIED"`. **To confirm with the Human Tester.**
- **Transverse (rotation) is noisier than sagittal (flexion/extension)** per the
  literature; ROM here mixes axes via the dominant-axis pick.
- **Static/no-motion files are flagged** (`usable_motion=false`), not silently
  scored.

## !! DATA-QUALITY FINDING — flag to Human Tester / lead !!
The four labeled cycle-1 trial CSVs are effectively **dead data — no usable
movement**. Every one of them has the accelerometer frozen for the *entire*
file and the angle channels varying by under ~0.5 deg total:

| File | ROM (deg) | usable_motion | accel_static |
|---|---|---|---|
| Jump_RL.csv | 0.23 | FALSE | TRUE |
| Anterior_Rotation_RL.csv | 0.30 | FALSE | TRUE |
| Posterior_Rotation_RL.csv | 0.26 | FALSE | TRUE |
| Tibial_Translation_RL.csv | 0.48 | FALSE | TRUE |

This looks like the BLE-init freeze (commit 657b146) affecting the whole
capture, not just the start. **The flagship cycle-1 metric cannot be
demonstrated on its own labeled trials — these need to be re-collected.**

The only real movement file is **`MPU_BothIMUs_20251205_155322.csv`** (dual-IMU,
unlabeled), which gives plausible output: ROM 148.8 deg, peak |rel angle| 79.5
deg, peak rate ~581 deg/s (verified NOT a single-sample spike: 53 samples >300
deg/s, 3-sample-smoothed peak 508 deg/s). The module's correctness is therefore
demonstrated on this file; the labeled trials are used to verify the
no-motion/frozen detection path.

## Changes log
- v1 initial: relative angular-velocity (rate) headline.
- v1 revised (post firmware trace): columns are fused **Euler angles**, so the
  **primary signal is relative ANGLE / ROM** (drift-free); rate is now the
  differentiated, lower-confidence secondary. Added Euler unwrap before
  differencing, provenance-based channel detection with heuristic cross-check,
  and loud no-motion flagging. Reworded "gyro differencing" language to reflect
  the actual angle path.
