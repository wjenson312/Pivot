# Hardware Upgrade Strategy — Improving Data Quality at the Source

**Cycle 2 research — Pivot wearable leg sleeve**
Author: Researcher (PivotTeam) · Date: 2026-07-01

## Purpose

Cycle 1 squeezed a genuinely useful, honestly-framed Knee Rotation Load
Index out of the cheapest possible sensing stack. The recently-built
functional sleeve calibration (`research/sleeve-calibration-protocol.md`,
`backend/sleeve_calibration.py`) closes the *software* gap — it derives
anatomical axes per session from movement. But it is a workaround for a
**hardware** limitation: the sensors have no absolute orientation reference,
mediocre gyros, and a sleeve that shifts on soft tissue. This document
ranks the hardware changes that would improve the raw data itself — ordered
by *impact-per-effort*, not by how exciting they sound — and ties each one
to a concrete effect on the backend pipeline.

The headline conclusion up front, because it reframes the question:

> **A magnetometer is not the highest-value upgrade, and GPS is not
> relevant to defining knee axes at all.** The single best orientation
> upgrade is a self-fusing IMU (BNO08x class) using its *non-magnetometer*
> drift-corrected rotation vector. And the biggest data-quality lever of
> all is not the chip — it's **mounting stability and soft-tissue artifact**,
> which corrupts data upstream of whatever sensor you choose.

## Current hardware baseline (what we're improving on)

| Item | Current | Consequence for the data |
|---|---|---|
| IMU | 2× **MPU6050**, 6-DOF (accel + gyro, **no magnetometer**) | No absolute heading; yaw integrates gyro → **drifts**. Axes fixed to chip package, not the leg. |
| Fusion | `MPU6050_light` complementary filter | Pitch/roll gravity-referenced & bounded; **yaw unreferenced & drifting**. |
| Gyro grade | Consumer-grade (high bias instability, temp-sensitive) | Integration drift; bias re-estimated only once at power-on (`calcOffsets()`). |
| Bus / sync | Both IMUs on one I²C bus via **TCA9548A mux**, read sequentially | Small but real **inter-sensor timing skew** in `omega_tibia − omega_femur`. |
| Rate | ~100 Hz (10 ms loop), I²C @ 100 kHz | Fine for gross knee motion; **marginal for impact/landing** transients. |
| Mount | Fabric sleeve, no keying | **Soft-tissue artifact (STA)** — sensor moves relative to bone. Dominant real-world error. |
| Board | Arduino MKR WiFi 1010 (SAMD21) + SD + BLE | Adequate; not the bottleneck. |

Everything below is scored against this baseline.

---

## Tier 1 — Highest leverage

### 1. Self-fusing IMU (BNO08x), using the *game rotation vector*

This is the recommendation. The **Bosch BNO085 / BNO086** (and the older
BNO055) run Bosch's proprietary sensor fusion *on the chip* and output a
ready-made orientation quaternion over I²C — no Madgwick/Mahony filter to
tune on the SAMD21, no per-axis integration in our code.

The crucial detail that most people miss, and the one that resolves the
whole "magnetometers don't work indoors" objection from
`sleeve-calibration-protocol.md`:

- The BNO08x exposes **multiple** orientation outputs. The
  **Game Rotation Vector** is a 6-DOF fusion (accel + gyro) that is
  **gyro-drift-corrected but deliberately ignores the magnetometer**. It
  gives a *stable, low-drift* relative orientation that does **not** depend
  on Earth's magnetic field — so it is immune to steel racks, plates, rebar,
  and motors. This is the best of both worlds for indoor training: it fixes
  the MPU6050's yaw-drift problem *without* inheriting the indoor-magnetic
  problem.
- The full **Rotation Vector** (mag-referenced, absolute heading) and
  **Geomagnetic Rotation Vector** remain available for outdoor/field use or
  as a cross-check — so we get the magnetometer path *optionally*, not
  mandatorily.

