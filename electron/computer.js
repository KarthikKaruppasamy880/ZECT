/**
 * Mentrix Computer Mode helpers — Windows + macOS (always gated by main process).
 */

const { spawn, execFile } = require("child_process");
const fs = require("fs");
const os = require("os");
const path = require("path");
const { promisify } = require("util");

const execFileAsync = promisify(execFile);

const WIN_APPS = [
  "notepad.exe",
  "code.exe",
  "explorer.exe",
  "msedge.exe",
  "chrome.exe",
  "calc.exe",
  "slack.exe",
  "powerpnt.exe",
  "zoom.exe",
];
const MAC_APPS = [
  "TextEdit",
  "Finder",
  "Safari",
  "Google Chrome",
  "Visual Studio Code",
  "Calculator",
  "Microsoft PowerPoint",
  "zoom.us",
];

function allowlisted(appName) {
  const raw = String(appName || "");
  if (process.platform === "darwin") {
    return MAC_APPS.some((a) => a.toLowerCase() === raw.toLowerCase() || raw.toLowerCase().includes(a.toLowerCase()));
  }
  const base = raw.split(/[/\\]/).pop().toLowerCase();
  return WIN_APPS.includes(base);
}

function resolveZoomExe() {
  if (process.env.ZOOM_DESKTOP_PATH && fs.existsSync(process.env.ZOOM_DESKTOP_PATH)) {
    return process.env.ZOOM_DESKTOP_PATH;
  }
  const home = os.homedir();
  const candidates = [
    path.join(process.env.PROGRAMFILES || "C:\\Program Files", "Zoom", "bin", "Zoom.exe"),
    path.join(process.env["PROGRAMFILES(X86)"] || "C:\\Program Files (x86)", "Zoom", "bin", "Zoom.exe"),
    path.join(home, "AppData", "Roaming", "Zoom", "bin", "Zoom.exe"),
    path.join(home, "AppData", "Local", "Zoom", "bin", "Zoom.exe"),
  ];
  for (const c of candidates) {
    if (c && fs.existsSync(c)) return c;
  }
  return null;
}

async function openApp(appName, args) {
  const a = args || {};
  const raw = String(appName || "");
  const isZoom =
    /zoom/i.test(raw) || String(a.app || "").toLowerCase().includes("zoom");
  if (isZoom) {
    return openZoom(a);
  }
  if (!allowlisted(appName)) {
    return { ok: false, error: "app_not_allowlisted", app: appName };
  }
  try {
    if (process.platform === "darwin") {
      await execFileAsync("open", ["-a", String(appName)]);
      return { ok: true, opened: appName, platform: "darwin", audited: true };
    }
    const base = String(appName).split(/[/\\]/).pop();
    const child = spawn(base, [], { detached: true, stdio: "ignore", shell: true });
    child.unref();
    return { ok: true, opened: base, platform: "win32", audited: true };
  } catch (err) {
    return { ok: false, error: String(err) };
  }
}

