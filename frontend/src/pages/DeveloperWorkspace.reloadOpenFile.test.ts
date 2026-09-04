import { describe, expect, it } from "vitest";
import { shouldReloadFileOnAgentChange } from "./DeveloperWorkspace";

// A Mission editing a file underneath an open editor buffer used to leave the
// Diff panel showing the stale baseline/content until the user manually
// reopened the file. onFilesChanged now reloads the buffer for the currently
// open path -- but only when it isn't holding unsaved user edits.
describe("shouldReloadFileOnAgentChange", () => {
  const resolve = (p: string) => `/repo/${p}`;

  it("reloads when a changed path resolves to the clean, currently open file", () => {
    expect(shouldReloadFileOnAgentChange(["src/a.ts"], "/repo/src/a.ts", false, resolve)).toBe(true);
  });

  it("does not reload when the open buffer has unsaved edits", () => {
    expect(shouldReloadFileOnAgentChange(["src/a.ts"], "/repo/src/a.ts", true, resolve)).toBe(false);
  });

  it("does not reload an unrelated open tab", () => {
    expect(shouldReloadFileOnAgentChange(["src/b.ts"], "/repo/src/a.ts", false, resolve)).toBe(false);
  });

  it("does nothing when no file is open", () => {
    expect(shouldReloadFileOnAgentChange(["src/a.ts"], "", false, resolve)).toBe(false);
  });
});
