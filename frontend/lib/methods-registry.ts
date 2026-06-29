import type { MethodDefinition } from "./types";

// One entry per analysis method / tab. Add new methods here as Backend +
// Researcher deliver each cycle's content. `ready: false` renders a disabled
// nav link with an empty-state instead of a broken page.
export const METHODS_REGISTRY: MethodDefinition[] = [
  {
    id: "knee-rotation-load",
    navLabel: "Knee Rotation Load",
    ready: true,
  },
];
