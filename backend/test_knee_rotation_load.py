"""
Basic correctness / sanity tests for knee_rotation_load.

Run:  python3 backend/test_knee_rotation_load.py
Exits non-zero on failure; prints a PASS/FAIL summary.
Pure stdlib (no pytest dependency) so it runs anywhere.
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import knee_rotation_load as krl  # noqa: E402

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


def _finite(seq):
    return all((not math.isnan(x)) and (not math.isinf(x)) for x in seq)


def test_no_nan_inf_and_lengths():
    print("[test] no NaN/Inf; series lengths match timestamps")
    res = krl.analyze_file(os.path.join(ROOT, "MPU_BothIMUs_20251205_155322.csv"))
    n = len(res.timestamps)
    check(n > 0, "timestamps non-empty")
    check(_finite(res.timestamps), "timestamps finite")
    for name, arr in res.series.items():
        check(len(arr) == n, f"series '{name}' length == timestamps ({len(arr)}=={n})")
        check(_finite(arr), f"series '{name}' all finite")
    for k, v in res.summary_metrics.items():
        check(v is None or isinstance(v, str) or (not isinstance(v, float)) or _finite([v]),
              f"summary '{k}' finite/valid")


def test_contract_shape():
    print("[test] output matches CONTRACT.md shape")
    res = krl.analyze_file(os.path.join(ROOT, "MPU_BothIMUs_20251205_155322.csv"))
    d = res.to_dict()
    for key in ("method", "version", "source_file", "units", "timestamps",
                "series", "summary_metrics", "quality_flags", "notes"):
        check(key in d, f"top-level key '{key}' present")
    for k in ("primary_signal", "rotation_load_index", "dominant_axis",
              "peak_rel_rate_dps", "relative_knee_load_score",
              "range_of_motion_score", "peak_impact_g",
              "landing_mechanics_score", "knee_health_score"):
        check(k in res.summary_metrics, f"summary_metrics has '{k}'")
    for k in ("channel_meaning", "usable_motion", "segment_assignment",
              "n_samples", "femur_imu"):
        check(k in res.quality_flags, f"quality_flags has '{k}'")
    check(res.quality_flags["segment_assignment"] == "UNVERIFIED",
          "femur/tibia flagged UNVERIFIED")


def test_plausible_ranges_real_movement():
    print("[test] plausible magnitudes on real-movement file")
    res = krl.analyze_file(os.path.join(ROOT, "MPU_BothIMUs_20251205_155322.csv"))
    rom = res.summary_metrics["rom_deg"]
    idx = res.summary_metrics["rotation_load_index"]
    check(res.quality_flags["usable_motion"] is True,
          "MPU_BothIMUs detected as usable motion")
    check(res.quality_flags["channel_meaning"] == "euler_deg",
          "channel_meaning == euler_deg (provenance)")
    # a human knee ROM during deliberate motion: tens of degrees, well under 360
    check(rom is not None and 5.0 < rom < 360.0,
          f"ROM plausible (5..360 deg): {rom}")
    check(0.0 <= idx <= 100.0, f"index within 0..100: {idx}")


def test_static_file_flagged():
    print("[test] frozen/static trial flagged, not silently scored")
    for fname in ("Jump_RL.csv", "Anterior_Rotation_RL.csv",
                  "Posterior_Rotation_RL.csv", "Tibial_Translation_RL.csv"):
        res = krl.analyze_file(os.path.join(ROOT, fname))
        check(res.quality_flags["usable_motion"] is False,
              f"{fname}: usable_motion == False (no real movement)")
        check(res.summary_metrics["rom_deg"] is not None
              and res.summary_metrics["rom_deg"] < 5.0,
              f"{fname}: ROM near zero ({res.summary_metrics['rom_deg']} deg)")
        check(any("WARNING" in s for s in res.notes),
              f"{fname}: carries an explicit no-movement WARNING note")


def test_known_movement_direction():
    """
    Known-movement signature check. The labeled trials are dead data (frozen),
    so we use MPU_BothIMUs as the known dynamic recording: a real movement must
    produce a relative-angle excursion and a rate response far above the static
    trials' noise floor (~1 deg/s).
    """
    print("[test] dynamic file shows movement signature vs static noise floor")
    dyn = krl.analyze_file(os.path.join(ROOT, "MPU_BothIMUs_20251205_155322.csv"))
    stat = krl.analyze_file(os.path.join(ROOT, "Jump_RL.csv"))
    check(dyn.summary_metrics["peak_rel_rate_dps"]
          > 20 * max(stat.summary_metrics["peak_rel_rate_dps"], 1e-6),
          "dynamic peak rate >> static peak rate")
    check(dyn.summary_metrics["rom_deg"] > 10 * stat.summary_metrics["rom_deg"],
          "dynamic ROM >> static ROM")


def test_knee_health_score_real_movement():
    print("[test] Knee Health Score computed and weighted correctly on real movement")
    res = krl.analyze_file(os.path.join(ROOT, "MPU_BothIMUs_20251205_155322.csv"))
    sm = res.summary_metrics
    check(sm["relative_knee_load_score"] == sm["rotation_load_index"],
          "relative_knee_load_score mirrors rotation_load_index (already 0-100)")
    check(0.0 <= sm["range_of_motion_score"] <= 100.0,
          f"range_of_motion_score within 0..100: {sm['range_of_motion_score']}")
    check(sm["peak_impact_g"] is not None and sm["peak_impact_g"] >= 0.0,
          f"peak_impact_g is a non-negative g value: {sm['peak_impact_g']}")
    check(sm["landing_mechanics_score"] is not None and 0.0 <= sm["landing_mechanics_score"] <= 100.0,
          f"landing_mechanics_score within 0..100: {sm['landing_mechanics_score']}")
    check(sm["knee_health_score"] is not None and 0.0 <= sm["knee_health_score"] <= 100.0,
          f"knee_health_score within 0..100: {sm['knee_health_score']}")
    expected = (
        krl.KNEE_HEALTH_WEIGHT_LOAD * sm["relative_knee_load_score"]
        + krl.KNEE_HEALTH_WEIGHT_ROM * sm["range_of_motion_score"]
        + krl.KNEE_HEALTH_WEIGHT_LANDING * sm["landing_mechanics_score"]
    )
    check(abs(sm["knee_health_score"] - round(expected, 2)) < 0.02,
          f"knee_health_score matches the weighted formula: {sm['knee_health_score']} ~= {expected:.2f}")


def test_knee_health_score_null_on_dead_data():
    print("[test] Knee Health Score is null (not silently scored) on frozen/no-motion trials")
    for fname in ("Jump_RL.csv", "Anterior_Rotation_RL.csv",
                  "Posterior_Rotation_RL.csv", "Tibial_Translation_RL.csv"):
        res = krl.analyze_file(os.path.join(ROOT, fname))
        sm = res.summary_metrics
        check(sm["landing_mechanics_score"] is None,
              f"{fname}: landing_mechanics_score is null (accel frozen)")
        check(sm["knee_health_score"] is None,
              f"{fname}: knee_health_score is null (a required sub-score is missing)")
        check(sm["relative_knee_load_score"] is not None and sm["range_of_motion_score"] is not None,
              f"{fname}: the other two sub-scores still compute (near-zero, not null)")


def test_unwrap_helper():
    print("[test] Euler unwrap removes the +-180 wrap")
    wrapped = [170.0, 175.0, -179.0, -174.0]   # crosses +180 -> -180
    unw = krl.unwrap_deg(wrapped)
    diffs = [abs(unw[i] - unw[i - 1]) for i in range(1, len(unw))]
    check(all(d < 90 for d in diffs),
          f"no >90 deg jumps after unwrap: {[round(d,1) for d in diffs]}")


def main():
    for t in (test_no_nan_inf_and_lengths, test_contract_shape,
              test_plausible_ranges_real_movement, test_static_file_flagged,
              test_known_movement_direction, test_knee_health_score_real_movement,
              test_knee_health_score_null_on_dead_data, test_unwrap_helper):
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
