# Critique — /docs/cycle-1-direction.md

Reviewed 2026-06-19. Verdict: STRONG. Both my caveats incorporated and verified in text:
- Duration-normalized cumulative as a per-second rate, no raw cross-trial cumulative (§4.4). OK.
- Rate-space headline (deg/s); integrated angle/ROM only when drift_bounded=true, labeled lower-confidence (§4.4, §4.2). OK.
- channel_meaning ambiguity already escalated into the spec (§2, §4.2, §6.3) — covers my research ISSUE 1.
- Femur/tibia mapping configurable + TBD, sign of omega_rel configurable (§4.3, §6.1). OK.
- accel_frozen surfaced in quality_flags, not hidden (§4.2, §5). OK.
- arduino_time_s for rate, no Nm, 0-100 index documented as unitless (§3, §4.1). OK.

## ISSUE (MED) — channel_meaning auto-detect by magnitude heuristic is unsafe (§4.2)
"Auto-detect via magnitude/units heuristic" is fragile: fused Euler ANGLES (deg, up to ~±180)
and gyro RATES (deg/s, tens-to-hundreds during fast rotation trials) OVERLAP in magnitude.
A magnitude heuristic can silently misclassify and then the cumulative computation is wrong
in a way that LOOKS plausible. Provenance (which firmware/filename produced each CSV) is the
reliable discriminator and should be the primary path; magnitude heuristic only as a secondary
cross-check that, on disagreement, sets a LOW-CONFIDENCE flag rather than committing silently.
Told Planner + will tell Backend to gate cumulative on confirmed provenance, not a guess.

No other blockers. Direction is shippable as written.
