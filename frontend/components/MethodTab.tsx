import type { MethodOutput, ResearchContent } from "@/lib/types";
import RotationRateChart from "@/components/RotationRateChart";
import KneeHealthScore from "@/components/KneeHealthScore";

function bandClass(band?: "low" | "moderate" | "high") {
  if (!band) return "";
  return `metric-card__band metric-card__band--${band}`;
}

/**
 * The ONE shared tab template used by every analysis method.
 * Contains exactly three things, in order:
 *   1. Researcher's plain-language paragraph(s) for this method
 *   2. The graph(s) of Backend's output for this method
 *   3. Backend's short method report (what it measures / how derived)
 */
export default function MethodTab({
  research,
  output,
}: {
  research: ResearchContent;
  output: MethodOutput;
}) {
  const qf = output.qualityFlags;
  const isEulerDerived = qf.channel_meaning === "euler_deg";
  const isLowConfidenceChannel = qf.channel_meaning_confidence === "low";
  const hasUnverifiedMapping = qf.segment_assignment === "UNVERIFIED";

  // Headline chart: prefer the primary signal (angle, when present and
  // drift-free) per CONTRACT.md; fall back to rate when angle isn't primary.
  const headline =
    output.primarySignal === "relative_angle_deg" && output.primarySeries.length > 0
      ? { series: output.primarySeries, label: "Relative knee angle", kind: "angle" as const }
      : { series: output.rateSeries, label: "Relative knee angular rate", kind: "rate" as const };
  const headlineUnit = headline.series[0]?.unit ?? (headline.kind === "angle" ? "deg" : "deg/s");

  // Secondary series: whichever of angle/rate isn't the headline, shown as
  // supplementary context rather than a second headline.
  const secondary =
    headline.kind === "angle"
      ? { series: output.rateSeries, label: "Relative knee angular rate (secondary, lower-confidence)" }
      : null;

  return (
    <div className="method-tab">
      <KneeHealthScore score={output.kneeHealthScore} />

      <div>
        <h1>{output.methodName}</h1>
        <p className="method-tab__meta">Trial: {output.trialLabel}</p>
      </div>

      {/* Persistent, non-dismissible honesty banner. Always visible — an
          athlete who saw this once should not later mistake the index for
          a calibrated force/torque measurement. */}
      <div className="caveat-banner">
        <strong>This is a relative, qualitative knee-motion index — not a calibrated joint force or torque (no Nm).</strong>{" "}
        It tells you more-vs-less and trending up-vs-down, not an absolute injury risk.
        <ul>
          {(isEulerDerived || isLowConfidenceChannel) && (
            <li>
              The rate (deg/s) readout on this trial is <strong>derived by differentiating angle
              data</strong>, which amplifies noise — treat it as <strong>lower-confidence</strong> than
              the angle/ROM signal.
              {isLowConfidenceChannel && " Channel-meaning detection itself is also low-confidence for this file."}
            </li>
          )}
          {hasUnverifiedMapping && (
            <li>
              Which sensor is femur vs. tibia is <strong>unverified</strong> for this trial (configured
              femur_imu={qf.femur_imu}); sign/axis convention may be inverted.
            </li>
          )}
          {qf.accel_static && (
            <li>
              Accelerometer data was <strong>frozen/static</strong> throughout this trial.
            </li>
          )}
          {output.notes.map((n, i) => <li key={i}>{n}</li>)}
        </ul>
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
          {output.summaryMetrics.map((m) => (
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

        <h2 style={{ marginTop: 20 }}>{headline.label}</h2>
        <div className="chart-wrap">
          <RotationRateChart series={headline.series} headlineUnit={headlineUnit} />
        </div>

        {secondary && secondary.series.length > 0 && (
          <>
            <h2 style={{ marginTop: 20 }}>{secondary.label}</h2>
            <div className="chart-wrap">
              <RotationRateChart series={secondary.series} headlineUnit={secondary.series[0]?.unit ?? "deg/s"} />
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
