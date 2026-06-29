"use client";

import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import type { RunRecord } from "@/lib/runs-registry";
import { formatRelativeTime } from "@/lib/format-time";

type Toast = { kind: "success" | "error"; message: string };
type Busy = { id: string; action: "selecting" | "deleting" } | null;

type SortOption = "recorded-desc" | "recorded-asc" | "name-asc" | "name-desc";

const SORT_LABELS: Record<SortOption, string> = {
  "recorded-desc": "Recorded (newest)",
  "recorded-asc": "Recorded (oldest)",
  "name-asc": "Name (A–Z)",
  "name-desc": "Name (Z–A)",
};

export default function RunList({
  runs,
  selectedRunId,
}: {
  runs: RunRecord[];
  selectedRunId: string | null;
}) {
  const router = useRouter();
  const [editingId, setEditingId] = useState<string | null>(null);
  const [draftName, setDraftName] = useState("");
  const [busy, setBusy] = useState<Busy>(null);
  const [sortBy, setSortBy] = useState<SortOption>("recorded-desc");
  const [query, setQuery] = useState("");
  const [toast, setToast] = useState<Toast | null>(null);

  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(null), 3500);
    return () => clearTimeout(t);
  }, [toast]);

  const filteredRuns = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return runs;
    return runs.filter((r) => r.name.toLowerCase().includes(q));
  }, [runs, query]);

  const sortedRuns = useMemo(() => {
    const copy = [...filteredRuns];
    switch (sortBy) {
      case "recorded-desc":
        copy.sort((a, b) => b.recordedAt.localeCompare(a.recordedAt));
        break;
      case "recorded-asc":
        copy.sort((a, b) => a.recordedAt.localeCompare(b.recordedAt));
        break;
      case "name-asc":
        copy.sort((a, b) => a.name.localeCompare(b.name));
        break;
      case "name-desc":
        copy.sort((a, b) => b.name.localeCompare(a.name));
        break;
    }
    return copy;
  }, [filteredRuns, sortBy]);

  async function selectRun(run: RunRecord) {
    setBusy({ id: run.id, action: "selecting" });
    try {
      const res = await fetch("/api/runs/select", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ runId: run.id }),
      });
      if (!res.ok) throw new Error();
      setToast({ kind: "success", message: `Now viewing "${run.name}"` });
      router.refresh();
    } catch {
      setToast({ kind: "error", message: `Couldn't select "${run.name}". Try again.` });
    } finally {
      setBusy(null);
    }
  }

  function startRename(run: RunRecord) {
    setEditingId(run.id);
    setDraftName(run.name);
  }

  async function commitRename(id: string) {
    const name = draftName.trim();
    setEditingId(null);
    if (!name) return;
    try {
      const res = await fetch(`/api/runs/${encodeURIComponent(id)}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name }),
      });
      if (!res.ok) throw new Error();
      setToast({ kind: "success", message: "Run renamed" });
      router.refresh();
    } catch {
      setToast({ kind: "error", message: "Couldn't rename run. Try again." });
    }
  }

  async function removeRun(run: RunRecord) {
    const confirmed = window.confirm(`Delete run "${run.name}"? This cannot be undone.`);
    if (!confirmed) return;
    setBusy({ id: run.id, action: "deleting" });
    try {
      const res = await fetch(`/api/runs/${encodeURIComponent(run.id)}`, { method: "DELETE" });
      if (!res.ok) throw new Error();
      setToast({ kind: "success", message: `Deleted "${run.name}"` });
      router.refresh();
    } catch {
      setToast({ kind: "error", message: `Couldn't delete "${run.name}". Try again.` });
    } finally {
      setBusy(null);
    }
  }

  return (
    <>
      {toast && <div className={`run-list__toast run-list__toast--${toast.kind}`}>{toast.message}</div>}
      <div className="run-list__toolbar">
        <input
          className="run-list__search"
          type="search"
          placeholder="Filter by name…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <span className="run-list__count">
          {query.trim()
            ? `${sortedRuns.length} of ${runs.length} runs`
            : `${runs.length} run${runs.length === 1 ? "" : "s"}`}
        </span>
        <label className="run-list__sort">
          Sort by:
          <select
            className="run-list__sort-select"
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as SortOption)}
          >
            {Object.entries(SORT_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
      </div>
      <table className="run-table">
      <thead>
        <tr>
          <th></th>
          <th>Run name</th>
          <th>Recorded</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        {sortedRuns.length === 0 && (
          <tr>
            <td colSpan={4} className="run-table__no-matches">
              No runs match &quot;{query.trim()}&quot;.
            </td>
          </tr>
        )}
        {sortedRuns.map((run) => {
          const isSelected = run.id === selectedRunId;
          const isEditing = editingId === run.id;
          const isSelecting = busy?.id === run.id && busy.action === "selecting";
          const isDeleting = busy?.id === run.id && busy.action === "deleting";
          const isBusy = isSelecting || isDeleting;
          return (
            <tr key={run.id} className={isSelected ? "run-table__row--selected" : ""}>
              <td>
                <button
                  className="run-table__select-btn"
                  disabled={isSelected || isBusy}
                  onClick={() => selectRun(run)}
                >
                  {isSelecting ? "Selecting…" : isSelected ? "Selected" : "Select"}
                </button>
              </td>
              <td>
                {isEditing ? (
                  <input
                    className="run-table__name-input"
                    autoFocus
                    value={draftName}
                    onChange={(e) => setDraftName(e.target.value)}
                    onBlur={() => commitRename(run.id)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") commitRename(run.id);
                      if (e.key === "Escape") setEditingId(null);
                    }}
                  />
                ) : (
                  <span className="run-table__name-wrap">
                    <span className="run-table__name-text">{run.name}</span>
                    <button
                      className="run-table__rename-btn"
                      onClick={() => startRename(run)}
                      title="Rename"
                      aria-label={`Rename ${run.name}`}
                    >
                      ✎
                    </button>
                  </span>
                )}
              </td>
              <td className="run-table__recorded" title={new Date(run.recordedAt).toLocaleString()}>
                {formatRelativeTime(run.recordedAt)}
              </td>
              <td>
                <button
                  className="run-table__delete-btn"
                  disabled={isBusy}
                  onClick={() => removeRun(run)}
                >
                  {isDeleting ? "Deleting…" : "Delete"}
                </button>
              </td>
            </tr>
          );
        })}
      </tbody>
      </table>
    </>
  );
}
