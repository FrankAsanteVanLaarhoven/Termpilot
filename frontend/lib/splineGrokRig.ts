import type { Application, CreateMaterialOptions, SPEObject } from "@splinetool/runtime";

export type GrokRig = {
  root: SPEObject;
  head: SPEObject;
  torso: SPEObject;
  pulse: SPEObject;
  armL: SPEObject;
  armR: SPEObject;
  eyeL: SPEObject;
  eyeR: SPEObject;
  handL: SPEObject;
  handR: SPEObject;
  hips: SPEObject;
  legL: SPEObject;
  legR: SPEObject;
  neck: SPEObject;
  foreL: SPEObject;
  foreR: SPEObject;
  shinL: SPEObject;
  shinR: SPEObject;
  footL: SPEObject;
  footR: SPEObject;
};

const BLACK: CreateMaterialOptions = { color: "#07090c", roughness: 0.08, metalness: 0.96 };
const GUN: CreateMaterialOptions = { color: "#202a34", roughness: 0.2, metalness: 0.86 };
const CYAN: CreateMaterialOptions = { color: "#18e3f2", roughness: 0.12, metalness: 0.5 };
const WHITE: CreateMaterialOptions = { color: "#f4f6f8", roughness: 0.18, metalness: 0.08 };

async function make(
  app: Application,
  type: string,
  options: Record<string, unknown>,
): Promise<SPEObject> {
  return app.createObject(type, options);
}

