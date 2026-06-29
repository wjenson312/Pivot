# Critique — /research/relative-tibial-femoral-rotation-rate.md

Reviewed 2026-06-19. Overall: STRONG and honest. Evidence labels are mostly well-calibrated,
relative-vs-calibrated is repeatedly stated, modality/joint/population transfer is flagged.
Below are the items I pushed back on (sent to Researcher via SendMessage).

## ISSUE 1 (HIGH) — Column-semantics ambiguity is method-breaking, buried as caveat #2
Caveat #2 notes imuN_g* may be fused Euler ANGLES (collectdata_dualIMU_BLE.ino, getAngleX/Y/Z)
vs true GYRO RATES (bluetoothSync.ino, getGyroX/Y/Z). This is not a footnote-level risk: if the
Anterior/Posterior rotation CSVs hold ANGLES, then differencing yields a relative ANGLE (not rate)
and the "cumulative rotation rate dose" is mathematically meaningless. Must be VERIFIED per-file
before anyone trusts the index. Asked Researcher to elevate it to a top-line blocker and Backend to gate on it.

## ISSUE 2 (MED) — Subtopic 2 headline "well-established" slightly over-borrows
Hewett 2005 is prospective for knee ABDUCTION MOMENT (valgus), not tibial rotation rate. The body
text handles this honestly ("rotation alone is partial", "proxy not predictor"), but the bold
"well-established" headline attached to a subtopic centered on rotation can read as if rotation-rate
prediction is well-established. Recommend splitting: mechanism well-established / rotation-rate-as-the-
tracked-signal emerging. Researcher already does this elsewhere (subtopics 4,5) so it's consistent to do here.

## ISSUE 3 (MED) — Cumulative-dose / Gabbett acute:chronic is the weakest transfer
Subtopic 3 is labeled well-established, but Gabbett/Frost/Schoenfeld are WHOLE-BODY or tissue-level
load epidemiology. Summing one joint's relative rotation over a 4-7s clip and calling it a "rotational
dose" comparable to acute:chronic workload is a large, unvalidated extrapolation. The principle (load
accumulates, spikes risky) is well-established; THIS specific operationalization is experimental.
Recommend relabeling the operationalization as experimental even though the underlying principle is solid.

## GOOD (no change needed)
- Did NOT claim rotation rate predicts injury (confirmed).
- Correctly justifies gyro-rate / differenced / no-accel-integration scope (subtopics 4-6, Woodman 2007).
- Sagittal-vs-transverse confidence split is exactly right and rarely flagged — credit.
- Frozen-accel artefact flagged (caveat #3) and femur/tibia mapping flagged (caveat #1).
