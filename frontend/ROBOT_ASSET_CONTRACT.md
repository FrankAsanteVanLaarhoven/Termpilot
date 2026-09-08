# TermPilot humanoid asset contract

Reusable pack: `packages/g1-humanoid` (`node packages/g1-humanoid/scripts/pack.mjs`).
The live controller is `frontend/lib/g1/G1Humanoid.tsx`.

TermPilot must not manufacture a substitute robot from primitive geometry.

## Web asset

The browser loads `public/robot/g1/g1.urdf` and its individual STL visual
meshes through Three.js and `urdf-loader`. Pointer tracking and TermPilot's
conversation states drive the loaded joint hierarchy directly. If WebGL or any
required asset fails, TermPilot falls back to the approved
`public/splash/grokbot-humanoid.png` reference and does not claim that fallback
is interactive.

## Robotics asset

A URDF/Xacro package is accepted only when it includes:

- a uniquely named link and joint tree;
- visual and collision meshes with explicit units;
- joint origins, axes, types and limits;
- masses, centres of mass and inertia tensors;
- source, version and licence provenance; and
- validation with `check_urdf` plus a visual inspection in RViz or the target simulator.

A Spline scene or rendered image is not a URDF and must not be presented as a
physical robot digital twin.

## Included reconstruction base

The interactive prototype uses the Unitree G1 model from
`inria-paris-robotics-lab/unitree_description` at upstream commit
`5635136ee43ef704e4edb87a58aa5495935d2fba`. The ROS package declares a BSD
licence in `package.xml`; TermPilot preserves the source attribution here.

This provides a genuine 29-DoF kinematic hierarchy and individual visual STL
meshes. TermPilot changes the browser materials, lighting and motion controller
to approach the supplied black-metal/cyan concept frame. The chest nameplate is
replaced with neon-tube **FAVL** so the reusable URDF reads as this reconstruction,
not Unitree OEM CAD. It is not presented as an exact Unitree simulator,
manufacturer CAD, or a physically validated model of the fictional robot in the
reference image.
