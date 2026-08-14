import { execSync } from "child_process";
import fs from "fs";
import os from "os";
import path from "path";

const TRANSCRIPT = "Hello this is a test sample for cloning my voice for presentations.";

export function cloneTranscript(): string {
  return TRANSCRIPT;
}

/** PCM WAV (sine). Prefer Windows SAPI speech when available. */
export function writeCloneSampleWav(dest: string): { path: string; kind: "sapi" | "pcm" } {
  fs.mkdirSync(path.dirname(dest), { recursive: true });
  if (process.platform === "win32") {
    try {
      const ps = [
        "Add-Type -AssemblyName System.Speech",
        `$s = New-Object System.Speech.Synthesis.SpeechSynthesizer`,
        `$s.SetOutputToWaveFile('${dest.replace(/'/g, "''")}')`,
        `$s.Speak('${TRANSCRIPT.replace(/'/g, "''")}')`,
        "$s.Dispose()",
      ].join("; ");
      execSync(`powershell -NoProfile -Command ${JSON.stringify(ps)}`, { stdio: "pipe", timeout: 30_000 });
      if (fs.existsSync(dest) && fs.statSync(dest).size > 1000) {
        return { path: dest, kind: "sapi" };
      }
    } catch {
      /* fall through to PCM */
    }
  }
  fs.writeFileSync(dest, pcmWav(3.2));
  return { path: dest, kind: "pcm" };
}

export function pcmWav(seconds = 3, sampleRate = 22050): Buffer {
  const n = Math.floor(sampleRate * seconds);
  const dataSize = n * 2;
  const buf = Buffer.alloc(44 + dataSize);
  buf.write("RIFF", 0);
  buf.writeUInt32LE(36 + dataSize, 4);
  buf.write("WAVE", 8);
  buf.write("fmt ", 12);
  buf.writeUInt32LE(16, 16);
  buf.writeUInt16LE(1, 20);
  buf.writeUInt16LE(1, 22);
  buf.writeUInt32LE(sampleRate, 24);
  buf.writeUInt32LE(sampleRate * 2, 28);
  buf.writeUInt16LE(2, 32);
  buf.writeUInt16LE(16, 34);
  buf.write("data", 36);
  buf.writeUInt32LE(dataSize, 40);
  for (let i = 0; i < n; i++) {
    const t = i / sampleRate;
    const sample = Math.sin(2 * Math.PI * 196 * t) * 9000 * (0.4 + 0.6 * Math.sin(2 * Math.PI * 3 * t));
    buf.writeInt16LE(Math.max(-32767, Math.min(32767, sample)), 44 + i * 2);
  }
  return buf;
}

export function tmpCloneWav(): { path: string; kind: "sapi" | "pcm" } {
  const dest = path.join(os.tmpdir(), `zect-r26-clone-${Date.now()}.wav`);
  return writeCloneSampleWav(dest);
}
