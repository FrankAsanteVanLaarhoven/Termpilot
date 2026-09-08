# @termpilot/g1-humanoid

Reusable FAVL G1 web humanoid used by TermPilot. Pack it once, drop it into
another React/Three.js app. The chest carries neon-tube **FAVL** in the URDF
mesh, so the mark stays with the asset.

## Pack for another project

From the TermPilot repo:

```bash
node packages/g1-humanoid/scripts/pack.mjs
```

That writes `packages/g1-humanoid/dist/g1-humanoid-reuse.zip` containing:

- `src/G1Humanoid.tsx` — gaze, spotlight, joints, lighting
- `robot/g1/` — URDF + STL visuals
- `CAPABILITIES.md` and this README
- `g1-humanoid.css` — required host CSS

Unzip into the other project. Point `urdfUrl` at the copied `robot/g1/g1.urdf`
served as a static file.

## Use

```tsx
import { G1Humanoid } from "./G1Humanoid";

<G1Humanoid
  urdfUrl="/robot/g1/g1.urdf"
  mood="idle"
  expression="welcome"
  variant="stage"
  ariaLabel="G1 humanoid"
/>
```

Peer dependencies: `react`, `three`, `urdf-loader`.

TermPilot's `GrokHumanoid` is a thin wrapper around this controller.
