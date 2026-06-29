import TabNav from "@/components/TabNav";
import RunList from "@/components/RunList";
import BleSyncPanel from "@/components/BleSyncPanel";
import { listRuns } from "@/lib/runs-registry";
import { getSelectedRunId } from "@/lib/selected-run";

// Primary entry point for the dashboard: pick which run every Data Analysis
// tab should render. Selection is stored as shared app state (a cookie —
// see lib/selected-run.ts) so it follows you across tabs.
export default function DatabasePage() {
  const runs = listRuns();
  const selectedRunId = getSelectedRunId();

  return (
    <>
      <TabNav />
      <div className="method-tab">
        <div>
          <h1>Database</h1>
          <p className="method-tab__meta">
            Runs loaded from the microSD card. Select one to view it in the Data Analysis tabs.
          </p>
        </div>

        <section className="panel">
          <BleSyncPanel existingRunIds={runs.map((r) => r.id)} />
        </section>

        <section className="panel">
          {runs.length === 0 ? (
            <div className="empty-state">
              No runs found yet. Expecting Backend output under
              /backend/outputs/*.knee_rotation_load.json.
            </div>
          ) : (
            <RunList runs={runs} selectedRunId={selectedRunId} />
          )}
        </section>
      </div>
    </>
  );
}