**Effect on the pipeline:**
- Kills the drift that forces the current per-trial baseline-zeroing
  (`knee_rotation_load.py` local 0.3 s baseline). Orientation becomes
  session-stable → `rel_angle_*` series become genuinely comparable across
  a session, satisfying `CONTRACT.md`'s "cross-trial comparability" goal at
  the source rather than by post-hoc normalization.
- The functional sleeve calibration **still applies and still adds value**
  (it maps the sensor frame to the *anatomical* frame — the chip still
  isn't glued to the tibia's long axis). But calibration inputs get cleaner:
  the game-rotation quaternion gives a low-noise, drift-free basis to run
  the PCA/SVD axis extraction on, raising `variance_explained` and letting
  us shrink rep counts (the "adaptive stopping" idea in the protocol doc).
- `drift_bounded` / `drift_residual_dps` quality flags move from
  "carefully argued" to "structurally true."

**Cost/effort:** ~$10–20/sensor (vs ~$3 MPU6050). Same 3.3 V I²C, drops
onto the existing TCA9548A mux. Main firmware work: swap `MPU6050_light`
for a BNO08x driver (Adafruit/SparkFun/Ceva SH-2) and log quaternions.
**This is the recommended near-term hardware bet.**

### 2. Mounting stability & soft-tissue-artifact reduction (near-zero BOM cost)

The uncomfortable truth in the IMU-kinematics literature: **soft-tissue
artifact is usually the dominant error term, larger than sensor noise.** A
$20 IMU rigidly coupled to the segment beats a $200 IMU flopping on a loose
sleeve. This is the cheapest "sensor" upgrade because it's not a sensor:

- **Rigid sensor pocket + mechanical keying** (already floated in the
  protocol doc): a stiff shell over a bony prominence — tibial tuberosity /
  anteromedial tibia for the shank, lateral femoral condyle region for the
  thigh — orients the board consistently *and* reduces jiggle. This both
  shrinks what calibration must correct and improves every raw sample.
- **Placement over bone, not muscle belly.** The anteromedial tibial shaft
  is nearly subcutaneous → very low STA. The thigh is the hard part (thick
  muscle); a firmer strap and distal-lateral placement help.
- **Compression + anti-migration silicone grip bands** to stop the slip
  that the protocol doc already calls out as a mid-session recalibration
  trigger.

**Effect on the pipeline:** reduces high-frequency STA noise on *every*
axis and every trial, improves the `usable_motion` / axis-`variance_explained`
QC numbers, and makes session-to-session calibration more repeatable.
Do this **regardless** of which chip we pick — it multiplies the value of
any sensor upgrade.

### 3. Better gyroscope grade (lower bias instability)

If we stay 6-DOF (or alongside the BNO08x), the gyro *quality* matters more
than adding a magnetometer for our integrate-angular-velocity pipeline.
Modern parts dramatically out-spec the MPU6050:

- **TDK ICM-42688-P** — very low noise/bias instability, 6-DOF, cheap,
  drop-in I²C/SPI. Excellent value.
- **ST ISM330DHCX** — industrial 6-DOF, on-chip machine-learning core &
  good temp stability.
- (Aspirational / overkill: ADIS16xxx industrial IMUs — tactical-grade
  bias stability, but $100s and bulky. Named only to bracket the range.)

**Effect:** lower gyro-integration drift and cleaner `omega_rel`, directly
improving both the calibration axis estimates and the per-trial rate/angle
signals. Pairs naturally with in-situ, temperature-aware bias re-estimation
(the sleeve calibration already re-measures `gyro_bias` per session — good;
periodic re-zeroing during quiet windows would extend that).

---

## Tier 2 — High value, more integration work

### 4. Add real load sensing (force), not just a "load index"

The product is framed around *load*, but today there is **no force
measurement anywhere** — the "Load Index" is a kinematics proxy
(`CONTRACT.md`: "NOT a calibrated joint torque… NOT an injury probability").
The single biggest step toward the product's actual claim is to measure
force:

- **Instrumented insole / FSR or capacitive pressure array** in the shoe →
  ground reaction force timing & magnitude, stance detection, impact peaks.
- Combined with the IMU kinematics, this is what lets a *load* estimate
  become physically grounded (kinematics × kinetics), and gives the planned
  **Jump-impact** method (`docs/build-summary.md`) a real impact signal
  instead of an accel transient.

