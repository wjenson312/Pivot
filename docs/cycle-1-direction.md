# Cycle 1 Direction — Knee Rotation Load Index (Relative Tibial–Femoral Rotation)

**Author:** Planner (PivotTeam)
**Date:** 2026-06-19
**Status:** Locked — direction set, cycle in progress

---

## 1. Chosen topic / application

**Build a relative tibial–femoral rotation metric** from the two IMUs during the
clinical-style rotation trials, framed as a **relative joint-motion / loading
index** (NOT a calibrated physical torque in Nm).

Cycle 1 delivers ONE analysis method:

> **Relative segment angular velocity** between the femur IMU and the tibia IMU,
> `omega_rel(t) = omega_tibia(t) - omega_femur(t)` per axis, summarized into a
> **Knee Rotation Load Index** (peak + mean relative rotation rate over the
> auto-detected active window, plus a duration-normalized cumulative rotation).

Primary input CSVs (repo root):
- `Anterior_Rotation_RL.csv`
- `Posterior_Rotation_RL.csv`
- `Tibial_Translation_RL.csv` (secondary / comparison)

`Jump_RL.csv` is held back for a later dynamic-loading cycle.

---

## 2. Rationale — grounded in what the IMUs can actually measure

Each CSV has, per IMU, 3-axis accel (g) and 3-axis "gyro" channels:
`imuN_acc_{x,y,z}`, `imuN_gx/gy/gz`. Two IMUs → IMU1 and IMU2.

Observations from inspecting the real data (corroborated by Critic):

- **The gyro channels vary meaningfully** through each trial and differ between
  the two IMUs — exactly the *relative* rotation signal we want.
- **The accelerometer columns appear frozen/constant** across the rotation /
  translation CSVs (e.g. `imu1_acc_*` at `0.553,-0.372,0.243`, `imu2_acc_*` at
  `-0.172,-0.25,0.039`). This is a **data-quality red flag**, likely predating
  the accel-freeze fix in commit `657b146`. We therefore do **NOT** base the
  cycle-1 metric on accelerometer integration (translation / jerk / accel-fusion
  flexion angle), which would be unreliable and drift-prone here.
- Sampling is ~17 ms (~59–60 Hz) but irregular; trials are short (~4–7 s, e.g.
  Anterior 273 rows vs Posterior 237 rows) — so cross-trial summaries must
  account for differing lengths (see §4).
- **Channel-meaning ambiguity (Backend finding):** the `imuN_gx/gy/gz` columns
  are NOT consistently raw rates. `collectdata_dualIMU_BLE.ino` logs **fused
  Euler angles (deg)**; `bluetoothSync.ino` logs **real gyro rates (deg/s)**.
  So "differencing" means different things per file and must be auto-detected.

Choosing gyro-derived **relative angular velocity** is the most defensible first
metric: it uses the channel with real signal; differencing cancels common-mode
whole-leg motion to isolate motion *across the joint*; and it needs no
calibration to be useful as a relative index, with a clean later upgrade path.

## 3. Physical-measure vs. index decision (explicit)

**Cycle 1 output is a RELATIVE / QUALITATIVE LOAD INDEX, not a physical torque.**
Headline values are rate-space (deg/s); the index is a unitless 0–100 "Knee
Rotation Load Index". **No Nm claims.** A calibrated physical measure is deferred
to a later cycle (needs orientation estimation + per-athlete scaling + ground
truth, none of which exist yet).

## 4. Intended analysis approach (for Backend — converged spec)

1. **Load & validate** a trial CSV against the documented column contract.
   Confirm units against firmware and sample rate from `arduino_time_s`.
2. **Quality checks, surfaced (not hidden) in `quality_flags`:**
   - `accel_frozen` — detect & report static accelerometer columns.
   - `channel_meaning` ∈ {`euler_deg`, `gyro_rate_dps`} — determine **primarily
     from PROVENANCE** (which firmware / filename produced the CSV), because
     fused Euler angles (deg, ≤±180) and gyro rates (deg/s, tens-to-hundreds in
     fast trials) overlap in magnitude and a magnitude heuristic can silently
     misclassify. Use the magnitude heuristic only as a secondary cross-check;
     on provenance-vs-heuristic disagreement, set a low-confidence flag rather
     than committing silently. Cumulative rotation computed accordingly: if
     `euler_deg`, derive rate by differentiation and flag lower-confidence; if
     `gyro_rate_dps`, difference directly.
   - `active_window_s`, `n_samples` — so trial-length differences are visible.
   - `drift_bounded` — compare quiet-baseline rate at start vs end; if residual
     drift exceeds threshold, set false.
3. **Relative angular velocity:** `omega_rel = omega_imu2 - omega_imu1` per axis;
   identify dominant rotation axis (likely gz). Optional low-pass; baseline-
   subtract using the quiet start segment. **Sign/direction configurable**
   (depends on segment mapping, see §6).
4. **Summarize (rate-space headline, drift-insensitive):**
   - `peak_rel_rate` and `mean_rel_rate` over the auto-detected active window
     (motion above a noise threshold).
   - `cumulative_rotation_deg / active_window_s` reported as a **per-second
     rate** — NO raw unnormalized cross-trial cumulative on the dashboard.
   - `rotation_load_index` — normalized 0–100 (document normalization basis).
   - Integrated relative angle / ROM shown **only when `drift_bounded = true`**,
     and labeled lower-confidence.
5. **Emit JSON + CSV** per Backend's `CONTRACT.md`: time series (`t`,
   `omega_rel_axis`) for plotting + scalar summary fields + the quality flags.

## 5. Athlete-facing feedback framing

> "During this movement, here's how much your shin rotated relative to your thigh
> — i.e. how much rotational load went *through your knee* rather than moving
> your whole leg as one. A higher Knee Rotation Load Index means more rotational
> stress at the joint for that rep/session."

Tab ("Knee Rotation Load") shows:
- Researcher one-paragraph plain-language explanation.
- A graph of relative rotation rate (deg/s) over time, peak marked.
- Backend report block: index (0–100), peak/mean rate, per-second cumulative.
- An explicit caveat: **relative index, not a calibrated force/torque**.
- A visible data-quality warning when `accel_frozen` is set, and a label
  reflecting `channel_meaning` (Euler-derived rate shown lower-confidence).

## 6. Open questions for the human tester

1. **Which IMU is which segment?** IMU1 vs IMU2 → femur vs tibia is
   **undocumented / TBD**. The sign/direction of `omega_rel` depends on it.
   Proceeding with it marked TBD and `omega_rel` sign configurable; the
   coordinator is relaying this question to the human tester.
2. **Accel freeze:** are the rotation/translation CSVs from before `657b146`?
   If so we may want re-collection later.
3. **Channel meaning per file:** confirm which firmware produced each CSV
   (Euler angles deg vs raw gyro deg/s) and the sensor full-scale settings.

## 7. Scope guardrails

- Do not touch `app/data-analysis/` collection pipeline except for a
  tester-reported hardware bug.
- One method, one frontend tab this cycle. Keep it shippable and honest.
- Backend and Frontend each add pass/fail entries to `/tests/report.md`.