async function openZoom(args) {
  const a = args || {};
  const joinUrl = String(
    a.join_url || a.url || process.env.ZOOM_DEFAULT_JOIN_URL || "",
  ).trim();
  try {
    if (joinUrl) {
      if (!/^https?:\/\/([\w.-]+\.)?zoom\.us\//i.test(joinUrl)) {
        return { ok: false, error: "invalid_zoom_join_url", hint: "Use a https://*.zoom.us/… link" };
      }
      if (process.platform === "darwin") {
        await execFileAsync("open", [joinUrl]);
      } else if (process.platform === "win32") {
        spawn("cmd", ["/c", "start", "", joinUrl], { detached: true, stdio: "ignore" }).unref();
      } else {
        spawn("xdg-open", [joinUrl], { detached: true, stdio: "ignore" }).unref();
      }
      return {
        ok: true,
        opened: "zoom_join_url",
        join_url: joinUrl,
        platform: process.platform,
        audited: true,
        note: "Join your meeting, share PowerPoint, then Narrate.",
      };
    }
    if (process.platform === "darwin") {
      await execFileAsync("open", ["-a", "zoom.us"]);
      return {
        ok: true,
        opened: "zoom.us",
        platform: "darwin",
        audited: true,
        note: "Join your meeting, share PowerPoint, then Narrate.",
      };
    }
    const exe = resolveZoomExe();
    if (!exe) {
      return {
        ok: false,
        error: "zoom_not_found",
        hint: "Install Zoom or set ZOOM_DESKTOP_PATH / ZOOM_DEFAULT_JOIN_URL",
      };
    }
    spawn(exe, [], { detached: true, stdio: "ignore" }).unref();
    return {
      ok: true,
      opened: exe,
      platform: "win32",
      audited: true,
      note: "Join your meeting, share PowerPoint, then Narrate.",
    };
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

// SendKeys treats these as key-modifier/grouping syntax — must be individually
// wrapped in braces to be sent as literal characters. Braces themselves go
// first so the wrapping braces just added aren't re-escaped by the second pass.
function escapeSendKeys(text) {
  return String(text)
    .replace(/[{}]/g, (c) => `{${c}}`)
    .replace(/[+^%~()[\]]/g, (c) => `{${c}}`);
}

// Best-effort foreground-window activation before click/type — without this,
// both previously acted on whatever window happened to already have focus,
// which is why "type into Notepad" was unreliable right after "open Notepad".
async function focusApp(appName) {
  const base = String(appName || "").split(/[/\\]/).pop().replace(/\.exe$/i, "");
  if (!base) return { ok: false, error: "no_app_name" };
  try {
    if (process.platform === "darwin") {
      await execFileAsync("osascript", ["-e", `tell application "${base.replace(/"/g, '\\"')}" to activate`]);
      return { ok: true };
    }
    const ps = `
Add-Type @"
using System; using System.Runtime.InteropServices;
public class F { [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd); }
"@
$p = Get-Process -Name '${base.replace(/'/g, "''")}' -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowHandle -ne 0 } | Select-Object -First 1
if ($p) { [F]::SetForegroundWindow($p.MainWindowHandle) }
`;
    await execFileAsync("powershell.exe", ["-NoProfile", "-Command", ps], { windowsHide: true });
    return { ok: true };
  } catch (err) {
    return { ok: false, error: String(err) };
  }
}

async function clickAt(x, y, appName) {
  const xi = Number(x) || 0;
  const yi = Number(y) || 0;
  if (appName) await focusApp(appName);
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

async function typeText(text, appName) {
  const raw = String(text || "").slice(0, 200);
  if (!raw) return { ok: false, error: "empty_text" };
  if (appName) await focusApp(appName);
  try {
    if (process.platform === "darwin") {
      const escaped = raw.replace(/\\/g, "\\\\").replace(/"/g, '\\"');
      await execFileAsync("osascript", ["-e", `tell application "System Events" to keystroke "${escaped}"`]);
      return { ok: true, desktop: "computer_type", chars: raw.length, platform: "darwin" };
    }
    const sendKeysEscaped = escapeSendKeys(raw).replace(/'/g, "''");
    const ps = `
Add-Type -AssemblyName System.Windows.Forms
[System.Windows.Forms.SendKeys]::SendWait('${sendKeysEscaped}')
`;
    await execFileAsync("powershell.exe", ["-NoProfile", "-Command", ps], { windowsHide: true });
    return { ok: true, desktop: "computer_type", chars: raw.length, platform: "win32" };
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
      const frontmost = String(stdout).trim();
      return {
        ok: true,
        desktop: "computer_ui_inspect",
        summary: { frontmost },
        platform: "darwin",
        verified: Boolean(frontmost),
        verification: {
          kind: "a11y_frontmost",
          note: "Keyboard/mouse only as fallback after identity check",
          frontmost,
        },
        allowlisted: allowlisted(frontmost),
      };
    }
    const ps = `
Add-Type @"
using System; using System.Text; using System.Runtime.InteropServices;
public class W {
  [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
}
"@
$h = [W]::GetForegroundWindow()
$sb = New-Object System.Text.StringBuilder 512
[void][W]::GetWindowText($h, $sb, $sb.Capacity)
$pidOut = 0
[void][W]::GetWindowThreadProcessId($h, [ref]$pidOut)
$procName = ""
try { $procName = (Get-Process -Id $pidOut -ErrorAction Stop).ProcessName } catch {}
Write-Output (($sb.ToString()) + "`n" + $procName + "`n" + $pidOut)
`;
    const { stdout } = await execFileAsync("powershell.exe", ["-NoProfile", "-Command", ps], {
      windowsHide: true,
    });
    const parts = String(stdout).trim().split(/\r?\n/);
    const foreground_title = (parts[0] || "").trim();
    const process_name = (parts[1] || "").trim();
    const pid = (parts[2] || "").trim();
    return {
      ok: true,
      desktop: "computer_ui_inspect",
      summary: { foreground_title, process_name, pid },
      platform: "win32",
      verified: Boolean(foreground_title || process_name),
      verification: {
        kind: "a11y_foreground",
        note: "Prefer process/window identity before click/type fallback",
        foreground_title,
        process_name,
      },
      allowlisted: allowlisted(process_name) || allowlisted(foreground_title),
    };
  } catch (err) {
    return { ok: false, error: String(err), verified: false };
  }
}


function refuseDelete(action, detail) {
  console.warn("[computer] refuse delete", action, detail || "");
  return {
    ok: false,
    error: "delete_never_allowed",
    action,
    audited: true,
    note: "Mentrix never deletes, unlinks, or rmdirs files",
  };
}

function stripPathQuotes(raw) {
  let s = String(raw || "").trim();
  // Paste from Explorer / chat often wraps paths in quotes
  if (
    (s.startsWith('"') && s.endsWith('"')) ||
    (s.startsWith("'") && s.endsWith("'"))
  ) {
    s = s.slice(1, -1).trim();
  }
  return s.replace(/^["']+|["']+$/g, "").trim();
}

function presentationAllowlistRoots() {
  const home = os.homedir();
  const roots = [
    path.join(home, "Documents"),
    path.join(home, "Desktop"),
    path.join(home, "Downloads"),
    // OneDrive redirected Desktop / Documents (common on corp Windows)
    path.join(home, "OneDrive", "Documents"),
    path.join(home, "OneDrive", "Desktop"),
    path.join(home, "OneDrive", "Downloads"),
    path.join(home, "OneDrive - Zinnia", "Documents"),
    path.join(home, "OneDrive - Zinnia", "Desktop"),
    path.join(home, "OneDrive - Zinnia", "Downloads"),
  ];
  try {
    const homeEntries = fs.readdirSync(home, { withFileTypes: true });
    for (const ent of homeEntries) {
      if (!ent.isDirectory()) continue;
      if (!/^OneDrive/i.test(ent.name)) continue;
      for (const sub of ["Documents", "Desktop", "Downloads"]) {
        roots.push(path.join(home, ent.name, sub));
      }
    }
  } catch {
    /* ignore */
  }
  return roots.map((r) => path.resolve(r));
}

function presentationPathAllowed(resolved) {
  const lower = resolved.toLowerCase();
  return presentationAllowlistRoots().some(
    (root) => lower === root.toLowerCase() || lower.startsWith(root.toLowerCase() + path.sep),
  );
}

function resolvePresentationPath(filePath, { pptxOnly = false } = {}) {
  const target = stripPathQuotes(filePath);
  if (!target) return { ok: false, error: "missing_path" };
  const resolved = path.resolve(target);
  const ext = path.extname(resolved).toLowerCase();
  const allowedExt = pptxOnly ? [".pptx"] : [".pptx", ".ppt", ".pdf"];
  if (!allowedExt.includes(ext)) {
    return {
      ok: false,
      error: pptxOnly ? "pptx_required_for_present_all" : "unsupported_presentation_type",
      path: resolved,
      hint: pptxOnly
        ? "Present all slides requires a .pptx file"
        : "Use a .pptx/.ppt/.pdf path without surrounding quotes",
    };
  }
  const blocked = [".env", "id_rsa", "credentials", "password", "secrets", ".aws", ".ssh"];
  if (blocked.some((b) => resolved.toLowerCase().includes(b))) {
    return { ok: false, error: "path_blocked", path: resolved };
  }
  if (!presentationPathAllowed(resolved)) {
    return {
      ok: false,
      error: "path_outside_allowlist",
      path: resolved,
      hint: "Allowed: Desktop, Documents, Downloads (including OneDrive copies)",
    };
  }
  if (!fs.existsSync(resolved)) {
    return { ok: false, error: "not_found", path: resolved, hint: "File does not exist at that path" };
  }
  return { ok: true, path: resolved, ext };
}

async function openPresentation(filePath) {
  const check = resolvePresentationPath(filePath);
  if (!check.ok) return check;
  const resolved = check.path;
  try {
    if (process.platform === "darwin") {
      await execFileAsync("open", [resolved]);
    } else if (process.platform === "win32") {
      spawn("cmd", ["/c", "start", "", resolved], { detached: true, stdio: "ignore" }).unref();
    } else {
      spawn("xdg-open", [resolved], { detached: true, stdio: "ignore" }).unref();
    }
    return {
      ok: true,
      desktop: "open_presentation",
      path: resolved,
      audited: true,
      platform: process.platform,
    };
  } catch (err) {
    return { ok: false, error: String(err), path: resolved };
  }
}

function stripXmlText(xml) {
  return String(xml || "")
    .replace(/<a:t[^>]*>/gi, "\u0001")
    .replace(/<[^>]+>/g, " ")
    .replace(/\u0001/g, "")
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/\s+/g, " ")
    .trim();
}

function extractAtText(xml) {
  const parts = [];
  const re = /<a:t[^>]*>([\s\S]*?)<\/a:t>/gi;
  let m;
  while ((m = re.exec(String(xml || ""))) !== null) {
    const t = String(m[1] || "")
      .replace(/&amp;/g, "&")
      .replace(/&lt;/g, "<")
      .replace(/&gt;/g, ">")
      .replace(/&quot;/g, '"')
      .replace(/&#39;/g, "'")
      .trim();
    if (t) parts.push(t);
  }
  return parts.join(" ").replace(/\s+/g, " ").trim();
}

async function extractPptxToTemp(pptxPath) {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "mentrix-pptx-"));
  try {
    if (process.platform === "win32") {
      const ps = `
Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::ExtractToDirectory('${pptxPath.replace(/'/g, "''")}', '${tmp.replace(/'/g, "''")}')
`;
      await execFileAsync("powershell.exe", ["-NoProfile", "-Command", ps], { windowsHide: true });
    } else {
      await execFileAsync("unzip", ["-q", "-o", pptxPath, "-d", tmp]);
    }
    return { ok: true, tmp };
  } catch (err) {
    try {
      fs.rmSync(tmp, { recursive: true, force: true });
    } catch {
      /* ignore */
    }
    return { ok: false, error: String(err) };
  }
}

function listSlideFiles(tmpRoot) {
  const slidesDir = path.join(tmpRoot, "ppt", "slides");
  if (!fs.existsSync(slidesDir)) return [];
  return fs
    .readdirSync(slidesDir)
    .filter((f) => /^slide\d+\.xml$/i.test(f))
    .sort((a, b) => {
      const na = Number((a.match(/\d+/) || ["0"])[0]);
      const nb = Number((b.match(/\d+/) || ["0"])[0]);
      return na - nb;
    })
    .map((f) => path.join(slidesDir, f));
}

async function parsePresentationSlides(filePath) {
  const check = resolvePresentationPath(filePath, { pptxOnly: true });
  if (!check.ok) return check;
  const extracted = await extractPptxToTemp(check.path);
  if (!extracted.ok) {
    return { ok: false, error: "pptx_extract_failed", detail: extracted.error, path: check.path };
  }
  const tmp = extracted.tmp;
  try {
    const slideFiles = listSlideFiles(tmp);
    const slides = [];
    for (let i = 0; i < slideFiles.length; i++) {
      const slideXml = fs.readFileSync(slideFiles[i], "utf8");
      const text = extractAtText(slideXml).slice(0, 2000);
      const num = Number((path.basename(slideFiles[i]).match(/\d+/) || [String(i + 1)])[0]);
      let notes = "";
      const notesPath = path.join(tmp, "ppt", "notesSlides", `notesSlide${num}.xml`);
      if (fs.existsSync(notesPath)) {
        notes = extractAtText(fs.readFileSync(notesPath, "utf8")).slice(0, 2000);
        // Drop common "Click to edit Master text styles" junk if that's all we got
        if (/click to edit master/i.test(notes) && notes.length < 80) notes = "";
      }
      slides.push({
        index: i,
        notes,
        text: text || stripXmlText(slideXml).slice(0, 500),
      });
    }
    return {
      ok: true,
      desktop: "parse_presentation_slides",
      path: check.path,
      slides,
      count: slides.length,
      audited: true,
    };
  } catch (err) {
    return { ok: false, error: String(err), path: check.path };
  } finally {
    try {
      fs.rmSync(tmp, { recursive: true, force: true });
    } catch {
      /* ignore */
    }
  }
}

async function powerpointKey(key, appName) {
  const k = String(key || "").toLowerCase().trim();
  const mapWin = { f5: "{F5}", right: "{RIGHT}", esc: "{ESC}", escape: "{ESC}" };
  const mapMac = { f5: 96, right: 124, esc: 53, escape: 53 };
  if (!mapWin[k]) {
    return { ok: false, error: "unsupported_powerpoint_key", key: k, hint: "Use f5 | right | esc" };
  }
  const app =
    appName ||
    (process.platform === "darwin" ? "Microsoft PowerPoint" : "POWERPNT");
  await focusApp(app);
  try {
    if (process.platform === "darwin") {
      await execFileAsync("osascript", [
        "-e",
        `tell application "System Events" to key code ${mapMac[k]}`,
      ]);
      return { ok: true, desktop: "powerpoint_key", key: k, app, platform: "darwin", audited: true };
    }
    const send = mapWin[k];
    const ps = `
Add-Type -AssemblyName System.Windows.Forms
[System.Windows.Forms.SendKeys]::SendWait('${send}')
`;
    await execFileAsync("powershell.exe", ["-NoProfile", "-Command", ps], { windowsHide: true });
    return { ok: true, desktop: "powerpoint_key", key: k, app, platform: "win32", audited: true };
  } catch (err) {
    return { ok: false, error: String(err), key: k };
  }
}

function writeNoteFile(args) {
  const a = args || {};
  const content = String(a.content || "");
  if (!content.trim()) return { ok: false, error: "empty_content" };
  const home = os.homedir();
  const folderRaw = String(a.folder || "Desktop");
  const folderName = /document/i.test(folderRaw) ? "Documents" : "Desktop";
  const base = path.join(home, folderName);
  let target = a.path ? String(a.path) : "";
  if (!target) {
    let name = path.basename(String(a.filename || "mentrix-note.md"));
    if (!/\.(md|txt)$/i.test(name)) name = `${name}.md`;
    target = path.join(base, name);
  }
  const resolved = path.resolve(target);
  const docs = path.resolve(path.join(home, "Documents"));
  const desk = path.resolve(path.join(home, "Desktop"));
  const allowed = [docs, desk].some(
    (root) =>
      resolved.toLowerCase() === root.toLowerCase() ||
      resolved.toLowerCase().startsWith(root.toLowerCase() + path.sep)
  );
  if (!allowed) {
    return { ok: false, error: "path_outside_allowlist", path: resolved };
  }
  const blocked = [".env", "id_rsa", "credentials", "password", "secrets", ".aws", ".ssh"];
  if (blocked.some((b) => resolved.toLowerCase().includes(b))) {
    return { ok: false, error: "path_blocked", path: resolved };
  }
  try {
    fs.mkdirSync(path.dirname(resolved), { recursive: true });
    fs.writeFileSync(resolved, content.slice(0, 50000), "utf8");
    return {
      ok: true,
      desktop: "write_note",
      path: resolved,
      bytes: Buffer.byteLength(content.slice(0, 50000), "utf8"),
      audited: true,
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
  openZoom,
  openPresentation,
  parsePresentationSlides,
  powerpointKey,
  focusApp,
  escapeSendKeys,
  screenshotDesktop,
  clickAt,
  typeText,
  scroll,
  uiInspect,
  refuseDelete,
  writeNoteFile,
  stripPathQuotes,
};