**Effect on the pipeline:** enables an entirely new true-signal method
under the same `CONTRACT.md` shape (new `series` like `grf_*`, new
`summary_metrics`), and lets existing metrics be gated on ground contact
(swing vs stance). This is additive to, not a replacement for, the IMU work.

### 5. Hardware time-synchronization between the two IMUs

`omega_rel = omega_tibia − omega_femur` is a *difference* of two sensors;
any timing skew between them injects error that grows with motion speed —
exactly during the fast cutting/jumping trials that matter most. Options:

- Sensors with a shared **sample clock / external FSYNC** latched from one
  timer, or read both truly simultaneously rather than sequentially through
  the mux.
- Or move to two IMUs on **separate I²C buses / SPI chip-selects** read
  back-to-back with timestamped samples, minimizing skew.

**Effect:** tightens the relative signal at high angular rates; improves
the rotation-axis calibration (whose whole premise is the *relative* omega)
and the peak-rate metrics. Lower glamour, real accuracy gain.

### 6. Higher sample rate + proper anti-alias filtering for impacts

100 Hz is fine for gross flexion but under-samples landing/impact
transients. For the Jump-impact method, raise the accel path to ~≥400–1000 Hz
with a correctly-set digital low-pass (DLPF) to avoid aliasing sharp impacts
into garbage. Keep the kinematics path at ~100–200 Hz. Modern IMUs (ICM-42688,
BNO08x) support this comfortably.

**Effect:** unlocks credible impact-magnitude features; prevents aliasing
artifacts that would otherwise masquerade as signal.

---

## Tier 3 — Complementary sensing (bigger scope, later)

- **Flexible bend sensor / soft goniometer across the knee.** A cheap
  resistive/capacitive flex strip gives a *direct* flexion angle that is
  drift-immune by construction — an independent ground-truth channel to
  validate and de-drift the IMU flexion axis. Great cross-check, cheap.
- **Third IMU on the foot** → full shank-foot-thigh chain, a cleaner
  external reference for tibial rotation, and true gait segmentation.
- **Surface EMG** on quads/hamstrings → muscle activation timing; turns a
  kinematic story into a neuromuscular one. Higher complexity, noisy on a
  moving athlete, later-stage.
- **Redundant IMUs per segment** (2 per segment, averaged) → statistically
  suppresses STA. Costs board space/power; a research-grade move.

---

## Soft-tissue artifact, ligament-load inference, and the tibial-translation question

### A surface wearable infers ligaments — it never measures them directly

A sleeve IMU is not attached to bone, and certainly not to a ligament. It is
attached to the **skin/sleeve surface**, and everything anatomical is
*inferred* from that surface motion:

```
skin/sleeve motion  →(STA error enters HERE)→  bone-segment motion
  →  relative femur/tibia kinematics  →  inferred ligament load
```

Ligaments (ACL, MCL, …) are internal bone-to-bone structures; a wearable
"sees" them only through the relative position/orientation of the two bones
they span (e.g. ACL strain rises with anterior tibial translation + internal
tibial rotation). **Soft-tissue artifact (STA) — the relative motion between
the skin-mounted sensor and the underlying bone — is injected at the very
first arrow, upstream of any ligament inference. Targeting ligaments does not
avoid it; if anything it makes STA more damaging**, because ligaments engage
over tiny ranges (a few degrees / a few millimetres), so the STA noise is the
same size as — or larger than — the signal. This is why mounting stability
(Tier 1 §2) is not just about clean angles: it is the gate on whether any
ligament-load claim is credible at all. And even with perfect mounting, a
surface wearable *infers* rather than *measures* ligament load, so the
Cycle-1 "relative proxy, not calibrated ground truth" framing must extend to
any ligament metric.

### Can STA be reduced enough to measure tibial translation? — the honest verdict

**Short answer: no — not to a clinically meaningful, absolute millimetre
scale during dynamic movement, with any surface-mounted method, IMU or
marker.** The numbers make this unambiguous:

