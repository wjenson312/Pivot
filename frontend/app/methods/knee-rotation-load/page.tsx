import TabNav from "@/components/TabNav";
import MethodTab from "@/components/MethodTab";
import { KNEE_ROTATION_LOAD_RESEARCH } from "@/lib/research-content";
import { loadKneeRotationLoadOutput } from "@/lib/load-method-output";
import { getSelectedRun } from "@/lib/selected-run";

export default function KneeRotationLoadPage() {
  const selectedRun = getSelectedRun();

  if (!selectedRun) {
    return (
      <>
        <TabNav />
        <div className="empty-state">
          No run selected. Go to the <strong>Database</strong> tab and select a run to view its
          analysis here.
        </div>
      </>
    );
  }

  const output = loadKneeRotationLoadOutput(selectedRun.id);

  return (
    <>
      <TabNav />
      {output ? (
        <MethodTab research={KNEE_ROTATION_LOAD_RESEARCH} output={output} />
      ) : (
        <div className="empty-state">
          Backend output not found for run &quot;{selectedRun.name}&quot;. Expecting a file under
          /backend/outputs/*.knee_rotation_load.json (produced by
          /backend/knee_rotation_load.py).
        </div>
      )}
    </>
  );
}