export async function buildGrokRig(app: Application): Promise<GrokRig> {
  for (const obj of app.getAllObjects()) {
    const name = (obj.name || "").toLowerCase();
    if (name.includes("camera") || name.includes("light") || name.includes("sun")) continue;
    try {
      obj.hide();
    } catch {
      /* some scene nodes are not hideable */
    }
  }

  try {
    app.setBackgroundColor("#05070a");
  } catch {
    /* host scene may lock background */
  }

  const root = await make(app, "Group", { name: "GrokRig", position: [0, -40, 0] });

  const torso = await make(app, "Cube", {
    name: "GrokTorso",
    parent: root,
    position: [0, 92, 0],
    width: 126,
    height: 112,
    depth: 62,
    cornerRadius: 22,
    material: GUN,
    castShadow: true,
  });
  torso.scale.x = 1.08;
  torso.scale.z = 0.92;

  const pulse = await make(app, "Group", {
    name: "GrokPulse",
    parent: root,
    position: [0, 108, 30],
  });
  const pulseSegments: Array<[number, number, number, number]> = [
    [-48, 0, 25, 0], [-24, 0, 14, 0], [-11, 7, 16, 58], [0, -1, 23, -70],
    [16, 1, 22, 48], [34, 0, 18, 0], [50, 0, 14, 0],
  ];
  for (const [x, y, width, rotation] of pulseSegments) {
    await make(app, "Cube", {
      name: "GrokPulseTrace", parent: pulse, position: [x, y, 4], width,
      height: 2.2, depth: 3.2, cornerRadius: 1, rotation: [0, 0, rotation], material: CYAN,
    });
  }

  const neck = await make(app, "Cylinder", {
    name: "GrokNeck",
    parent: root,
    position: [0, 152, 0],
    height: 22,
    width: 16,
    material: GUN,
  });

  await make(app, "Cylinder", {
    name: "GrokCableL",
    parent: root,
    position: [-7, 150, 6],
    height: 18,
    width: 4.4,
    rotation: [8, 0, -12],
    material: { color: "#1a222c", roughness: 0.5, metalness: 0.4 },
  });
  await make(app, "Cylinder", {
    name: "GrokCableR",
    parent: root,
    position: [7, 150, 6],
    height: 18,
    width: 4.4,
    rotation: [8, 0, 12],
    material: { color: "#1a222c", roughness: 0.5, metalness: 0.4 },
  });

  const head = await make(app, "Group", { name: "GrokHead", parent: root, position: [0, 188, 0] });

  await make(app, "Sphere", {
    name: "GrokSkull",
    parent: head,
    position: [0, 0, 0],
    width: 94,
    scale: [0.9, 1.08, 0.86],
    material: BLACK,
    castShadow: true,
  });

  const eye = async (name: string, x: number) => {
    return make(app, "Sphere", {
      name,
      parent: head,
      position: [x, 16, 34],
      width: 18,
      scale: [0.5, 1.05, 0.34],
      rotation: [0, 0, name.endsWith("L") ? -14 : 14],
      material: WHITE,
    });
  };
  const eyeL = await eye("GrokEyeL", -13);
  const eyeR = await eye("GrokEyeR", 13);

  // Temple actuator visible in the three-quarter reference view.
  await make(app, "Cylinder", {
    name: "GrokTempleL", parent: head, position: [-42, 2, 0], rotation: [0, 0, 90],
    height: 8, width: 19, material: GUN,
  });
  await make(app, "Torus", {
    name: "GrokTempleRingL", parent: head, position: [-47, 2, 0], rotation: [0, 90, 0],
    width: 22, height: 22, depth: 5, material: CYAN,
  });
  await make(app, "Cylinder", {
    name: "GrokTempleCoreL", parent: head, position: [-50, 2, 0], rotation: [0, 0, 90],
    height: 3, width: 8, material: BLACK,
  });

  await make(app, "Torus", {
    name: "GrokCollar", parent: root, position: [0, 151, 0], rotation: [90, 0, 0],
    width: 42, height: 42, depth: 7, material: GUN,
  });

  // Cyan shell seams are separate geometry so they remain legible in dark mode.
  for (const x of [-58, 58]) {
    await make(app, "Cube", {
      name: "GrokChestSeam", parent: root, position: [x, 83, 31],
      width: 3, height: 34, depth: 3, cornerRadius: 1, material: CYAN,
    });
  }

  await make(app, "Sphere", {
    name: "GrokShoulderL",
    parent: root,
    position: [-68, 128, 0],
    width: 32,
    material: GUN,
  });
  await make(app, "Sphere", {
    name: "GrokShoulderR",
    parent: root,
    position: [68, 128, 0],
    width: 32,
    material: GUN,
  });
  for (const [name, x] of [["L", -68], ["R", 68]] as const) {
    await make(app, "Torus", {
      name: `GrokShoulderRing${name}`, parent: root, position: [x, 128, 17],
      width: 29, height: 29, depth: 7, material: CYAN,
    });
    await make(app, "Cylinder", {
      name: `GrokShoulderHub${name}`, parent: root, position: [x, 128, 20], rotation: [90, 0, 0],
      height: 6, width: 13, material: BLACK,
    });
  }

  const armL = await make(app, "Group", { name: "GrokArmL", parent: root, position: [-72, 118, 0] });
  const armR = await make(app, "Group", { name: "GrokArmR", parent: root, position: [72, 118, 0] });

  await make(app, "Cylinder", {
    name: "GrokUpperL",
    parent: armL,
    position: [0, -32, 0],
    height: 58,
    width: 16,
    material: GUN,
  });
  await make(app, "Cube", {
    name: "GrokUpperArmorL", parent: armL, position: [-2, -32, 8],
    width: 25, height: 49, depth: 24, cornerRadius: 8, material: BLACK,
  });
  await make(app, "Cylinder", {
    name: "GrokUpperR",
    parent: armR,
    position: [0, -32, 0],
    height: 58,
    width: 16,
    material: GUN,
  });
  await make(app, "Cube", {
    name: "GrokUpperArmorR", parent: armR, position: [2, -32, 8],
    width: 25, height: 49, depth: 24, cornerRadius: 8, material: BLACK,
  });
  await make(app, "Sphere", {
    name: "GrokElbowL",
    parent: armL,
    position: [0, -62, 0],
    width: 10,
    material: GUN,
  });
  await make(app, "Torus", {
    name: "GrokElbowRingL", parent: armL, position: [0, -62, 9],
    width: 18, height: 18, depth: 5, material: CYAN,
  });
  await make(app, "Sphere", {
    name: "GrokElbowR",
    parent: armR,
    position: [0, -62, 0],
    width: 10,
    material: GUN,
  });
  await make(app, "Torus", {
    name: "GrokElbowRingR", parent: armR, position: [0, -62, 9],
    width: 18, height: 18, depth: 5, material: CYAN,
  });
  const foreL = await make(app, "Group", { name: "GrokForearmL", parent: armL, position: [0, -62, 0] });
  const foreR = await make(app, "Group", { name: "GrokForearmR", parent: armR, position: [0, -62, 0] });
  await make(app, "Cylinder", {
    name: "GrokForeL",
    parent: foreL,
    position: [4, -34, 6],
    height: 54,
    width: 14,
    rotation: [12, 0, 8],
    material: GUN,
  });
  await make(app, "Cube", {
    name: "GrokForeArmorL", parent: foreL, position: [4, -34, 11], rotation: [12, 0, 8],
    width: 22, height: 43, depth: 22, cornerRadius: 7, material: BLACK,
  });
  await make(app, "Cylinder", {
    name: "GrokForeR",
    parent: foreR,
    position: [-4, -34, 6],
    height: 54,
    width: 14,
    rotation: [12, 0, -8],
    material: GUN,
  });
  await make(app, "Cube", {
    name: "GrokForeArmorR", parent: foreR, position: [-4, -34, 11], rotation: [12, 0, -8],
    width: 22, height: 43, depth: 22, cornerRadius: 7, material: BLACK,
  });
  const handL = await make(app, "Sphere", {
    name: "GrokHandL",
    parent: foreL,
    position: [8, -64, 12],
    width: 9,
    material: BLACK,
  });
  const handR = await make(app, "Sphere", {
    name: "GrokHandR",
    parent: foreR,
    position: [-8, -64, 12],
    width: 9,
    material: BLACK,
  });

  await make(app, "Cylinder", {
    name: "GrokRingL",
    parent: armL,
    position: [0, -40, 0],
    height: 4,
    width: 11,
    material: CYAN,
  });
  await make(app, "Cylinder", {
    name: "GrokRingR",
    parent: armR,
    position: [0, -40, 0],
    height: 4,
    width: 11,
    material: CYAN,
  });

  const hips = await make(app, "Group", { name: "GrokHips", parent: root, position: [0, 34, 0] });
  await make(app, "Cube", {
    name: "GrokHip",
    parent: hips,
    position: [0, 0, 0],
    width: 72,
    height: 22,
    depth: 46,
    cornerRadius: 8,
    material: GUN,
  });
  for (const x of [-24, -12, 0, 12, 24]) {
    await make(app, "Cylinder", {
      name: "GrokAbdominalCable", parent: root, position: [x, 54, 4],
      height: 42, width: 4, rotation: [x * 0.18, 0, x * -0.35], material: x === 0 ? CYAN : BLACK,
    });
  }
  await make(app, "Torus", {
    name: "GrokWaistRing", parent: hips, position: [0, 4, 0], rotation: [90, 0, 0],
    width: 66, height: 46, depth: 7, material: CYAN,
  });

  const legL = await make(app, "Group", { name: "GrokLegL", parent: root, position: [-22, 0, 0] });
  const legR = await make(app, "Group", { name: "GrokLegR", parent: root, position: [22, 0, 0] });
  await make(app, "Cylinder", {
    name: "GrokThighL",
    parent: legL,
    position: [0, -8, 0],
    height: 70,
    width: 22,
    material: GUN,
  });
  await make(app, "Cylinder", {
    name: "GrokThighR",
    parent: legR,
    position: [0, -8, 0],
    height: 70,
    width: 22,
    material: GUN,
  });
  await make(app, "Sphere", {
    name: "GrokKneeL",
    parent: legL,
    position: [0, -44, 4],
    width: 12,
    material: GUN,
  });
  await make(app, "Sphere", {
    name: "GrokKneeR",
    parent: legR,
    position: [0, -44, 4],
    width: 12,
    material: GUN,
  });
  const shinL = await make(app, "Group", { name: "GrokLowerLegL", parent: legL, position: [0, -44, 4] });
  const shinR = await make(app, "Group", { name: "GrokLowerLegR", parent: legR, position: [0, -44, 4] });
  await make(app, "Cylinder", {
    name: "GrokShinL",
    parent: shinL,
    position: [0, -38, -2],
    height: 62,
    width: 18,
    material: GUN,
  });
  await make(app, "Cylinder", {
    name: "GrokShinR",
    parent: shinR,
    position: [0, -38, -2],
    height: 62,
    width: 18,
    material: GUN,
  });
  const footL = await make(app, "Cube", {
    name: "GrokFootL",
    parent: shinL,
    position: [0, -74, 6],
    width: 28,
    height: 12,
    depth: 48,
    cornerRadius: 4,
    material: BLACK,
  });
  const footR = await make(app, "Cube", {
    name: "GrokFootR",
    parent: shinR,
    position: [0, -74, 6],
    width: 28,
    height: 12,
    depth: 48,
    cornerRadius: 4,
    material: BLACK,
  });
  await make(app, "Cylinder", {
    name: "GrokAnkleL",
    parent: shinL,
    position: [0, -66, -4],
    height: 5,
    width: 12,
    material: CYAN,
  });
  await make(app, "Cylinder", {
    name: "GrokAnkleR",
    parent: shinR,
    position: [0, -66, -4],
    height: 5,
    width: 12,
    material: CYAN,
  });

  await make(app, "DirectionalLight", {
    name: "GrokKey",
    position: [180, 260, 220],
    intensity: 1.35,
    color: "#f2f6ff",
  });
  await make(app, "PointLight", {
    name: "GrokFill",
    position: [-140, 120, 160],
    intensity: 0.55,
    color: "#7ec8ff",
  });
  await make(app, "PointLight", {
    name: "GrokRim",
    position: [80, 40, -160],
    intensity: 0.8,
    color: "#3ad0ff",
  });

  root.scale.x = 1.2;
  root.scale.y = 1.2;
  root.scale.z = 1.2;
  root.position.y = -90;
  root.rotation.y = 0.2;

  for (const obj of app.getAllObjects()) {
    const name = obj.name || "";
    if (name.startsWith("Grok")) continue;
    if (/camera|cam\b|orbit/i.test(name)) continue;
    try {
      obj.hide();
    } catch {
      /* keep cameras */
    }
  }

  poseStudioCamera(app);

  try {
    app.setZoom(1.05);
  } catch {
    /* zoom is optional */
  }

  return { root, head, torso, pulse, armL, armR, eyeL, eyeR, handL, handR, hips, legL, legR, neck, foreL, foreR, shinL, shinR, footL, footR };
}

