import { execFileSync } from "child_process";
import os from "os";

export function runPythonScript(scriptPath: string, args: string[] = []): void {
  const override = (process.env.ZECT_PYTHON || "").trim();
  if (override) {
    execFileSync(override, [scriptPath, ...args], { stdio: "pipe" });
    return;
  }
  if (os.platform() === "win32") {
    execFileSync("py", ["-3.12", scriptPath, ...args], { stdio: "pipe" });
    return;
  }
  execFileSync("python3", [scriptPath, ...args], { stdio: "pipe" });
}
