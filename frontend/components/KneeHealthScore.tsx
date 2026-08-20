import type { KneeHealthScore as KneeHealthScoreData } from "@/lib/types";

const RADIUS = 42;
const STROKE = 8;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

/** Red (0) -> yellow (~50) -> green (100), via HSL hue interpolation. */
function colorForScore(score: number): string {
  const hue = Math.max(0, Math.min(120, (score / 100) * 120));
  return `hsl(${hue}, 68%, 46%)`;
}

export default function KneeHealthScore({ score }: { score: KneeHealthScoreData }) {
  const value = score.value;
  const hasValue = value !== null;
  const color = hasValue ? colorForScore(value) : "var(--text-dim)";
  const offset = hasValue ? CIRCUMFERENCE * (1 - value / 100) : 0;

  return (
    <div className="knee-health-score">
      <div className="knee-health-score__hero">
        <svg width={104} height={104} viewBox="0 0 104 104" className="knee-health-score__ring">
          <circle cx={52} cy={52} r={RADIUS} fill="none" stroke="var(--border)" strokeWidth={STROKE} />
          {hasValue && (
            <circle
              cx={52}
              cy={52}
              r={RADIUS}
              fill="none"
              stroke={color}
              strokeWidth={STROKE}
              strokeLinecap="round"
              strokeDasharray={CIRCUMFERENCE}
              strokeDashoffset={offset}
              transform="rotate(-90 52 52)"
            />
          )}
          <text x={52} y={49} textAnchor="middle" className="knee-health-score__ring-value">
            {hasValue ? Math.round(value) : "—"}
          </text>
          <text x={52} y={66} textAnchor="middle" className="knee-health-score__ring-unit">
            {hasValue ? "/ 100" : "n/a"}
          </text>
        </svg>
        <div>
          <div className="knee-health-score__label">Knee Health Score</div>
          <p className="knee-health-score__desc">
            Weighted composite of relative knee load, range of motion, and landing mechanics — a
            relative, qualitative proxy, not a clinical or injury-risk score.
          </p>
          {!hasValue && (
            <p className="knee-health-score__nodata">
              Not available for this trial — at least one sub-score below is missing (needs usable,
              non-frozen accelerometer data and a real range-of-motion reading).
            </p>
          )}
        </div>
      </div>

      <div className="knee-health-score__subscores">
        {score.subScores.map((s) => (
          <div className="knee-health-score__subscore" key={s.key}>
            <div className="knee-health-score__subscore-label">{s.label}</div>
            <div
              className="knee-health-score__subscore-value"
              style={{ color: s.value !== null ? colorForScore(s.value) : "var(--text-dim)" }}
            >
              {s.value !== null ? Math.round(s.value) : "—"}
              <span className="knee-health-score__subscore-unit">/100</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
