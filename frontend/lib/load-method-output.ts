import fs from "node:fs";
import path from "node:path";
import type {
  ChannelMeaning,
  ChannelMeaningConfidence,
  KneeHealthScore,
  MethodOutput,
  MethodSeries,
  PrimarySignal,
  QualityFlags,
  SummaryMetric,
} from "./types";

// Reads Backend's raw output (read-only) and adapts it into the shared
// MethodOutput shape consumed by MethodTab. We never write into /backend —
// this only reads JSON files Backend's knee_rotation_load.py produces, under
// /backend/outputs/*.knee_rotation_load.json.
//
// Schema reference: /backend/CONTRACT.md (Pivot Backend Data Contract v1).

const BACKEND_OUTPUTS_DIR = path.join(process.cwd(), "..", "backend", "outputs");
const BACKEND_MODULE_PATH = "/backend/knee_rotation_load.py";
const BACKEND_CONTRACT_PATH = "/backend/CONTRACT.md";
const BACKEND_REPORT_PATH = "/backend/knee_rotation_load_REPORT.md";

// Preferred default trial: the one confirmed real-movement file per Backend's
// report. Falls back to the first usable_motion=true file found, then to the
// first file at all (so the tab still renders something rather than nothing).
const PREFERRED_DEFAULT_TRIAL = "MPU_BothIMUs_20251205_155322";

interface RawBackendResult {
  method: string;
  version: string;
  source_file: string;
  units: Record<string, string | null>;
  timestamps: number[];
  series: Record<string, number[]>;
  summary_metrics: Record<string, number | string | null>;
  quality_flags: Record<string, unknown>;
  notes: string[];
}

function buildSeries(
  timestamps: number[],
  raw: Record<string, number[]>,
  prefix: "rel_angle" | "rel_rate",
  unit: string
): MethodSeries[] {
  const order: { suffix: string; label: string; role?: "dominant" | "component" }[] = [
    { suffix: "dominant", label: "dominant axis", role: "dominant" },
    { suffix: "x", label: "x axis", role: "component" },
    { suffix: "y", label: "y axis", role: "component" },
    { suffix: "z", label: "z axis", role: "component" },
  ];
  return order
    .filter((o) => raw[`${prefix}_${o.suffix}`])
    .map((o) => ({
      key: `${prefix}_${o.suffix}`,
      label: o.label,
      unit,
      role: o.role,
      points: timestamps.map((t, i) => ({ t, value: raw[`${prefix}_${o.suffix}`][i] })),
    }));
}

/**
 * Resolve channel_meaning + confidence FAIL-SAFE: any missing/unexpected
 * value defaults to the LOWER-confidence interpretation (euler_deg / low
 * confidence) rather than silently claiming a clean gyro-rate measurement.
 * Per Critic review: failing open here hides the "derived/noisy" caveat.
 */
function resolveChannelMeaning(qf: Record<string, unknown>): {
  channelMeaning: ChannelMeaning;
  confidence: ChannelMeaningConfidence;
  rateIsLowConfidence: boolean;
} {
  const rawMeaning = qf.channel_meaning;
  const channelMeaning: ChannelMeaning = rawMeaning === "gyro_rate_dps" ? "gyro_rate_dps" : "euler_deg";

  const rawConfidence = qf.channel_meaning_confidence;
  const confidence: ChannelMeaningConfidence = rawConfidence === "high" ? "high" : "low";

  // rate_is_low_confidence should default to true (the cautious assumption)
  // unless Backend explicitly says false.
  const rateIsLowConfidence = qf.rate_is_low_confidence === false ? false : true;

  return { channelMeaning, confidence, rateIsLowConfidence };
}

