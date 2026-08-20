/**
 * Unit checks for Computer Mode allowlist helpers (no Electron runtime).
 */
const { describe, it } = require("node:test");
const assert = require("node:assert/strict");
const computer = require("./computer.js");

describe("allowlisted", () => {
  it("matches notepad without .exe suffix", () => {
    assert.equal(computer.allowlisted("notepad"), true);
    assert.equal(computer.allowlisted("notepad.exe"), true);
  });
  it("matches Notepad++", () => {
    assert.equal(computer.allowlisted("notepad++.exe"), true);
    assert.equal(computer.allowlisted("notepad++"), true);
  });
  it("matches Teams variants", () => {
    assert.equal(computer.allowlisted("ms-teams"), true);
    assert.equal(computer.allowlisted("Teams.exe"), true);
  });
  it("matches PowerPoint", () => {
    assert.equal(computer.allowlisted("powerpnt.exe"), true);
    assert.equal(computer.allowlisted("POWERPNT"), true);
  });
  it("matches Snipping Tool hosts", () => {
    assert.equal(computer.allowlisted("SnippingTool.exe"), true);
    assert.equal(computer.allowlisted("snippingtool"), true);
    assert.equal(computer.allowlisted("ScreenClippingHost.exe"), true);
  });
  it("rejects unknown apps", () => {
    assert.equal(computer.allowlisted("malware.exe"), false);
  });
});

describe("isNotepadPlusPlusName", () => {
  it("recognizes npp aliases", () => {
    assert.equal(computer.isNotepadPlusPlusName("npp"), true);
    assert.equal(computer.isNotepadPlusPlusName("Notepad++"), true);
    assert.equal(computer.isNotepadPlusPlusName("notepad.exe"), false);
  });
});

describe("TYPE_MAX_CHARS", () => {
  it("is raised for short keystrokes but still bounded", () => {
    assert.equal(computer.TYPE_MAX_CHARS, 500);
  });
});

describe("processMatchesIntended", () => {
  it("requires allowlisted inspect", () => {
    assert.equal(
      computer.processMatchesIntended(
        { ok: true, allowlisted: false, summary: { process_name: "notepad" } },
        "notepad.exe",
      ),
      false,
    );
  });
  it("matches intended stem", () => {
    assert.equal(
      computer.processMatchesIntended(
        { ok: true, allowlisted: true, summary: { process_name: "notepad" } },
        "notepad.exe",
      ),
      true,
    );
  });
  it("matches notepad++", () => {
    assert.equal(
      computer.processMatchesIntended(
        { ok: true, allowlisted: true, summary: { process_name: "notepad++" } },
        "notepad++.exe",
      ),
      true,
    );
  });
});

describe("readPresentationBytes", () => {
  it("does not read outside Desktop/Documents/Downloads", () => {
    const out = computer.readPresentationBytes("C:\\\\Windows\\\\Temp\\\\deck.pptx");
    assert.equal(out.ok, false);
    assert.ok(
      ["path_outside_allowlist", "not_found", "unsupported_presentation_type", "path_blocked"].includes(out.error),
    );
  });
});
