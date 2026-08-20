"""
Pivot — Knee Rotation Load Index (cycle 1).

Relative tibial-femoral knee motion as a RELATIVE / QUALITATIVE knee
joint-loading proxy. NOT a calibrated joint torque (no newton-metres) and NOT
an injury probability.

IMPORTANT — what the source columns actually are:
The real cycle-1 CSVs come from collectdata_dualIMU_BLE.ino, which transmits
fused Euler ANGLES (getAngleX/Y/Z, in degrees). The BLE logger
(logdata_dualIMU_BLE.py) hardcodes a header that MISLABELS those columns as
`imuN_g*` (gyro-looking names). They are angles, not gyro rates. Only
bluetoothSync.ino logs true gyro rates (deg/s), under a different header.
Therefore, for these files the primary signal is the relative knee ANGLE / ROM
(degrees) computed by differencing the two segments' Euler angles — no
integration, no gyro drift. A relative RATE (deg/s) is derived by
DIFFERENTIATING that angle and is flagged lower-confidence (differentiation
amplifies noise).

Method (plain language)
-----------------------
Pivot has one IMU on the thigh (femur) and one on the shin (tibia). When the
knee moves, the two sensors rotate by different amounts. We take the difference
of the two segments' angular velocities:

    omega_rel = omega_tibia - omega_femur

By rigid-body kinematics this difference is the knee joint's own angular
velocity, isolating joint motion from whole-limb swing (Seel et al. 2014,
Sensors). Differencing also cancels drift/orientation error shared by both
sensors. We keep the HEADLINE in RATE space (deg/s) so gyro integration drift
does not accumulate. From that we report:

  * peak relative rotation rate  (max |omega_rel|)         -> acute strain proxy
  * mean relative rotation rate over the active window     -> intensity
  * a 0-100 Knee Rotation Load Index normalised to the active window
  * cumulative rotation, reported as a PER-SECOND rate so trials of different
    length stay comparable (lower-confidence, drift-gated)

Channel semantics (important)
-----------------------------
The CSV `imuN_g*` columns are NOT always raw gyro rates:
  * `bluetoothSync.ino`            logs true gyro RATES  (deg/s)
  * `collectdata_dualIMU_BLE.ino`  logs fused Euler ANGLES (deg)
This module auto-detects which it is (see detect_channel_meaning) and computes
the relative rotation rate accordingly:
  * if RATES:  omega_rel is differenced directly.
  * if ANGLES: omega_rel is the time-derivative (per-sample diff / dt) of the
    relative angle, and the result is flagged lower-confidence (differentiating
    noisy angle data amplifies noise).

Data-quality handling
----------------------
  * Frozen/static detection: the BLE-init freeze (commit 657b146) leaves
    accel + gyro columns repeating a constant value. We detect leading frozen
    rows (and whole-file static capture) and flag/trim them. A file with no
    real motion is reported with quality_flags.usable_motion = False.
  * Irregular dt: timing uses arduino_time_s deltas (NOT a constant rate, NOT
    receive_time_s).
  * Femur vs tibia assignment is UNVERIFIED in the data; it is a configurable
    parameter (femur_imu) and flagged segment_assignment = "UNVERIFIED".

Output: see CONTRACT.md. Returns a dict; write_outputs() dumps JSON + a flat CSV.
"""

from __future__ import annotations

import csv
import json
import math
import os
from dataclasses import dataclass, field
from typing import Optional

from imu_common import (
    apply_calibration,
    count_leading_frozen,
    load_calibration_profile,
    load_csv,
    unwrap_deg,
    _diff_dt,
    _std,
)


CONTRACT_VERSION = "1"
# For fused-angle (euler_deg) data the primary signal is the relative knee
# ANGLE / ROM; a relative RATE is also derived (lower-confidence). For true
# gyro-rate (gyro_rate_dps) data the primary signal is the relative rate.
METHOD_NAME = "relative_tibial_femoral_knee_motion"

