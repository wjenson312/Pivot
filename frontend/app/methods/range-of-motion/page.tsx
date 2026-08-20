import MethodTab from "@/components/MethodTab";
import { RANGE_OF_MOTION_RESEARCH } from "@/lib/research-content";
import { loadKneeRotationLoadOutput } from "@/lib/load-method-output";
import { getSelectedRun } from "@/lib/selected-run";

// See knee-rotation-load/page.tsx for why this is forced dynamic.
export const dynamic = "force-dynamic";
export const revalidate = 0;

export default function RangeOfMotionPage() {
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
      title="Range of Motion"
      research={RANGE_OF_MOTION_RESEARCH}
      output={output}
      headline={{ series: output.primarySeries, label: "Relative knee angle" }}
      metricKeys={["range_of_motion_score", "rom_deg", "peak_abs_rel_angle_deg"]}
    />
  );
}
