import MethodTab from "@/components/MethodTab";
import { KNEE_ROTATION_LOAD_RESEARCH } from "@/lib/research-content";
import { loadKneeRotationLoadOutput } from "@/lib/load-method-output";
import { getSelectedRun } from "@/lib/selected-run";

// Force a fresh render per request: this page's content depends entirely on
// which run is selected (a cookie), and the client router cache has served
// a stale run's data after switching runs in the past.
export const dynamic = "force-dynamic";
export const revalidate = 0;

export default function KneeRotationLoadPage() {
  const selectedRun = getSelectedRun();

  if (!selectedRun) {
    return (
      <div className="empty-state">
        No run selected. Go to the <strong>Database</strong> tab and select a run to view its
        analysis here.
      </div>
    );
  }

  const output = loadKneeRotationLoadOutput(selectedRun.id);

  if (!output) {
    return (
      <div className="empty-state">
        Backend output not found for run &quot;{selectedRun.name}&quot;. Expecting a file under
        /backend/outputs/*.knee_rotation_load.json (produced by
        /backend/knee_rotation_load.py).
      </div>
    );
  }

  const headline =
    output.primarySignal === "relative_angle_deg" && output.primarySeries.length > 0
      ? { series: output.primarySeries, label: "Relative knee angle" }
      : { series: output.rateSeries, label: "Relative knee angular rate" };
  const secondary =
    output.primarySignal === "relative_angle_deg"
      ? { series: output.rateSeries, label: "Relative knee angular rate (secondary, lower-confidence)" }
      : null;

  return (
    <MethodTab
      title="Knee Rotation Load"
      research={KNEE_ROTATION_LOAD_RESEARCH}
      output={output}
      headline={headline}
      secondary={secondary}
      metricKeys={["relative_knee_load_score", "peak_rel_rate_dps", "mean_active_rate_dps"]}
    />
  );
}
