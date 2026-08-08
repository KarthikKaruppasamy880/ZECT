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
  it("matches Teams variants", () => {
    assert.equal(computer.allowlisted("ms-teams"), true);
    assert.equal(computer.allowlisted("Teams.exe"), true);
  });
  it("rejects unknown apps", () => {
    assert.equal(computer.allowlisted("malware.exe"), false);
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
});
