import { NextRequest, NextResponse } from "next/server";
import fs from "node:fs";
import path from "node:path";
import { execFile } from "node:child_process";
import { remapSdCardCsv } from "@/lib/sd-card-csv";

// Lands a CSV pulled from the device's microSD card over BLE (see
// lib/ble-sync.ts) and runs it through Backend's existing pipeline, same as
// /backend/outputs/* generated from /data/cycle-1. We never write into
// /backend's source — only into /data/uploaded and /backend/outputs, which
// is exactly what running knee_rotation_load.py by hand already does.
const REPO_ROOT = path.join(process.cwd(), "..");
const UPLOAD_DIR = path.join(REPO_ROOT, "data", "uploaded");
const BACKEND_SCRIPT = path.join(REPO_ROOT, "backend", "knee_rotation_load.py");
const BACKEND_OUTPUTS_DIR = path.join(REPO_ROOT, "backend", "outputs");

const FILENAME_PATTERN = /^[\w.-]+\.csv$/i;

function runBackendScript(absCsvPath: string): Promise<{ stdout: string; stderr: string }> {
  return new Promise((resolve, reject) => {
    execFile(
      "python3",
      [BACKEND_SCRIPT, absCsvPath],
      { cwd: REPO_ROOT, timeout: 60_000 },
      (error, stdout, stderr) => {
        if (error) {
          reject(new Error(stderr.trim() || stdout.trim() || error.message));
          return;
        }
        resolve({ stdout, stderr });
      }
    );
  });
}

export async function POST(req: NextRequest) {
  const body = await req.json().catch(() => null);
  const filename = typeof body?.filename === "string" ? body.filename.trim() : "";
  const content = typeof body?.content === "string" ? body.content : null;

  if (!filename || content === null) {
    return NextResponse.json({ error: "filename and content are required" }, { status: 400 });
  }
  if (!FILENAME_PATTERN.test(filename)) {
    return NextResponse.json({ error: "Invalid filename" }, { status: 400 });
  }

  const trialId = filename.replace(/\.csv$/i, "");
  const outputJsonPath = path.join(BACKEND_OUTPUTS_DIR, `${trialId}.knee_rotation_load.json`);
  const alreadyImported = fs.existsSync(outputJsonPath);

  let remapped: string;
  try {
    remapped = remapSdCardCsv(content);
  } catch (err) {
    return NextResponse.json({ error: (err as Error).message }, { status: 422 });
  }

  fs.mkdirSync(UPLOAD_DIR, { recursive: true });
  const csvPath = path.join(UPLOAD_DIR, filename);
  fs.writeFileSync(csvPath, remapped);

  try {
    await runBackendScript(csvPath);
  } catch (err) {
    return NextResponse.json(
      { error: `Backend processing failed for "${filename}": ${(err as Error).message}` },
      { status: 500 }
    );
  }

  return NextResponse.json({ ok: true, trialId, alreadyImported });
}
