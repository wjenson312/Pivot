import { cookies } from "next/headers";
import { getRun, type RunRecord } from "./runs-registry";

// The selected run is the dashboard's one piece of shared application state:
// every Data Analysis tab reads it to decide which trial's output to render.
// Stored as a cookie (not a query param) so the selection made on the
// Database tab persists across all tabs without each page needing to thread
// it through links.
export const SELECTED_RUN_COOKIE = "spk_selected_run";

export function getSelectedRunId(): string | null {
  return cookies().get(SELECTED_RUN_COOKIE)?.value ?? null;
}

export function getSelectedRun(): RunRecord | null {
  const id = getSelectedRunId();
  if (!id) return null;
  return getRun(id);
}
