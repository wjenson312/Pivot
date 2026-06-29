"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  type BleConnection,
  connectToDevice,
  disconnectDevice,
  downloadRemoteFile,
  isWebBluetoothSupported,
  listRemoteFiles,
} from "@/lib/ble-sync";

type FileStatus = "new" | "imported" | "importing" | "done" | "error";

interface RemoteFile {
  filename: string;
  status: FileStatus;
  error?: string;
  bytesReceived?: number;
}

export default function BleSyncPanel({ existingRunIds }: { existingRunIds: string[] }) {
  const router = useRouter();
  // navigator.bluetooth only exists client-side; resolving this in an effect
  // (rather than at render time) avoids an SSR/hydration mismatch — the
  // server has no navigator at all, so it always renders the same neutral
  // shell until the client determines real support.
  const [supported, setSupported] = useState<boolean | null>(null);
  useEffect(() => {
    setSupported(isWebBluetoothSupported());
  }, []);

  const [conn, setConn] = useState<BleConnection | null>(null);
  const [deviceName, setDeviceName] = useState<string | null>(null);
  const [connecting, setConnecting] = useState(false);
  const [listing, setListing] = useState(false);
  const [importing, setImporting] = useState(false);
  const [files, setFiles] = useState<RemoteFile[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);

  async function refreshFileList(c: BleConnection) {
    setListing(true);
    setError(null);
    try {
      const remoteNames = await listRemoteFiles(c);
      const existing = new Set(existingRunIds);
      const next: RemoteFile[] = remoteNames.map((name) => ({
        filename: name,
        status: existing.has(name.replace(/\.csv$/i, "")) ? "imported" : "new",
      }));
      setFiles(next);
      setSelected(new Set(next.filter((f) => f.status === "new").map((f) => f.filename)));
    } catch (err) {
      setError((err as Error).message || "Could not list files on the device.");
    } finally {
      setListing(false);
    }
  }

  async function handleConnect() {
    setError(null);
    setConnecting(true);
    try {
      const c = await connectToDevice();
      c.device.addEventListener("gattserverdisconnected", () => {
        setConn(null);
        setDeviceName(null);
        setFiles([]);
        setSelected(new Set());
      });
      setConn(c);
      setDeviceName(c.device.name ?? "device");
      await refreshFileList(c);
    } catch (err) {
      setError((err as Error).message || "Could not connect to device.");
    } finally {
      setConnecting(false);
    }
  }

  function handleDisconnect() {
    if (conn) disconnectDevice(conn);
    setConn(null);
    setDeviceName(null);
    setFiles([]);
    setSelected(new Set());
  }

  function toggleSelected(filename: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(filename)) next.delete(filename);
      else next.add(filename);
      return next;
    });
  }

  async function handleImport() {
    if (!conn) return;
    setImporting(true);
    setError(null);

    const targets = files.filter((f) => selected.has(f.filename));
    for (const target of targets) {
      setFiles((prev) =>
        prev.map((f) => (f.filename === target.filename ? { ...f, status: "importing", bytesReceived: 0 } : f))
      );
      try {
        const content = await downloadRemoteFile(conn, target.filename, (bytes) => {
          setFiles((prev) =>
            prev.map((f) => (f.filename === target.filename ? { ...f, bytesReceived: bytes } : f))
          );
        });
        const res = await fetch("/api/runs/import", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ filename: target.filename, content }),
        });
        const resBody = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(resBody.error || "Import failed.");
        setFiles((prev) => prev.map((f) => (f.filename === target.filename ? { ...f, status: "done" } : f)));
      } catch (err) {
        setFiles((prev) =>
          prev.map((f) =>
            f.filename === target.filename
              ? { ...f, status: "error", error: (err as Error).message }
              : f
          )
        );
      }
    }

    setImporting(false);
    router.refresh();
  }

  if (supported === null) {
    return (
      <div className="ble-sync">
        <strong>Sync from device</strong>
      </div>
    );
  }

  if (!supported) {
    return (
      <div className="ble-sync">
        <strong>Sync from device</strong>
        <p className="ble-sync__hint">
          Web Bluetooth isn&apos;t supported in this browser. Use a recent version of Chrome or
          Edge (desktop or Android) to sync runs from the device&apos;s microSD card.
        </p>
      </div>
    );
  }

  return (
    <div className="ble-sync">
      <div className="ble-sync__header">
        <strong>Sync from device</strong>
        {conn ? (
          <button className="ble-sync__btn" onClick={handleDisconnect}>
            Disconnect{deviceName ? ` (${deviceName})` : ""}
          </button>
        ) : (
          <button className="ble-sync__btn ble-sync__btn--primary" onClick={handleConnect} disabled={connecting}>
            {connecting ? "Connecting…" : "Connect to device"}
          </button>
        )}
      </div>

      <p className="ble-sync__hint">
        Hold the device&apos;s button for 2+ seconds until it enters BLE sync mode before
        connecting — it only accepts connections while advertising in that mode.
      </p>

      {error && <div className="ble-sync__error">{error}</div>}

      {conn && (
        <>
          {listing ? (
            <p className="ble-sync__hint">Listing files on device…</p>
          ) : files.length === 0 ? (
            <p className="ble-sync__hint">No run_*.csv files found on the device&apos;s SD card.</p>
          ) : (
            <>
              <ul className="ble-sync__file-list">
                {files.map((f) => (
                  <li key={f.filename} className="ble-sync__file">
                    <label className="ble-sync__file-label">
                      <input
                        type="checkbox"
                        checked={selected.has(f.filename)}
                        disabled={f.status === "importing" || f.status === "imported" || importing}
                        onChange={() => toggleSelected(f.filename)}
                      />
                      {f.filename}
                    </label>
                    <span className={`ble-sync__file-status ble-sync__file-status--${f.status}`}>
                      {f.status === "imported" && "already imported"}
                      {f.status === "new" && "new"}
                      {f.status === "importing" && `downloading… ${f.bytesReceived ?? 0} B`}
                      {f.status === "done" && "imported ✓"}
                      {f.status === "error" && (f.error || "failed")}
                    </span>
                  </li>
                ))}
              </ul>
              <button
                className="ble-sync__btn ble-sync__btn--primary"
                onClick={handleImport}
                disabled={importing || selected.size === 0}
              >
                {importing ? "Importing…" : `Import ${selected.size} selected`}
              </button>
            </>
          )}
        </>
      )}
    </div>
  );
}
