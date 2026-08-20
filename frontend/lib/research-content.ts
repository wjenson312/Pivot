import type { ResearchContent } from "./types";

// Derived view of Researcher's brief for the "Knee Rotation Load" method.
// Source of truth: /ai-agent/research/relative-tibial-femoral-rotation-rate.md
// We never edit that file — this is a hand-curated copy of its key content
// shaped for the shared MethodTab template.
export const KNEE_ROTATION_LOAD_RESEARCH: ResearchContent = {
  summary: [
    "Pivot has one motion sensor on your thigh (femur) and one on your shin (tibia). When your knee twists or bends, the two sensors rotate by different amounts. By subtracting the thigh sensor's rotation rate from the shin sensor's rotation rate, we get the relative rotation rate across the knee — how fast the joint itself is being twisted/flexed, separate from how fast your whole leg is swinging.",
    "We roll this into a Knee Rotation Load Index (the peak relative rotation rate in a movement, plus the cumulative amount over a session). A higher index means the knee is being rotated harder and more often — which the literature links to greater strain on the ACL and surrounding tissue. This is a relative, qualitative load signal, not a calibrated joint torque in newton-metres. It tells you more vs. less and trending up vs. down, not an absolute force value.",
  ],
  subtopics: [
    {
      title: "Tibial rotation and anterior translation load the ACL",
      strength: "well-established",
      body: "Cadaveric and in-vivo strain studies show the ACL is the primary restraint to anterior tibial translation and a secondary restraint to internal tibial rotation, with ACL force/strain rising as these motions increase (Markolf et al. 1995, 1990; Beynnon et al. 1995; Fleming & Beynnon 2004). When the shin rotates or slides relative to the thigh, the ACL is what stops it — larger/faster relative tibial-femoral rotation means the ACL and capsule are working harder.",
    },
    {
      title: "Combined rotational + valgus loading: injury mechanism (well-established) vs. rotation-rate as a tracked risk signal (emerging)",
      strength: "emerging",
      body: "Non-contact ACL injuries cluster around a multiplanar pattern combining internal tibial rotation with knee valgus near full extension during landing/cutting — that mechanism itself is well-established (Hewett et al. 2005; Quatman et al. 2010; Koga et al. 2010). Using a rotation-rate signal like this one to track that risk in the field is emerging: rotation alone is a partial picture (valgus and timing also matter), so the index is framed as a load proxy, not an injury predictor.",
    },
    {
      title: "Cumulative/repetitive load: dose-response principle (well-established) vs. this single-joint rotational dose (experimental)",
      strength: "experimental",
      body: "That tissue adapts to load following a dose-response relationship — moderate cyclic loading strengthens tissue, while load accumulating faster than adaptation drives overuse injury — is a well-established principle (Frost 2003; Schoenfeld 2010; Gabbett 2016, acute:chronic workload). Operationalizing that principle as a single-joint rotational 'dose' from two IMUs, as done here, is experimental and not yet validated against real injury outcomes — best read relative to the athlete's own trend, not an absolute cutoff.",
    },
    {
      title: "Relative segment angular velocity (gyro differencing) reflects joint angular velocity",
      strength: "emerging",
      body: "omega_rel = omega_tibia − omega_femur is a kinematically sound estimate of knee angular velocity (Seel et al. 2014) — well-established as kinematics. Using it as a loading proxy is emerging: rotation rate correlates with strain rate, but angular velocity is not force; it indexes how vigorously the joint is driven, not the actual load path (which also depends on muscle co-contraction and ground reaction force).",
    },
    {
      title: "IMUs can validly measure knee angle and angular velocity in the field",
      strength: "well-established",
      body: "Wearable IMUs estimate knee flexion-extension angle/rate with good agreement to optical motion capture (Seel et al. 2014; Cooper et al. 2009; Favre et al. 2008). Transverse-plane (rotation) estimates are noisier and less validated than sagittal angle (Cutti et al. 2010). Working with rate (not integrated angle) and with relative (differenced) quantities cancels shared drift — the basis for this method's design.",
    },
    {
      title: "Why not accelerometer-derived translation this cycle",
      strength: "well-established",
      body: "Estimating tibial translation by double-integrating accelerometer signals is known to be unreliable — integration compounds bias/noise into rapidly growing position error (Woodman 2007). This is the methodological reason, independent of this dataset's frozen-accelerometer artifact, to scope cycle 1 to rotation rate rather than translation.",
    },
  ],
  sourcePath: "/ai-agent/research/relative-tibial-femoral-rotation-rate.md",
};

