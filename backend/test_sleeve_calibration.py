"""
Basic correctness / sanity tests for sleeve_calibration.

Run:  python3 backend/test_sleeve_calibration.py
Exits non-zero on failure; prints a PASS/FAIL summary.
Pure stdlib (no pytest dependency), mirroring test_knee_rotation_load.py.
"""

import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sleeve_calibration as sc  # noqa: E402

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "cycle-1")

_failures = []
_checks = 0


def check(cond, msg):
    global _checks
    _checks += 1
    if not cond:
        _failures.append(msg)
        print(f"  FAIL: {msg}")
    else:
        print(f"  ok  : {msg}")


def _make_synthetic_cols(stand_still=True, n_stand=50, n_flex=100, n_rot=100, seed=42):
    """
    Build a synthetic cols dict (same shape load_csv would produce) for a
    clean calibration recording: imu2 is the tibia (moves during FLEX, thigh
    i.e. imu1 stays still), flexion-extension purely about the raw Z axis,
    rotation purely about the raw X axis (deliberately orthogonal, known
    axes) with small perpendicular noise.
    """
    rng = random.Random(seed)
    cols = {
        "arduino_time_s": [], "imu1_gx": [], "imu1_gy": [], "imu1_gz": [],
        "imu2_gx": [], "imu2_gy": [], "imu2_gz": [], "calib_step": [],
    }
    t = 0.0

    def add_row(step, g1, g2):
        nonlocal t
        cols["arduino_time_s"].append(t)
        cols["imu1_gx"].append(g1[0]); cols["imu1_gy"].append(g1[1]); cols["imu1_gz"].append(g1[2])
        cols["imu2_gx"].append(g2[0]); cols["imu2_gy"].append(g2[1]); cols["imu2_gz"].append(g2[2])
        cols["calib_step"].append(step)
        t += 0.01

    noise = lambda: rng.uniform(-0.5, 0.5)  # small perpendicular noise, deg/s

    for k in range(n_stand):
        wobble = 0.0 if stand_still else rng.uniform(-20.0, 20.0)
        add_row(sc.STEP_STAND, [noise(), noise(), noise()], [noise() + wobble, noise() + wobble, noise() + wobble])

    for k in range(n_flex):
        w = 40.0 * math.sin(2 * math.pi * k / 20.0)  # oscillating about Z (femur still)
        add_row(sc.STEP_FLEX, [noise(), noise(), noise()], [noise(), noise(), w + noise()])

    half = n_rot // 2
    for k in range(half):
        w = 25.0 * math.sin(2 * math.pi * k / 15.0)  # oscillating about X
        add_row(sc.STEP_INT_ROT, [noise(), noise(), noise()], [w + noise(), noise(), noise()])
    for k in range(n_rot - half):
        w = 25.0 * math.sin(2 * math.pi * k / 15.0)
        add_row(sc.STEP_EXT_ROT, [noise(), noise(), noise()], [w + noise(), noise(), noise()])

    return cols


def test_femur_tibia_identity_and_axis_recovery():
    print("[test] synthetic clean calibration recovers known axes + femur/tibia identity")
    cols = _make_synthetic_cols()
    res = sc.compute(cols)
    check(res.segment_assignment["tibia_imu"] == 2, "imu2 (the mover) identified as tibia")
    check(res.segment_assignment["femur_imu"] == 1, "imu1 (the still one) identified as femur")

    fe = res.axes["flexion_extension"]["vector"]
    rot = res.axes["rotation"]["vector"]
    ab = res.axes["ab_adduction"]["vector"]
    check(abs(sc._dot(fe, [0.0, 0.0, 1.0])) > 0.98,
          f"flexion-extension axis recovered near true Z axis: {fe}")
    check(abs(sc._dot(rot, [1.0, 0.0, 0.0])) > 0.90,
          f"rotation axis recovered near true X axis: {rot}")
    check(abs(sc._dot(fe, rot)) < 1e-6, "flexion-extension and rotation axes orthogonal")
    check(abs(sc._dot(fe, ab)) < 1e-6, "flexion-extension and ab_adduction axes orthogonal")
    check(abs(sc._dot(rot, ab)) < 1e-6, "rotation and ab_adduction axes orthogonal")

    check(res.axes["flexion_extension"]["variance_explained"] > 0.9,
          f"flexion-extension variance_explained high: {res.axes['flexion_extension']['variance_explained']}")
    check(res.axes["rotation"]["variance_explained"] > 0.9,
          f"rotation variance_explained high: {res.axes['rotation']['variance_explained']}")
    check(res.quality_flags["calibration_confidence"] == "high",
          f"clean synthetic recording rated high confidence: {res.quality_flags['calibration_confidence']}")
    check(res.quality_flags["usable"] is True, "clean synthetic recording usable")


