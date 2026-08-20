import MethodTab from "@/components/MethodTab";
import { LANDING_MECHANICS_RESEARCH } from "@/lib/research-content";
import { loadKneeRotationLoadOutput } from "@/lib/load-method-output";
import { getSelectedRun } from "@/lib/selected-run";

// See knee-rotation-load/page.tsx for why this is forced dynamic.
export const dynamic = "force-dynamic";
export const revalidate = 0;

export default function LandingMechanicsPage() {
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

  return (
    <MethodTab
      title="Landing Mechanics"
      research={LANDING_MECHANICS_RESEARCH}
      output={output}
      headline={{ series: output.accelMagnitudeSeries, label: "Tibia accelerometer magnitude" }}
      metricKeys={["landing_mechanics_score", "peak_impact_g"]}
    />
  );
}