// Derived view for the "Range of Motion" sub-score tab.
// Source of truth: /ai-agent/research/athlete-training-metrics-reference.md,
// /ai-agent/research/wearable-metrics-by-location.md
export const RANGE_OF_MOTION_RESEARCH: ResearchContent = {
  summary: [
    "Range of motion (ROM) is how far your knee joint can move — the peak-to-peak swing of the relative angle between the thigh and shin sensors over a trial. It's a standard mobility screen: low ROM relative to what a joint should achieve can flag a mobility deficit or guarding around an injury; healthy, full ROM is generally the goal.",
    "The Range of Motion Score normalizes the raw ROM (in degrees) onto a 0-100 scale against a 90° reference — the same reference the Relative Knee Load score uses for its angle branch. That reference is a provisional convention for this dataset, not a clinical norm, and will be retuned as more real trials come in.",
  ],
  subtopics: [
    {
      title: "Dual-IMU ROM tracking is validated against motion capture",
      strength: "well-established",
      body: "A thigh+shank IMU pair spanning the knee gets within a few degrees of goniometry/optical motion capture once calibrated, for sagittal-plane (flexion-extension) motion in particular (Seel et al. 2014; Cooper et al. 2009; Favre et al. 2008). Soft-tissue motion relative to the sensor housing is the main error source, not the sensing principle itself.",
    },
    {
      title: "ROM as a mobility screen (well-established) vs. this 0-100 normalization (experimental)",
      strength: "experimental",
      body: "Using joint ROM to screen for mobility deficits is standard practice in sports medicine and physical therapy. Compressing that raw degree figure into a 0-100 score against a single 90° reference is this project's own simplification, not a validated clinical threshold — read it as a relative, trial-to-trial comparison, not an absolute pass/fail mobility grade.",
    },
    {
      title: "A single-trial ROM number can't diagnose a deficit on its own",
      strength: "well-established",
      body: "Clinical ROM screening compares a joint against a healthy contralateral side, a pre-injury baseline, or normative population data — a lone number from one trial, with no comparison point, only tells you what happened in that specific movement, not whether the joint's mobility is actually restricted.",
    },
  ],
  sourcePath: "/ai-agent/research/athlete-training-metrics-reference.md",
};

// Derived view for the "Landing Mechanics" sub-score tab.
// Source of truth: /ai-agent/research/wearable-metrics-by-location.md,
// /ai-agent/research/hardware-upgrade-strategy.md
export const LANDING_MECHANICS_RESEARCH: ResearchContent = {
  summary: [
    "Landing mechanics is about how the body absorbs force when it hits the ground — a major screen for ACL injury risk, clinically assessed through things like knee valgus (inward buckling) and trunk lean on landing. Pivot's two IMUs, mounted on the thigh and shin, can't isolate those frontal-plane signals with confidence yet.",
    "What this tab actually shows is a coarser proxy: the peak deviation from resting gravity (1g) in the tibia (shin) accelerometer during the trial — how hard an impact registered at the shin — inverted so a softer, more controlled landing scores higher. Treat this as an impact-intensity proxy, not a landing-technique assessment.",
  ],
  subtopics: [
    {
      title: "Valgus + trunk lean is the well-established clinical screen (this sensor doesn't measure it)",
      strength: "well-established",
      body: "Landing mechanics screening for ACL risk centers on frontal-plane knee valgus and trunk control near touchdown (Hewett et al. 2005). Thigh+shank IMU setups like Pivot's can approximate gross valgus patterns but miss the precision of 3D motion capture for the frontal-plane angles this screen actually relies on — accuracy is meaningfully lower here than for sagittal-plane (flexion) ROM.",
    },
    {
      title: "Accelerometer peak magnitude as an impact-intensity proxy",
      strength: "experimental",
      body: "A single accelerometer's peak deviation from 1g is a rough stand-in for impact intensity, not a calibrated ground-reaction-force measurement — that would need a force plate or instrumented insole and higher sample-rate, anti-aliased accelerometer data than the current hardware collects. The team's own hardware-upgrade research already flags this: without an insole/FSR sensor, an impact feature is 'an accel transient,' not a physically grounded force signal.",
    },
    {
      title: "This is a proxy, not a landing-technique assessment",
      strength: "experimental",
      body: "A hard peak reading here says the impact was intense; it does not say whether the knee collapsed into valgus, whether the trunk stayed controlled, or whether the landing was otherwise 'good' or 'bad' technique. Read the Landing Mechanics score as intensity, not quality, until a true frontal-plane or ground-reaction-force signal is added.",
    },
  ],
  sourcePath: "/ai-agent/research/wearable-metrics-by-location.md",
};