def test_stand_still_violation_flagged():
    print("[test] STAND-stage movement is flagged, not silently accepted")
    cols = _make_synthetic_cols(stand_still=False)
    res = sc.compute(cols)
    check(res.quality_flags["stand_still_ok"] is False,
          "stand_still_ok False when STAND rows show large gyro variance")
    check(any("WARNING" in n and "STAND" in n for n in res.notes),
          "a WARNING note calls out the STAND-stage issue")


def test_orthonormal_frame_helper():
    print("[test] orthonormal_frame() gives unit, mutually-orthogonal, right-handed axes")
    e1, e2, e3 = sc.orthonormal_frame([2.0, 0.0, 0.0], [1.0, 1.0, 0.0])
    for name, v in (("e1", e1), ("e2", e2), ("e3", e3)):
        check(abs(sc._norm(v) - 1.0) < 1e-9, f"{name} is unit length")
    check(abs(sc._dot(e1, e2)) < 1e-9, "e1 . e2 ~= 0")
    check(abs(sc._dot(e1, e3)) < 1e-9, "e1 . e3 ~= 0")
    check(abs(sc._dot(e2, e3)) < 1e-9, "e2 . e3 ~= 0")
    cross = sc._cross(e1, e2)
    check(all(abs(cross[i] - e3[i]) < 1e-9 for i in range(3)), "e1 x e2 == e3 (right-handed)")


def test_dominant_eigenvector_pure_single_axis():
    print("[test] dominant_eigenvector recovers a known pure-rotation axis with no noise")
    axis = sc._normalize([1.0, 2.0, -1.0])
    samples = [[w * axis[0], w * axis[1], w * axis[2]] for w in (10, -8, 6, -12, 9, -7)]
    m = sc.second_moment_matrix([s[0] for s in samples], [s[1] for s in samples], [s[2] for s in samples])
    v, _, variance_explained = sc.dominant_eigenvector(m)
    check(abs(sc._dot(v, axis)) > 0.9999, f"recovered axis matches known axis (dot={sc._dot(v, axis):.6f})")
    check(variance_explained > 0.9999, f"variance_explained ~= 1.0 for a pure single-axis signal: {variance_explained}")


def test_missing_calib_step_column_raises():
    print("[test] analyze_file rejects a regular trial CSV (no calib_step column)")
    try:
        sc.analyze_file(os.path.join(ROOT, "Jump_RL.csv"))
        check(False, "expected ValueError for a file with no calib_step column")
    except ValueError:
        check(True, "ValueError raised for a file with no calib_step column")


def main():
    for t in (test_femur_tibia_identity_and_axis_recovery, test_stand_still_violation_flagged,
              test_orthonormal_frame_helper, test_dominant_eigenvector_pure_single_axis,
              test_missing_calib_step_column_raises):
        t()
    print(f"\n{_checks - len(_failures)}/{_checks} checks passed.")
    if _failures:
        print("FAILED:")
        for f in _failures:
            print("  -", f)
        sys.exit(1)
    print("ALL PASS")


if __name__ == "__main__":
    main()