| Quantity | Magnitude | Source |
|---|---|---|
| Signal we'd need to resolve (ATT: ACL-deficient side-to-side diff.) | **≥3 mm** diagnostic; <3 mm is "normal" | KT-1000 clinical thresholds |
| Skin-marker **translational** error vs bone pins, walking | **up to ~13 mm** | Benoit et al. 2006 (in-vivo bone pins) |
| Skin-marker translational error vs bone pins, **cutting** | **up to ~16 mm** | Benoit et al. 2006 |
| Raw skin motion relative to bone (thigh / shank) | **up to ~30 mm / ~15 mm** | Peters et al. 2010 (systematic review) |

The STA translational error (~13–16 mm dynamic) is **3–5× the entire clinical
signal** (~3 mm). Worse, the clinical measurement is a *quasi-static* pull at
a fixed low load with the knee at ~30° (Lachman position); dynamic sport
movement — cutting, landing — is the *worst case* for STA, exactly where the
error peaks. On top of that, an **IMU is a doubly bad instrument for
translation specifically**: getting position from an IMU means
double-integrating acceleration, whose error grows unbounded with time (drift)
— IMUs are orientation sensors, not position sensors. So "tibial translation
from a sleeve IMU" stacks STA *and* integration drift against a 3 mm target.

### STA-minimization methods, ranked by cost/effort vs error reduction

Ranked for a wearable-IMU context. Note the ceiling: these meaningfully
improve **rotational** kinematics (which is what your rotation-axis metric
needs), but **none recovers true millimetre bone translation** from a surface
sensor.

**Tier A — cheap, largest real reduction (do these):**
1. **Place the sensor over the anteromedial tibial shaft (subcutaneous
   bone).** Near-zero cost, biggest single win. The shank already has roughly
   half the STA of the thigh (~15 vs ~30 mm), and the anteromedial tibial
   crest is nearly skin-on-bone — the lowest-STA real estate on the lower
   limb. This is a placement decision, not a purchase.
2. **Rigid, keyed, pre-tensioned mounting** (stiff shell/cluster, tight strap,
   silicone anti-migration grip). The systematic-review finding is that
   **most STA is a near-rigid transformation of the sensor mount, not
   soft-tissue *deformation***; the non-rigid part contributes little error.
   That means the dominant error is the whole sensor rocking/sliding as a
   unit — which firm, rigid, pre-tensioned coupling directly attacks. Also
   cheap; design-time effort only.

**Tier B — moderate software effort, helps rotation, not translation:**
3. **Functional / double anatomical calibration** (your existing
   `sleeve_calibration.py` plus a neutral re-zero). Reduces *orientation*
   error and axis misalignment; does nothing for absolute translation.
4. **Multibody kinematic optimization (MKO) with joint constraints.**
   Enforces a knee model to reject non-physiological motion; **improves
   rotational estimates but does not recover true bone translation, and
   badly-chosen constraints can *inject* joint-centre/kinetic error**
   (Richard et al.; Gasparutto et al.). Medium effort, rotation-only benefit.

**Tier C — high effort, low marginal return for a field wearable:**
5. **STA field-modelling/compensation** (PCA-mode, affine, Kriging/RBF).
   Because the non-rigid component is small (per the review), these buy
   little beyond good rigid placement, and they need a per-subject reference
   to train against — impractical in the field.

**Tier D — the only thing that actually measures translation (not a field
method):**
6. **A reference modality: biplanar fluoroscopy / dynamic RSA, dynamic MRI,
   or intracortical bone pins.** These *do* resolve millimetre tibiofemoral
   translation, and are how the STA literature above was even quantified.
   Use one **once, as ground truth** to validate/bound the wearable — never
   as the wearable itself. (A quasi-static instrumented arthrometer, e.g.
   KT-1000-class, is the clinical middle ground, but it is a bench test, not
   a dynamic in-sleeve measurement.)

### What this means for the roadmap

- **Absolute tibial translation from the sleeve is not a credible Cycle-2
  deliverable.** Don't promise millimetre ATT from a surface IMU.
