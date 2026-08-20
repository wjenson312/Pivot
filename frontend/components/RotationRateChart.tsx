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

// Dominant/headline series gets the one warm brand accent; the rest stay
// in the achromatic-plus-supporting-wash family (see globals.css tokens).
const COLORS = ["#ff6363", "#56c2ff", "#59d499", "#9c9c9d"];

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
        <CartesianGrid strokeDasharray="3 3" stroke="#363739" />
        <XAxis
          dataKey="t"
          stroke="#9c9c9d"
          tick={{ fontSize: 11, fontFamily: "var(--font-sans)" }}
          label={{ value: "time (s)", position: "insideBottom", offset: -4, fill: "#9c9c9d", fontSize: 11 }}
        />
        <YAxis
          stroke="#9c9c9d"
          tick={{ fontSize: 11, fontFamily: "var(--font-sans)" }}
          label={{
            value: headlineUnit,
            angle: -90,
            position: "insideLeft",
            fill: "#9c9c9d",
            fontSize: 11,
          }}
        />
        <Tooltip
          contentStyle={{
            background: "#111214",
            border: "1px solid #363739",
            borderRadius: 8,
            fontSize: 12,
            fontFamily: "var(--font-sans)",
          }}
          labelStyle={{ color: "#ffffff" }}
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
          fill="#ffb166"
          stroke="#040506"
          label={{ value: "peak", position: "top", fill: "#ffb166", fontSize: 11 }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
