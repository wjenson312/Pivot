# Sleeve Calibration Protocol — Establishing Cardinal Knee Axes Before Data Collection

**Cycle 2 proposal — Pivot wearable leg sleeve (dual IMU: femur + tibia)**
Author: Researcher (PivotTeam) · Date: 2026-07-01

## Why this is needed (the gap it closes)

Cycle 1 shipped an honest, working Knee Rotation Load Index, but it carries
three open items that a calibration step is the direct fix for
(`docs/cycle-1-direction.md` §6, `backend/knee_rotation_load.py` quality
flags, `docs/build-summary.md` line 179 — "relative-index-not-Nm framing
until a calibration path actually exists"):

1. **`segment_assignment: "UNVERIFIED"`** — which physical IMU (imu1/imu2) is
   femur vs. tibia is a hand-set `femur_imu` parameter, not measured.
2. **`dominant_axis`** is picked *after the fact*, per trial, as
   `max(axes, key=std)` (`knee_rotation_load.py:362`). It names whichever raw
   sensor channel happened to move most in *that* clip — not a fixed
   anatomical axis. Because the fabric sleeve can be donned at a different
   twist/tilt every session, "gz" in one trial and "gz" in another are not
   guaranteed to mean the same physical rotation.
3. **No anatomical zero.** The relative angle's "0°" is baseline-subtracted
   from each trial's own first 0.3 s (`knee_rotation_load.py:333-336`) —
   i.e. "wherever the leg happened to be when recording started," not
   "knee fully extended." ROM values are internally consistent but not
   comparable to a real anatomical reference.

None of this is a data-quality bug — it's a missing calibration step. The
IMUs have no magnetometer (`MPU6050_light`, complementary-filter accel+gyro
fusion only — see `bluetooth/*.ino`), so their raw X/Y/Z axes are fixed to
the chip package, not to the leg. Whatever direction the sleeve happens to
sit in when strapped on is the sensor's "X axis" that session. Cardinal knee
axes (flexion–extension, ab/adduction, internal–external rotation) must be
**derived empirically**, per session, from how the sensors actually move
during known reference motions — this is standard practice in IMU-based
joint kinematics, called **functional calibration** (as opposed to a
magnetometer/marker-based anatomical calibration, which this hardware can't
do).

## What movement is best for this, and why

The literature (largely already cited in this repo's own research brief,
`research/relative-tibial-femoral-rotation-rate.md`) converges on the same
answer: **don't try to calibrate all three axes at once — isolate one DOF at
a time with a slow, controlled, repeated movement, and let the sensor data
itself reveal the axis.** Concretely, a three-stage protocol.

The core math tool used below is **PCA/SVD** — Principal Component Analysis
via Singular Value Decomposition. PCA finds the direction along which a set
of vectors varies the most; here the vectors are angular-velocity samples
collected during a calibration movement, and the "most-varying direction" is
the physical rotation axis of that movement. SVD is simply the numerically
stable way to compute PCA (decomposing the sample matrix directly, rather
than building a covariance matrix first) — the two terms describe the same
step, "find the dominant rotation axis from the movement data."

### Stage 0 — Static neutral pose ("N-pose"), ~5 s
Subject stands still, knee fully extended, leg vertical, feet forward.
- Uses each IMU's accelerometer gravity vector as an absolute reference —
  the one direction the system *can* know without a magnetometer.
- Doubles as a gyro-bias recheck in situ (the firmware's `calcOffsets()`
  only runs once, at power-on on a bench — this repeats it with the sleeve
  actually worn, which is what matters).
- Defines the anatomical zero: "0° relative angle" becomes "knee fully
  extended," shared across every trial in the session, instead of each
  trial's own arbitrary starting posture.

### Stage 1 — Isolated flexion–extension, ~5–10 slow reps
Thigh held still, shank swings through a slow, controlled flexion–extension
arc (e.g. seated knee bend/extend, or standing non-weight-bearing leg
swing) — no rotation, no ab/adduction, full available ROM.
- This is the highest-value calibration movement: flexion–extension is the
  largest-ROM, easiest-to-voluntarily-isolate knee DOF, and it's exactly the
  approach validated in the literature this project already cites — Seel,
  Raisch & Schauer (2014, *Sensors*) derive the joint axis from gyroscope
  data during a functional movement rather than a magnetometer; Favre et al.
  (2009, *J Biomech*, "Functional calibration procedure for 3D knee joint
  angle description using inertial sensors") is the canonical version of
  exactly this protocol.
- Analysis: take `omega_rel(t) = omega_tibia(t) - omega_femur(t)` per axis
  through this movement (already what the pipeline computes) as an N×3
  matrix, and run PCA/SVD on it. The eigenvector of the largest eigenvalue
  *is* the empirical flexion–extension axis, expressed in the raw sensor
  frame — no assumption that raw "gz" already means anything anatomical.
  The fraction of variance explained by that first eigenvector is itself a
  built-in QC number (a clean hinge movement should put ≥~90% of the
  rotational energy on one axis).

### Stage 2 — Internal/external tibial rotation, ~5 oscillating cycles

Knee bent ~30–45°, thigh stabilized. Internal and external rotation are
`+`/`-` of the *same* physical axis (the tibia's long axis), so this is one
calibration, not two — but it runs as three distinct, individually
instructable sub-steps repeated in a loop, not one blended "twist" cue:

- **2a — Rotate internal.** Slowly rotate the shank to end-range internal
  rotation (toes turning inward).
- **2b — Return to neutral, pause.** Foot pointing straight ahead, hold
  briefly. This is not filler — the oscillation (2a/2c) gives PCA the axis
  *direction*, but not a "zero rotation" reference point along that axis.
  The neutral pause supplies that reference, the same role Stage 0's static
  extension pose plays for flexion.
- **2c — Rotate external.** Slowly rotate the shank to end-range external
  rotation (toes turning outward), then back through 2b to repeat.

Repeat 2a→2b→2c ~5 times. A static hold cannot calibrate this axis on its
own: PCA finds the axis from the *direction* of angular velocity over time,
and a hold produces ~zero gyro signal everywhere — there's no rotation to
extract an axis from. Oscillating both directions (rather than only
internal or only external) maximizes the angular-velocity amplitude PCA/SVD
has to work with, improving the variance-explained QC number.

This is the axis this project cares about most (the "Knee Rotation Load
Index" *is* this axis), and it's also the noisiest, least-validated one —
the project's own research brief flags transverse-plane IMU estimates as
more sensitive to sensor placement than sagittal ones (Cutti et al., 2010,
*Med Biol Eng Comput*). A dedicated functional calibration is the standard
mitigation for exactly that limitation, because it measures *this sleeve,
this session's* actual rotation axis rather than assuming the chip's Z axis
lines up with the tibia's long axis. Same PCA/SVD analysis as Stage 1, on
the tibia IMU's own angular velocity (not the relative signal) during 2a/2c.

### Ab/adduction axis — derived, not measured directly
Voluntary isolated ab/adduction (varus/valgus) is small-ROM and hard to
perform cleanly without also flexing or rotating, so don't try to calibrate
it with its own movement. Standard practice (Ehrig et al., 2007, *J
Biomech*, "A survey of formal methods for determining functional joint
axes") is to define it as orthogonal to the flexion–extension and rotation
axes via Gram-Schmidt / cross product, giving a right-handed, exactly
orthogonal frame from the two movements above.

### Bonus — femur/tibia identity, for free
Stage 1 already requires the thigh to stay still while the shank moves.
Whichever physical IMU (imu1/imu2) shows the larger gyro variance *during
that clip* is the tibia — resolving the `segment_assignment: "UNVERIFIED"`
flag automatically, per session, without relying on the tester remembering
to check physical labels on the sleeve.

## Practical protocol for the human tester

1. Record one CSV per session using the existing firmware/format (no
   firmware change needed — `bluetoothSync.ino` and
   `collectdata_dualIMU_BLE.ino` already log both IMUs' full acc+gyro/angle
   at their current sample rate).
2. Sequence within that file: ~5 s standing still (Stage 0) → 5–10 slow
   knee bends (Stage 1) → ~5 s pause → 5 slow shin twists at ~30–45° flexion
   (Stage 2). Keep each stage slow and controlled — fast/ballistic movement
   during calibration adds soft-tissue artifact noise to the axis estimate
   (Favre et al., 2009).
3. Tag the file as a calibration run (the frontend's `RunMetadata` in
   `frontend/lib/runs-registry.ts` already has a free-form `metadata` field
   reserved for exactly this kind of tag — no schema change needed).

### Recalibration cadence — per donning, not per user

Calibrate **once per session, immediately before that session's trials** —
not once ever per athlete. What this protocol measures isn't anything
intrinsic to the subject's knee; it's the rotational offset of the sensor
package relative to the limb *for that specific strap-on*. Nothing about a
fabric sleeve keys the chip's axes to a fixed anatomical landmark, so that
offset is different every time the sleeve goes on, even on the same leg for
the same athlete. This matches standard operating procedure for commercial
IMU mocap systems (Xsens MVN, APDM Opal, Noraxon myoMotion), which all
require a fresh N-pose + functional-movement calibration at the start of
every wearing session regardless of whether the subject wore the suit
yesterday.

The trigger for recalibrating is "has the sleeve been re-donned or
visibly shifted," not "is it a new calendar day" or "is it a new user":
- Always recalibrate after taking the sleeve off and putting it back on.
- Recalibrate mid-session if the sleeve is felt or seen to slip — a real
  risk during cutting/jumping trials with a fabric sleeve — rather than
  trusting a calibration from before the slip for trials recorded after it.
- A calibration does *not* need to be repeated between back-to-back trials
  within the same uninterrupted wearing (no removal, no noticeable
  movement) — one calibration file covers all trials in that continuous
  wear.

## Guided walkthrough sequence (for a step-by-step calibration UI)

The stages above map onto a wizard-style flow — one screen per step, each
with its own instruction line and illustration, similar in shape to the
existing `BleSyncPanel.tsx` flow. Internal rotation, the neutral pause, and
external rotation are three separate screens, not one combined instruction,
since each is a visually distinct pose the UI should show its own image for:

1. **Stand still** — image: figure standing straight, feet forward, weight
   even. "Stand still, knee straight, for 5 seconds." → Stage 0.
2. **Bend and straighten** — image: side view, shin swinging through a
   flexion arc with the thigh outline emphasized to cue "keep this part
   still." "Slowly bend and straighten your knee, keeping your thigh still.
   Repeat 5–10 times." → Stage 1.
3. **Rotate shin inward** — image: top-down view of the foot/shin turning
   inward, knee shown bent. "With your knee bent, slowly rotate your shin
   inward." → Stage 2a.
4. **Return to center, pause** — image: foot pointing straight ahead, a
   centered marker icon. "Return to center and hold." → Stage 2b.
5. **Rotate shin outward** — image: mirror of step 3, toes turning out.
   "Now slowly rotate your shin outward." → Stage 2c.
6. Steps 3→4→5 loop back to step 3 for ~5 cycles — the UI cycles through
   the same three screens repeatedly rather than treating each rep as a new
   step; one continuous BLE recording runs underneath the whole loop.
7. **Review** — show the calibration QC result plainly per axis (e.g. a
   green check "Calibration good" vs. a prompt to redo one specific step
   whose variance-explained came back low), rather than a single pass/fail
   for the whole sequence.

Implementation note: because this all rides on one continuous recording,
the UI needs to mark stage-boundary timestamps as the walkthrough advances
(e.g. write `t_stage_start`/`t_stage_end` alongside the CSV, or send a BLE
marker byte at each transition) so the backend calibration module knows
which rows belong to which step — the same "provenance over guessing"
principle already used for `channel_meaning`.

## Alternative / complementary ways to define the knee's cardinal axes

Functional (movement-based) calibration above is the practical choice for
this hardware, but other approaches are worth naming — either as validation
of the functional-calibration axes, or as future hardware/design directions:

- **Marker-based / optical motion capture as ground truth.** Palpate bony
  landmarks (femoral epicondyles, malleoli) and track them optically to
  define an anatomical frame directly, then compare the PCA-derived axes
  against it. This is how the cited literature *validates* functional
  calibration in the first place — useful as a one-time bench check, not a
  field method.
- **Add a magnetometer (9-DOF IMU, e.g. MPU9250-class).** Gives an absolute
  heading reference, so axes could be computed from known sensor-mounting
  geometry instead of purely from movement. Tradeoff: a magnetometer only
  works as a heading reference if it's actually reading Earth's field, and
  indoor training environments routinely aren't — steel gym equipment (racks,
  plates), rebar in floors/walls, and motors (treadmills, HVAC) add or bend
  the local field, and unlike gravity this distortion is *location-dependent*,
  so it changes as the athlete moves near equipment mid-session. The usual
  figure-8 device calibration only cancels distortion attached to the sensor
  itself (e.g. a metal snap on the sleeve) — it does not fix distortion from
  things fixed in the room. Net effect: not unusable indoors, but not
  trustworthy un-monitored either. **Raised as a possible future hardware
  direction (2026-07-01) but the transition plan needs more in-depth
  thought before committing** — not scoped further here; the functional
  (movement-based) calibration below is the near-term plan regardless.
- **Kinematic-constraint fitting from ordinary movement.** Seel, Schauer &
  Raisch (2012, cited below) fit the joint axis by assuming the knee is
  close to a 1- or 2-DOF hinge and solving for the axis that best explains
  *whatever* movement is already being recorded — a normal training rep,
  not a dedicated calibration clip. This is the most promising direction
  for eventually skipping a separate calibration step (see below).
- **Mechanical keying of the sleeve.** A rigid pocket, seam, or alignment
  mark that consistently orients the sensor board the same way relative to
  a bony landmark (patella, tibial tuberosity) every time it's donned.
  Doesn't eliminate the need to calibrate (soft tissue still shifts under
  the sleeve), but shrinks the offset calibration has to correct for and
  makes session-to-session estimates more consistent.
- **Camera cross-check.** This repo already has a standalone MediaPipe pose
  experiment (`app/bodyModel/pose_detector.py`, explicitly "not part of the
  IMU/Pivot pipeline" per the README). Not wired in today, but a phone
  camera recording the calibration movement alongside the IMUs is a cheap
  way to spot-check the PCA-derived axis against a markerless video
  estimate, without needing true optical mocap.

## Shortening/simplifying calibration later

- **Adaptive stopping instead of a fixed rep count.** Compute the PCA
  variance-explained metric incrementally as BLE data streams in, and stop
  each stage as soon as it crosses a confidence threshold (e.g. ≥90%)
  rather than always demanding 5–10 reps. A clean, well-executed set could
  finish a stage in 2–3 reps; a shaky one would keep prompting
  automatically. Same style of live detection the pipeline already does
  for `active_window_s`, just run online instead of post-hoc.
- **Kinematic-constraint self-calibration.** If the Seel et al. (2012)
  constraint-fitting approach above is implemented, the *dedicated*
  protocol could shrink to just Stage 0 (the static zero genuinely needs a
  deliberate still pose) — the rotation and flexion axes could instead be
  continuously refined in the background from ordinary training movement,
  with the explicit Stage 1/2 sequence kept only as an occasional accuracy
  check rather than a mandatory every-session step.
- **Mechanical keying turns full recalibration into a quick verify.** If
  the sleeve reliably re-dons in nearly the same orientation, most sessions
  would only need a short confirmation motion (Stage 0 + 2–3 knee bends) to
  check the previous session's stored axes still fit, falling back to the
  full 3-stage sequence only when that check fails.
- **Prior-informed confirmation.** Because the sensor board's mounting
  orientation in the sleeve pocket is roughly consistent by design, the
  system already has an approximate expected direction for each axis.
  Comparing a new session's PCA result against that expectation (instead of
  treating every axis as unknown from scratch) lets a good match
  short-circuit to "confirmed" quickly, reserving the full guided sequence
  for cases that fall outside the expected tolerance.

## Significance for the analysis pipeline

- **Turns three "configurable"/"UNVERIFIED" knobs into measured values.**
  `femur_imu`, `sign`, and `dominant_axis` are today hand-set or
  after-the-fact guesses (`knee_rotation_load.py:253-254`, `:362`,
  `:477-480`). A calibration profile makes them outputs of a controlled
  reference measurement instead, which is exactly the "provenance over
  guessing" discipline this codebase already applies to `channel_meaning`
  (`FILE_PROVENANCE` / `detect_channel_meaning_heuristic`).
- **Makes ROM and rotation numbers cross-trial and cross-session
  comparable.** `CONTRACT.md`'s "cross-trial comparability" section already
  requires this; right now the anatomical zero is trial-local. A shared
  N-pose zero fixes that.
- **Directly de-risks the project's own flagged weak point.** The research
  brief already rates transverse-plane (rotation) IMU estimates as more
  sensor-placement-sensitive than sagittal ones. A rotation-axis functional
  calibration is the literature's standard answer to that specific
  limitation — it matters most for the exact metric this project is built
  around.
- **No hardware or firmware changes required.** A calibration run is just
  another CSV in the same format; this is a new small backend analysis step
  (e.g. `backend/sleeve_calibration.py`, parallel to
  `knee_rotation_load.py`) that outputs a per-session calibration profile
  (rotation axes, femur/tibia assignment, zero-pose offset, PCA
  variance-explained QC numbers) which `analyze_file()` would consume
  instead of the current hand-set `femur_imu`/`sign` arguments.
- **QC number, not just a transform.** The variance-explained-by-first-
  eigenvector figure from Stages 1–2 is a natural new `quality_flags` entry
  (e.g. `calibration_axis_confidence`) — same "surface it, don't hide it"
  philosophy already used for `channel_meaning_confidence` and
  `drift_bounded`.

## Scope note

This is a **functional** calibration (axes derived from movement), not an
anatomical/marker-based one — there's no magnetometer or optical reference
to align to true North or a skin-marker skeleton. That means the resulting
axes are internally consistent and repeatable per session, but still framed
as *relative* (as the rest of Cycle 1's output already is) — not a claim of
absolute anatomical ground truth. This complements, not replaces, the
existing "relative index, not calibrated torque" framing.

## References

- Favre J, Aissaoui R, Jolles BM, de Guise JA, Aminian K (2009). Functional
  calibration procedure for 3D knee joint angle description using inertial
  sensors. *Journal of Biomechanics*, 42(14):2330–2335.
- Seel T, Raisch J, Schauer T (2014). IMU-based joint angle measurement for
  gait analysis. *Sensors*, 14(4):6891–6909.
- Seel T, Schauer T, Raisch J (2012). Joint axis and position estimation
  from inertial measurement data by exploiting kinematic constraints. *IEEE
  Conference on Control Applications*.
- Cutti AG, Ferrari A, Garofalo P, Raggi M, Cappello A, Ferrari A (2010).
  'Outwalk': a protocol for clinical gait analysis based on inertial and
  magnetic sensors. *Medical & Biological Engineering & Computing*,
  48(1):17–25.
- Ehrig RM, Taylor WR, Duda GN, Heller MO (2007). A survey of formal methods
  for determining functional joint axes. *Journal of Biomechanics*,
  40(9):2150–2157.
- Picerno P, Cereatti A, Cappozzo A (2008). Joint kinematics estimate using
  wearable inertial and magnetic sensing modules. *Gait & Posture*,
  28(4):588–595.
- Besier TF, Sturnieks DL, Alderson JA, Lloyd DG (2003). Repeatability of
  gait data using a functional hip joint centre and a mean helical knee
  axis. *Journal of Biomechanics*, 36(8):1159–1168.
- Grood ES, Suntay WJ (1983). A joint coordinate system for the clinical
  description of three-dimensional motions: application to the knee.
  *Journal of Biomechanical Engineering*, 105(2):136–144.
