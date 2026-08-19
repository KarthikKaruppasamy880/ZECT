import { describe, expect, it } from "vitest";
import { mergePresentTemplateLists } from "./presentTemplates";

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
});
