import {
  BLE_CONTROL_CHAR_UUID,
  BLE_DEVICE_NAME,
  BLE_SD_CHAR_UUID,
  BLE_SERVICE_UUID,
  concatGetChunks,
  feedGetChunk,
  feedListChunk,
  newGetAccumulator,
  newListAccumulator,
  toDevicePath,
} from "./ble-protocol";

export function isWebBluetoothSupported(): boolean {
  return typeof navigator !== "undefined" && "bluetooth" in navigator;
}

export interface BleConnection {
  device: BluetoothDevice;
  controlChar: BluetoothRemoteGATTCharacteristic;
  sdChar: BluetoothRemoteGATTCharacteristic;
}

// The device only accepts connections while it's in BLE_SYNC mode (entered
// by holding the physical button for 2+ seconds — see bluetoothSync.ino),
// at which point it advertises this service. Outside that window it isn't
// connectable at all, which is why requestDevice() will find nothing if the
// device hasn't been put into sync mode first.
export async function connectToDevice(): Promise<BleConnection> {
  const device = await navigator.bluetooth.requestDevice({
    filters: [{ services: [BLE_SERVICE_UUID] }, { name: BLE_DEVICE_NAME }],
    optionalServices: [BLE_SERVICE_UUID],
  });
  const server = await device.gatt?.connect();
  if (!server) throw new Error("Could not open a GATT connection to the device.");
  const service = await server.getPrimaryService(BLE_SERVICE_UUID);
  const controlChar = await service.getCharacteristic(BLE_CONTROL_CHAR_UUID);
  const sdChar = await service.getCharacteristic(BLE_SD_CHAR_UUID);
  return { device, controlChar, sdChar };
}

export function disconnectDevice(conn: BleConnection): void {
  conn.device.gatt?.disconnect();
}

const LIST_TIMEOUT_MS = 30_000;
const GET_TIMEOUT_MS = 120_000;

function withTimeout<T>(promise: Promise<T>, ms: number, message: string): Promise<T> {
  let timer: ReturnType<typeof setTimeout>;
  const timeout = new Promise<never>((_, reject) => {
    timer = setTimeout(() => reject(new Error(message)), ms);
  });
  return Promise.race([promise, timeout]).finally(() => clearTimeout(timer)) as Promise<T>;
}

/** Sends LIST and resolves with the run_*.csv filenames currently on the SD card. */
export async function listRemoteFiles(conn: BleConnection): Promise<string[]> {
  const job = new Promise<string[]>((resolve, reject) => {
    let acc = newListAccumulator();

    function onNotify(this: BluetoothRemoteGATTCharacteristic) {
      const value = this.value;
      if (!value) return;
      const text = new TextDecoder().decode(value);
      acc = feedListChunk(acc, text);
      if (acc.done) {
        cleanup();
        resolve(acc.files);
      }
    }

    function cleanup() {
      conn.sdChar.removeEventListener("characteristicvaluechanged", onNotify);
    }

    conn.sdChar.addEventListener("characteristicvaluechanged", onNotify);
    conn.sdChar
      .startNotifications()
      .then(() => conn.controlChar.writeValue(new TextEncoder().encode("LIST")))
      .catch((err) => {
        cleanup();
        reject(err);
      });
  });

  return withTimeout(job, LIST_TIMEOUT_MS, "Timed out waiting for the device's file list.");
}

/** Sends "GET <filename>" and resolves with the file's raw text content. */
export async function downloadRemoteFile(
  conn: BleConnection,
  filename: string,
  onProgress?: (bytesReceived: number) => void
): Promise<string> {
  const job = new Promise<string>((resolve, reject) => {
    let acc = newGetAccumulator();

    function onNotify(this: BluetoothRemoteGATTCharacteristic) {
      const value = this.value;
      if (!value) return;
      const bytes = new Uint8Array(value.buffer, value.byteOffset, value.byteLength);
      acc = feedGetChunk(acc, bytes);
      if (!acc.done) {
        onProgress?.(acc.chunks.reduce((n, c) => n + c.length, 0));
        return;
      }
      cleanup();
      if (acc.error) {
        reject(new Error(acc.error));
      } else {
        resolve(new TextDecoder().decode(concatGetChunks(acc)));
      }
    }

    function cleanup() {
      conn.sdChar.removeEventListener("characteristicvaluechanged", onNotify);
    }

    conn.sdChar.addEventListener("characteristicvaluechanged", onNotify);
    conn.sdChar
      .startNotifications()
      .then(() => conn.controlChar.writeValue(new TextEncoder().encode(`GET ${toDevicePath(filename)}`)))
      .catch((err) => {
        cleanup();
        reject(err);
      });
  });

  return withTimeout(job, GET_TIMEOUT_MS, `Timed out downloading "${filename}" from the device.`);
}
