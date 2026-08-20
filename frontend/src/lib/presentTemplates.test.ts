import { describe, expect, it } from "vitest";
import { isGenerateTemplateReady, mergePresentTemplateLists } from "./presentTemplates";

const BUILTIN = [
  { id: "general", name: "General" },
  { id: "zinnia-executive-v1", name: "Zinnia — Executive brief" },
];

describe("mergePresentTemplateLists", () => {
  it("keeps Zinnia/org/user registry cards when Presenton remote list is empty", () => {
    const list = mergePresentTemplateLists(
      BUILTIN,
      [],
      [
        { id: "zinnia-executive-v1", name: "Zinnia — Executive brief" },
        { id: "org-brand", name: "Org brand" },
        { id: "user-my-deck", name: "My deck" },
      ],
    );
    const ids = list.map((t) => t.id);
    expect(ids).toContain("zinnia-executive-v1");
    expect(ids).toContain("org-brand");
    expect(ids).toContain("user-my-deck");
    expect(ids).toContain("general");
  });

  it("does not wipe registry cards when a later empty Presenton payload is applied", () => {
    const first = mergePresentTemplateLists(BUILTIN, [], [{ id: "user-my-deck", name: "My deck" }]);
    const second = mergePresentTemplateLists(BUILTIN, [], [], first);
    expect(second.map((t) => t.id)).toContain("user-my-deck");
  });

  it("keeps native_ready from registry cards", () => {
    const list = mergePresentTemplateLists(
      BUILTIN,
      [],
      [{ id: "zinnia-executive-v1", name: "Exec", native_ready: true }],
    );
    expect(list.find((t) => t.id === "zinnia-executive-v1")?.native_ready).toBe(true);
  });

  it("generate picker only allows READY registry templates", () => {
    expect(
      isGenerateTemplateReady({ id: "zinnia-delivery-v1", name: "Delivery", native_ready: false }),
    ).toBe(false);
    expect(
      isGenerateTemplateReady({ id: "zinnia-executive-v1", name: "Exec", native_ready: true }),
    ).toBe(true);
    expect(isGenerateTemplateReady({ id: "general", name: "General" }, { presentonReady: true })).toBe(true);
    expect(isGenerateTemplateReady({ id: "general", name: "General" }, { presentonReady: false })).toBe(false);
  });
});
