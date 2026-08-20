# Critique — /frontend (Knee Rotation Load tab)

Reviewed 2026-06-19. Strong: non-dismissible no-Nm honesty banner; conditional Euler-derived /
unverified-mapping / accel-frozen warnings; units read from contract (chart Y-axis uses dominant.unit,
not hardcoded deg/s); peak marker; research paragraph above chart; adapter correctly remaps
euler_deg->fused_euler_deg and segment_assignment UNVERIFIED->unverified (banner WILL fire). Meets all
three of my criteria. Findings:

## FINDING 0 (BLOCKER, added after Backend schema change) — adapter is on the OLD contract; chart will be EMPTY
Backend revised CONTRACT.md + regenerated JSON to a NEW schema: series rel_rate_*/rel_angle_*
(not omega_rel_*), summary primary_signal/rom_deg/peak_abs_rel_angle_deg (cumulative_* REMOVED),
method "relative_tibial_femoral_knee_motion". The Frontend adapter (load-method-output.ts) still
reads omega_rel_dominant/omega_rel_{xyz} (lines 41-44) and cumulative_rotation_deg/cumulative_rate_dps
(lines 65-66, 83-93). Against the new JSON: toSeries finds NO matching keys -> empty chart
("No series data"); cumulative cards render 0. HARD INTEGRATION BREAK. Frontend must:
- map series to rel_rate_*/rel_angle_*; plot rel_angle_dominant (deg) as headline when
  primary_signal=="relative_angle_deg" (CONTRACT line 53), else rel_rate_dominant.
- replace cumulative cards with rom_deg / peak_abs_rel_angle_deg / peak_rel_rate_dps.
- channel_meaning value is still "euler_deg" in JSON (adapter's euler_deg check still valid),
  but also read the new rate_is_low_confidence + channel_meaning_confidence flags.

## FINDING 1 (HIGH) — default view loads the DEAD trial
load-method-output.ts loadKneeRotationLoadOutput() takes files[0] after .sort(). Alphabetically that's
Anterior_Rotation_RL.knee_rotation_load.json — the trial with usable_motion=FALSE, index 0.34, flat chart.
The dashboard's DEFAULT demo is the one CSV with no real movement. Should prefer a trial with
usable_motion=true (e.g. MPU_BothIMUs) or at least skip files flagged unusable.

## FINDING 2 (HIGH) — usable_motion never surfaced as a first-class state
Backend emits usable_motion=false + a "WARNING: not a valid movement recording" note for dead files.
The adapter drops usable_motion entirely (qualityFlags only carries accel_static/channel/mapping/notes).
The warning shows only as a generic <li> in the banner. A trial with no real motion should render a
prominent empty/invalid state ("this trial contains no usable movement"), not a near-flat chart that
looks like a real (tiny) measurement. Add usable_motion to QualityFlags + a dedicated UI state.

## FINDING 3 (MED) — fail-OPEN on channel_meaning
Line 98: channel_meaning === "euler_deg" ? "fused_euler_deg" : "raw_rate_dps". Any missing/unknown value
defaults to the HIGHER-confidence "raw_rate_dps" label, hiding the lower-confidence caveat. Should
fail safe to fused_euler_deg (lower-confidence) on anything that isn't an explicit confirmed rate.
Also it ignores channel_meaning_confidence=low from Backend — a low-confidence rate should still trip
the lower-confidence note even if labeled gyro_rate_dps.

## FINDING 4 (LOW) — placeholder generatedAt
generatedAt = "see /backend/outputs" — not a real timestamp. Backend JSON has no generatedAt field;
either add one to the contract or omit the line rather than show a placeholder.

## FINDING 5 (LOW) — chart peak marker inherits Backend diff-noise
Peak is max|value| of dominant series; if Backend's differentiated-angle peak is a single-sample noise
spike (see backend-critique FINDING re 580 deg/s), the "peak" dot lands on noise. Resolves if Backend
low-passes; otherwise consider a light smoothing for display only (clearly labeled).
