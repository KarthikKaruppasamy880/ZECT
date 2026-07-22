/**
 * Mentrix Computer Mode helpers — Windows + macOS (always gated by main process).
 */

const { spawn, execFile } = require("child_process");
const fs = require("fs");
const os = require("os");
const path = require("path");
const { promisify } = require("util");

const execFileAsync = promisify(execFile);

const WIN_APPS = ["notepad.exe", "code.exe", "explorer.exe", "msedge.exe", "chrome.exe", "calc.exe"];
const MAC_APPS = ["TextEdit", "Finder", "Safari", "Google Chrome", "Visual Studio Code", "Calculator"];

function allowlisted(appName) {
  const raw = String(appName || "");
  if (process.platform === "darwin") {
    return MAC_APPS.some((a) => a.toLowerCase() === raw.toLowerCase() || raw.toLowerCase().includes(a.toLowerCase()));
  }
  const base = raw.split(/[/\\]/).pop().toLowerCase();
  return WIN_APPS.includes(base);
}

async function openApp(appName) {
  if (!allowlisted(appName)) {
    return { ok: false, error: "app_not_allowlisted", app: appName };
  }
  try {
    if (process.platform === "darwin") {
      await execFileAsync("open", ["-a", String(appName)]);
      return { ok: true, opened: appName, platform: "darwin", audited: true };
    }
    const base = String(appName).split(/[/\\]/).pop();
    spawn(base, [], { detached: true, stdio: "ignore", shell: true }).unref();
    return { ok: true, opened: base, platform: "win32", audited: true };
  } catch (err) {
    return { ok: false, error: String(err) };
  }
}

async function screenshotDesktop() {
  const out = path.join(os.tmpdir(), `mentrix-shot-${Date.now()}.png`);
  try {
    if (process.platform === "darwin") {
      await execFileAsync("screencapture", ["-x", out]);
    } else if (process.platform === "win32") {
      const ps = `
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$bounds = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$bmp = New-Object System.Drawing.Bitmap $bounds.Width, $bounds.Height
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen($bounds.Location, [System.Drawing.Point]::Empty, $bounds.Size)
$bmp.Save('${out.replace(/'/g, "''")}')
$g.Dispose(); $bmp.Dispose()
`;
      await execFileAsync("powershell.exe", ["-NoProfile", "-Command", ps], { windowsHide: true });
    } else {
      return { ok: false, error: "unsupported_platform" };
    }
    const stat = fs.statSync(out);
    return { ok: true, desktop: "screenshot", path: out, bytes: stat.size, audited: true };
  } catch (err) {
    return { ok: false, error: String(err) };
  }
}

async function clickAt(x, y) {
  const xi = Number(x) || 0;
  const yi = Number(y) || 0;
  try {
    if (process.platform === "darwin") {
      const script = `tell application "System Events" to click at {${xi}, ${yi}}`;
      await execFileAsync("osascript", ["-e", script]);
      return { ok: true, desktop: "computer_click", x: xi, y: yi, platform: "darwin" };
    }
    const ps = `
Add-Type @"
using System; using System.Runtime.InteropServices;
public class M {
  [DllImport("user32.dll")] public static extern bool SetCursorPos(int X, int Y);
  [DllImport("user32.dll")] public static extern void mouse_event(int f, int dx, int dy, int c, int ei);
}
"@
[M]::SetCursorPos(${xi}, ${yi})
[M]::mouse_event(0x02, 0, 0, 0, 0)
[M]::mouse_event(0x04, 0, 0, 0, 0)
`;
    await execFileAsync("powershell.exe", ["-NoProfile", "-Command", ps], { windowsHide: true });
    return { ok: true, desktop: "computer_click", x: xi, y: yi, platform: "win32" };
  } catch (err) {
    return { ok: false, error: String(err), note: "Click may require accessibility permission" };
  }
}

async function typeText(text) {
  const t = String(text || "").slice(0, 200).replace(/"/g, "");
  if (!t) return { ok: false, error: "empty_text" };
  try {
    if (process.platform === "darwin") {
      await execFileAsync("osascript", ["-e", `tell application "System Events" to keystroke "${t}"`]);
      return { ok: true, desktop: "computer_type", chars: t.length, platform: "darwin" };
    }
    const ps = `
Add-Type -AssemblyName System.Windows.Forms
[System.Windows.Forms.SendKeys]::SendWait('${t.replace(/'/g, "''")}')
`;
    await execFileAsync("powershell.exe", ["-NoProfile", "-Command", ps], { windowsHide: true });
    return { ok: true, desktop: "computer_type", chars: t.length, platform: "win32" };
  } catch (err) {
    return { ok: false, error: String(err) };
  }
}

async function scroll(direction = "down") {
  const delta = String(direction).toLowerCase() === "up" ? 120 : -120;
  try {
    if (process.platform === "darwin") {
      await execFileAsync("osascript", [
        "-e",
        'tell application "System Events" to key code ' + (delta > 0 ? "126" : "125"),
      ]);
      return { ok: true, desktop: "computer_scroll", direction, platform: "darwin" };
    }
    const ps = `
Add-Type @"
using System; using System.Runtime.InteropServices;
public class S { [DllImport("user32.dll")] public static extern void mouse_event(int f, int dx, int dy, int d, int ei); }
"@
[S]::mouse_event(0x0800, 0, 0, ${delta}, 0)
`;
    await execFileAsync("powershell.exe", ["-NoProfile", "-Command", ps], { windowsHide: true });
    return { ok: true, desktop: "computer_scroll", direction, platform: "win32" };
  } catch (err) {
    return { ok: false, error: String(err) };
  }
}

async function uiInspect() {
  try {
    if (process.platform === "darwin") {
      const { stdout } = await execFileAsync("osascript", [
        "-e",
        'tell application "System Events" to get name of first application process whose frontmost is true',
      ]);
      return {
        ok: true,
        desktop: "computer_ui_inspect",
        summary: { frontmost: String(stdout).trim() },
        platform: "darwin",
      };
    }
    const ps = `
Add-Type @"
using System; using System.Text; using System.Runtime.InteropServices;
public class W {
  [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
}
"@
$h = [W]::GetForegroundWindow()
$sb = New-Object System.Text.StringBuilder 512
[void][W]::GetWindowText($h, $sb, $sb.Capacity)
$sb.ToString()
`;
    const { stdout } = await execFileAsync("powershell.exe", ["-NoProfile", "-Command", ps], {
      windowsHide: true,
    });
    return {
      ok: true,
      desktop: "computer_ui_inspect",
      summary: { foreground_title: String(stdout).trim() },
      platform: "win32",
    };
  } catch (err) {
    return { ok: false, error: String(err) };
  }
}

module.exports = {
  WIN_APPS,
  MAC_APPS,
  allowlisted,
  openApp,
  screenshotDesktop,
  clickAt,
  typeText,
  scroll,
  uiInspect,
};
