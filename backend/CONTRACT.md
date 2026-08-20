# Pivot Backend Data Contract (v1)

This is the **stable output shape every backend analysis method must follow** so
Frontend's dashboard tab template can stay generic. Future methods change *which*
named series / summary fields they populate — they do **not** change this shape.

Produced by `backend/knee_rotation_load.py` (`analyze_file()` -> `Result`,
serialized by `write_outputs()` to `backend/outputs/<csvbase>.knee_rotation_load.json`
plus a parallel flat `.csv` with the time series).

## Top-level JSON

```json
{
  "method": "relative_tibial_femoral_knee_motion",
  "version": "1",
  "source_file": "MPU_BothIMUs_20251205_155322.csv",
  "units": {
    "time": "s",
    "rel_angle": "deg",
    "rel_rate": "deg/s",
    "rom_deg": "deg",
    "rotation_load_index": "unitless_0_100",
    "relative_knee_load_score": "unitless_0_100",
    "range_of_motion_score": "unitless_0_100",
    "peak_impact_g": "g",
    "landing_mechanics_score": "unitless_0_100",
    "knee_health_score": "unitless_0_100"
  },
  "timestamps": [ /* float seconds, baseline-zeroed to trial start */ ],
  "series": { /* see below — every array is the SAME length as timestamps */ },
  "summary_metrics": { /* scalars, see below */ },
  "quality_flags": { /* see below — render as a caveats banner */ },
  "notes": [ /* human-readable strings, render verbatim in the tab */ ]
}
```

### Invariants (Frontend can rely on these)
- `timestamps` and every array in `series` have identical length.
- `units` maps a signal family name to its unit string. Plot using these.
- `summary_metrics` values are scalars (number, string, or `null`).
- `quality_flags` values are scalars (bool / number / string / `null`).
- `notes` is a list of strings; show them as a caveats list.
- A field may be `null` when not applicable to that file (e.g. `rom_deg` is
  `null` for true gyro-rate files). Frontend should skip `null` cards/series.

## `series` (time series; plot vs `timestamps`)
Always present:
- `rel_rate_x`, `rel_rate_y`, `rel_rate_z` — relative angular RATE per axis (deg/s)
- `rel_rate_dominant` — the dominant-axis relative rate (deg/s)
- `rel_rate_magnitude` — vector magnitude of relative rate (deg/s)

Present only when `channel_meaning == "euler_deg"` (fused-angle source):
- `rel_angle_x`, `rel_angle_y`, `rel_angle_z` — relative knee ANGLE per axis (deg)
- `rel_angle_dominant` — dominant-axis relative angle (deg)
- `rel_angle_magnitude` — vector magnitude of relative angle (deg)

Present only when `quality_flags.calibration_applied == true` (a sleeve
calibration profile was supplied to `analyze_file`/`compute`):
- `rel_rate_flexion`, `rel_rate_rotation`, `rel_rate_ab_adduction` — relative
  rate (deg/s) projected onto the calibration's anatomical axes, in addition
  to the raw x/y/z series above
- `rel_angle_flexion`, `rel_angle_rotation`, `rel_angle_ab_adduction` — same,
  for relative angle (deg), only when also `channel_meaning == "euler_deg"`

Present only when the tibia IMU's accelerometer columns exist in the source
CSV (independent of `usable_motion` — present even for a flagged/dead trial,
so the Landing Mechanics tab still has something to plot):
- `accel_magnitude_tibia` — resultant accelerometer magnitude (g) at the
  tibia IMU, `sqrt(acc_x^2 + acc_y^2 + acc_z^2)`; hovers near 1g (gravity)
  at rest, deviates on impact/movement. Headline series for the Landing
  Mechanics tab.

Frontend: prefer plotting `rel_angle_dominant` (deg) as the headline when
present (it is drift-free); otherwise plot `rel_rate_dominant` (deg/s).
`summary_metrics.primary_signal` tells you which. When
`quality_flags.calibration_applied` is true, `rel_rate_dominant`/
`rel_angle_dominant` are the calibrated **rotation**-axis series (the axis
this metric cares about, fixed by calibration) rather than whichever raw
axis happened to move most in that trial.

## `summary_metrics` (render as cards)
- `primary_signal` — `"relative_angle_deg"` or `"relative_rate_dps"` (which is headline)
- `rom_deg` — peak-to-peak relative knee angle on the dominant axis (deg) | `null`
- `peak_abs_rel_angle_deg` — max |relative angle| on dominant axis (deg) | `null`
- `peak_rel_rate_dps` — max relative angular rate magnitude (deg/s)
- `mean_active_rate_dps` — mean relative rate over the active window (deg/s)
- `rotation_load_index` — 0-100 unitless **relative** Knee Motion/Load Index
  (ROM-normalised for angle data; peak-rate-normalised for rate data)
