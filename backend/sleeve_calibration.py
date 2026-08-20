"""
Pivot — Sleeve Functional Calibration.

Derives the knee's cardinal axes (flexion-extension, internal/external
rotation, ab/adduction) from a dedicated calibration recording, instead of
knee_rotation_load.py's per-trial "whichever raw sensor axis moved most"
guess (`dominant_axis = max(axes, key=std)`) and hand-set `femur_imu`/`sign`
arguments. See ai-agent/research/sleeve-calibration-protocol.md for why/what-movement,
and the plan this implements for the engineering design.

Input: a `calib_*.csv` recorded by bluetoothSync.ino's CALIBRATING state —
same dual-IMU columns knee_rotation_load.py reads (`arduino_time_s`,
`imuN_acc_*`, `imuN_gx/gy/gz`), plus a `calib_step` column marking which
guided step each row belongs to: STAND, FLEX, INT_ROT, NEUTRAL, EXT_ROT.

Method (plain language)
-----------------------
Rather than trust that the sensor's raw X/Y/Z axes mean anything anatomical
(the sleeve can be donned at any twist/tilt), each axis is found empirically
from a movement that isolates it:
  * FLEX rows (thigh held still, shank swinging) -> flexion-extension axis.
  * INT_ROT + EXT_ROT rows (shank twisted in/out) -> rotation axis.
  * ab/adduction is NOT measured directly (small-ROM, hard to isolate
    voluntarily) — it's derived as the axis orthogonal to the other two
    (Gram-Schmidt), completing a right-handed orthonormal frame.
The "axis a movement mostly rotates about" is the dominant eigenvector of
the (uncentered) second-moment matrix of the relative angular-velocity
samples during that movement — found here by power iteration, since only
the TOP eigenvector is needed (no numpy: there is no third-party dependency
anywhere under backend/, and a 3x3 power iteration is ~10 lines of pure
Python — see imu_common.py's precedent).

STAND rows also give a residual gyro-bias estimate (calcOffsets() already
runs at firmware boot, but not with the sleeve worn in situ) and a
stillness QC check, and (since the thigh is deliberately held still during
FLEX) let femur/tibia identity be read off the data instead of hand-set:
whichever IMU shows more gyro variance during FLEX is the tibia.

Scope limit: this calibrates axis directions + segment identity + gyro
bias, NOT an absolute "0 deg = full extension" angle zero — bluetoothSync.ino
logs true gyro rates, not fused Euler angles, so there is no absolute angle
to baseline here. See ai-agent/research/sleeve-calibration-protocol.md.

Output: a session-level calibration profile JSON — NOT a CONTRACT.md-shaped
per-trial result (no timestamps/series to plot). Consumed by
knee_rotation_load.py (and any future method) via
imu_common.load_calibration_profile / imu_common.apply_calibration.
"""

from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, field
from typing import Optional

from imu_common import load_csv

METHOD_NAME = "sleeve_functional_calibration"
CONTRACT_VERSION = "1"

# --- documented constants ----------------------------------------------------
STEP_STAND = "STAND"
STEP_FLEX = "FLEX"
STEP_INT_ROT = "INT_ROT"
STEP_NEUTRAL = "NEUTRAL"
STEP_EXT_ROT = "EXT_ROT"

POWER_ITERATIONS = 200          # fixed iteration count for the eigenvector solve
STAND_STILL_MAX_STD_DPS = 5.0   # STAND-stage gyro std above this => not actually still
VARIANCE_EXPLAINED_HIGH = 0.85  # >= this on both FE and rotation axes => "high" confidence
VARIANCE_EXPLAINED_MEDIUM = 0.60


# ---------------------------------------------------------------------------
# Small 3-vector / 3x3-matrix helpers (pure Python, no numpy — see module
# docstring; matches the zero-third-party-dependency precedent already set
# by knee_rotation_load.py / imu_common.py).
# ---------------------------------------------------------------------------
def _dot(a: list, b: list) -> float:
    return sum(a[i] * b[i] for i in range(3))


def _cross(a: list, b: list) -> list:
    return [
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    ]


def _norm(v: list) -> float:
    return math.sqrt(_dot(v, v))


