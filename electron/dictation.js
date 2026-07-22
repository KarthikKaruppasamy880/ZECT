/**
 * Free-form dictation for Mentrix Connect Voice fallback (when Realtime unavailable).
 * Windows: System.Speech DictationGrammar. macOS: emits status for renderer Web Speech / manual.
 */

const { spawn } = require("child_process");
const path = require("path");
const fs = require("fs");
const os = require("os");

const WIN_PS = `
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Speech
$engine = New-Object System.Speech.Recognition.SpeechRecognitionEngine
try { $engine.SetInputToDefaultAudioDevice() } catch { Write-Output "DICT_ERROR mic_unavailable"; exit 1 }
$dictation = New-Object System.Speech.Recognition.DictationGrammar
$engine.LoadGrammar($dictation)
Write-Output "DICT_READY"
while ($true) {
  try {
    $result = $engine.Recognize()
    if ($null -ne $result -and $result.Text) {
      Write-Output ("DICT_TEXT " + $result.Text)
    }
  } catch { Start-Sleep -Milliseconds 200 }
}
`;

function startDictation(onText, onStatus) {
  if (process.platform === "win32") {
    const scriptPath = path.join(os.tmpdir(), "zect-mentrix-dictation.ps1");
    fs.writeFileSync(scriptPath, WIN_PS, "utf8");
    const child = spawn(
      "powershell.exe",
      ["-NoProfile", "-ExecutionPolicy", "Bypass", "-File", scriptPath],
      { windowsHide: true, stdio: ["ignore", "pipe", "pipe"] },
    );
    let buf = "";
    const handle = (line) => {
      const t = line.trim();
      if (!t) return;
      if (t.startsWith("DICT_READY")) onStatus?.({ ok: true, reason: "dictation_listening" });
      else if (t.startsWith("DICT_TEXT")) onText?.(t.slice("DICT_TEXT".length).trim());
      else if (t.startsWith("DICT_ERROR")) onStatus?.({ ok: false, reason: t.slice(10).trim() });
    };
    child.stdout.on("data", (chunk) => {
      buf += chunk.toString("utf8");
      const parts = buf.split(/\r?\n/);
      buf = parts.pop() || "";
      parts.forEach(handle);
    });
    child.on("exit", (code) => onStatus?.({ ok: false, reason: `dictation_exited_${code}` }));
    return {
      stop: () => {
        try {
          child.kill();
        } catch {
          /* ignore */
        }
        try {
          fs.unlinkSync(scriptPath);
        } catch {
          /* ignore */
        }
      },
    };
  }

  // macOS: no built-in free dictation IPC without TCC complexity — signal renderer
  onStatus?.({ ok: true, reason: "dictation_use_realtime_or_type", platform: "darwin" });
  return { stop: () => {} };
}

module.exports = { startDictation };