- `relative_knee_load_score` — identical value to `rotation_load_index`, named
  for its role as a Knee Health Score input (see below); already 0-100, no
  rescaling applied
- `range_of_motion_score` — 0-100, `rom_deg` normalised against the same 90°
  reference as `rotation_load_index`'s angle branch | `null` (angle-type data
  only, same condition as `rom_deg`)
- `peak_impact_g` — peak deviation from the ~1g gravity baseline in the tibia
  IMU's resultant accelerometer magnitude (g) | `null` when no accelerometer
  data or `usable_motion == false`
- `landing_mechanics_score` — 0-100, `peak_impact_g` inverted and normalised
  against a provisional 4g reference (softer landing = higher score) | `null`
  under the same condition as `peak_impact_g`. Coarse impact-magnitude proxy
  only — does **not** capture knee valgus or trunk lean (see
  `ai-agent/research/wearable-metrics-by-location.md`).
- `knee_health_score` — 0-100, weighted roll-up of the three scores above
  (40% `relative_knee_load_score`, 30% `range_of_motion_score`, 30%
  `landing_mechanics_score`) | `null` unless all three inputs are available.
  Same relative/qualitative framing as its inputs — not a validated
  clinical or injury-risk score.
- `dominant_axis` — `"x"` | `"y"` | `"z"` (variance-picked, uncalibrated), or
  `"rotation"` when `quality_flags.calibration_applied == true` (fixed by
  the sleeve calibration instead of picked per-trial)

## `quality_flags` (render as a caveats banner)
- `accel_static` (bool) — accelerometer columns frozen for the whole file
- `gyro_varies` (bool) — the angle/gyro channels show real variation
- `usable_motion` (bool) — **if false, the file is not a valid movement recording**;
  Frontend should show metrics greyed/with a prominent warning
- `channel_meaning` — `"euler_deg"` (fused angles) | `"gyro_rate_dps"` (true rates)
- `channel_meaning_confidence` — `"high"` | `"low"`
- `channel_meaning_heuristic` — what the magnitude cross-check guessed
- `rate_is_low_confidence` (bool) — true when rate was differentiated from angle
- `sample_rate_hz` (number | null)
- `n_samples` (int)
- `n_dropped_leading_frozen` (int) — leading BLE-init-frozen rows removed
- `active_window_s` (number) — duration of the detected motion window
- `drift_residual_dps` (number) — quiet-baseline rate drift start-vs-end
- `drift_bounded` (bool) — only claimed true for genuine gyro-rate data
- `segment_assignment` — `"UNVERIFIED"` (hand-set `femur_imu`, unconfirmed) |
  `"confirmed"` (read from a supplied sleeve calibration profile)
- `femur_imu`, `tibia_imu` (int) — assumed assignment (configurable), or the
  calibration-derived assignment when `calibration_applied` is true
- `sign` (int) — sign convention applied (configurable)
- `calibration_applied` (bool) — whether a sleeve calibration profile
  (`backend/sleeve_calibration.py` output) was supplied
- `calibration_source` (string | null) — calibration profile's source
  filename, when applied
- `calibration_confidence` (string | null) — the calibration profile's own
  `"high"`/`"medium"`/`"low"` confidence, carried through when applied

## Cross-trial comparability
Do **not** compare raw cumulative quantities across trials of different length.
The comparable headline figures are `rom_deg` (angle data) and
`peak_rel_rate_dps` / `mean_active_rate_dps` over the active window, plus the
0-100 `rotation_load_index`. `active_window_s` and `n_samples` are exposed so
trial-length differences are visible.

## What this is / is NOT
Relative, qualitative knee-motion proxy. **NOT** a calibrated joint torque (no
newton-metres) and **NOT** an injury probability. See the method report.

## Sleeve calibration profiles are NOT a dashboard method
`backend/sleeve_calibration.py` produces a **session-level** JSON artifact
(`backend/outputs/<calib_basename>.sleeve_calibration.json`) — segment
assignment, three calibrated axis vectors, gyro bias, and confidence flags.
It deliberately does **not** follow this contract's shape: there is no
`timestamps`/`series` (nothing to plot on a per-trial timeline), so it isn't
rendered in its own dashboard tab. It's an *input* other analysis methods
optionally consume (via `imu_common.load_calibration_profile` /
`imu_common.apply_calibration`) to replace hand-set `femur_imu`/`sign` and
the per-trial variance-picked `dominant_axis` with values derived from an
actual calibration recording — see the `calibration_*` quality-flag fields
above and `ai-agent/research/sleeve-calibration-protocol.md`.
