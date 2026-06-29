# Cycle 1 Build Summary — Knee Rotation Load (Relative Tibial–Femoral Knee Motion)

**Author:** Planner (PivotTeam)
**Date:** 2026-06-20
**Status:** Cycle 1 closed. All four gates met (Researcher, Backend, Frontend, Critic).

---

## 1. What was built

A first end-to-end analysis method, surfaced as one dashboard tab:

- **Method name:** `relative_tibial_femoral_knee_motion` ("Knee Rotation Load")
- **Signal:** relative motion between the femur IMU and the tibia IMU
  (`tibia − femur`, baseline-zeroed, sign/segment configurable).
- **Headline metric:** *relative knee angle* and its range of motion (ROM),
  rolled into a 0–100 **Knee Motion / Load Index**. A secondary, lower-confidence
  *relative angular rate* (deg/s) is derived by differentiating the angle.
- **Backend:** `/Users/williamjenson/Desktop/SPK_Startup/SPK/backend/knee_rotation_load.py`,
  data contract at `/Users/williamjenson/Desktop/SPK_Startup/SPK/backend/CONTRACT.md`,
  method report at `/Users/williamjenson/Desktop/SPK_Startup/SPK/backend/knee_rotation_load_REPORT.md`,
  tests at `/Users/williamjenson/Desktop/SPK_Startup/SPK/backend/test_knee_rotation_load.py`
  (67/67 checks pass), JSON+CSV outputs per trial in `/Users/williamjenson/Desktop/SPK_Startup/SPK/backend/outputs/`.
- **Frontend:** tab at `/Users/williamjenson/Desktop/SPK_Startup/SPK/frontend/app/methods/knee-rotation-load/page.tsx`,
  chart component at `/Users/williamjenson/Desktop/SPK_Startup/SPK/frontend/components/RotationRateChart.tsx`,
  shared `MethodTab` template (Researcher paragraph + chart + Backend report block + caveats banner),
  confirmed serving at `http://localhost:3000` (`/` redirects to `/methods/knee-rotation-load`).
- **Research:** `/Users/williamjenson/Desktop/SPK_Startup/SPK/research/relative-tibial-femoral-rotation-rate.md`
  (revised post-Critic to reflect the angle-not-rate correction below).
- **Tests:** `/Users/williamjenson/Desktop/SPK_Startup/SPK/tests/report.md` — Backend PASS (67/67),
  Frontend PASS (build, route, template sections, real-data chart, live server check).
- **Critique:** `/Users/williamjenson/Desktop/SPK_Startup/SPK/critique/` — `direction-critique.md`,
  `data-baseline-critique.md`, `backend-critique.md`, `frontend-critique.md`,
  `research-critique.md`, and the standout `channel-meaning-FINDING.md`.

## 2. Key decisions made

### 2.1 Physical-measure vs. index — DECIDED: relative/qualitative index
Output is explicitly a **relative, qualitative knee-motion proxy** — NOT a
calibrated joint torque (no Nm) and NOT an injury probability. It says
*more/less* and *trending up/down* motion through the joint, not an absolute
force. A calibrated physical measure remains a later-cycle goal (needs
orientation/inverse-dynamics + ground-reaction-force + per-athlete scaling).

### 2.2 Mid-cycle correction: angle, not rate, is the honest primary signal
Cycle 1 started from a gyro-rate-differencing plan. Critic traced the firmware
and receiver code and found a **method-breaking mislabel**:
`collectdata_dualIMU_BLE.ino` transmits fused **Euler angles** (`getAngleX/Y/Z`,
deg), not gyro rates — the BLE logger (`logdata_dualIMU_BLE.py`) blindly names
those columns `imuN_gx/gy/gz` regardless of content. All four labeled cycle-1
trial CSVs use this header, so their `_g*` columns are angles, not deg/s.
(The true gyro-rate path exists only in `bluetoothSync.ino`'s different header,
unused by these trials.)

The team treated this as method-breaking, not a footnote, and pivoted:
- **Primary signal → relative knee ANGLE / ROM** (drift-free, since it's a
  direct fused quantity, not an integral).
- **Relative RATE → secondary, derived by differentiating the unwrapped angle**,
  flagged `rate_is_low_confidence=true` (differentiation amplifies noise).
- `channel_meaning` (`euler_deg` | `gyro_rate_dps`) is resolved **primarily from
  file provenance** (which firmware/header produced the CSV), per Critic's
  second finding that a magnitude-only heuristic is unsafe (Euler angles ≤±180
  deg and gyro rates of tens-to-hundreds deg/s overlap in range). The magnitude
  heuristic now runs only as a secondary cross-check; disagreement sets
  `channel_meaning_confidence="low"` rather than silently committing.
- Euler angles are unwrapped across the ±180° discontinuity before any
  differencing/summing, avoiding false spikes at the wrap boundary.

This is the single most important finding of the cycle: it changed both the
headline metric's identity and units, and it was caught and corrected before
shipping rather than after.

### 2.3 Data contract (Backend-authored, stable shape)
See `backend/CONTRACT.md` in full. Highlights:
- Fixed top-level JSON shape (`timestamps`, `series`, `summary_metrics`,
  `quality_flags`, `notes`) that future methods populate but don't restructure.
- `summary_metrics.primary_signal` tells Frontend whether to headline
  `rel_angle_dominant` (deg) or `rel_rate_dominant` (deg/s).
