import Link from "next/link";
import KneeHealthScore from "@/components/KneeHealthScore";
import { loadKneeRotationLoadOutput } from "@/lib/load-method-output";
import { getSelectedRun } from "@/lib/selected-run";
import type { MethodOutput } from "@/lib/types";

// Recomputed fresh per request from whichever run is selected — see
// knee-rotation-load/page.tsx for why this is forced dynamic.
export const dynamic = "force-dynamic";
export const revalidate = 0;

function buildInsights(output: MethodOutput): string[] {
  const qf = output.qualityFlags;
  const sm = output.summaryMetrics;
  const byKey = (k: string) => sm.find((m) => m.key === k);

  if (!qf.usable_motion) {
    return [
      "This trial shows little to no real movement — the accelerometer and/or angle channels were static for the whole recording. Treat the scores above as flags, not real measurements, for this run.",
    ];
  }

  const insights: string[] = [];

  const load = byKey("relative_knee_load_score");
  if (load) {
    insights.push(
      `Relative knee load scored ${load.value}/100 for this trial, dominant on the ${dominantAxis(output)} axis.`
    );
  }

  const peakRate = byKey("peak_rel_rate_dps");
  if (peakRate) {
    insights.push(`Peak relative rotation rate reached ${peakRate.value} ${peakRate.unit}.`);
  }

  const rom = byKey("rom_deg");
  if (rom) {
    insights.push(`Range of motion for this trial: ${rom.value}${rom.unit} peak-to-peak on the dominant axis.`);
  }

  const impact = byKey("peak_impact_g");
  if (impact) {
    insights.push(`Peak tibia accelerometer impact: ${impact.value}${impact.unit} above resting gravity.`);
  } else {
    insights.push("No landing-mechanics reading for this trial — needs usable, non-frozen accelerometer data.");
  }

  if (qf.segment_assignment === "UNVERIFIED") {
    insights.push(
      `Femur/tibia sensor assignment is unverified for this trial (configured femur_imu=${qf.femur_imu}) — confirm against the physical sleeve before trusting sign/axis direction.`
    );
  }

  insights.push(
    `Sample rate ~${qf.sample_rate_hz ?? "n/a"} Hz, ${qf.n_samples} samples, ${qf.active_window_s}s active window.`
  );

  return insights;
}

function dominantAxis(output: MethodOutput): string {
  return output.report.fields.dominant_axis ? String(output.report.fields.dominant_axis) : "n/a";
}

export default function HomePage() {
  const selectedRun = getSelectedRun();

  if (!selectedRun) {
    return (
      <div className="method-tab">
        <div>
          <h1>Welcome to Pivot</h1>
          <p className="method-tab__meta">Relative knee load, range of motion, and landing mechanics, in one place.</p>
        </div>
        <div className="empty-state">
          No run selected yet. Go to the{" "}
          <Link href="/database" style={{ color: "var(--text)" }}>
            Database
          </Link>{" "}
          tab and select a run to see its Knee Health Score and insights here.
        </div>
      </div>
    );
  }

  const output = loadKneeRotationLoadOutput(selectedRun.id);

  if (!output) {
    return (
      <div className="method-tab">
        <div>
          <h1>Welcome to Pivot</h1>
        </div>
        <div className="empty-state">
          Backend output not found for run &quot;{selectedRun.name}&quot;. Expecting a file under
          /backend/outputs/*.knee_rotation_load.json (produced by /backend/knee_rotation_load.py).
        </div>
      </div>
    );
  }

  const insights = buildInsights(output);

  return (
    <div className="method-tab">
      <div>
        <h1>Home</h1>
        <p className="method-tab__meta">Trial: {output.trialLabel}</p>
      </div>

      <KneeHealthScore score={output.kneeHealthScore} />

      <section className="panel">
        <h2>General insights</h2>
        <ul style={{ margin: 0, paddingLeft: 20 }}>
          {insights.map((line, i) => (
            <li key={i} style={{ marginBottom: 8, lineHeight: 1.6, color: "var(--text-dim)" }}>
              {line}
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
