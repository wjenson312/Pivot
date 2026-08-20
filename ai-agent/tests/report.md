# Pivot — Test Report

<!-- Each agent appends only its own section. Do not overwrite others' entries. -->

## Backend — Relative Tibial-Femoral Knee Motion (cycle 1)

Test: `backend/test_knee_rotation_load.py` (pure stdlib, no deps).
Run: `python3 backend/test_knee_rotation_load.py`

### 2026-06-19 — PASS (67/67 checks)
- No NaN/Inf in timestamps or any series; all series lengths == timestamps len.
- Output conforms to CONTRACT.md shape (top-level keys, required summary_metrics
  + quality_flags present; femur/tibia flagged UNVERIFIED).
- Real-movement file MPU_BothIMUs_20251205_155322.csv: ROM 148.8 deg (plausible),
  index within 0..100, usable_motion=true, channel_meaning=euler_deg (provenance).
- Known-movement direction: dynamic file peak rate and ROM >> static trials' noise floor.
- Frozen/static detection: all four labeled trials (Jump, Anterior, Posterior,
  Tibial) flagged usable_motion=false, ROM < 0.5 deg, with no-movement WARNING note.
- Euler unwrap helper removes the +-180 deg discontinuity.

NOTE (Human Tester): the four labeled cycle-1 trial CSVs contain no usable
movement (whole-file frozen accel; angle channels vary <0.5 deg) — likely the
BLE-init freeze (commit 657b146) over the whole capture. Flagship metric is
demonstrated on MPU_BothIMUs_20251205_155322.csv; labeled trials need
re-collection. See backend/knee_rotation_load_REPORT.md.
NOTE: index pegs at 100 for MPU_BothIMUs (ROM 148.8 vs 90 deg ref) — expected;
REF_ROM_DEG retunable once more real trials exist.

## Frontend — Knee Rotation Load dashboard tab (cycle 1)

Test: `frontend/tests/smoke.test.mjs`. Run: `npm test` from `/frontend`.

### 2026-06-20 — PASS
- App builds clean: `npx next build` compiles all 3 routes with no type errors.
- Methods registry has a `ready: true` method (knee-rotation-load).
- Route file exists and renders the shared `MethodTab` template.
- `MethodTab` contains the 3 required sections in order: Researcher's plain-language content, Backend's chart(s), Backend's method report.
- Chart receives non-empty data: loader reads `/backend/outputs/MPU_BothIMUs_20251205_155322.knee_rotation_load.json` (939 samples, real motion) as the default trial.
- Dev server confirmed serving at http://localhost:3000: `/` redirects to `/methods/knee-rotation-load`, 200, full tab renders with real Backend data.

Notes: default-trial selection prefers the one usable_motion=true file over an alphabetically-first dead-data trial, with fallback chain documented in lib/load-method-output.ts. channel_meaning/confidence resolution fails safe to the lower-confidence interpretation. Honesty caveats (relative-index/no-Nm, unverified femur/tibia mapping, accel-frozen, low-confidence derived rate) render as a persistent banner. No cross-trial cumulative comparison shown.