- `quality_flags` carries the full honesty surface: `accel_static`,
  `usable_motion`, `channel_meaning` (+confidence +heuristic), `rate_is_low_confidence`,
  `segment_assignment="UNVERIFIED"`, `femur_imu`/`tibia_imu`/`sign` (configurable),
  `drift_bounded`, `active_window_s`, `n_samples`.
- Explicit cross-trial comparability rule: never compare raw cumulative sums
  across trials of different length/duration; compare `rom_deg`,
  `peak_rel_rate_dps` / `mean_active_rate_dps` (active-window-normalized), or
  the 0–100 index instead.

### 2.4 Femur vs. tibia mapping — still UNVERIFIED, by design
Which IMU index (1 or 2) is femur vs tibia is undocumented in the data and was
never assumed. Backend made it a configurable parameter (`femur_imu`, default 1)
with a configurable `sign`, and flags `segment_assignment="UNVERIFIED"` in every
output. **This needs the human tester to confirm physical mounting.**

### 2.5 Stack / structural choices
- Backend: pure-stdlib Python module + pure-stdlib test file (no new deps for
  cycle 1), JSON+CSV dual output per trial.
- Frontend: Next.js route under `app/methods/<method-slug>/page.tsx` using a
  shared `MethodTab` template component, so future methods are mostly
  config + a results loader, not new page scaffolding.
- Default-trial selection in the tab prefers the one file with
  `usable_motion=true` over an alphabetically-first dead-data trial (see §3).

## 3. Critical data-quality finding — human tester action item

**All four labeled cycle-1 trial CSVs are dead data — no usable movement:**

| File | ROM (deg) | usable_motion | accel_static |
|---|---|---|---|
| Jump_RL.csv | 0.23 | FALSE | TRUE |
| Anterior_Rotation_RL.csv | 0.30 | FALSE | TRUE |
| Posterior_Rotation_RL.csv | 0.26 | FALSE | TRUE |
| Tibial_Translation_RL.csv | 0.48 | FALSE | TRUE |

Each has the accelerometer frozen for the *entire* file and angle channels
varying by under ~0.5° total — consistent with the BLE-init freeze that
commit `657b146` addressed, but apparently affecting these captures in full,
not just a leading segment.

The method is correctly implemented and **is demonstrated working** only on
**`MPU_BothIMUs_20251205_155322.csv`** (unlabeled, real dual-IMU motion: ROM
148.8°, peak |relative angle| 79.5°, peak rate ~581°/s, verified not a
single-sample artifact — 53 samples >300°/s, smoothed peak 508°/s). The four
labeled trials are still useful as a verification path for the
no-motion/frozen-detection logic, which correctly flags them rather than
silently scoring garbage.

**This is a top action item, not a footnote: the labeled Anterior/Posterior
Rotation and Tibial Translation trials need to be re-collected** before the
method can be validated against known clinical movements.

## 4. Human-tester observations relayed so far

- No direct hardware/display change requests have reached the Planner this
  cycle (those route to Backend/Frontend directly).
- Two confirmations are still needed from the human tester (see §5).
- The coordinator independently verified the Frontend tab renders real Backend
  data with the honesty banner in place at `http://localhost:3000`, and
  appended Frontend's `/tests/report.md` section after Frontend hit a
  root-path permission gap.

## 5. Open questions

1. **Femur vs. tibia mapping (IMU1 vs IMU2)** — unconfirmed. Affects sign and
   labeling of every relative-motion output. Needs the human tester to confirm
   physical mounting.
2. **Re-collection of labeled trials** — Anterior/Posterior Rotation and
   Tibial Translation (and ideally Jump) need fresh capture once the
   accel/angle freeze is confirmed fixed, so the method can be validated
   against known movements instead of only an unlabeled file.
3. **Confirm provenance per future file** — which firmware/receiver produced
   each new CSV (Euler-angle BLE path vs true-gyro-rate serial path), so
   `channel_meaning` keeps resolving correctly as more data arrives.
4. **ROM normalization reference** — the 0–100 index currently normalizes to a
   90° reference ROM; retune once more real trials exist.

## 6. Proposed direction for cycle 2

Two reasonable next steps; recommend (a) first since it directly unblocks
validating cycle 1's work, with (b) as the follow-on analytic deepening:

**(a) Data recollection + validation pass.** Re-collect Anterior/Posterior
Rotation and Tibial Translation trials post-freeze-fix; re-run
`knee_rotation_load.py` against them; have Critic confirm ROM values are
plausible for each labeled movement type. Lean on: Backend (re-run + tune
reference ROM), Critic (validate against expected movement magnitudes),
human tester (perform the labeled trials with the fix in place, confirm
femur/tibia mounting at the same time).

**(b) Extend to dynamic loading (Jump_RL.csv) once re-collected**, or add a
second method using `Tibial_Translation_RL.csv`'s translation framing
(if real translation signal — not just angle — becomes available with better
data). Lean on: Researcher (grounding for impact/dynamic loading proxies),
Backend (reuse the angle/rate pipeline, add an impact/peak-rate-focused
summary), Frontend (second tab from the same `MethodTab` template).

Either way, carry forward the cycle-1 discipline that worked well: provenance-
based (not magnitude-guessed) interpretation of ambiguous channels, explicit
`usable_motion`/quality flags surfaced rather than hidden, and an explicit
relative-index-not-Nm framing until a calibration path actually exists.
