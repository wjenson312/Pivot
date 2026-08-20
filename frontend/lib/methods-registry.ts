import type { MethodDefinition } from "./types";

// One entry per analysis method / tab — the single source of truth AppDock
// reads to build the floating nav's sub-score items. `ready: false` would
// mean "no page yet" (not currently used; all three ship together).
export const METHODS_REGISTRY: MethodDefinition[] = [
  {
    id: "knee-rotation-load",
    navLabel: "Knee Rotation Load",
    ready: true,
  },
  {
    id: "range-of-motion",
    navLabel: "Range of Motion",
    ready: true,
  },
  {
    id: "landing-mechanics",
    navLabel: "Landing Mechanics",
    ready: true,
  },
];
