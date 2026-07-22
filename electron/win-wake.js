/**
 * Windows offline wake listening via System.Speech (default mic / headset).
 * Chromium/Electron cannot use Chrome's proprietary webkitSpeechRecognition.
 */

const { spawn } = require("child_process");
const path = require("path");
const fs = require("fs");
const os = require("os");

const PS_SCRIPT = `
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Speech
$engine = New-Object System.Speech.Recognition.SpeechRecognitionEngine
try {
  $engine.SetInputToDefaultAudioDevice()
} catch {
  Write-Output "WAKE_ERROR mic_unavailable"
  exit 1
}
$choices = New-Object System.Speech.Recognition.Choices
foreach ($p in @('hey mentrix','mentrix engage','mentrix','hey matrix','wake mentrix')) {
  [void]$choices.Add($p)
}
$gb = New-Object System.Speech.Recognition.GrammarBuilder
$gb.Culture = $engine.RecognizerInfo.Culture
$gb.Append($choices)
$grammar = New-Object System.Speech.Recognition.Grammar $gb
$engine.LoadGrammar($grammar)
Write-Output "WAKE_READY"
while ($true) {
  try {
    $result = $engine.Recognize()
    if ($null -ne $result -and $result.Text) {
      Write-Output ("WAKE_MATCH " + $result.Text)
    }
  } catch {
    Start-Sleep -Milliseconds 200
  }
}
`;

function startWindowsWake(onMatch, onStatus) {
  if (process.platform !== "win32") {
    onStatus?.({ ok: false, reason: "not_windows" });
    return { stop: () => {} };
  }

  const scriptPath = path.join(os.tmpdir(), "zect-mentrix-wake.ps1");
  fs.writeFileSync(scriptPath, PS_SCRIPT, "utf8");

  const child = spawn(
    "powershell.exe",
    ["-NoProfile", "-ExecutionPolicy", "Bypass", "-File", scriptPath],
    { windowsHide: true, stdio: ["ignore", "pipe", "pipe"] },
  );

  let buf = "";
  const handleLine = (line) => {
    const t = line.trim();
    if (!t) return;
    if (t.startsWith("WAKE_READY")) {
      onStatus?.({ ok: true, reason: "listening", engine: "windows-speech" });
    } else if (t.startsWith("WAKE_MATCH")) {
      const phrase = t.slice("WAKE_MATCH".length).trim() || "Hey Mentrix";
      onMatch?.(phrase);
    } else if (t.startsWith("WAKE_ERROR")) {
      onStatus?.({ ok: false, reason: t.slice("WAKE_ERROR".length).trim() || "error" });
    }
  };

  child.stdout.on("data", (chunk) => {
    buf += chunk.toString("utf8");
    const parts = buf.split(/\r?\n/);
    buf = parts.pop() || "";
    parts.forEach(handleLine);
  });
  child.stderr.on("data", (chunk) => {
    const msg = chunk.toString("utf8").trim();
    if (msg) onStatus?.({ ok: false, reason: msg.slice(0, 200) });
  });
  child.on("exit", (code) => {
    onStatus?.({ ok: false, reason: `exited_${code}` });
  });

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

module.exports = { startWindowsWake };
