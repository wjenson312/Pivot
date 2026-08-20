// Shared contract types for analysis-method outputs rendered by the dashboard.
// These mirror /backend/CONTRACT.md (Pivot Backend Data Contract v1). Frontend
// never edits /backend originals — these types describe what we read from
// Backend's JSON output files at render time.

export type EvidenceStrength = "well-established" | "emerging" | "experimental";

export interface ResearchSubtopic {
  title: string;
  strength: EvidenceStrength;
  body: string;
}

export interface ResearchContent {
  /** Plain-language paragraph(s) aimed at a non-technical athlete/coach. */
  summary: string[];
  /** Ranked subtopics with evidence-strength badges, drawn from the Researcher's brief. */
  subtopics: ResearchSubtopic[];
  /** Path to the original research markdown, shown as a source note (not rendered raw). */
  sourcePath: string;
}

export type ChannelMeaning = "euler_deg" | "gyro_rate_dps";
export type ChannelMeaningConfidence = "high" | "low";
export type PrimarySignal = "relative_angle_deg" | "relative_rate_dps";

export interface QualityFlags {
  accel_static: boolean;
  gyro_varies: boolean;
  /** If false, the file is NOT a valid movement recording — must be a first-class UI state. */
  usable_motion: boolean;
  channel_meaning: ChannelMeaning;
  channel_meaning_confidence: ChannelMeaningConfidence;
  rate_is_low_confidence: boolean;
  sample_rate_hz: number | null;
  n_samples: number;
  n_dropped_leading_frozen: number;
  active_window_s: number;
  drift_residual_dps: number;
  drift_bounded: boolean;
  segment_assignment: "UNVERIFIED" | "confirmed";
  femur_imu: number;
  tibia_imu: number;
  sign: number;
}

export interface SeriesPoint {
  t: number; // seconds
  value: number;
}

export interface MethodSeries {
  key: string;
  label: string;
  unit: string;
  points: SeriesPoint[];
  role?: "dominant" | "component";
}

export interface SummaryMetric {
  key: string;
  label: string;
  value: number | string | null;
  unit: string;
  /** 0-100 normalized index, used to render a low/moderate/high band. */
  band?: "low" | "moderate" | "high";
}

export interface KneeHealthSubScore {
  key: "relative_knee_load" | "range_of_motion" | "landing_mechanics";
  label: string;
  value: number | null;
}

export interface KneeHealthScore {
  /** 0-100 weighted composite, or null when a required sub-score is unavailable. */
  value: number | null;
  subScores: KneeHealthSubScore[];
}

export interface MethodReport {
  whatItMeasures: string;
  howDerived: string;
  fields: Record<string, string | number>;
}

export interface MethodOutput {
  methodId: string;
  methodName: string;
  trialLabel: string;
  primarySignal: PrimarySignal;
  /** Series for the primary signal (angle, when present) — preferred headline plot. */
  primarySeries: MethodSeries[];
  /** Series for the secondary/rate signal — always present, lower confidence when derived. */
  rateSeries: MethodSeries[];
  /** Tibia accelerometer magnitude (g) over time — headline for the Landing Mechanics tab. */
  accelMagnitudeSeries: MethodSeries[];
  summaryMetrics: SummaryMetric[];
  kneeHealthScore: KneeHealthScore;
  qualityFlags: QualityFlags;
  notes: string[];
  report: MethodReport;
  sourcePaths: string[];
}

export interface MethodDefinition {
  id: string;
  navLabel: string;
  ready: boolean;
}
