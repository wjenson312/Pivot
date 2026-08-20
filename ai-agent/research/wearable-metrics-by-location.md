# Wearable-Measurable Athlete Metrics, Grouped by Sensor Location

Filtered from `athlete-training-metrics-reference.md` to metrics a body-worn device can capture. Groups are ordered by metric count (largest first); within each group, metrics are ranked from lowest hardware cost + implementation effort to highest. Each metric carries an **accuracy score (1-10)** — how faithfully current wearable hardware captures the metric compared to the gold-standard method (lab equipment, force plates, blood draws, etc.).

Excluded entirely: body composition (needs scales/imaging), blood/hormonal panels (needs lab draws), nutrition intake (needs logging), strength testing (needs external load/force plates), and cognitive testing (needs screens/software). Edge cases that are becoming wearable (glucose, lactate) are included under skin patches.

---

## 1. Wrist / Finger (watch, band, or ring) — 14 metrics

1. **Cadence (steps per minute)** — Accuracy 9/10 — Basic accelerometer step counting is a solved problem on every fitness band.
2. **Resting heart rate** — Accuracy 9/10 — Optical (PPG) sensors are excellent at rest, where motion artifact is minimal.
3. **Heart rate zones** — Accuracy 7/10 — Derived from live HR in software; accuracy inherits PPG's weakness during high-intensity, high-motion exercise.
4. **Heart rate recovery** — Accuracy 8/10 — Measured in the still minutes after effort stops, where PPG performs well.
5. **Sleep duration** — Accuracy 8/10 — Accelerometer + HR sleep/wake inference is reliable for total time, standard on consumer devices.
6. **Maximum heart rate** — Accuracy 6/10 — Same PPG sensor, but requires a true maximal effort and PPG degrades exactly then; chest straps do better.
7. **Total distance covered** — Accuracy 8/10 — Commodity GPS is solid outdoors over normal distances; struggles indoors and on tight cuts.
8. **Top speed (max velocity)** — Accuracy 6/10 — Consumer GPS sample rates smooth out brief sprint peaks; radar/timing gates remain the standard.
9. **Sleep quality/efficiency (stages)** — Accuracy 5/10 — Deep/REM staging from HR+motion only modestly agrees with polysomnography; treat as trend data.
10. **Heart rate variability (HRV) / resting HRV trend** — Accuracy 7/10 — Good at rest/overnight when beat detection is clean; unusable mid-exercise from the wrist.
11. **Body temperature trends** — Accuracy 6/10 — Skin temperature tracks deviation-from-baseline well but is not core temperature; useful directionally.
12. **Acceleration splits (0-10m, 0-20m)** — Accuracy 4/10 — Consumer wrist GPS lacks the sample rate to resolve short splits; timing gates are far superior.
13. **Swimming stroke rate / distance per stroke** — Accuracy 7/10 — Wrist IMU stroke detection is good for freestyle, weaker for stroke changes and open water.
14. **Estimated VO2 max** — Accuracy 5/10 — Modeled from HR-vs-pace over weeks; tracks trend direction but individual values can miss lab tests by ±10%.

---

## 2. Torso / Waist (chest strap, GPS vest pod, waistband clip) — 12 metrics

1. **Sprint count** — Accuracy 8/10 — Simple threshold counting on the speed stream; accuracy depends only on the threshold definition.
2. **High-speed running distance** — Accuracy 8/10 — Same speed stream bucketed above a threshold; 10 Hz pods handle this well.
3. **Number of accelerations/decelerations** — Accuracy 7/10 — Event counting is standard on team-sport pods, but counts vary meaningfully between vendors' algorithms.
4. **Time-motion analysis (walking/jogging/sprinting %)** — Accuracy 8/10 — Straightforward binning of a validated speed stream.
5. **Player load / acceleration load** — Accuracy 7/10 — Internally consistent and repeatable, but it's a proprietary composite with no external gold standard.
6. **Vertical jump height** — Accuracy 7/10 — Waist-IMU flight-time method reads ~1-2 cm off force-plate values; excellent for tracking change.
7. **Approach jump height / touch height** — Accuracy 7/10 — Same flight-time method applied to run-up jumps; slightly noisier due to lateral motion.
8. **Acute:chronic workload ratio (ACWR)** — Accuracy 8/10 — Pure arithmetic on load data; the accuracy bottleneck is wear compliance, not hardware.
9. **Training monotony and strain** — Accuracy 8/10 — Also pure software on the load history; accurate if the athlete wears the device consistently.
10. **Deceleration capacity** — Accuracy 6/10 — Resolving peak deceleration needs high-rate fused GNSS+IMU; consumer-grade hardware underestimates it.
11. **Total impacts/collisions** — Accuracy 5/10 — Impact detection works, but severity classification and false positives (e.g., hard landings vs. tackles) remain unreliable.
12. **Center of mass displacement** — Accuracy 4/10 — Pelvis-IMU estimates drift and are sensitive to mounting; motion capture is far superior.

