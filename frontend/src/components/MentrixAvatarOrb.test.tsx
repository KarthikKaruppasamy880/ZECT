import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import MentrixAvatarOrb from "@/components/MentrixAvatarOrb";

describe("MentrixAvatarOrb", () => {
  it("renders a hero face with idle animation hooks", () => {
    render(<MentrixAvatarOrb state="idle" />);
    const orb = screen.getByTestId("mentrix-avatar");
    expect(orb.getAttribute("data-state")).toBe("idle");
    expect(orb.className).toMatch(/h-28/);
    expect(orb.querySelector(".mentrix-orb-face")).toBeTruthy();
    expect(orb.querySelectorAll(".mentrix-orb-eye")).toHaveLength(2);
    expect(orb.querySelector(".mentrix-orb-mouth")).toBeTruthy();
  });

  it("stays compact in Display mode", () => {
    render(<MentrixAvatarOrb state="speaking" compact />);
    const orb = screen.getByTestId("mentrix-avatar");
    expect(orb.className).toMatch(/h-10/);
    expect(orb.getAttribute("data-state")).toBe("speaking");
  });
});
