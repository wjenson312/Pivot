import type { ResearchContent } from "./types";

// Derived view of Researcher's brief for the "Knee Rotation Load" method.
// Source of truth: /research/relative-tibial-femoral-rotation-rate.md
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
  sourcePath: "/research/relative-tibial-femoral-rotation-rate.md",
};
