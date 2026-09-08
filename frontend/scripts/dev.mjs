import { spawn } from "node:child_process";

const raw = process.argv.slice(2);
const args = [];
for (let index = 0; index < raw.length; index += 1) {
  const arg = raw[index];
  if (arg === "--strictPort") continue;
  if (arg === "--host") {
    args.push("-H", raw[index + 1] ?? "0.0.0.0");
    index += 1;
    continue;
  }
  args.push(arg);
}

const child = spawn(process.execPath, ["node_modules/next/dist/bin/next", "dev", ...args], {
  stdio: "inherit",
});

child.on("exit", (code, signal) => {
  if (signal) process.kill(process.pid, signal);
  else process.exit(code ?? 1);
});