# --- detection / processing thresholds (documented constants) ---------------
STATIC_STD_DPS = 1.5       # per-axis std below this over whole file => no motion
ANGLE_RANGE_DEG = 90.0     # if any g-channel spans more than this, treat as angle(deg)
ACTIVE_THRESH_FRAC = 0.15  # active-window threshold = frac of peak |omega_rel|
ACTIVE_MIN_DPS = 5.0       # ...but at least this many deg/s to count as "active"
DRIFT_TOL_DPS = 2.0        # quiet-baseline rate residual tolerance for drift gate
REF_LANDING_IMPACT_G = 4.0  # provisional peak dynamic-accel reference for a "hard" landing;
                             # retune once real jump/landing trials exist (same status as
                             # REF_ROM_DEG/REF_PEAK_DPS below — see knee_rotation_load_REPORT.md)

# Knee Health Score weights: relative knee load counts slightly more than ROM
# or landing mechanics, which are weighted equally. Must sum to 1.0.
KNEE_HEALTH_WEIGHT_LOAD = 0.4
KNEE_HEALTH_WEIGHT_ROM = 0.3
KNEE_HEALTH_WEIGHT_LANDING = 0.3


@dataclass
class Result:
    method: str
    version: str
    source_file: str
    units: dict
    timestamps: list
    series: dict
    summary_metrics: dict
    quality_flags: dict
    notes: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "method": self.method,
            "version": self.version,
            "source_file": self.source_file,
            "units": self.units,
            "timestamps": self.timestamps,
            "series": self.series,
            "summary_metrics": self.summary_metrics,
            "quality_flags": self.quality_flags,
            "notes": self.notes,
        }


# ---------------------------------------------------------------------------
# Data-quality detection
# ---------------------------------------------------------------------------
# load_csv, count_leading_frozen, and _std now live in imu_common.py, shared
# with sleeve_calibration.py (and any future analysis method) — imported
# above, kept as module-level names here so existing call sites are unchanged.


def detect_channel_meaning_heuristic(cols: dict) -> str:
    """
    Magnitude-based GUESS of whether imuN_g* are gyro RATES (deg/s) or fused
    Euler ANGLES (deg). This is a SECONDARY cross-check only — magnitudes
    overlap (Euler runs to ~+/-180 deg; fast gyro rates also reach hundreds
    deg/s), so a guess can misclassify silently. Prefer provenance
    (channel_meaning_for_file) and use this only to confirm / flag disagreement.

    Heuristic: fused angle channels tend to sit at large STATIC tilt offsets
    (large mean magnitude with comparatively small std), and/or span a very
    wide absolute range. Resting gyro rates hover near zero with small mean.
    """
    gkeys = ["imu1_gx", "imu1_gy", "imu1_gz", "imu2_gx", "imu2_gy", "imu2_gz"]
    for k in gkeys:
        c = [x for x in cols[k] if not math.isnan(x)]
        if not c:
            continue
        rng = max(c) - min(c)
        if rng > ANGLE_RANGE_DEG:
            return "euler_deg"
        mean_mag = abs(sum(c) / len(c))
        if mean_mag > 25.0 and _std(c) < mean_mag:  # large steady offset => tilt angle
            return "euler_deg"
    return "gyro_rate_dps"


# Provenance map: which firmware sketch produced a file determines column
# semantics RELIABLY (collectdata_dualIMU_BLE.ino -> fused Euler getAngleX/Y/Z;
# bluetoothSync.ino -> gyro rates getGyroX/Y/Z). Magnitude alone is not enough
# (Critic). Filenames here are the known real captures at repo root; extend as
# new files are added, or pass channel_meaning explicitly.
FILE_PROVENANCE = {
    # dual-IMU BLE collector -> fused Euler ANGLES in deg
    "MPU_BothIMUs_20251205_155322.csv": "euler_deg",
    "Jump_RL.csv": "euler_deg",
    "Anterior_Rotation_RL.csv": "euler_deg",
    "Posterior_Rotation_RL.csv": "euler_deg",
    "Tibial_Translation_RL.csv": "euler_deg",
}


