"use client";

import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceDot,
} from "recharts";
import type { MethodSeries } from "@/lib/types";

const COLORS = ["#4cc3ff", "#7ee0a8", "#e0a87e", "#c8e07e"];

export default function RotationRateChart({
  series,
  headlineUnit,
}: {
  series: MethodSeries[];
  headlineUnit: string;
}) {
  if (!series || series.length === 0 || series.every((s) => s.points.length === 0)) {
    return <div className="empty-state">No series data available for this trial yet.</div>;
  }

  const timeSet = new Set<number>();
  series.forEach((s) => s.points.forEach((p) => timeSet.add(p.t)));
  const times = Array.from(timeSet).sort((a, b) => a - b);

  const merged = times.map((t) => {
    const row: Record<string, number> = { t };
    series.forEach((s) => {
      const pt = s.points.find((p) => p.t === t);
      if (pt) row[s.label] = pt.value;
    });
    return row;
  });

  const dominant = series.find((s) => s.role === "dominant") ?? series[0];
  let peak = dominant.points[0];
  for (const p of dominant.points) {
    if (Math.abs(p.value) > Math.abs(peak.value)) peak = p;
  }

  return (
    <ResponsiveContainer width="100%" height="100%">
      <LineChart data={merged} margin={{ top: 10, right: 20, bottom: 10, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#2a3543" />
        <XAxis
          dataKey="t"
          stroke="#9aa7b4"
          tick={{ fontSize: 11 }}
          label={{ value: "time (s)", position: "insideBottom", offset: -4, fill: "#9aa7b4", fontSize: 11 }}
        />
        <YAxis
          stroke="#9aa7b4"
          tick={{ fontSize: 11 }}
          label={{
            value: headlineUnit,
            angle: -90,
            position: "insideLeft",
            fill: "#9aa7b4",
            fontSize: 11,
          }}
        />
        <Tooltip
          contentStyle={{ background: "#182230", border: "1px solid #2a3543", fontSize: 12 }}
          labelStyle={{ color: "#e6edf3" }}
        />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        {series.map((s, i) => (
          <Line
            key={s.key}
            type="monotone"
            dataKey={s.label}
            stroke={COLORS[i % COLORS.length]}
            strokeWidth={s.role === "dominant" ? 2.5 : 1.25}
            dot={false}
            isAnimationActive={false}
          />
        ))}
        <ReferenceDot
          x={peak.t}
          y={peak.value}
          r={5}
          fill="#f2c14e"
          stroke="#0b0f14"
          label={{ value: "peak", position: "top", fill: "#f2c14e", fontSize: 11 }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
