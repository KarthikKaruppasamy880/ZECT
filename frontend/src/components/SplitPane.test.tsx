import { describe, expect, it } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import SplitPane from "./SplitPane";

describe("SplitPane", () => {
  it("never uses zero width and toggles collapse with Enter", () => {
    render(
      <SplitPane axis="horizontal" storageKey="zect_test_split" initial={50} min={16} max={80} testId="split-test">
        <div>left</div>
        <div>right</div>
      </SplitPane>,
    );
    const handle = screen.getByTestId("split-test-handle");
    expect(handle.getAttribute("aria-valuemin")).toBe("16");
    fireEvent.keyDown(handle, { key: "Enter" });
    expect(screen.getByTestId("split-test").getAttribute("data-collapsed")).toBe("true");
    expect(Number(handle.getAttribute("aria-valuenow"))).toBeGreaterThan(0);
    fireEvent.keyDown(handle, { key: "Enter" });
    expect(screen.getByTestId("split-test").getAttribute("data-collapsed")).toBe("false");
  });
});
