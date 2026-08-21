import { describe, expect, it } from "vitest";
import {
  isGalleryTemplateVisible,
  isGenerateTemplateReady,
  mergePresentTemplateLists,
  canDeleteGalleryTemplate,
} from "./presentTemplates";

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

  it("gallery always lists canonical Zinnia even when hide-not-ready is on", () => {
    expect(
      isGalleryTemplateVisible({ id: "zinnia-executive-v1", name: "Exec", native_ready: false }, true),
    ).toBe(true);
    expect(
      isGalleryTemplateVisible({ id: "user-my-deck", name: "Mine", native_ready: false }, true),
    ).toBe(false);
    expect(
      isGalleryTemplateVisible({ id: "user-my-deck", name: "Mine", native_ready: false }, false),
    ).toBe(true);
    expect(
      isGalleryTemplateVisible({ id: "org-brand", name: "Org", visual: { ready: true } }, true),
    ).toBe(true);
  });
});

describe("canDeleteGalleryTemplate", () => {
  it("hides Delete on builtin org and zinnia shells", () => {
    expect(canDeleteGalleryTemplate("zinnia-executive-v1")).toBe(false);
    expect(canDeleteGalleryTemplate("org-standard")).toBe(false);
    expect(canDeleteGalleryTemplate("org-delivery")).toBe(false);
    expect(canDeleteGalleryTemplate("user-abc")).toBe(true);
    expect(canDeleteGalleryTemplate("org-brand-upload")).toBe(true);
  });
});
