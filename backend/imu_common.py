"""
Pivot — shared IMU CSV loading / math helpers.

Extracted from knee_rotation_load.py so a second analysis module
(sleeve_calibration.py) — and any future backend method — can reuse the
same CSV loading, frozen/static detection, angle-unwrap, and dt handling
instead of re-deriving it per file. knee_rotation_load.py re-imports these
names so existing call sites (and its test suite) are unaffected.

Also home for calibration-profile consumption: any analysis method that
wants anatomically meaningful axes (flexion / rotation / ab-adduction)
instead of raw sensor x/y/z reads a calibration profile produced by
sleeve_calibration.py via load_calibration_profile() and projects raw
gyro samples onto its axes via apply_calibration() — this is the one
reusable step every future method should share rather than re-guessing
axis meaning per trial.
"""

from __future__ import annotations

import csv
import json
import math
import os

FROZEN_EPS = 1e-9  # two samples "identical" if abs diff below this

# Non-numeric columns load_csv must pass through as raw strings rather than
# attempting a float parse (which would silently turn them into NaN).
_STRING_COLUMNS = {"calib_step"}


def load_csv(path: str) -> dict:
    """Read a dual-IMU CSV into column lists of floats. Raises on missing cols."""
    cols: dict = {}
    with open(path, newline="") as fh:
        reader = csv.DictReader(fh)
        required = {
            "arduino_time_s",
            "imu1_gx", "imu1_gy", "imu1_gz",
            "imu2_gx", "imu2_gy", "imu2_gz",
        }
        if not required.issubset(reader.fieldnames or []):
            missing = required - set(reader.fieldnames or [])
            raise ValueError(
                f"{os.path.basename(path)} missing required columns: {sorted(missing)}. "
                "This module expects the dual-IMU layout (imu1_*/imu2_*)."
            )
        for row in reader:
            for k, v in row.items():
                if k in _STRING_COLUMNS:
                    cols.setdefault(k, []).append(v)
                    continue
                try:
                    cols.setdefault(k, []).append(float(v))
                except (TypeError, ValueError):
                    cols.setdefault(k, []).append(math.nan)
    return cols


def count_leading_frozen(values: list) -> int:
    """Number of leading samples equal to the first value (BLE-init freeze)."""
    if not values:
        return 0
    n = 1
    while n < len(values) and abs(values[n] - values[0]) <= FROZEN_EPS:
        n += 1
    return n


def _std(xs: list) -> float:
    xs = [x for x in xs if not math.isnan(x)]
    if len(xs) < 2:
        return 0.0
    m = sum(xs) / len(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / len(xs))


def unwrap_deg(values: list) -> list:
    """
    Unwrap a sequence of angles in degrees across the +/-180 discontinuity so
    that consecutive differences reflect true rotation, not a 360-deg jump.
    NaNs are passed through unchanged.
    """
    if not values:
        return values
    out = list(values)
    offset = 0.0
    for i in range(1, len(out)):
        if math.isnan(out[i]) or math.isnan(values[i - 1]):
            continue
        d = values[i] - values[i - 1]
        if d > 180.0:
            offset -= 360.0
        elif d < -180.0:
            offset += 360.0
        out[i] = values[i] + offset
    return out


def _diff_dt(t: list) -> list:
    """Per-sample dt using actual timestamps; first dt back-filled from second."""
    dt = [0.0] * len(t)
    for i in range(1, len(t)):
        d = t[i] - t[i - 1]
        dt[i] = d if d > 0 else 0.0
    if len(t) > 1:
        # fill any nonpositive (including index 0) with median positive dt
        pos = [d for d in dt if d > 0]
        med = sorted(pos)[len(pos) // 2] if pos else 0.0
        dt = [d if d > 0 else med for d in dt]
    return dt


# ---------------------------------------------------------------------------
# Calibration profile consumption (shared by knee_rotation_load.py and any
# future analysis method)
# ---------------------------------------------------------------------------
def load_calibration_profile(path: str) -> dict:
    """Read a sleeve_calibration.py output JSON (a session-level artifact,
    not a CONTRACT.md-shaped per-trial result — see backend/CONTRACT.md)."""
    with open(path) as fh:
        return json.load(fh)


def apply_calibration(gx: list, gy: list, gz: list, profile: dict) -> dict:
    """
    Project raw per-sample [gx,gy,gz] vectors onto a calibration profile's
    three calibrated axes (flexion_extension, rotation, ab_adduction) via a
    per-sample dot product. Replaces "guess the dominant axis from variance"
    with values fixed by an actual sleeve calibration.
    """
    fe = profile["axes"]["flexion_extension"]["vector"]
    rot = profile["axes"]["rotation"]["vector"]
    ab = profile["axes"]["ab_adduction"]["vector"]

    def project(axis):
        ax, ay, az = axis
        return [gx[i] * ax + gy[i] * ay + gz[i] * az for i in range(len(gx))]

    return {
        "flexion": project(fe),
        "rotation": project(rot),
        "ab_adduction": project(ab),
    }
