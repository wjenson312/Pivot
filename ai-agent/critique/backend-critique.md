# Critique — /backend/knee_rotation_load.py + outputs

Reviewed 2026-06-19. Module is strong: incorporated the angle/provenance finding (FILE_PROVENANCE
maps all 5 trial CSVs -> euler_deg, credits Critic), provenance preferred over heuristic, Euler unwrap
before diff, differentiation flagged lower-confidence, frozen trim, configurable femur_imu + UNVERIFIED,
arduino_time_s timing, duration-normalized cumulative, honest no-Nm notes. Good.

## FINDING 1 (HIGH, real-world) — the PRIMARY trial has no usable motion
Anterior_Rotation_RL.csv (cycle-1 flagship input) output: usable_motion=FALSE, accel_static=TRUE,
peak_rel_rate=1.0 deg/s, index=0.34, cumulative=0, active_window=0. The module correctly WARNS
"not a valid movement recording." So the headline metric CANNOT be demonstrated on its own primary
dataset — the accel is frozen whole-file and the angle channels barely move. This is the single most
important finding for the cycle: the flagship CSV is effectively dead data (pre-657b146 capture).
Planner/lead must know before build-summary; likely needs re-collection. Posterior/Tibial should be
checked the same way (I only confirmed Anterior + MPU so far).

## FINDING 2 (MED, logic) — drift_bounded can NEVER be true for real data
Line 360: drift_bounded = (channel_meaning=="gyro_rate_dps") AND (residual<=tol). Every real file is
euler_deg, so drift_bounded is ALWAYS false -> integrated relative angle/ROM is ALWAYS withheld. The
ROM upgrade path is dead code for the actual dataset. Conservative/safe, but means the "relative angle/ROM
when drift_bounded" feature never fires. Given the data IS angles (no integration drift to fear — angles
are already fused/bounded), this gate is arguably backwards: for euler_deg you could show relative ANGLE
directly (it's a measured angle, not an integrated one) rather than withholding it. Worth Backend reconsidering.

## FINDING 3 (LOW, honesty) — stale "gyro differencing" wording
Module docstring + first note say "from gyro differencing" even when channel_meaning=euler_deg (the value
is differentiated ANGLE, not differenced gyro). Minor but it's exactly the kind of mislabel that caused
the original confusion. Reword to reflect actual path per file.

## FINDING 4 (MED, missing artifacts) — no CONTRACT.md, no method report, no /tests entry
Role spec requires backend CONTRACT.md + method report + a pass/fail entry in /tests/report.md.
None exist yet. The output JSON schema is good and self-consistent, but the contract isn't documented
for Frontend to rely on, and tests/report.md is empty.

## Numbers sanity
MPU_BothIMUs: peak 580 deg/s, index pegged at 100, cumulative_rate 182 deg/s, dominant axis x. Plausible
for vigorous motion BUT differentiated-angle peaks are noise-amplified and the index saturating at 100 on
a non-trial file suggests REF_PEAK_DPS=300 may be low / the peak may include diff noise. Recommend Backend
sanity-check peak against a low-pass and confirm 580 isn't a single-sample diff spike.