def _normalize(v: list) -> list:
    n = _norm(v)
    if n < 1e-12:
        return [1.0, 0.0, 0.0]
    return [x / n for x in v]


def _mat_vec(m: list, v: list) -> list:
    return [sum(m[i][j] * v[j] for j in range(3)) for i in range(3)]


def second_moment_matrix(xs: list, ys: list, zs: list) -> list:
    """Uncentered second-moment ("covariance-like") matrix of 3-vector
    samples. Uncentered (not mean-subtracted) on purpose: a pure hinge/twist
    movement produces samples that oscillate +/- along the true axis, so the
    axis of interest is the direction the vectors themselves concentrate
    along, not the direction of deviation from their mean — mean-centering
    would instead chase any residual bias offset."""
    n = len(xs)
    if n == 0:
        return [[0.0] * 3 for _ in range(3)]
    sxx = sum(x * x for x in xs) / n
    syy = sum(y * y for y in ys) / n
    szz = sum(z * z for z in zs) / n
    sxy = sum(x * y for x, y in zip(xs, ys)) / n
    sxz = sum(x * z for x, z in zip(xs, zs)) / n
    syz = sum(y * z for y, z in zip(ys, zs)) / n
    return [[sxx, sxy, sxz], [sxy, syy, syz], [sxz, syz, szz]]


def dominant_eigenvector(m: list, iterations: int = POWER_ITERATIONS) -> tuple:
    """
    Power iteration for the top eigenvector of a symmetric 3x3 matrix. Only
    the dominant eigenvector is needed (the calibration axis), so this is
    simpler than a full eigendecomposition/SVD. Returns (unit_vector,
    eigenvalue, variance_explained). variance_explained is the eigenvalue
    as a fraction of the matrix trace (sum of all eigenvalues for a
    symmetric PSD matrix) — 1.0 means all the rotational energy sits on one
    axis (a clean, well-isolated calibration movement); low values mean the
    movement wasn't cleanly single-axis (thigh moved during FLEX, mixed
    flexion into the rotation stage, etc.).
    """
    trace = m[0][0] + m[1][1] + m[2][2]
    if trace < 1e-9:
        return [1.0, 0.0, 0.0], 0.0, 0.0
    v = _normalize([1.0, 1.0, 1.0])
    for _ in range(iterations):
        v = _normalize(_mat_vec(m, v))
    mv = _mat_vec(m, v)
    eigenvalue = _dot(v, mv)
    variance_explained = max(0.0, min(1.0, eigenvalue / trace))
    return v, eigenvalue, variance_explained


def orthonormal_frame(flexion_extension: list, rotation_raw: list) -> tuple:
    """
    Gram-Schmidt: keep flexion_extension as-is (e1), project rotation_raw
    onto the plane orthogonal to e1 to get an exactly-orthogonal rotation
    axis (e2), then ab_adduction = e1 x e2 completes a right-handed
    orthonormal frame — ab/adduction is derived this way rather than
    measured directly (small-ROM, hard to voluntarily isolate).
    """
    e1 = _normalize(flexion_extension)
    proj = _dot(rotation_raw, e1)
    perp = [rotation_raw[i] - proj * e1[i] for i in range(3)]
    e2 = _normalize(perp)
    e3 = _cross(e1, e2)
    return e1, e2, e3


# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------
@dataclass
class Result:
    method: str
    version: str
    source_file: str
    segment_assignment: dict
    axes: dict
    gyro_bias: dict
    quality_flags: dict
    notes: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "method": self.method,
            "version": self.version,
            "source_file": self.source_file,
            "segment_assignment": self.segment_assignment,
            "axes": self.axes,
            "gyro_bias": self.gyro_bias,
            "quality_flags": self.quality_flags,
            "notes": self.notes,
        }


def _rows_for_step(cols: dict, step: str) -> list:
    return [i for i, s in enumerate(cols["calib_step"]) if s == step]


def _series(cols: dict, imu: int, axis: str, idx: list) -> list:
    return [cols[f"imu{imu}_{axis}"][i] for i in idx]