def channel_meaning_for_file(filename: str) -> Optional[str]:
    """Provenance-based channel meaning, or None if file is unknown."""
    return FILE_PROVENANCE.get(os.path.basename(filename))


# ---------------------------------------------------------------------------
# Core computation
# ---------------------------------------------------------------------------
# unwrap_deg and _diff_dt now live in imu_common.py — see note above.


def compute(
    cols: dict,
    femur_imu: int = 1,
    sign: int = 1,
    channel_meaning: Optional[str] = None,
    provenance: Optional[str] = None,
    calibration: Optional[dict] = None,
) -> Result:
    """
    Compute the relative tibial-femoral angular-velocity index.

    femur_imu: which IMU index (1 or 2) is mounted on the femur. The other is
               assumed tibia. UNVERIFIED in the data — caller/tester must confirm.
               Ignored (calibration's segment_assignment wins) when
               `calibration` is provided.
    sign:      +1 or -1 applied to omega_rel; lets the tester orient the sign
               convention without re-deriving. Ignored when `calibration` is
               provided (calibration doesn't currently derive a sign, so the
               caller's value is still used in that case — see compute() body).
    channel_meaning: forces "euler_deg" or "gyro_rate_dps". If None, resolved
               from `provenance` (preferred) then a magnitude heuristic.
    provenance: provenance-derived channel meaning (from firmware/filename), the
               RELIABLE source. The magnitude heuristic is only a cross-check.
    calibration: a loaded sleeve_calibration.py profile dict (see
               imu_common.load_calibration_profile). When given, femur/tibia
               assignment comes from its segment_assignment instead of the
               femur_imu argument, per-axis series are produced by projecting
               onto its calibrated flexion/rotation/ab_adduction axes
               (imu_common.apply_calibration) instead of raw sensor x/y/z, and
               `dominant_axis` is fixed to `"rotation"` (the axis this metric
               cares about) instead of picked per-trial by variance.
    """
    if calibration is not None:
        femur_imu = calibration["segment_assignment"]["femur_imu"]
    assert femur_imu in (1, 2)
    tibia_imu = 2 if femur_imu == 1 else 1

    t_raw = cols["arduino_time_s"]
    n_total = len(t_raw)

    # --- resolve channel meaning: provenance preferred, heuristic cross-checks --
    heuristic = detect_channel_meaning_heuristic(cols)
    channel_meaning_confidence = "high"
    if channel_meaning is None:
        if provenance is not None:
            channel_meaning = provenance
            if provenance != heuristic:
                channel_meaning_confidence = "low"  # disagreement: surface, don't hide
        else:
            channel_meaning = heuristic
            channel_meaning_confidence = "low"  # heuristic-only is never high-confidence

    # --- frozen / static detection on a reference channel (accel if present) ---
    ref_key = "imu1_acc_x" if "imu1_acc_x" in cols else "imu1_gx"
    leading_frozen = count_leading_frozen(cols[ref_key])
    accel_static = False
    if "imu1_acc_x" in cols:
        accel_static = leading_frozen >= n_total  # frozen for the whole file

    # whole-file motion check on the g-channels (in their native units)
    g_stds = [
        _std(cols[f"imu{tibia_imu}_gx"]), _std(cols[f"imu{tibia_imu}_gy"]),
        _std(cols[f"imu{tibia_imu}_gz"]), _std(cols[f"imu{femur_imu}_gx"]),
        _std(cols[f"imu{femur_imu}_gy"]), _std(cols[f"imu{femur_imu}_gz"]),
    ]
    max_g_std = max(g_stds) if g_stds else 0.0
    # for rate data, near-zero std => no motion; for angle data, near-zero range => no motion
    usable_motion = max_g_std > STATIC_STD_DPS

    # --- trim leading frozen rows (but not if the WHOLE file is frozen) ---------
    start = leading_frozen if (0 < leading_frozen < n_total) else 0
    idx = list(range(start, n_total))

    t = [t_raw[i] for i in idx]
    t0 = t[0] if t else 0.0
    t = [x - t0 for x in t]  # baseline-zeroed timestamps
    dt = _diff_dt(t)

    def axis(imu, ax):
        return [cols[f"imu{imu}_{ax}"][i] for i in idx]

    is_angle = (channel_meaning == "euler_deg")

    # --- relative ANGLE per axis (deg). For euler_deg this is the PRIMARY,
    #     drift-free signal; for gyro_rate_dps it is None (we have no absolute
    #     angle, only rate). ------------------------------------------------
    rel_angle = {}      # ax -> list (deg) or None
    rel_rate = {}       # ax -> list (deg/s)
    for ax in ("gx", "gy", "gz"):
        tib = axis(tibia_imu, ax)
        fem = axis(femur_imu, ax)
        if is_angle:
            # Unwrap each segment's angle across the +/-180 discontinuity BEFORE
            # differencing, or wraps become garbage spikes (Critic).
            tib = unwrap_deg(tib)
            fem = unwrap_deg(fem)
            ang = [sign * (tib[k] - fem[k]) for k in range(len(idx))]
            # baseline-zero the relative angle to the quiet start (first 0.3 s)
            base_idx = [k for k in range(len(ang)) if t[k] <= 0.3] or [0]
            base = sum(ang[k] for k in base_idx) / len(base_idx)
            ang = [a - base for a in ang]
            rel_angle[ax] = ang
            # secondary: differentiate to a rate (deg/s) — noise-amplifying, low-conf
            rate = [0.0] * len(ang)
            for k in range(1, len(ang)):
                rate[k] = (ang[k] - ang[k - 1]) / dt[k] if dt[k] > 0 else 0.0
            if len(rate) > 1:
                rate[0] = rate[1]
            rel_rate[ax] = rate
        else:
            # true gyro rates: difference directly gives relative rate (deg/s)
            rel_rate[ax] = [sign * (tib[k] - fem[k]) for k in range(len(idx))]
            rel_angle[ax] = None

    n = len(idx)

    # --- dominant axis & magnitude (on the PRIMARY signal) --------------------
    if is_angle:
        primary = rel_angle
        ang_x, ang_y, ang_z = rel_angle["gx"], rel_angle["gy"], rel_angle["gz"]
        mag = [math.sqrt(ang_x[k] ** 2 + ang_y[k] ** 2 + ang_z[k] ** 2) for k in range(n)]
    else:
        primary = rel_rate
        rx, ry, rz = rel_rate["gx"], rel_rate["gy"], rel_rate["gz"]
        mag = [math.sqrt(rx[k] ** 2 + ry[k] ** 2 + rz[k] ** 2) for k in range(n)]
    # rate magnitude (always available) for the rate-space metrics
    rrx, rry, rrz = rel_rate["gx"], rel_rate["gy"], rel_rate["gz"]
    rate_mag = [math.sqrt(rrx[k] ** 2 + rry[k] ** 2 + rrz[k] ** 2) for k in range(n)]

    calibrated_rate = None
    calibrated_angle = None
    if calibration is not None:
        # Calibration fixes which axis matters ("rotation" — the Knee
        # Rotation Load Index's axis of interest) instead of picking
        # whichever raw sensor channel happened to move most in this clip.
        dominant = "rotation"
        calibrated_rate = apply_calibration(rrx, rry, rrz, calibration)
        dom_rate = calibrated_rate["rotation"]
        if is_angle:
            calibrated_angle = apply_calibration(ang_x, ang_y, ang_z, calibration)
            dom_ang = calibrated_angle["rotation"]
    else:
        axes = {"x": primary["gx"], "y": primary["gy"], "z": primary["gz"]}
        dominant = max(axes, key=lambda a: _std(axes[a])) if n else "z"
        dom_rate = rel_rate[("g" + dominant)]
        if is_angle:
            dom_ang = rel_angle[("g" + dominant)]

    # --- ROM on the dominant relative-angle axis (deg) — headline for angle data
    if is_angle:
        rom_deg = (max(dom_ang) - min(dom_ang)) if dom_ang else 0.0
        peak_abs_angle = max((abs(a) for a in dom_ang), default=0.0)
    else:
        rom_deg = None
        peak_abs_angle = None

    # --- rate-space metrics (peak/mean over active window) --------------------
    peak_rate = max(rate_mag) if rate_mag else 0.0
    thresh = max(ACTIVE_MIN_DPS, ACTIVE_THRESH_FRAC * peak_rate)
    active = [k for k in range(n) if rate_mag[k] >= thresh]
    if active:
        active_window_s = t[active[-1]] - t[active[0]]
        mean_active = sum(rate_mag[k] for k in active) / len(active)
    else:
        active_window_s = 0.0
        mean_active = 0.0

    # 0-100 index: ROM-based for angle data (90 deg ~ vigorous knee excursion);
    # peak-rate-based for true rate data (300 deg/s ~ very vigorous).
    REF_ROM_DEG = 90.0
    REF_PEAK_DPS = 300.0
    if is_angle:
        rotation_load_index = max(0.0, min(100.0, 100.0 * (rom_deg or 0.0) / REF_ROM_DEG))
    else:
        rotation_load_index = max(0.0, min(100.0, 100.0 * peak_rate / REF_PEAK_DPS))

    # This IS already a 0-100 index (see rotation_load_index above) — Knee
    # Health Score below uses it directly as the "relative knee load" sub-score.
    relative_knee_load_score = rotation_load_index

    # --- range of motion score (0-100) -----------------------------------------
    # Reuses the same REF_ROM_DEG=90 reference already established for
    # rotation_load_index's angle branch. Only meaningful when we have a real
    # ROM figure (angle-type data); null (not zero) otherwise, same convention
    # as rom_deg itself.
    if is_angle and rom_deg is not None:
        range_of_motion_score = max(0.0, min(100.0, 100.0 * rom_deg / REF_ROM_DEG))
    else:
        range_of_motion_score = None

    # --- landing mechanics score (0-100) ----------------------------------------
    # Simplified impact-magnitude proxy: peak deviation from the ~1g gravity
    # baseline in the tibia (shank) IMU's resultant accelerometer magnitude,
    # inverted so a SOFTER/more-controlled landing (lower peak impact) scores
    # HIGHER. This does not correct for sensor orientation relative to gravity
    # and does not capture frontal-plane knee valgus/trunk lean (see
    # ai-agent/research/wearable-metrics-by-location.md) — it is a coarse
    # proxy, not a validated landing-technique assessment. Null when there's
    # no accelerometer data or the trial isn't usable motion (nothing to
    # measure an impact against).
    tib_acc_keys = (f"imu{tibia_imu}_acc_x", f"imu{tibia_imu}_acc_y", f"imu{tibia_imu}_acc_z")
    has_accel = all(k in cols for k in tib_acc_keys)
    motion_is_usable = usable_motion and not accel_static
    peak_impact_g = None
    landing_mechanics_score = None
    accel_magnitude_tibia = None
    if has_accel:
        tib_ax, tib_ay, tib_az = axis(tibia_imu, "acc_x"), axis(tibia_imu, "acc_y"), axis(tibia_imu, "acc_z")
        # Exposed as a series regardless of usable_motion so the Landing
        # Mechanics tab has something to plot even for a flagged/dead trial
        # (a flat line at ~1g visually confirms "yes, this one is frozen").
        accel_magnitude_tibia = [math.sqrt(tib_ax[k] ** 2 + tib_ay[k] ** 2 + tib_az[k] ** 2) for k in range(n)]
        if motion_is_usable:
            peak_impact_g = max((abs(m - 1.0) for m in accel_magnitude_tibia), default=0.0)
            landing_mechanics_score = max(0.0, min(100.0, 100.0 * (1.0 - peak_impact_g / REF_LANDING_IMPACT_G)))

    # --- Knee Health Score (0-100): weighted roll-up of the three sub-scores ---
    # Null (not partially computed) unless all three sub-scores are available —
    # same "don't silently score incomplete data" discipline as the rest of
    # this module (e.g. rom_deg=null on rate-only files).
    if range_of_motion_score is not None and landing_mechanics_score is not None:
        knee_health_score = max(0.0, min(100.0, (
            KNEE_HEALTH_WEIGHT_LOAD * relative_knee_load_score
            + KNEE_HEALTH_WEIGHT_ROM * range_of_motion_score
            + KNEE_HEALTH_WEIGHT_LANDING * landing_mechanics_score
        )))
    else:
        knee_health_score = None

    # --- drift gate (only meaningful / claimed for true rate data) ------------
    def quiet_mean(seg):
        return (sum(seg) / len(seg)) if seg else 0.0
    head = [rate_mag[k] for k in range(n) if t[k] <= 0.5]
    tail = [rate_mag[k] for k in range(n) if t and t[k] >= (t[-1] - 0.5)]
    drift_residual = abs(quiet_mean(tail) - quiet_mean(head))
    drift_bounded = (not is_angle) and (drift_residual <= DRIFT_TOL_DPS)

    pos_dt = sorted([d for d in dt if d > 0])
    sample_rate_hz = (1.0 / pos_dt[len(pos_dt) // 2]) if pos_dt else float("nan")

    notes = [
        "Relative/qualitative knee-motion proxy from differencing the two segment "
        "IMUs — NOT a calibrated joint torque (no Nm) and NOT an injury probability.",
        f"Channel meaning resolved as '{channel_meaning}' "
        f"(confidence={channel_meaning_confidence}; magnitude heuristic said '{heuristic}').",
    ]
    if calibration is not None:
        notes.append(
            f"Femur/tibia assignment CONFIRMED via sleeve calibration "
            f"(femur_imu={femur_imu}); dominant_axis fixed to 'rotation' by the "
            "calibration's derived axes instead of picked per-trial by variance."
        )
    else:
        notes.append(
            f"Femur/tibia assignment is UNVERIFIED (femur_imu={femur_imu}); confirm with "
            "the physical sleeve. Sign is configurable (sign param)."
        )
    if is_angle:
        notes.append(
            "These columns are fused Euler ANGLES (deg) — the BLE logger mislabels them "
            "'_g*' but the firmware (collectdata_dualIMU_BLE.ino) sends getAngleX/Y/Z. "
            "PRIMARY signal is the relative knee ANGLE / ROM (deg), which needs no "
            "integration and is drift-free. A relative RATE (deg/s) is also provided by "
            "differentiating the angle, but that amplifies noise — treat rate as "
            "LOWER-CONFIDENCE."
        )
    if channel_meaning_confidence == "low":
        notes.append(
            "Channel meaning is LOW confidence (provenance unknown or it disagrees with "
            "the magnitude heuristic). Outputs are UNVALIDATED until the tester confirms "
            "whether these columns are gyro rates (deg/s) or fused Euler angles (deg)."
        )
    if leading_frozen and start:
        notes.append(f"Dropped {start} leading frozen rows (BLE-init freeze, commit 657b146).")
    if not usable_motion or accel_static:
        notes.append(
            "WARNING: this file shows little/no real movement (accel frozen and/or "
            "angle/gyro channels nearly static). Metrics are near-zero and NOT a valid "
            "movement recording — likely a capture/hardware issue to confirm with the tester."
        )
    notes.append(
        "Landing mechanics score is a coarse peak-impact-magnitude proxy from the tibia "
        "accelerometer (softer landing = higher score) — it does NOT capture knee valgus "
        "or trunk lean, the frontal-plane signals landing-mechanics screens actually care "
        "about (see ai-agent/research/wearable-metrics-by-location.md). Knee Health Score "
        f"is a weighted composite ({int(KNEE_HEALTH_WEIGHT_LOAD*100)}% relative knee load, "
        f"{int(KNEE_HEALTH_WEIGHT_ROM*100)}% range of motion, {int(KNEE_HEALTH_WEIGHT_LANDING*100)}% "
        "landing mechanics) — a relative proxy, like its components, NOT a clinical or "
        "validated injury-risk score."
    )
    if knee_health_score is None:
        notes.append(
            "Knee Health Score is null: at least one sub-score is unavailable for this "
            "trial (needs usable, non-frozen accelerometer data for landing mechanics, and "
            "angle-type data with a real ROM for the range-of-motion sub-score)."
        )

    # --- series: always expose relative rate; expose relative angle when we have it
    series = {
        "rel_rate_x": rrx, "rel_rate_y": rry, "rel_rate_z": rrz,
        "rel_rate_dominant": dom_rate,
        "rel_rate_magnitude": rate_mag,
    }
    if is_angle:
        series.update({
            "rel_angle_x": rel_angle["gx"], "rel_angle_y": rel_angle["gy"],
            "rel_angle_z": rel_angle["gz"],
            "rel_angle_dominant": dom_ang,
            "rel_angle_magnitude": mag,
        })
    if calibrated_rate is not None:
        # Calibrated series alongside the raw x/y/z ones — flexion and
        # ab_adduction are exposed too, not just the dominant rotation axis.
        series.update({
            "rel_rate_flexion": calibrated_rate["flexion"],
            "rel_rate_rotation": calibrated_rate["rotation"],
            "rel_rate_ab_adduction": calibrated_rate["ab_adduction"],
        })
        if calibrated_angle is not None:
            series.update({
                "rel_angle_flexion": calibrated_angle["flexion"],
                "rel_angle_rotation": calibrated_angle["rotation"],
                "rel_angle_ab_adduction": calibrated_angle["ab_adduction"],
            })
    if accel_magnitude_tibia is not None:
        series["accel_magnitude_tibia"] = accel_magnitude_tibia

    summary_metrics = {
        "primary_signal": "relative_angle_deg" if is_angle else "relative_rate_dps",
        "rom_deg": round(rom_deg, 3) if rom_deg is not None else None,
        "peak_abs_rel_angle_deg": round(peak_abs_angle, 3) if peak_abs_angle is not None else None,
        "peak_rel_rate_dps": round(peak_rate, 3),
        "mean_active_rate_dps": round(mean_active, 3),
        "rotation_load_index": round(rotation_load_index, 2),
        "relative_knee_load_score": round(relative_knee_load_score, 2),
        "range_of_motion_score": round(range_of_motion_score, 2) if range_of_motion_score is not None else None,
        "peak_impact_g": round(peak_impact_g, 3) if peak_impact_g is not None else None,
        "landing_mechanics_score": round(landing_mechanics_score, 2) if landing_mechanics_score is not None else None,
        "knee_health_score": round(knee_health_score, 2) if knee_health_score is not None else None,
        "dominant_axis": dominant,
    }
    quality_flags = {
        "accel_static": bool(accel_static),
        "gyro_varies": bool(usable_motion),
        "usable_motion": bool(usable_motion and not accel_static),
        "channel_meaning": channel_meaning,
        "channel_meaning_confidence": channel_meaning_confidence,
        "channel_meaning_heuristic": heuristic,
        "rate_is_low_confidence": bool(is_angle),
        "sample_rate_hz": round(sample_rate_hz, 2) if not math.isnan(sample_rate_hz) else None,
        "n_samples": n,
        "n_dropped_leading_frozen": start,
        "active_window_s": round(active_window_s, 3),
        "drift_residual_dps": round(drift_residual, 3),
        "drift_bounded": bool(drift_bounded),
        "segment_assignment": "confirmed" if calibration is not None else "UNVERIFIED",
        "femur_imu": femur_imu,
        "tibia_imu": tibia_imu,
        "sign": sign,
        "calibration_applied": calibration is not None,
        "calibration_source": (calibration or {}).get("source_file"),
        "calibration_confidence": (calibration or {}).get("quality_flags", {}).get("calibration_confidence"),
    }

    return Result(
        method=METHOD_NAME,
        version=CONTRACT_VERSION,
        source_file="",  # filled by analyze_file
        units={
            "time": "s",
            "rel_angle": "deg",
            "rel_rate": "deg/s",
            "rom_deg": "deg",
            "rotation_load_index": "unitless_0_100",
            "relative_knee_load_score": "unitless_0_100",
            "range_of_motion_score": "unitless_0_100",
            "peak_impact_g": "g",
            "landing_mechanics_score": "unitless_0_100",
            "knee_health_score": "unitless_0_100",
            "accel_magnitude_tibia": "g",
        },
        timestamps=[round(x, 6) for x in t],
        series={k: [round(v, 4) for v in vs] for k, vs in series.items()},
        summary_metrics=summary_metrics,
        quality_flags=quality_flags,
        notes=notes,
    )


def analyze_file(
    path: str,
    femur_imu: int = 1,
    sign: int = 1,
    channel_meaning: Optional[str] = None,
    calibration_path: Optional[str] = None,
) -> Result:
    cols = load_csv(path)
    prov = channel_meaning_for_file(path)
    calibration = load_calibration_profile(calibration_path) if calibration_path else None
    res = compute(
        cols, femur_imu=femur_imu, sign=sign,
        channel_meaning=channel_meaning, provenance=prov,
        calibration=calibration,
    )
    res.source_file = os.path.basename(path)
    return res


# ---------------------------------------------------------------------------
# Output writers
# ---------------------------------------------------------------------------
def write_outputs(res: Result, out_dir: str) -> dict:
    os.makedirs(out_dir, exist_ok=True)
    base = os.path.splitext(res.source_file)[0]
    json_path = os.path.join(out_dir, f"{base}.knee_rotation_load.json")
    csv_path = os.path.join(out_dir, f"{base}.knee_rotation_load.csv")

    with open(json_path, "w") as fh:
        json.dump(res.to_dict(), fh, indent=2)

    # flat CSV: timestamps + series
    with open(csv_path, "w", newline="") as fh:
        w = csv.writer(fh)
        keys = list(res.series.keys())
        w.writerow(["time_s"] + keys)
        for i, ts in enumerate(res.timestamps):
            w.writerow([ts] + [res.series[k][i] for k in keys])

    return {"json": json_path, "csv": csv_path}


if __name__ == "__main__":
    import sys

    root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "cycle-1")
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs")
    files = sys.argv[1:] or [
        "MPU_BothIMUs_20251205_155322.csv",
        "Jump_RL.csv",
        "Anterior_Rotation_RL.csv",
        "Posterior_Rotation_RL.csv",
        "Tibial_Translation_RL.csv",
    ]
    for f in files:
        path = f if os.path.isabs(f) else os.path.join(root, f)
        res = analyze_file(path)
        paths = write_outputs(res, out_dir)
        print(f"\n== {res.source_file}")
        print("  summary:", json.dumps(res.summary_metrics))
        print("  flags  :", json.dumps({k: res.quality_flags[k] for k in
              ("usable_motion", "channel_meaning", "rotation_load_index"
               if "rotation_load_index" in res.quality_flags else "n_samples")}))
        print("  wrote  :", paths["json"])
