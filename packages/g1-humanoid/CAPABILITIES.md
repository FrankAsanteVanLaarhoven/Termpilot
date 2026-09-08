# G1 humanoid capabilities

The reusable web controller in `src/G1Humanoid.tsx` (source of truth:
`frontend/lib/g1/G1Humanoid.tsx`) provides:

| Capability | Behaviour |
| --- | --- |
| URDF load | Three.js + `urdf-loader` of the 29-DoF `g1.urdf` and STL visuals |
| FAVL chest mark | Neon-blue tube initials on `logo_link`; the mark is in the URDF mesh, not a CSS overlay |
| Neck-pivoted gaze | Helmet rotates at a neck pivot, not the chest joint, so the head stays attached |
| Screen-aligned look | Cursor left/right yaws the head; cursor up/down nods. Eyes follow in the visor |
| Page pointer | `pointermove` is window-level, so looking at UI beside the canvas still works |
| Follow spotlight | A `SpotLight` tracks the pointer and lights the visor from that side |
| Key / rim / fill | Front key, cyan rim, cool fill, camera-mounted face light |
| Conversation motion | Listening, thinking and speaking change gesture, breath and blink |
| Bounded joints | Shoulder, elbow, wrist, hip, knee and ankle stay inside small safe ranges |
| Fit-to-stage | Model is scaled to a known height so the camera is never inside a mesh |
| Fallback | If WebGL or meshes fail, the host supplies a static image; it is not claimed interactive |

## Required host files

Copy from TermPilot:

- `frontend/public/robot/g1/g1.urdf`
- `frontend/public/robot/g1/assets/visuals/*.STL`
- Optional: `frontend/public/splash/grokbot-humanoid.png` as fallback
- CSS classes `.tp-bot`, `.tp-bot-spline`, `.tp-bot-loading`, `.tp-bot-reference` from `frontend/app/globals.css`

## Licence note

Kinematic meshes come from `inria-paris-robotics-lab/unitree_description` (BSD in
`package.xml`, upstream commit `5635136ee43ef704e4edb87a58aa5495935d2fba`).
Keep that attribution. The chest nameplate is TermPilot's FAVL neon mark, not
Unitree manufacturer CAD. Rebuild it with `scripts/make_favl_logo.py`.