def _bias(cols: dict, imu: int, idx: list) -> list:
    """Mean gyro reading per axis over a (supposedly still) set of rows —
    a residual bias estimate/correction beyond firmware calcOffsets()."""
    if not idx:
        return [0.0, 0.0, 0.0]
    return [sum(_series(cols, imu, ax, idx)) / len(idx) for ax in ("gx", "gy", "gz")]


def _bias_corrected(cols: dict, imu: int, idx: list, bias: list) -> list:
    """[gx,gy,gz] samples for `idx`, bias-subtracted, as a list of 3-vectors."""
    gx = _series(cols, imu, "gx", idx)
    gy = _series(cols, imu, "gy", idx)
    gz = _series(cols, imu, "gz", idx)
    return [[gx[k] - bias[0], gy[k] - bias[1], gz[k] - bias[2]] for k in range(len(idx))]


def _std(xs: list) -> float:
    if len(xs) < 2:
        return 0.0
    m = sum(xs) / len(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / len(xs))


def compute(cols: dict) -> Result:
    stand_idx = _rows_for_step(cols, STEP_STAND)
    flex_idx = _rows_for_step(cols, STEP_FLEX)
    rot_idx = _rows_for_step(cols, STEP_INT_ROT) + _rows_for_step(cols, STEP_EXT_ROT)

    # --- gyro bias + stillness QC from STAND -------------------------------
    bias1 = _bias(cols, 1, stand_idx)
    bias2 = _bias(cols, 2, stand_idx)
    stand_mag_std = 0.0
    if stand_idx:
        for imu, bias in ((1, bias1), (2, bias2)):
            corrected = _bias_corrected(cols, imu, stand_idx, bias)
            mags = [_norm(v) for v in corrected]
            stand_mag_std = max(stand_mag_std, _std(mags))
    stand_still_ok = bool(stand_idx) and stand_mag_std <= STAND_STILL_MAX_STD_DPS

    # --- femur/tibia identity: higher gyro variance during FLEX == tibia ---
    flex1 = _bias_corrected(cols, 1, flex_idx, bias1)
    flex2 = _bias_corrected(cols, 2, flex_idx, bias2)
    std1 = _std([_norm(v) for v in flex1]) if flex1 else 0.0
    std2 = _std([_norm(v) for v in flex2]) if flex2 else 0.0
    tibia_imu = 2 if std2 >= std1 else 1
    femur_imu = 1 if tibia_imu == 2 else 2

    tib_bias = bias2 if tibia_imu == 2 else bias1
    fem_bias = bias1 if tibia_imu == 2 else bias2

    # --- flexion-extension axis from FLEX omega_rel -------------------------
    tib_flex = _bias_corrected(cols, tibia_imu, flex_idx, tib_bias)
    fem_flex = _bias_corrected(cols, femur_imu, flex_idx, fem_bias)
    rel_flex = [[tib_flex[k][a] - fem_flex[k][a] for a in range(3)] for k in range(len(flex_idx))]
    fe_axis, _, fe_variance = dominant_eigenvector(
        second_moment_matrix([v[0] for v in rel_flex], [v[1] for v in rel_flex], [v[2] for v in rel_flex])
    )

    # --- rotation axis from INT_ROT+EXT_ROT omega_rel -----------------------
    tib_rot = _bias_corrected(cols, tibia_imu, rot_idx, tib_bias)
    fem_rot = _bias_corrected(cols, femur_imu, rot_idx, fem_bias)
    rel_rot = [[tib_rot[k][a] - fem_rot[k][a] for a in range(3)] for k in range(len(rot_idx))]
    rot_axis_raw, _, rot_variance = dominant_eigenvector(
        second_moment_matrix([v[0] for v in rel_rot], [v[1] for v in rel_rot], [v[2] for v in rel_rot])
    )

    # --- ab/adduction derived by orthogonality ------------------------------
    fe_axis, rot_axis, ab_axis = orthonormal_frame(fe_axis, rot_axis_raw)

    # --- confidence ----------------------------------------------------------
    if stand_still_ok and fe_variance >= VARIANCE_EXPLAINED_HIGH and rot_variance >= VARIANCE_EXPLAINED_HIGH:
        confidence = "high"
    elif fe_variance >= VARIANCE_EXPLAINED_MEDIUM and rot_variance >= VARIANCE_EXPLAINED_MEDIUM:
        confidence = "medium"
    else:
        confidence = "low"
    usable = bool(flex_idx) and bool(rot_idx) and confidence != "low"

    notes = [
        "Functional calibration: axis directions + femur/tibia identity + gyro "
        "bias, derived from isolated flexion-extension and rotation movements — "
        "NOT an absolute '0 deg = full extension' angle zero (bluetoothSync.ino "
        "logs true gyro rates, no fused angle to baseline).",
        f"Femur/tibia identity: imu{tibia_imu} assigned tibia (higher gyro "
        f"variance during FLEX: std={std2 if tibia_imu == 2 else std1:.2f} vs "
        f"{std1 if tibia_imu == 2 else std2:.2f} dps).",
        f"Flexion-extension axis variance-explained={fe_variance:.2f}, "
        f"rotation axis variance-explained={rot_variance:.2f} "
        "(1.0 = a clean, single-axis movement; low values mean the stage wasn't "
        "cleanly isolated — redo that step).",
    ]
    if not stand_idx:
        notes.append("WARNING: no STAND rows found — gyro bias defaulted to zero, unverified.")
    elif not stand_still_ok:
        notes.append(
            f"WARNING: STAND stage gyro std ({stand_mag_std:.2f} dps) exceeds "
            f"{STAND_STILL_MAX_STD_DPS} dps — subject likely wasn't fully still."
        )
    if not flex_idx or not rot_idx:
        notes.append("WARNING: missing FLEX or INT_ROT/EXT_ROT rows — calibration incomplete.")

    return Result(
        method=METHOD_NAME,
        version=CONTRACT_VERSION,
        source_file="",  # filled by analyze_file
        segment_assignment={
            "femur_imu": femur_imu,
            "tibia_imu": tibia_imu,
            "basis": "gyro_variance_during_flex",
        },
        axes={
            "flexion_extension": {"vector": [round(x, 6) for x in fe_axis], "variance_explained": round(fe_variance, 4)},
            "rotation": {"vector": [round(x, 6) for x in rot_axis], "variance_explained": round(rot_variance, 4)},
            "ab_adduction": {"vector": [round(x, 6) for x in ab_axis], "derived": "gram_schmidt"},
        },
        gyro_bias={"imu1": [round(x, 4) for x in bias1], "imu2": [round(x, 4) for x in bias2]},
        quality_flags={
            "stand_still_ok": stand_still_ok,
            "flex_variance_explained": round(fe_variance, 4),
            "rotation_variance_explained": round(rot_variance, 4),
            "calibration_confidence": confidence,
            "usable": usable,
        },
        notes=notes,
    )