- **Credible reframes** if ACL-relevant information is the goal: (a) detect
  the *timing/rate* of a dynamic laxity event (e.g. a pivot-shift-like jerk)
  rather than its absolute magnitude — event detection tolerates the
  translation error that magnitude estimation cannot; (b) a **quasi-static,
  controlled in-sleeve laxity test** (low-load, near-static, over subcutaneous
  tibia) where STA and integration drift are minimized, reported as a
  *relative asymmetry index* between limbs, not an absolute millimetre; (c)
  validate any such proxy once against a Tier-D reference before making a
  claim. All three keep the honest "relative proxy" framing.

---

## GPS: honest assessment — not for axes

The prompt raises GPS alongside the magnetometer, so to be explicit:

- **GPS cannot define knee axes.** It gives *position* at meter-scale
  accuracy and ~1–10 Hz — orders of magnitude too coarse (both spatially
  and temporally) to say anything about a limb segment's *orientation* or a
  joint's rotation axis. It measures where the athlete is on the field, not
  how the shin is rotating. Even RTK-GPS (cm-level) tracks a point, not an
  orientation, and needs a base station.
- **Where GPS *could* add value — separately:** whole-athlete context —
  sprint speed, distance covered, acceleration/deceleration load, field
  heat-maps, session external-load (the "GPS unit" metrics used in team
  sports like Catapult/STATSports vests). That's a *different product
  surface* (session load & positioning), not an input to the knee-axis /
  joint-kinematics pipeline, and it should not be conflated with the
  orientation problem this document is about.

Bottom line: shelve GPS for the biomechanics pipeline; revisit only if the
product later wants team-sport external-load context.

---

## Magnetometer: the in-depth verdict (previously deferred)

Earlier this was flagged "needs more in-depth thought before committing"
(`memory/magnetometer-upgrade-direction.md`). Here is that thought:

**A raw magnetometer (9-DOF part like MPU9250/ICM-20948/LSM9DS1) is a
qualified *no* as the primary axis reference, for indoor training** — the
distortion mechanics in the protocol doc stand: hard-iron (steel plates,
racks), soft-iron (field-bending metal), motor/EMI sources, and critically
*location-dependence* (the distortion changes as the athlete moves through
the gym), which the standard figure-8 device calibration cannot fix because
it only cancels sensor-attached distortion, not room-fixed sources.

**But the conclusion is not "avoid magnetometers" — it's "don't depend on
them, and don't consume them raw":**

1. **Prefer on-chip fusion that treats the magnetometer as optional
   (BNO08x, Tier 1).** Its game-rotation-vector ignores the magnetometer
   entirely for a drift-free indoor solution, while still *offering* the
   mag-referenced absolute heading when the environment is clean (outdoor
   field work, rehab clinic). We get the upside without betting the pipeline
   on it.
2. **If a magnetometer is present, gate it on a live magnetic-disturbance
   check.** Good AHRS stacks (and the BNO08x itself) expose a magnetic
   "disturbance detected" / calibration-accuracy status; the BNO08x
   temporarily de-weights the magnetometer when the field looks wrong. The
   backend should *record that status per sample* and refuse to trust
   absolute-heading-derived quantities when disturbance is flagged — same
   "surface confidence, don't hide it" discipline as
   `channel_meaning_confidence`.

So: **magnetometer as an opportunistic, self-validating cross-check inside a
fusion chip — yes. Magnetometer as the load-bearing indoor axis reference —
no.**

## How to make the eventual swap clean (design the contract now)

Per the standing note to design the hardware-swap contract early
(`memory/magnetometer-upgrade-direction.md`), the backend should be shaped
so a Tier-1 sensor change is additive, not a rewrite:

- **Keep the CSV/loader schema orientation-source-agnostic.** Add optional
  quaternion columns (`imuN_qw,qx,qy,qz`) that `imu_common.load_csv`
  tolerates when present and ignores when absent — exactly the pattern
  already used for the optional `calib_step` column. Old 6-DOF files keep
  working.