---

## 3. Limb / Joint Sleeve or Strap (thigh, shank, upper arm, forearm) — 8 metrics

1. **Angular velocity of a joint or limb segment** — Accuracy 9/10 — A gyroscope measures this directly; it is the raw sensor output, not an inference.
2. **Joint range of motion (ROM)** — Accuracy 7/10 — Dual-IMU spanning the joint gets within a few degrees of goniometry when calibrated; soft-tissue motion is the error source.
3. **Knee/hip/shoulder rotation angles during activity** — Accuracy 6/10 — Dual-IMU relative orientation (SPK's core measurement) is good for flexion/extension but degrades for axial rotation, where soft-tissue artifact and drift bite hardest.
4. **Kinematic movement asymmetry** — Accuracy 7/10 — Left/right comparison benefits from error canceling across matched sensors; better than the absolute angles it's built from.
5. **Punch/strike force and speed** — Accuracy 5/10 — IMU peak acceleration/velocity correlates with strike quality but "force" is a modeled proxy, loosely validated.
6. **Landing mechanics (knee valgus, trunk lean)** — Accuracy 5/10 — Thigh+shank IMU valgus estimates capture gross patterns but miss the precision of 3D motion capture for frontal-plane angles.
7. **Arm/joint torque during throwing** — Accuracy 6/10 — Forearm-sleeve elbow-stress estimates (Motus-style) are validated enough for workload trending, not for absolute torque.
8. **Muscle activation timing/sequencing (surface EMG)** — Accuracy 6/10 — Timing/onset detection is decent; amplitude comparison is fragile due to skin contact, sweat, and electrode placement.

---

## 4. Foot (pod or instrumented insole) — 6 metrics

1. **Stride length and stride frequency** — Accuracy 8/10 — Foot-pod dead-reckoning per step is mature; frequency is near-perfect, length within a few percent.
2. **Ground contact time** — Accuracy 8/10 — Touchdown/toe-off detection from a foot IMU agrees closely with force-plate timing.
3. **Vertical oscillation** — Accuracy 7/10 — IMU double-integration per stride is good after calibration but drifts at extreme paces.
4. **Stride/gait symmetry** — Accuracy 8/10 — Bilateral pods comparing timing benefit from the same error-canceling as other symmetry metrics.
5. **Ground reaction force (GRF)** — Accuracy 6/10 — Pressure insoles estimate vertical force reasonably but miss shear forces entirely; force plates remain the standard.
6. **Joint loading rate** — Accuracy 5/10 — A modeled proxy from insole/IMU impact profiles; directionally useful, not a substitute for lab measurement.

---

## 5. Skin Patch / Biosensor — 5 metrics

1. **Core body temperature trend** — Accuracy 7/10 — Heat-flux patches (CORE-style) track core temp within ~0.2-0.3 °C of ingestible-pill reference under most conditions.
2. **Sweat rate / sweat sodium concentration** — Accuracy 6/10 — Microfluidic patches measure local sweat well, but extrapolating one site to whole-body loss adds error.
3. **Continuous glucose** — Accuracy 8/10 — CGM is mature, clinically validated medical technology; interstitial lag vs. blood is the main caveat during rapid exercise swings.
4. **Hydration status** — Accuracy 3/10 — Emerging bioimpedance/sweat approaches; little independent validation exists yet.
5. **Continuous blood lactate** — Accuracy 3/10 — Wearable lactate is still research-grade/pre-commercial; today's prototypes don't yet match finger-prick meters.

---

## 6. Head (mouthguard, headband) — 2 metrics

1. **Head impact count and severity** — Accuracy 7/10 — Instrumented mouthguards couple rigidly to the skull and are validated in rugby/football; false-positive filtering is the remaining challenge.
2. **Sleep staging (EEG headband)** — Accuracy 8/10 — Headband EEG approaches polysomnography agreement — far better than wrist staging — but nightly compliance is the practical limit.

---

## Reading for SPK

The limb/joint sleeve group (Section 3) is smallest in metric count but least commoditized — wrist and torso metrics are saturated markets (Garmin, Whoop, Catapult), while validated joint-angle, valgus, and torque measurement from sleeves remains an open opportunity. Notably, the axial rotation angle SPK targets scores 6/10 on current hardware largely due to soft-tissue artifact and drift — meaning calibration and mounting (per the hardware-upgrade strategy) is exactly where accuracy points are won. A sleeve platform can also absorb several foot-group metrics (contact time, symmetry) if a shank-mounted IMU is part of the system.
