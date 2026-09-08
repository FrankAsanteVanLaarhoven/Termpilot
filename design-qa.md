# TermPilot Robot Design QA

## Visual target

- Source: `upload/Screenshot 2026-09-05 at 06.10.31(1).png`
- Required traits: glossy black humanoid shell, rounded head, paired white eyes, exposed neck and abdominal mechanisms, concentric mechanical joints, and cyan illuminated seams with an ECG chest trace.

## Implemented result

- The exact supplied character artwork is used as the automatic visual fallback.
- The live Spline runtime reconstructs the same design language with an elongated glossy head, white eyes, temple actuator, collar, broad chest shell, cyan ECG trace, concentric shoulder/elbow joints, arm armour, abdominal cables, waist ring, and articulated limbs.
- Pointer gaze and expression-specific head, arm, breathing, and pulse animation are connected.

## Comparison

| Criterion | Result | Evidence |
|---|---|---|
| Reference body identity | Pass in fallback | Browser capture shows the supplied full-body character artwork. |
| Black metallic material language | Pass in fallback | Black reflective shell and gunmetal mechanisms are visible. |
| White eye design | Pass in fallback | Two vertical white eyes match the reference. |
| Cyan seams and chest ECG | Pass in fallback | Cyan joint seams and chest pulse are visible. |
| Responsive desktop composition | Pass | Robot remains left of the onboarding card without overlap. |
| Graceful degradation | Pass | WebGL failure switches to the exact reference render without breaking the flow. |
| Live 3D visual fidelity | Blocked | The managed browser reports WebGL disabled and cannot render the Spline canvas. |

## Remaining uncertainty

The supplied reference contains one three-quarter view. Rear geometry and hidden side topology are reconstructed rather than observed. Live 3D rendering must be checked in a WebGL-capable browser before claiming a verified 360-degree match.

**final result: blocked**
