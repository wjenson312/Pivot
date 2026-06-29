// Mirrors the BLE GATT contract exposed by the firmware in
// /app/data-analysis/arduinoCode/bluetooth/bluetoothSync/bluetoothSync.ino.
// Keep these in sync if that sketch's service/characteristic UUIDs change.

export const BLE_DEVICE_NAME = "MKR1010_MPU";
export const BLE_SERVICE_UUID = "180d";
export const BLE_CONTROL_CHAR_UUID = "11111111-1111-1111-1111-111111111111";
export const BLE_SD_CHAR_UUID = "22222222-2222-2222-2222-222222222222";

// --- Pure framing logic, factored out so it's testable without a real BLE
// connection (Web Bluetooth only exists in a real browser + real device). ---

export interface ListAccumulator {
  buffer: string;
  files: string[];
  done: boolean;
}

export function newListAccumulator(): ListAccumulator {
  return { buffer: "", files: [], done: false };
}

/**
 * Feed one notification's decoded text into a LIST accumulator. The firmware
 * (handleControlWrite + the BLE_SYNC loop block) sends one "/<name>\n" line
 * per matching file, then a final bare "EOF" notification with no newline.
 */
export function feedListChunk(acc: ListAccumulator, text: string): ListAccumulator {
  if (acc.done) return acc;
  if (text === "EOF") {
    return { ...acc, done: true };
  }
  let buffer = acc.buffer + text;
  const files = [...acc.files];
  let idx: number;
  while ((idx = buffer.indexOf("\n")) !== -1) {
    const line = buffer.slice(0, idx);
    buffer = buffer.slice(idx + 1);
    if (line.startsWith("/")) files.push(line.slice(1));
  }
  return { buffer, files, done: false };
}

export interface GetAccumulator {
  chunks: Uint8Array[];
  done: boolean;
  error: string | null;
}

export function newGetAccumulator(): GetAccumulator {
  return { chunks: [], done: false, error: null };
}

/**
 * Feed one notification's raw bytes into a GET accumulator. The firmware
 * sends up to 180-byte raw file chunks, then a final "EOF" (3 bytes) when
 * the file is exhausted, or "ERR" (3 bytes) immediately if the file doesn't
 * exist. Sentinels are only ever sent as their own notification, never
 * appended to data, but since they're indistinguishable from a coincidental
 * 3-byte data chunk at the protocol level, this is a known firmware
 * limitation rather than something the client can fully resolve.
 */
export function feedGetChunk(acc: GetAccumulator, bytes: Uint8Array): GetAccumulator {
  if (acc.done) return acc;
  const text = bytesToAscii(bytes);
  if (bytes.length === 3 && text === "EOF") {
    return { ...acc, done: true };
  }
  if (bytes.length === 3 && text === "ERR") {
    return { ...acc, done: true, error: "Device reported the file does not exist." };
  }
  return { ...acc, chunks: [...acc.chunks, bytes] };
}

export function concatGetChunks(acc: GetAccumulator): Uint8Array {
  const total = acc.chunks.reduce((n, c) => n + c.length, 0);
  const out = new Uint8Array(total);
  let offset = 0;
  for (const chunk of acc.chunks) {
    out.set(chunk, offset);
    offset += chunk.length;
  }
  return out;
}

function bytesToAscii(bytes: Uint8Array): string {
  let s = "";
  for (let i = 0; i < bytes.length; i++) s += String.fromCharCode(bytes[i]);
  return s;
}

/** Filenames flow back to the device with the leading slash they arrived with. */
export function toDevicePath(filename: string): string {
  return filename.startsWith("/") ? filename : `/${filename}`;
}
