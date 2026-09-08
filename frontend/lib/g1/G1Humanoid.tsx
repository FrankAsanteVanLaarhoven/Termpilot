"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";

export type G1Mood = "idle" | "listening" | "processing" | "speaking";
export type G1Expression = "idle" | "welcome" | "curious" | "listen" | "think" | "glad" | "careful";
export type G1Cue = "idle" | "hello" | "wave" | "point" | "listen" | "think" | "yes" | "no" | "invite";
export const G1_URDF = "/robot/g1/g1.urdf";

type Pointer = { x: number; y: number; overSignin: boolean };

type XrMode = "immersive-vr" | "immersive-ar";

export function G1Humanoid({
  mood = "idle",
  expression = "idle",
  variant = "stage",
  className = "",
  urdfUrl = G1_URDF,
  ariaLabel = "Interactive G1 humanoid",
  loading = null,
  fallback = null,
  allowXr = false,
  cue = "idle",
  speaking = false,
  turning = false,
  micActive = false,
  onMic,
}: {
  mood?: G1Mood | string;
  expression?: G1Expression | string;
  variant?: "splash" | "stage" | "compact";
  className?: string;
  urdfUrl?: string;
  ariaLabel?: string;
  loading?: ReactNode;
  fallback?: ReactNode;
  allowXr?: boolean;
  cue?: G1Cue | string;
  speaking?: boolean;
  turning?: boolean;
  micActive?: boolean;
  onMic?: () => void;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const micHitRef = useRef<HTMLButtonElement>(null);
  const moodRef = useRef(mood);
  const expressionRef = useRef(expression);
  const cueRef = useRef(cue);
  const speakingRef = useRef(speaking);
  const turningRef = useRef(turning);
  const micActiveRef = useRef(micActive);
  const onMicRef = useRef(onMic);
  const pointerRef = useRef<Pointer>({ x: 0, y: 0, overSignin: false });
  const xrRendererRef = useRef<{
    setSession: (session: XRSession) => Promise<void>;
    isPresenting: boolean;
  } | null>(null);
  const [modelState, setModelState] = useState<"loading" | "ready" | "fallback">("loading");
  const [xrSupport, setXrSupport] = useState<{ vr: boolean; ar: boolean }>({ vr: false, ar: false });
  const [xrBusy, setXrBusy] = useState<XrMode | null>(null);
  const [xrNote, setXrNote] = useState<string | null>(null);
  moodRef.current = mood;
  expressionRef.current = expression;
  cueRef.current = cue;
  speakingRef.current = speaking;
  turningRef.current = turning;
  micActiveRef.current = micActive;
  onMicRef.current = onMic;

  useEffect(() => {
    if (!allowXr) return;
    const xr = navigator.xr;
    if (!xr) {
      setXrNote("XR needs a headset or an AR-capable phone, on HTTPS.");
      return;
    }
    void Promise.all([
      xr.isSessionSupported("immersive-vr").catch(() => false),
      xr.isSessionSupported("immersive-ar").catch(() => false),
    ]).then(([vr, ar]) => {
      setXrSupport({ vr, ar });
      if (!vr && !ar) setXrNote("This device has no WebXR session. Install the PWA and open it from the home screen, or use a headset.");
    });
  }, [allowXr]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const canvasEl = canvas;
    let disposed = false;
    let frame = 0;
    let cleanup = () => {};

    async function mount() {
      try {
        const THREE = await import("three");
        const { default: URDFLoader } = await import("urdf-loader");
        if (disposed) return;

        const renderer = new THREE.WebGLRenderer({ canvas: canvasEl, alpha: true, antialias: true, powerPreference: "high-performance" });
        renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        if (allowXr) renderer.xr.enabled = true;
        renderer.outputColorSpace = THREE.SRGBColorSpace;
        renderer.toneMapping = THREE.ACESFilmicToneMapping;
        renderer.toneMappingExposure = 1.42;
        renderer.shadowMap.enabled = true;
        renderer.shadowMap.type = THREE.PCFShadowMap;

        const scene = new THREE.Scene();
        const fullBody = variant === "splash";
        const camera = new THREE.PerspectiveCamera(fullBody ? 32 : 28, 1, 0.05, 40);
        // URDF +X is face-forward. Splash is framed from the mesh bounds so the
        // whole G1 stays in view; in-app stage stays a head-and-chest portrait.
        const lookTarget = new THREE.Vector3(0, fullBody ? 0.35 : 0.9, 0);
        camera.position.set(fullBody ? 3.6 : 2.55, fullBody ? 0.35 : 0.98, fullBody ? 0.04 : 0.06);
        camera.lookAt(lookTarget);
        scene.add(camera);
        scene.add(new THREE.HemisphereLight(0xd7f7ff, 0x05070c, 1.7));
        const key = new THREE.DirectionalLight(0xffffff, 5.4);
        key.position.set(2.8, 2.6, 1.35);
        key.castShadow = true;
        scene.add(key);
        const face = new THREE.PointLight(0xffffff, 18, 8, 1.35);
        face.position.set(0.55, 0.15, 0);
        camera.add(face);
        const rim = new THREE.PointLight(0x00e5ff, 26, 9, 1.45);
        rim.position.set(-1.7, 1.7, 1.8);
        scene.add(rim);
        const fill = new THREE.PointLight(0x9adfff, 14, 8, 1.6);
        fill.position.set(2.1, 0.85, -1.7);
        scene.add(fill);
        const spot = new THREE.SpotLight(0xd8f6ff, 16, 14, Math.PI / 7, 0.38, 1.15);
        spot.castShadow = true;
        spot.position.set(2.35, 1.72, 0);
        spot.target.position.set(0.08, 0.92, 0);
        scene.add(spot);
        scene.add(spot.target);

        const floor = new THREE.Mesh(new THREE.CircleGeometry(1.05, 96), new THREE.MeshPhysicalMaterial({ color: 0x071018, metalness: 0.82, roughness: 0.24, transparent: true, opacity: 0.72 }));
        floor.rotation.x = -Math.PI / 2;
        floor.position.y = -0.71;
        floor.receiveShadow = true;
        scene.add(floor);

        const loadingManager = new THREE.LoadingManager();
        const loader = new URDFLoader(loadingManager);
        loader.parseCollision = false;
        const robot = await new Promise<import("urdf-loader").URDFRobot>((resolve, reject) => {
          let parsedRobot: import("urdf-loader").URDFRobot | undefined;
          loadingManager.onLoad = () => {
            if (parsedRobot) resolve(parsedRobot);
          };
          loadingManager.onError = (url) => reject(new Error(`Failed to load URDF asset: ${url}`));
          loader.load(
            urdfUrl,
            (model) => { parsedRobot = model; },
            undefined,
            reject,
          );
        });
        if (disposed) { renderer.dispose(); return; }
        robot.rotation.x = -Math.PI / 2;
        const pivot = new THREE.Group();
        pivot.add(robot);
        scene.add(pivot);

        const dark = new THREE.MeshPhysicalMaterial({ color: 0x0a1218, metalness: 0.78, roughness: 0.28, clearcoat: 0.85, clearcoatRoughness: 0.16, emissive: 0x041018, emissiveIntensity: 0.35 });
        const graphite = new THREE.MeshPhysicalMaterial({ color: 0x1c2c38, metalness: 0.72, roughness: 0.32, clearcoat: 0.8, emissive: 0x06222c, emissiveIntensity: 0.28 });
        const cyan = new THREE.LineBasicMaterial({ color: 0x15e6f4, transparent: true, opacity: 0.36 });
        const neon = new THREE.MeshStandardMaterial({
          color: 0x00e5ff,
          emissive: 0x00d4ff,
          emissiveIntensity: 5.2,
          metalness: 0.05,
          roughness: 0.12,
          toneMapped: false,
          depthTest: true,
          depthWrite: true,
          polygonOffset: true,
          polygonOffsetFactor: -2,
          polygonOffsetUnits: -2,
        });
        const plaque = new THREE.MeshPhysicalMaterial({
          color: 0x0a1218,
          metalness: 0.88,
          roughness: 0.28,
          clearcoat: 0.6,
          emissive: 0x021018,
          emissiveIntensity: 0.2,
        });
        const micMat = new THREE.MeshStandardMaterial({
          color: 0x00e5ff,
          emissive: 0x00d4ff,
          emissiveIntensity: 3.8,
          metalness: 0.25,
          roughness: 0.18,
          toneMapped: false,
        });
        const ownedBy = (node: import("three").Object3D, name: string) => {
          let current: import("three").Object3D | null = node;
          while (current) {
            if (current.name === name) return true;
            current = current.parent;
          }
          return false;
        };
        let meshIndex = 0;
        robot.traverse((node) => {
          if (!(node instanceof THREE.Mesh)) return;
          if (ownedBy(node, "mic_button_link")) {
            const count = node.geometry.getAttribute("position")?.count ?? 0;
            // Gem has the cap sphere; the carved well is a plain hex socket.
            node.material = count > 400 ? micMat : plaque;
            node.castShadow = true;
            node.receiveShadow = true;
            return;
          }
          if (ownedBy(node, "logo_link")) {
            const count = node.geometry.getAttribute("position")?.count ?? 0;
            node.material = count > 4000 ? neon : plaque;
            node.castShadow = true;
            node.receiveShadow = true;
            node.renderOrder = 1;
            return;
          }
          node.material = meshIndex++ % 4 === 0 ? graphite : dark;
          node.castShadow = true;
          node.receiveShadow = true;
          const edges = new THREE.LineSegments(new THREE.EdgesGeometry(node.geometry, 27), cyan);
          edges.renderOrder = 2;
          node.add(edges);
        });
        robot.userData.mark = "FAVL";
        const logo = robot.links.logo_link;
        const logoLight = new THREE.PointLight(0x33f0ff, 3.2, 0.16, 2);
        if (logo) {
          logoLight.position.set(0.080, 0, 0.181);
          logo.add(logoLight);
        }
        const micLink = robot.links.mic_button_link;
        const micAim = new THREE.Object3D();
        micAim.name = "mic_hit";
        // Invisible hit disc at the chest skin so the inset navel is still tappable.
        micAim.position.set(0.084, 0, 0.118);
        micAim.rotation.y = Math.PI / 2;
        const micDisc = new THREE.Mesh(
          new THREE.CircleGeometry(0.07, 24),
          new THREE.MeshBasicMaterial({
            transparent: true,
            opacity: 0,
            depthTest: false,
            side: THREE.DoubleSide,
          }),
        );
        micDisc.name = "mic_hit";
        micAim.add(micDisc);
        if (micLink) micLink.add(micAim);
        else robot.add(micAim);
        const isChestTarget = (node: import("three").Object3D) =>
          ownedBy(node, "mic_button_link") ||
          ownedBy(node, "logo_link") ||
          ownedBy(node, "torso_link") ||
          node.name === "mic_hit";

        // URDF mesh sources do not all use the same authored unit scale. Fit the
        // complete articulated hierarchy to a known stage height before placing
        // the camera, preventing the camera from ending up inside a link mesh.
        robot.updateMatrixWorld(true);
        const rawBounds = new THREE.Box3().setFromObject(robot);
        const rawSize = rawBounds.getSize(new THREE.Vector3());
        if (!Number.isFinite(rawSize.y) || rawSize.y <= 0) throw new Error("Invalid URDF model bounds");
        robot.scale.setScalar(1.58 / rawSize.y);
        robot.updateMatrixWorld(true);
        const fittedBounds = new THREE.Box3().setFromObject(robot);
        const fittedCenter = fittedBounds.getCenter(new THREE.Vector3());
        robot.position.x -= fittedCenter.x;
        robot.position.z -= fittedCenter.z;
        robot.position.y += -0.71 - fittedBounds.min.y;
        robot.updateMatrixWorld(true);

        const head = robot.links.head_link;
        const eyes: { root: import("three").Group; pupil: import("three").Mesh }[] = [];
        // Rotate a neck pivot, never head_link itself. The G1 head mesh is a
        // long neck+helmet whose joint sits in the chest; rotating the link
        // swings the helmet off the shoulders.
        let gaze: import("three").Group | null = null;
        if (head) {
          const neck = new THREE.Vector3(0, 0, 0.36);
          gaze = new THREE.Group();
          gaze.position.copy(neck);
          head.add(gaze);
          for (const child of [...head.children]) {
            if (child === gaze) continue;
            head.remove(child);
            child.position.sub(neck);
            gaze.add(child);
          }
          const scleraMaterial = new THREE.MeshBasicMaterial({ color: 0xf4fdff, toneMapped: false });
          const pupilMaterial = new THREE.MeshBasicMaterial({ color: 0x00e5ff, toneMapped: false });
          for (const side of [-1, 1]) {
            const root = new THREE.Group();
            root.position.set(0.096, side * 0.036, 0.092);
            const sclera = new THREE.Mesh(new THREE.SphereGeometry(0.017, 20, 14), scleraMaterial);
            sclera.scale.set(0.62, 1, 0.82);
            const pupil = new THREE.Mesh(new THREE.SphereGeometry(0.0075, 16, 12), pupilMaterial);
            pupil.position.set(0.011, 0, 0);
            root.add(sclera, pupil);
            gaze.add(root);
            eyes.push({ root, pupil });
          }
        }

        const setJoint = (name: string, value: number) => {
          try { robot.setJointValue(name, value); } catch { /* optional joint */ }
        };
        const homeCamera = camera.position.clone();
        const homeRobotY = robot.position.y;
        const resize = () => {
          const rect = canvasEl.getBoundingClientRect();
          const width = Math.max(1, Math.round(rect.width));
          const height = Math.max(1, Math.round(rect.height));
          renderer.setSize(width, height, false);
          camera.aspect = width / height;
          camera.updateProjectionMatrix();
        };
        const frameSplash = () => {
          if (!fullBody) return;
          robot.updateMatrixWorld(true);
          const box = new THREE.Box3().setFromObject(robot);
          if (box.isEmpty()) return;
          const size = box.getSize(new THREE.Vector3());
          const center = box.getCenter(new THREE.Vector3());
          lookTarget.copy(center);
          const pad = 1.2;
          const vFov = THREE.MathUtils.degToRad(camera.fov);
          const distH = (size.y * pad) / (2 * Math.tan(vFov / 2));
          const hFov = 2 * Math.atan(Math.tan(vFov / 2) * Math.max(camera.aspect, 0.25));
          const distW = (Math.max(size.x, size.z) * pad) / (2 * Math.tan(hFov / 2));
          const dist = Math.min(8, Math.max(distH, distW, 2.2));
          camera.position.set(center.x + dist, center.y, center.z);
          camera.lookAt(lookTarget);
          camera.updateProjectionMatrix();
          homeCamera.copy(camera.position);
        };
        const observer = new ResizeObserver(() => {
          resize();
          frameSplash();
        });
        observer.observe(canvasEl);
        resize();
        frameSplash();
        const onPointer = (event: PointerEvent) => {
          const rect = canvasEl.getBoundingClientRect();
          const x = ((event.clientX - rect.left) / Math.max(rect.width, 1) - 0.5) * 2;
          const y = ((event.clientY - rect.top) / Math.max(rect.height, 1) - 0.5) * 2;
          const card = document.querySelector(".tp-splash-card");
          let overSignin = false;
          if (card) {
            const box = card.getBoundingClientRect();
            overSignin =
              event.clientX >= box.left &&
              event.clientX <= box.right &&
              event.clientY >= box.top &&
              event.clientY <= box.bottom;
          }
          pointerRef.current = {
            x: THREE.MathUtils.clamp(x, -1.65, 1.65),
            y: THREE.MathUtils.clamp(y, -1.35, 1.35),
            overSignin,
          };
        };
        window.addEventListener("pointermove", onPointer, { passive: true });
        const raycaster = new THREE.Raycaster();
        const ndc = new THREE.Vector2();
        const micNdc = new THREE.Vector3();
        const hitFromEvent = (event: PointerEvent) => {
          const box = canvasEl.getBoundingClientRect();
          if (box.width < 1 || box.height < 1) return false;
          ndc.x = ((event.clientX - box.left) / box.width) * 2 - 1;
          ndc.y = -((event.clientY - box.top) / box.height) * 2 + 1;
          raycaster.setFromCamera(ndc, camera);
          const hits = raycaster.intersectObject(pivot, true);
          return hits.some((hit) => isChestTarget(hit.object));
        };
        const onCanvasMove = (event: PointerEvent) => {
          canvasEl.style.cursor = hitFromEvent(event) ? "pointer" : "default";
        };
        const onCanvasClick = (event: PointerEvent) => {
          if (!hitFromEvent(event)) return;
          event.preventDefault();
          event.stopPropagation();
          onMicRef.current?.();
        };
        canvasEl.addEventListener("pointermove", onCanvasMove);
        canvasEl.addEventListener("pointerdown", onCanvasClick);

        const clock = new THREE.Clock();
        let pointMix = 0;
        let greetMix = fullBody ? 1 : 0;
        let listenMix = 0;
        let thinkMix = 0;
        let yesMix = 0;
        let noMix = 0;
        let inviteMix = 0;
        const animate = () => {
          if (disposed) return;
          const t = clock.getElapsedTime();
          const p = pointerRef.current;
          const cue = cueRef.current;
          const active = moodRef.current === "speaking" || expressionRef.current === "glad" || cue === "hello";
          const listening = moodRef.current === "listening" || expressionRef.current === "listen" || cue === "listen";
          const thinking = moodRef.current === "processing" || expressionRef.current === "think" || cue === "think";
          const breath = Math.sin(t * 1.55) * 0.025;
          const gesture = active ? Math.sin(t * 3.1) * 0.23 : listening ? 0.16 : Math.sin(t * 0.72) * 0.035;
          const busy = cue === "listen" || cue === "think" || cue === "point" || cue === "no" || p.overSignin;
          const spinTarget = fullBody && turningRef.current ? Math.PI : 0;
          pivot.rotation.y += (spinTarget - pivot.rotation.y) * 0.09;
          const facing = 1 - Math.min(Math.abs(pivot.rotation.y) / Math.PI, 1);
          const greetPulse = t < 6.5 || (t % 12 > 0 && t % 12 < 2.8);
          const wantGreet =
            cue === "hello" ||
            cue === "wave" ||
            (fullBody && greetPulse && !busy && facing > 0.8 && !turningRef.current && cue === "idle");
          greetMix += ((wantGreet ? 1 : 0) - greetMix) * 0.14;
          pointMix += ((cue === "point" || (fullBody && p.overSignin) ? 1 : 0) - pointMix) * 0.16;
          listenMix += ((cue === "listen" || listening ? 1 : 0) - listenMix) * 0.12;
          thinkMix += ((cue === "think" || thinking ? 1 : 0) - thinkMix) * 0.12;
          yesMix += ((cue === "yes" ? 1 : 0) - yesMix) * 0.16;
          noMix += ((cue === "no" ? 1 : 0) - noMix) * 0.2;
          inviteMix += ((cue === "invite" ? 1 : 0) - inviteMix) * 0.12;
          const g = greetMix;
          const pt = pointMix;
          const idle = Math.max(0, 1 - g - pt - listenMix - thinkMix - inviteMix);
          const wave = Math.sin(t * 10) * 0.5 + 0.5;
          const hipSway = Math.sin(t * 1.1) * 0.045;
          const turn = THREE.MathUtils.clamp(p.x * (fullBody ? 0.28 : 0.08) + pt * 0.32, -0.45, 0.5);

          setJoint("waist_yaw_joint", turn + Math.sin(t * 0.7) * 0.04 * idle);

          setJoint(
            "left_shoulder_pitch_joint",
            (-0.12 + breath - gesture * 0.4 - p.y * 0.08) * idle +
              -0.55 * pt +
              -0.2 * g +
              -0.7 * listenMix +
              -0.85 * thinkMix +
              -0.25 * inviteMix,
          );
          setJoint(
            "right_shoulder_pitch_joint",
            (-0.12 - breath + gesture - p.y * 0.08) * idle - 0.62 * g - 0.15 * pt - 0.25 * inviteMix - 0.2 * yesMix,
          );
          setJoint(
            "left_shoulder_roll_joint",
            (0.14 + p.x * 0.1) * idle + 1.15 * pt + 0.2 * g + 0.7 * listenMix + 0.85 * thinkMix + 0.55 * inviteMix,
          );
          setJoint(
            "right_shoulder_roll_joint",
            (-0.14 + p.x * 0.08) * idle - 0.42 * g - 0.2 * pt - 0.55 * inviteMix - 0.4 * yesMix,
          );
          setJoint("left_shoulder_yaw_joint", p.x * -0.12 * idle + 0.55 * pt + 0.35 * listenMix + 0.4 * thinkMix);
          setJoint("right_shoulder_yaw_joint", p.x * -0.12 * idle + 0.25 * g);
          setJoint("left_elbow_joint", (0.3 + Math.abs(gesture) * 0.42) * idle + 0.2 * pt + 0.35 * g + 1.1 * listenMix + 1.2 * thinkMix);
          setJoint(
            "right_elbow_joint",
            (0.3 + (active ? 0.48 : 0.15)) * idle + (1.15 + wave * 0.55) * g + 0.35 * pt + 0.4 * inviteMix,
          );
          setJoint("left_wrist_roll_joint", Math.sin(t * 1.15) * 0.11 * idle + 0.2 * pt);
          setJoint("right_wrist_roll_joint", 0);
          setJoint("left_wrist_pitch_joint", p.y * -0.12 * idle + 0.25 * pt);
          setJoint("right_wrist_pitch_joint", 0);
          setJoint("left_wrist_yaw_joint", p.x * 0.12 * idle + 0.5 * pt);
          setJoint("right_wrist_yaw_joint", 0);

          setJoint("left_hip_pitch_joint", -0.06 + hipSway + breath * 0.15);
          setJoint("right_hip_pitch_joint", -0.06 - hipSway - breath * 0.15);
          setJoint("left_hip_roll_joint", turn * 0.08);
          setJoint("right_hip_roll_joint", turn * 0.08);
          setJoint("left_hip_yaw_joint", turn * 0.12);
          setJoint("right_hip_yaw_joint", turn * 0.12);
          setJoint("left_knee_joint", 0.12 + Math.abs(hipSway) * 0.4);
          setJoint("right_knee_joint", 0.12 + Math.abs(hipSway) * 0.4);
          setJoint("left_ankle_pitch_joint", -hipSway * 0.3);
          setJoint("right_ankle_pitch_joint", hipSway * 0.3);
          setJoint("left_ankle_roll_joint", 0);
          setJoint("right_ankle_roll_joint", 0);
          // Screen: +x is cursor right, +y is cursor down. URDF head: +X face,
          // +Y left, +Z up. Yaw around Z, pitch (nod) around Y — never roll
          // around X, which previously swung the helmet off the neck.
          if (gaze) {
            const yaw = THREE.MathUtils.clamp(
              p.x * 0.4 + Math.sin(t * 11) * 0.38 * noMix,
              -0.55,
              0.55,
            );
            const pitch = THREE.MathUtils.clamp(
              p.y * 0.26 +
                (thinking ? Math.sin(t * 1.8) * 0.03 : 0) +
                Math.sin(t * 8.5) * 0.24 * yesMix +
                0.18 * listenMix,
              -0.32,
              0.34,
            );
            gaze.rotation.set(0, pitch, yaw);
          }
          eyes.forEach((eye) => {
            const blink = Math.sin(t * 0.68) > 0.982 ? 0.12 : 1;
            eye.root.scale.y = blink;
            eye.pupil.position.y = THREE.MathUtils.clamp(p.x * 0.005, -0.005, 0.005);
            eye.pupil.position.z = THREE.MathUtils.clamp(-p.y * 0.0045, -0.0045, 0.0045);
          });
          robot.position.y = homeRobotY + Math.sin(t * 1.55) * 0.006;
          const sway = fullBody ? 0.012 : 0.03;
          camera.position.x += (homeCamera.x - Math.abs(p.x) * sway - camera.position.x) * 0.05;
          camera.position.y += (homeCamera.y - p.y * (fullBody ? 0.02 : 0.04) - camera.position.y) * 0.05;
          camera.position.z += (homeCamera.z - p.x * (fullBody ? 0.04 : 0.08) - camera.position.z) * 0.05;
          key.position.z = 1.35 - p.x * 0.3;
          key.position.y = 2.6 - p.y * 0.16;
          rim.intensity = 24 + Math.sin(t * 1.2) * 2.4 + (active ? 6 : 0);
          const talking = speakingRef.current;
          const vu = talking
            ? 0.4 + 0.6 * Math.abs(Math.sin(t * 17)) * (0.55 + 0.45 * Math.abs(Math.sin(t * 29)))
            : 0;
          if (talking) {
            neon.color.setHex(0x22ff66);
            neon.emissive.setHex(0x3ddc97);
            neon.emissiveIntensity = 4 + vu * 8;
          } else {
            neon.color.setHex(0x00e5ff);
            neon.emissive.setHex(0x00d4ff);
            neon.emissiveIntensity = 5.2 + Math.sin(t * 2.15) * 0.8;
          }
          logoLight.color.setHex(0x33f0ff);
          logoLight.intensity = 2.4 + Math.sin(t * 2.15) * 0.6;
          if (micActiveRef.current) {
            micMat.color.setHex(0x22ff66);
            micMat.emissive.setHex(0x3ddc97);
            micMat.emissiveIntensity = 4.2 + vu * 5;
          } else {
            micMat.color.setHex(0x00e5ff);
            micMat.emissive.setHex(0x00d4ff);
            micMat.emissiveIntensity = 3.6 + Math.sin(t * 2.15) * 0.7;
          }
          fill.position.z = -1.7 - p.x * 0.18;
          spot.position.set(2.35, 1.72 - p.y * 0.5, -p.x * 0.9);
          spot.target.position.set(0.08, 0.92 - p.y * 0.18, -p.x * 0.32);
          camera.lookAt(lookTarget);
          const micBtn = micHitRef.current;
          if (micBtn && micAim.parent) {
            micNdc.set(0, 0, 0);
            micAim.getWorldPosition(micNdc);
            micNdc.project(camera);
            const onScreen = Math.abs(micNdc.x) < 1.15 && Math.abs(micNdc.y) < 1.15 && micNdc.z < 1;
            micBtn.style.display = onScreen ? "block" : "none";
            if (onScreen) {
              micBtn.style.left = `${(micNdc.x * 0.5 + 0.5) * 100}%`;
              micBtn.style.top = `${(-micNdc.y * 0.5 + 0.5) * 100}%`;
            }
          }
          renderer.render(scene, camera);
        };
        setModelState("ready");
        if (allowXr) {
          xrRendererRef.current = renderer.xr;
          renderer.setAnimationLoop(animate);
        } else {
          const loop = () => {
            if (disposed) return;
            animate();
            frame = requestAnimationFrame(loop);
          };
          frame = requestAnimationFrame(loop);
        }
        cleanup = () => {
          observer.disconnect();
          window.removeEventListener("pointermove", onPointer);
          canvasEl.removeEventListener("pointermove", onCanvasMove);
          canvasEl.removeEventListener("pointerdown", onCanvasClick);
          renderer.setAnimationLoop(null);
          xrRendererRef.current = null;
          renderer.dispose();
        };
      } catch (error) {
        console.error("G1 humanoid failed to load", error);
        if (!disposed) setModelState("fallback");
      }
    }
    void mount();
    return () => { disposed = true; cancelAnimationFrame(frame); cleanup(); };
  }, [urdfUrl, allowXr, variant]);

  async function enterXr(mode: XrMode) {
    const xr = navigator.xr;
    const webxr = xrRendererRef.current;
    if (!xr || !webxr) {
      setXrNote("Robot is still loading. Wait a moment, then launch XR.");
      return;
    }
    setXrBusy(mode);
    setXrNote(null);
    try {
      const optional =
        mode === "immersive-ar"
          ? ["local-floor", "dom-overlay", "hit-test"]
          : ["local-floor", "bounded-floor", "hand-tracking"];
      const session = await xr.requestSession(mode, { optionalFeatures: optional });
      await webxr.setSession(session);
    } catch (error) {
      setXrNote(error instanceof Error ? error.message : "Could not start the XR session.");
    } finally {
      setXrBusy(null);
    }
  }

  return (
    <div className={`tp-bot ${variant} mood-${mood} expr-${expression} ${className}`} data-spline={modelState} aria-label={ariaLabel}>
      <canvas ref={canvasRef} className="tp-bot-spline" aria-hidden />
      {modelState === "ready" && onMic && (
        <button
          ref={micHitRef}
          type="button"
          className={`tp-mic-hit ${micActive ? "is-on" : ""}`}
          aria-label={micActive ? "Stop listening" : "Tap the chest button to talk"}
          onPointerDown={(event) => {
            event.preventDefault();
            event.stopPropagation();
            onMic();
          }}
        />
      )}
      {modelState === "loading" && <div className="tp-bot-loading" aria-hidden>{loading}</div>}
      {modelState === "fallback" && fallback}
      {allowXr && (
        <div className="tp-xr-dock">
          {xrSupport.vr && (
            <button type="button" className="tp-xr-launch" disabled={xrBusy !== null} onClick={() => void enterXr("immersive-vr")}>
              {xrBusy === "immersive-vr" ? "Starting VR…" : "Launch in VR"}
            </button>
          )}
          {xrSupport.ar && (
            <button type="button" className="tp-xr-launch" disabled={xrBusy !== null} onClick={() => void enterXr("immersive-ar")}>
              {xrBusy === "immersive-ar" ? "Starting AR…" : "Launch in AR"}
            </button>
          )}
          {xrNote && <p className="tp-xr-note">{xrNote}</p>}
        </div>
      )}
    </div>
  );
}
