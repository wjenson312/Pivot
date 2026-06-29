import Link from "next/link";
import { getSelectedRun } from "@/lib/selected-run";

// Renders above every tab (wired into the root layout) so the currently
// selected run is never ambiguous, regardless of which Data Analysis tab
// you're looking at.
export default function ActiveRunBanner() {
  const run = getSelectedRun();

  return (
    <div className="active-run-banner">
      {run ? (
        <>
          <span className="active-run-banner__label">Viewing run</span>
          <span className="active-run-banner__name">{run.name}</span>
        </>
      ) : (
        <span className="active-run-banner__label active-run-banner__label--empty">
          No run selected
        </span>
      )}
      <Link href="/database" className="active-run-banner__change">
        {run ? "Change" : "Select a run"}
      </Link>
    </div>
  );
}
