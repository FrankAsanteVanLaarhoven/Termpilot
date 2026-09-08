#!/usr/bin/env node
import { spawnSync } from "node:child_process";
import { cpSync, mkdirSync, writeFileSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..", "..", "..");
const pkg = join(root, "packages", "g1-humanoid");
const staging = join(pkg, "dist", "g1-humanoid-reuse");
const zip = join(pkg, "dist", "g1-humanoid-reuse.zip");

mkdirSync(staging, { recursive: true });
cpSync(join(root, "frontend", "lib", "g1", "G1Humanoid.tsx"), join(staging, "src", "G1Humanoid.tsx"));
cpSync(join(pkg, "README.md"), join(staging, "README.md"));
cpSync(join(pkg, "CAPABILITIES.md"), join(staging, "CAPABILITIES.md"));
cpSync(join(pkg, "package.json"), join(staging, "package.json"));
cpSync(join(root, "frontend", "ROBOT_ASSET_CONTRACT.md"), join(staging, "ROBOT_ASSET_CONTRACT.md"));
cpSync(join(root, "frontend", "public", "robot", "g1"), join(staging, "robot", "g1"), { recursive: true });
if (existsSync(join(root, "frontend", "public", "splash", "grokbot-humanoid.png"))) {
  mkdirSync(join(staging, "splash"), { recursive: true });
  cpSync(
    join(root, "frontend", "public", "splash", "grokbot-humanoid.png"),
    join(staging, "splash", "grokbot-humanoid.png"),
  );
}

writeFileSync(
  join(staging, "g1-humanoid.css"),
  `.tp-bot { position: relative; width: 100%; height: 100%; min-height: 280px; }
.tp-bot.compact { min-height: 160px; height: 180px; }
.tp-bot.stage { min-height: 360px; height: 420px; }
.tp-bot-spline { position: absolute; inset: 0; z-index: 2; width: 100%; height: 100%; display: block; background: transparent; }
.tp-bot-reference { position: absolute; inset: 0; z-index: 2; width: 100%; height: 100%; object-fit: contain; }
.tp-bot[data-spline="fallback"] .tp-bot-spline { display: none; }
.tp-bot-loading { position: absolute; inset: 0; display: grid; place-items: center; z-index: 1; }
`,
);

const zipped = spawnSync("ditto", ["-c", "-k", "--sequesterRsrc", "--keepParent", staging, zip], {
  stdio: "inherit",
});
if (zipped.status !== 0) {
  spawnSync("zip", ["-r", zip, "g1-humanoid-reuse"], { cwd: join(pkg, "dist"), stdio: "inherit" });
}
console.log(`packed ${zip}`);