function poseStudioCamera(app: Application): void {
  const controls = (app.controls ?? (app as unknown as { _controls?: { object?: { position: { set: (x: number, y: number, z: number) => void }; lookAt?: (x: number, y: number, z: number) => void } } })._controls) as
    | {
        object?: { position: { x: number; y: number; z: number; set?: (x: number, y: number, z: number) => void }; lookAt?: (x: number, y: number, z: number) => void };
        target?: { set?: (x: number, y: number, z: number) => void; x?: number; y?: number; z?: number };
      }
    | undefined;

  if (controls?.target?.set) controls.target.set(0, 70, 0);
  if (controls?.object?.position?.set) {
    controls.object.position.set(210, 110, 340);
    controls.object.lookAt?.(0, 70, 0);
  }

  for (const obj of app.getAllObjects()) {
    const name = (obj.name || "").toLowerCase();
    if (!name.includes("camera") && !name.includes("cam")) continue;
    obj.position.x = 210;
    obj.position.y = 110;
    obj.position.z = 340;
    obj.rotation.x = -0.14;
    obj.rotation.y = 0.2;
    obj.rotation.z = 0;
  }
}

export type GrokExpression = "idle" | "welcome" | "curious" | "listen" | "think" | "glad" | "careful";

export function animateGrokRig(
  rig: GrokRig,
  clock: { t: number; gazeX: number; gazeY: number; mood: string; expression?: GrokExpression },
): void {
  const breath = Math.sin(clock.t * 1.55) * 3.2;
  const expr = clock.expression ?? "idle";
  const bounce = expr === "glad" ? Math.abs(Math.sin(clock.t * 4.2)) * 10 : 0;
  const retreat = expr === "careful" ? -14 : expr === "curious" ? 10 : 0;
  rig.root.position.y = -90 + breath * 0.15 + bounce;
  rig.root.position.z = retreat;
  rig.root.rotation.y = 0.2 + clock.gazeX * 0.08;
  rig.torso.position.y = 92 + breath * 0.25;
  rig.torso.rotation.y = clock.gazeX * 0.12;
  rig.torso.rotation.x = -clock.gazeY * 0.04;
  rig.hips.rotation.y = -clock.gazeX * 0.08;
  rig.hips.rotation.z = -clock.gazeX * 0.025;
  rig.neck.rotation.y = clock.gazeX * 0.12;
  rig.neck.rotation.x = clock.gazeY * 0.05;
  rig.head.rotation.y = clock.gazeX * 0.32 + (expr === "think" ? -0.24 : expr === "curious" ? 0.14 : 0);
  rig.head.rotation.x = clock.gazeY * 0.16 + (expr === "listen" ? 0.07 : 0);
  rig.head.rotation.z = expr === "welcome" ? Math.sin(clock.t * 2.2) * 0.07 : expr === "curious" ? 0.1 : 0;
  const sway = Math.sin(clock.t * 1.25) * 0.052;
  const blinkPhase = clock.t % 4.8;
  const blink = blinkPhase > 4.52 && blinkPhase < 4.66 ? 0.08 : 1;
  rig.eyeL.position.x = -13 + clock.gazeX * 2.2;
  rig.eyeR.position.x = 13 + clock.gazeX * 2.2;
  rig.eyeL.position.y = 16 - clock.gazeY * 2;
  rig.eyeR.position.y = 16 - clock.gazeY * 2;
  rig.eyeL.scale.y = blink * (expr === "glad" ? 0.82 : 1.05);
  rig.eyeR.scale.y = blink * (expr === "glad" ? 0.82 : 1.05);
  if (expr === "welcome") {
    rig.armR.rotation.z = -0.2 - Math.abs(Math.sin(clock.t * 5.2)) * 0.84;
    rig.armR.rotation.x = 0.38;
    rig.armL.rotation.z = 0.14 + sway;
    rig.armL.rotation.x = 0.05;
  } else if (expr === "think") {
    rig.armL.rotation.z = 0.84;
    rig.armL.rotation.x = 0.56;
    rig.armR.rotation.z = -0.12 + sway;
    rig.armR.rotation.x = 0.04;
  } else if (expr === "glad") {
    rig.armL.rotation.z = 0.56 + Math.sin(clock.t * 5) * 0.17;
    rig.armR.rotation.z = -0.56 - Math.sin(clock.t * 5) * 0.17;
    rig.armL.rotation.x = 0.28;
    rig.armR.rotation.x = 0.28;
  } else {
    rig.armL.rotation.z = 0.14 + sway;
    rig.armR.rotation.z = -0.14 - sway;
    rig.armL.rotation.x = Math.sin(clock.t * 1.1) * 0.035;
    rig.armR.rotation.x = Math.cos(clock.t * 1.1) * 0.035;
  }
  const speaking = expr === "glad" || clock.mood === "speaking";
  const elbowBend = expr === "think" ? 1.02 : expr === "welcome" ? 0.58 : speaking ? 0.42 + Math.sin(clock.t * 5.2) * 0.16 : 0.16;
  rig.foreL.rotation.x = elbowBend - clock.gazeY * 0.08;
  rig.foreR.rotation.x = elbowBend - clock.gazeY * 0.08;
  rig.foreL.rotation.z = 0.08 + clock.gazeX * 0.06;
  rig.foreR.rotation.z = -0.08 + clock.gazeX * 0.06;
  const handBeat = speaking ? Math.sin(clock.t * 5.2) * 0.18 : Math.sin(clock.t * 1.4) * 0.035;
  rig.handL.rotation.x = -clock.gazeY * 0.16 + handBeat;
  rig.handR.rotation.x = -clock.gazeY * 0.16 - handBeat;
  rig.handL.rotation.z = clock.gazeX * 0.14 + (expr === "welcome" ? 0.32 : 0);
  rig.handR.rotation.z = clock.gazeX * 0.14 - (expr === "welcome" ? 0.32 : 0);
  const stride = expr === "glad" ? Math.sin(clock.t * 4.2) * 0.055 : Math.sin(clock.t * 1.1) * 0.012;
  rig.legL.rotation.x = stride - clock.gazeY * 0.025;
  rig.legR.rotation.x = -stride - clock.gazeY * 0.025;
  rig.legL.rotation.z = -clock.gazeX * 0.018;
  rig.legR.rotation.z = -clock.gazeX * 0.018;
  const kneeBend = expr === "glad" ? 0.12 + Math.abs(Math.sin(clock.t * 4.2)) * 0.12 : Math.max(0, clock.gazeY) * 0.07;
  rig.shinL.rotation.x = kneeBend + Math.max(0, stride) * 0.6;
  rig.shinR.rotation.x = kneeBend + Math.max(0, -stride) * 0.6;
  rig.shinL.rotation.y = clock.gazeX * 0.025;
  rig.shinR.rotation.y = clock.gazeX * 0.025;
  rig.footL.rotation.x = -kneeBend * 0.45 + clock.gazeY * 0.025;
  rig.footR.rotation.x = -kneeBend * 0.45 + clock.gazeY * 0.025;
  rig.footL.rotation.y = -clock.gazeX * 0.035;
  rig.footR.rotation.y = -clock.gazeX * 0.035;
  const rate =
    expr === "glad" || clock.mood === "speaking"
      ? 8
      : expr === "listen" || clock.mood === "listening"
        ? 5.4
        : expr === "careful"
          ? 1.8
          : 3.1;
  const beat = 1 + Math.abs(Math.sin(clock.t * rate)) * (expr === "careful" ? 0.2 : 0.55);
  rig.pulse.scale.x = beat;
  rig.pulse.scale.z = beat;
}