function adapt(raw: RawBackendResult, sourceJsonPath: string): MethodOutput {
  const sm = raw.summary_metrics;
  const qfRaw = raw.quality_flags;
  const units = raw.units ?? {};

  const { channelMeaning, confidence, rateIsLowConfidence } = resolveChannelMeaning(qfRaw);

  const usableMotion = qfRaw.usable_motion === true;
  const accelStatic = Boolean(qfRaw.accel_static);

  const primarySignal: PrimarySignal =
    sm.primary_signal === "relative_rate_dps" ? "relative_rate_dps" : "relative_angle_deg";

  const angleUnit = units.rel_angle ?? "deg";
  const rateUnit = units.rel_rate ?? "deg/s";
  const romUnit = units.rom_deg ?? "deg";

  const kneeHealthScore: KneeHealthScore = {
    value: sm.knee_health_score === null || sm.knee_health_score === undefined ? null : Number(sm.knee_health_score),
    subScores: [
      {
        key: "relative_knee_load",
        label: "Relative Knee Load",
        value: sm.relative_knee_load_score === null || sm.relative_knee_load_score === undefined
          ? null
          : Number(sm.relative_knee_load_score),
      },
      {
        key: "range_of_motion",
        label: "Range of Motion",
        value: sm.range_of_motion_score === null || sm.range_of_motion_score === undefined
          ? null
          : Number(sm.range_of_motion_score),
      },
      {
        key: "landing_mechanics",
        label: "Landing Mechanics",
        value: sm.landing_mechanics_score === null || sm.landing_mechanics_score === undefined
          ? null
          : Number(sm.landing_mechanics_score),
      },
    ],
  };

  // rotation_load_index / relative_knee_load_score is headlined by the Knee
  // Health Score hero above, so it's left out of this generic diagnostics
  // grid to avoid showing the same number twice.
  const summaryMetrics: SummaryMetric[] = [
    {
      key: "rom_deg",
      label: "Range of motion (ROM)",
      value: sm.rom_deg === null || sm.rom_deg === undefined ? null : Number(sm.rom_deg),
      unit: romUnit,
    },
    {
      key: "peak_abs_rel_angle_deg",
      label: "Peak relative angle",
      value:
        sm.peak_abs_rel_angle_deg === null || sm.peak_abs_rel_angle_deg === undefined
          ? null
          : Number(sm.peak_abs_rel_angle_deg),
      unit: angleUnit,
    },
    {
      key: "peak_rel_rate_dps",
      label: "Peak relative rate",
      value: Number(sm.peak_rel_rate_dps ?? 0),
      unit: rateUnit,
    },
    {
      key: "mean_active_rate_dps",
      label: "Mean active rate",
      value: Number(sm.mean_active_rate_dps ?? 0),
      unit: rateUnit,
    },
  ].filter((m) => m.value !== null) as SummaryMetric[];

  const qualityFlags: QualityFlags = {
    accel_static: accelStatic,
    gyro_varies: Boolean(qfRaw.gyro_varies),
    usable_motion: usableMotion,
    channel_meaning: channelMeaning,
    channel_meaning_confidence: confidence,
    rate_is_low_confidence: rateIsLowConfidence,
    sample_rate_hz:
      typeof qfRaw.sample_rate_hz === "number" ? (qfRaw.sample_rate_hz as number) : null,
    n_samples: Number(qfRaw.n_samples ?? 0),
    n_dropped_leading_frozen: Number(qfRaw.n_dropped_leading_frozen ?? 0),
    active_window_s: Number(qfRaw.active_window_s ?? 0),
    drift_residual_dps: Number(qfRaw.drift_residual_dps ?? 0),
    drift_bounded: Boolean(qfRaw.drift_bounded),
    segment_assignment: qfRaw.segment_assignment === "confirmed" ? "confirmed" : "UNVERIFIED",
    femur_imu: Number(qfRaw.femur_imu ?? 1),
    tibia_imu: Number(qfRaw.tibia_imu ?? 2),
    sign: Number(qfRaw.sign ?? 1),
  };

  return {
    methodId: "knee-rotation-load",
    methodName: "Knee Rotation Load",
    trialLabel: raw.source_file,
    primarySignal,
    primarySeries: buildSeries(raw.timestamps, raw.series, "rel_angle", angleUnit),
    rateSeries: buildSeries(raw.timestamps, raw.series, "rel_rate", rateUnit),
    summaryMetrics,
    kneeHealthScore,
    qualityFlags,
    notes: raw.notes ?? [],
    report: {
      whatItMeasures:
        "The relative knee angle (and, secondarily, angular rate) between the tibia (shin) and " +
        "femur (thigh) IMUs — how far/fast the knee joint itself is bending or rotating, isolated " +
        "from whole-limb orientation. Reported as range of motion (ROM), peak relative angle, peak " +
        "and mean active rate, and a 0-100 Knee Motion / Load Index — one of three inputs (alongside " +
        "a range-of-motion score and a landing-mechanics impact proxy) rolled into the Knee Health " +
        "Score shown at the top of this tab.",
      howDerived:
        "Per axis, each segment's fused Euler angle is unwrapped across the +-180 deg discontinuity, " +
        "then the relative angle is sign * (tibia - femur), baseline-zeroed to the quiet start. This " +
        "angle is directly measured (drift-free), not integrated. ROM is peak-to-peak of the dominant " +
        "axis; the 0-100 index normalizes ROM to a 90 deg reference. A relative RATE (deg/s) is also " +
        "produced by differentiating the angle against actual arduino_time_s deltas — differentiation " +
        "amplifies noise, so rate is flagged lower-confidence than the angle.",
      fields: {
        method: raw.method,
        version: raw.version,
        primary_signal: primarySignal,
        dominant_axis: String(sm.dominant_axis ?? "n/a"),
        sample_rate_hz: String(qfRaw.sample_rate_hz ?? "n/a"),
        n_samples: String(qfRaw.n_samples ?? "n/a"),
        active_window_s: String(qfRaw.active_window_s ?? "n/a"),
        femur_imu: String(qfRaw.femur_imu ?? "n/a"),
        tibia_imu: String(qfRaw.tibia_imu ?? "n/a"),
        segment_assignment: String(qfRaw.segment_assignment ?? "UNVERIFIED"),
      },
    },
    sourcePaths: [
      BACKEND_MODULE_PATH,
      BACKEND_CONTRACT_PATH,
      BACKEND_REPORT_PATH,
      sourceJsonPath.replace(path.join(process.cwd(), ".."), ""),
    ],
  };
}