def analyze_file(path: str) -> Result:
    cols = load_csv(path)
    if "calib_step" not in cols:
        raise ValueError(
            f"{os.path.basename(path)} has no 'calib_step' column — this doesn't look "
            "like a calibration recording (expected bluetoothSync.ino's CALIBRATING output)."
        )
    res = compute(cols)
    res.source_file = os.path.basename(path)
    return res


def write_outputs(res: Result, out_dir: str) -> dict:
    os.makedirs(out_dir, exist_ok=True)
    base = os.path.splitext(res.source_file)[0]
    json_path = os.path.join(out_dir, f"{base}.sleeve_calibration.json")
    with open(json_path, "w") as fh:
        json.dump(res.to_dict(), fh, indent=2)
    return {"json": json_path}


if __name__ == "__main__":
    import sys

    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs")
    if len(sys.argv) < 2:
        print("Usage: python3 sleeve_calibration.py <calib_NNNN.csv> [more files...]")
        sys.exit(1)
    for f in sys.argv[1:]:
        res = analyze_file(f)
        paths = write_outputs(res, out_dir)
        print(f"\n== {res.source_file}")
        print("  segment_assignment:", json.dumps(res.segment_assignment))
        print("  axes              :", json.dumps(res.axes))
        print("  quality_flags     :", json.dumps(res.quality_flags))
        print("  wrote             :", paths["json"])
