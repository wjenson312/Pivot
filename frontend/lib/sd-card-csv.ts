// The SD-card firmware (bluetoothSync.ino, see logFile.println at line 242)
// writes a different column layout than Backend's knee_rotation_load.py
// expects (which matches the BLE-streamed CSVs in /data/cycle-1, produced by
// collectdata_dualIMU_BLE.ino + logdata_dualIMU_BLE.py). This module is the
// minimal structural adapter between the two — column renames and a
// microseconds -> seconds conversion for the timestamp — with no scientific
// interpretation. All channel-meaning / quality-flag logic stays in
// knee_rotation_load.py.
//
// Source header (bluetoothSync.ino):
//   ts,ax1,ay1,az1,gx1,gy1,gz1,ax2,ay2,az2,gx2,gy2,gz2
//   ts is micros() — an integer microsecond counter since device boot.
//   Unlike collectdata_dualIMU_BLE.ino, this firmware logs getGyroX/Y/Z
//   directly (true gyro rate, deg/s) rather than getAngleX/Y/Z — so these
//   files carry no fused-angle channel at all. knee_rotation_load.py's
//   existing channel-meaning detection already handles that case.
export const SD_CARD_CSV_HEADER = "ts,ax1,ay1,az1,gx1,gy1,gz1,ax2,ay2,az2,gx2,gy2,gz2";

const BACKEND_CSV_HEADER = [
  "arduino_time_s",
  "imu1_acc_x",
  "imu1_acc_y",
  "imu1_acc_z",
  "imu1_gx",
  "imu1_gy",
  "imu1_gz",
  "imu2_acc_x",
  "imu2_acc_y",
  "imu2_acc_z",
  "imu2_gx",
  "imu2_gy",
  "imu2_gz",
].join(",");

const EXPECTED_COLUMN_COUNT = 13;

/**
 * Converts a raw SD-card CSV (bluetoothSync.ino's layout) into the column
 * layout knee_rotation_load.py requires. Throws if the header doesn't match
 * the one known firmware format, rather than guessing at an unfamiliar
 * layout.
 */
export function remapSdCardCsv(raw: string): string {
  const lines = raw.split(/\r?\n/).filter((l) => l.length > 0);
  if (lines.length === 0) throw new Error("CSV is empty.");

  const header = lines[0].trim();
  if (header !== SD_CARD_CSV_HEADER) {
    throw new Error(
      `Unrecognized CSV header from device: "${header}". Expected the bluetoothSync.ino ` +
        `SD-card layout: "${SD_CARD_CSV_HEADER}".`
    );
  }

  const outLines = [BACKEND_CSV_HEADER];
  for (let i = 1; i < lines.length; i++) {
    const cols = lines[i].split(",");
    if (cols.length !== EXPECTED_COLUMN_COUNT) continue; // skip malformed/truncated rows
    const tsMicros = Number(cols[0]);
    if (!Number.isFinite(tsMicros)) continue;
    const tsSeconds = tsMicros / 1_000_000;
    outLines.push([tsSeconds, ...cols.slice(1)].join(","));
  }

  if (outLines.length === 1) {
    throw new Error("CSV has a valid header but no usable data rows.");
  }

  return outLines.join("\n") + "\n";
}