- **Record the orientation provenance explicitly.** Extend the
  `channel_meaning` idea to an orientation source tag
  (`gyro_only` | `complementary` | `bno_game_rv` | `bno_rv_mag`), plus a
  per-sample magnetic-disturbance/accuracy status when available. Methods
  branch on provenance instead of guessing — the same discipline
  `FILE_PROVENANCE` already applies.
- **Route everything through `imu_common`.** `apply_calibration()` already
  projects raw `[gx,gy,gz]` onto anatomical axes; a quaternion source just
  feeds it a cleaner orientation. Future methods keep importing the one
  shared primitive, so the sensor upgrade touches the loader + firmware, not
  every analysis method.

This way the BNO08x upgrade is: new firmware + a few optional columns + one
new provenance tag — with the calibration math, the contract, and every
existing trial file untouched.

## Recommendation (what to actually do, in order)

1. **Mounting/keying + placement-over-bone** — near-zero cost, improves
   *all* existing and future data immediately. Do this first, this cycle.
2. **Prototype one BNO085** on the existing mux, log the game-rotation
   vector alongside the current MPU6050 stream, and A/B the drift and the
   calibration `variance_explained` numbers on real recordings. Cheap,
   decisive experiment.
3. **Add optional quaternion columns + orientation-provenance tag** to the
   loader/firmware so the swap is contract-clean before committing.
4. **Then** decide Tier-2 (force insole for real load; inter-IMU sync;
   impact-rate path) based on which analysis method Cycle 2 prioritizes.
5. **GPS: not on this roadmap** for the biomechanics pipeline.

## References

- Madgwick SOH, Harrison AJL, Vaidyanathan R (2011). Estimation of IMU and
  MARG orientation using a gradient descent algorithm. *IEEE ICORR*.
- Sabatini AM (2011). Estimating three-dimensional orientation of human body
  parts by inertial/magnetic sensing. *Sensors*, 11(2):1489–1525.
- Seel T, Raisch J, Schauer T (2014). IMU-based joint angle measurement for
  gait analysis. *Sensors*, 14(4):6891–6909.
- Cutti AG, et al. (2010). 'Outwalk': inertial-and-magnetic gait protocol.
  *Med Biol Eng Comput*, 48(1):17–25. (Documents the magnetic-sensor
  sensitivity this doc weighs against.)
- Leardini A, et al. (2005). Human movement analysis using stereophotogram-
  metry Part 3: soft tissue artifact assessment and compensation. *Gait &
  Posture*, 21(2):212–225. (STA as a dominant error source.)
- Benoit DL, Ramsey DK, Lamontagne M, Xu L, Wretenberg P, Renström P (2006).
  Effect of skin movement artifact on knee kinematics during gait and cutting
  motions measured in vivo. *Gait & Posture*, 24(2):152–164. (Bone-pin vs
  skin-marker: translational error up to ~13 mm walking / ~16 mm cutting.)
- Peters A, Galna B, Sangeux M, Morris M, Baker R (2010). Quantification of
  soft tissue artifact in lower limb human motion analysis: a systematic
  review. *Gait & Posture*, 31(1):1–8. (Thigh ≤~30 mm, shank ≤~15 mm skin
  motion; rotation errors up to ~35°.)
- Camomilla V, Dumas R, Cappozzo A (2017). Human movement analysis: the soft
  tissue artefact issue. *Journal of Biomechanics*, 62:1–4 (and the
  associated STA special-issue review series). (Most STA is a near-rigid
  cluster transformation; non-rigid deformation contributes little.)
- Richard V, Cappozzo A, Dumas R (2017); Gasparutto X, et al. (2015). Multibody
  kinematic optimization / subject-specific knee models for STA compensation —
  improves rotational estimates but can inject joint-centre/kinetic error and
  does not recover true bone translation. *Journal of Biomechanics*.
- KT-1000 arthrometer clinical thresholds for anterior tibial translation:
  side-to-side difference <3 mm normal, ≥3 mm indicative, >5 mm diagnostic of
  ACL deficiency (clinical arthrometry literature).
- Bosch Sensortec, *BNO080/085 Datasheet & SH-2 Reference Manual* — Game
  Rotation Vector (magnetometer-independent) vs Rotation Vector
  (magnetometer-referenced) output modes.
