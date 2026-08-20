import type { MethodOutput, MethodSeries, ResearchContent } from "@/lib/types";
import RotationRateChart from "@/components/RotationRateChart";

function bandClass(band?: "low" | "moderate" | "high") {
  if (!band) return "";
  return `metric-card__band metric-card__band--${band}`;
}

type ChartSpec = { series: MethodSeries[]; label: string; unit?: string };

/**
 * The ONE shared tab template used by every analysis method/sub-score page.
 * Contains exactly three things, in order:
 *   1. Researcher's plain-language paragraph(s) for this method
 *   2. The graph(s) of Backend's output for this method
 *   3. Backend's short method report (what it measures / how derived)
 *
 * Callers pick which chart is the headline for their tab (e.g. angle for
 * Range of Motion, accelerometer magnitude for Landing Mechanics) rather
 * than this component guessing from output.primarySignal, since that field
 * only means something for the Knee Rotation Load tab.
 */
export default function MethodTab({
  title,
  research,
  output,
  headline,
  secondary,
  metricKeys,
}: {
  title: string;
  research: ResearchContent;
  output: MethodOutput;
  headline: ChartSpec;
  secondary?: ChartSpec | null;
  /** Restrict output.summaryMetrics to these keys, in this order. Omit to show all. */
  metricKeys?: string[];
}) {
  const qf = output.qualityFlags;
  const headlineUnit = headline.unit ?? headline.series[0]?.unit ?? "";

  const metrics = metricKeys
    ? metricKeys
        .map((k) => output.summaryMetrics.find((m) => m.key === k))
        .filter((m): m is NonNullable<typeof m> => Boolean(m))
    : output.summaryMetrics;

  return (
    <div className="method-tab">
      <div>
        <h1>{title}</h1>
        <p className="method-tab__meta">Trial: {output.trialLabel}</p>
      </div>

      {/* 1. Researcher's plain-language content */}
      <section className="panel">
        <h2>What this measures</h2>
        {research.summary.map((p, i) => (
          <p key={i}>{p}</p>
        ))}
        {research.subtopics.length > 0 && (
          <div style={{ marginTop: 16 }}>
            {research.subtopics.map((s, i) => (
              <div className="subtopic" key={i}>
                <div className="subtopic__title">
                  <span>{s.title}</span>
                  <span className={`badge badge--${s.strength}`}>{s.strength}</span>
                </div>
                <p>{s.body}</p>
              </div>
            ))}
          </div>
        )}
        <p className="source-note">Source: {research.sourcePath}</p>
      </section>

      {/* 2. Backend's graph(s) */}
      <section className="panel">
        <h2>Data</h2>

        {!qf.usable_motion ? (
          <div className="caveat-banner" style={{ marginBottom: 16 }}>
            <strong>This trial contains no usable movement.</strong> The accelerometer and/or
            angle channels were static for the whole recording (likely the BLE-init freeze,
            commit 657b146). The numbers below are near-zero and are NOT a valid movement
            measurement — flagging rather than scoring them as a real (tiny) result.
          </div>
        ) : null}

        <div className="metric-cards">
          {metrics.map((m) => (
            <div className="metric-card" key={m.key}>
              <div className="metric-card__label">{m.label}</div>
              <div className="metric-card__value">
                {m.value}
                <span className="metric-card__unit">{m.unit}</span>
              </div>
              {m.band && <div className={bandClass(m.band)}>{m.band}</div>}
            </div>
          ))}
        </div>

        {headline.series.length > 0 && (
          <>
            <h2 style={{ marginTop: 20 }}>{headline.label}</h2>
            <div className="chart-wrap">
              <RotationRateChart series={headline.series} headlineUnit={headlineUnit} />
            </div>
          </>
        )}

        {secondary && secondary.series.length > 0 && (
          <>
            <h2 style={{ marginTop: 20 }}>{secondary.label}</h2>
            <div className="chart-wrap">
              <RotationRateChart
                series={secondary.series}
                headlineUnit={secondary.unit ?? secondary.series[0]?.unit ?? ""}
              />
            </div>
          </>
        )}

        <p className={`quality-note ${!qf.usable_motion || qf.accel_static ? "quality-note--flagged" : ""}`}>
          {qf.n_dropped_leading_frozen > 0 &&
            `Dropped ${qf.n_dropped_leading_frozen} leading frozen sample(s) (BLE-init freeze). `}
          Sample rate ~{qf.sample_rate_hz ?? "n/a"} Hz, {qf.n_samples} samples, active window{" "}
          {qf.active_window_s}s.
        </p>
      </section>

      {/* 3. Backend's method report */}
      <section className="panel">
        <h2>Method report</h2>
        <p>
          <strong>What it measures:</strong> {output.report.whatItMeasures}
        </p>
        <p>
          <strong>How it&apos;s derived:</strong> {output.report.howDerived}
        </p>
        <div className="report-grid">
          {Object.entries(output.report.fields).map(([k, v]) => (
            <div className="report-field" key={k}>
              <div className="report-field__key">{k}</div>
              <div className="report-field__val">{String(v)}</div>
            </div>
          ))}
        </div>
        <p className="source-note" style={{ marginTop: 12 }}>
          Source: {output.sourcePaths.join(", ")}
        </p>
      </section>
    </div>
  );
}