function listOutputFiles(): string[] {
  if (!fs.existsSync(BACKEND_OUTPUTS_DIR)) return [];
  return fs
    .readdirSync(BACKEND_OUTPUTS_DIR)
    .filter((f) => f.endsWith(".knee_rotation_load.json"))
    .sort();
}

/**
 * Returns the knee-rotation-load output for a given trial, or for the
 * dashboard's default trial when no trialId is given, or null if no output
 * files exist yet.
 *
 * Default-trial selection order (per Critic review — do not default to an
 * alphabetically-first dead-data trial):
 *   1. The requested trialId, if it matches an existing output file.
 *   2. PREFERRED_DEFAULT_TRIAL if present.
 *   3. The first file with quality_flags.usable_motion === true.
 *   4. The first file at all (so a "no usable movement" state can render
 *      instead of a blank tab, when every trial in /backend/outputs is dead).
 */
export function loadKneeRotationLoadOutput(trialId?: string): MethodOutput | null {
  try {
    const files = listOutputFiles();
    if (files.length === 0) return null;

    let chosen: string | null = null;

    if (trialId) {
      const requestedFile = `${trialId}.knee_rotation_load.json`;
      if (files.includes(requestedFile)) chosen = requestedFile;
    }

    if (!chosen) {
      const preferredFile = `${PREFERRED_DEFAULT_TRIAL}.knee_rotation_load.json`;
      chosen = files.includes(preferredFile) ? preferredFile : null;
    }

    if (!chosen) {
      for (const f of files) {
        const full = path.join(BACKEND_OUTPUTS_DIR, f);
        const raw = JSON.parse(fs.readFileSync(full, "utf-8")) as RawBackendResult;
        if (raw.quality_flags?.usable_motion === true) {
          chosen = f;
          break;
        }
      }
    }

    if (!chosen) chosen = files[0];

    const full = path.join(BACKEND_OUTPUTS_DIR, chosen);
    const raw = JSON.parse(fs.readFileSync(full, "utf-8")) as RawBackendResult;
    return adapt(raw, full);
  } catch {
    return null;
  }
}

/** All available trials, for the trial picker dropdown. */
export function listAvailableTrials(): string[] {
  return listOutputFiles().map((f) => f.replace(".knee_rotation_load.json", ""));
}
