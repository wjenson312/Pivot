import fs from "node:fs";
import path from "node:path";
import { listAvailableTrials } from "./load-method-output";

// Frontend-owned metadata overlay for each data run. One run == one Backend
// trial (keyed by trial id, i.e. the source CSV's basename). This lives
// entirely under /frontend — we never write into /backend (see
// load-method-output.ts) — it just layers editable name/visibility on top of
// Backend's read-only outputs.
//
// Schema is intentionally minimal for this iteration: only `name` and
// `recordedAt` are surfaced in the UI. `metadata` is reserved now so future
// fields (collection location, notes, device info, environmental conditions,
// etc.) can be added without another migration of the registry file.

const REGISTRY_PATH = path.join(process.cwd(), "data", "runs-registry.json");

export interface RunMetadata {
  [key: string]: unknown;
}

interface RunRecordEntry {
  name: string;
  recordedAt: string; // ISO 8601
  deleted: boolean;
  createdAt: string;
  updatedAt: string;
  metadata: RunMetadata;
}

export interface RunRecord extends RunRecordEntry {
  /** Stable id == the Backend trial id (source CSV basename, no extension). */
  id: string;
}

type Registry = Record<string, RunRecordEntry>;

function readRegistry(): Registry {
  try {
    return JSON.parse(fs.readFileSync(REGISTRY_PATH, "utf-8")) as Registry;
  } catch {
    return {};
  }
}

function writeRegistry(registry: Registry): void {
  fs.mkdirSync(path.dirname(REGISTRY_PATH), { recursive: true });
  fs.writeFileSync(REGISTRY_PATH, JSON.stringify(registry, null, 2));
}

// Backend's trial ids often end in `_YYYYMMDD_HHMMSS` (set by the firmware's
// run-numbering — see Arduino bluetoothSync.ino's nextRunFilename, and the
// MPU_BothIMUs_20251205_155322-style names already in /backend/outputs). When
// present, that's the real recorded-at time. Otherwise fall back to the
// output file's mtime as a best-effort proxy until Backend/firmware starts
// recording true capture time directly.
function inferRecordedAt(trialId: string): string {
  const match = trialId.match(/(\d{8})_(\d{6})$/);
  if (match) {
    const [, d, t] = match;
    const iso = `${d.slice(0, 4)}-${d.slice(4, 6)}-${d.slice(6, 8)}T${t.slice(0, 2)}:${t.slice(2, 4)}:${t.slice(4, 6)}`;
    const parsed = new Date(iso);
    if (!Number.isNaN(parsed.getTime())) return parsed.toISOString();
  }
  try {
    const outputPath = path.join(
      process.cwd(),
      "..",
      "backend",
      "outputs",
      `${trialId}.knee_rotation_load.json`
    );
    return fs.statSync(outputPath).mtime.toISOString();
  } catch {
    return new Date(0).toISOString();
  }
}

/**
 * All non-deleted runs, registry-backed. Any trial Backend has produced
 * output for that isn't in the registry yet is auto-onboarded on read, so
 * new SD-card runs show up in the Database tab with no manual step.
 */
export function listRuns(): RunRecord[] {
  const registry = readRegistry();
  const trialIds = listAvailableTrials();
  let dirty = false;

  for (const id of trialIds) {
    if (!registry[id]) {
      const now = new Date().toISOString();
      registry[id] = {
        name: id,
        recordedAt: inferRecordedAt(id),
        deleted: false,
        createdAt: now,
        updatedAt: now,
        metadata: {},
      };
      dirty = true;
    }
  }
  if (dirty) writeRegistry(registry);

  return trialIds
    .map((id) => ({ id, ...registry[id] }))
    .filter((r) => !r.deleted)
    .sort((a, b) => b.recordedAt.localeCompare(a.recordedAt));
}

export function getRun(id: string): RunRecord | null {
  const registry = readRegistry();
  if (!registry[id] || registry[id].deleted) return null;
  return { id, ...registry[id] };
}

export function renameRun(id: string, name: string): RunRecord | null {
  const registry = readRegistry();
  if (!registry[id]) return null;
  registry[id] = { ...registry[id], name, updatedAt: new Date().toISOString() };
  writeRegistry(registry);
  return { id, ...registry[id] };
}

/**
 * Soft-delete: hides the run from the Database tab. Backend's original
 * output files are never touched — this only flips a flag in the frontend's
 * own registry, consistent with load-method-output.ts's read-only contract.
 */
export function deleteRun(id: string): boolean {
  const registry = readRegistry();
  if (!registry[id]) return false;
  registry[id] = { ...registry[id], deleted: true, updatedAt: new Date().toISOString() };
  writeRegistry(registry);
  return true;
}
