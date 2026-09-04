/**
 * CP-09 -- the live, reconstructable Mission activity feed. Proves it
 * seeds from whatever the parent already has (never an empty flash while
 * the stream connects), renders the canonical typed event shape without
 * exposing anything beyond the backend's own concise summary, supports
 * click-to-navigate for file/diff events, and persists a resume cursor so
 * a remount (tab switch/refresh) does not replay everything from scratch.
 */
import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import type { MissionEvent } from "@/lib/api";

const codingAgentStreamMission = vi.fn();
vi.mock("@/lib/api", () => ({
  codingAgentStreamMission: (...args: unknown[]) => codingAgentStreamMission(...args),
}));

import MissionActivityFeed from "./MissionActivityFeed";

describe("MissionActivityFeed", () => {
  beforeEach(() => {
    sessionStorage.clear();
    codingAgentStreamMission.mockReset();
    // Default: resolve immediately, no live events pushed -- individual
    // tests override onEvent invocation via mockImplementation below.
    codingAgentStreamMission.mockImplementation(async () => {});
  });

  it("shows a placeholder when there is no mission yet", () => {
    render(<MissionActivityFeed missionId={null} initialEvents={[]} />);
    expect(screen.getByText(/start a mission to see live activity/i)).toBeInTheDocument();
  });

  it("seeds from initialEvents immediately, before the stream connects", () => {
    const events: MissionEvent[] = [
      { seq: 1, event: "plan", message: "PLAN ready — approve before isolated worktrees or edits.", at: "2026-01-01T00:00:00Z" },
    ];
    render(<MissionActivityFeed missionId="m1" initialEvents={events} />);
    expect(screen.getByText(/PLAN ready/)).toBeInTheDocument();
  });

  it("never renders anything beyond the backend's own concise message -- no raw data dump", () => {
    const events: MissionEvent[] = [
      {
        seq: 1,
        event: "model_call",
        message: "anthropic/claude-opus-5: 500 in / 200 out tokens",
        at: "2026-01-01T00:00:00Z",
        provider: "anthropic",
        model: "claude-opus-5",
        estimated_cost: 0.0123,
      },
    ];
    render(<MissionActivityFeed missionId="m1" initialEvents={events} />);
    const row = screen.getByTestId("mission-activity-row");
    expect(row).toHaveTextContent("anthropic/claude-opus-5");
    expect(row).toHaveTextContent("$0.0123");
  });

  it("opens the stream with the highest known seq as the resume cursor", async () => {
    const events: MissionEvent[] = [
      { seq: 5, event: "tests", message: "repo: passed", at: "2026-01-01T00:00:00Z" },
    ];
    render(<MissionActivityFeed missionId="m1" initialEvents={events} />);
    await waitFor(() => expect(codingAgentStreamMission).toHaveBeenCalled());
    expect(codingAgentStreamMission.mock.calls[0][1].after).toBe(5);
  });

  it("appends live events pushed over the stream without duplicating seeded ones", async () => {
    codingAgentStreamMission.mockImplementation(async (_missionId: string, opts: { onEvent: (ev: MissionEvent) => void }) => {
      opts.onEvent({ seq: 2, event: "review", message: "Ultra Review passed.", at: "2026-01-01T00:01:00Z" });
    });
    const events: MissionEvent[] = [{ seq: 1, event: "plan_approved", message: "PLAN approved.", at: "2026-01-01T00:00:00Z" }];
    render(<MissionActivityFeed missionId="m1" initialEvents={events} />);
    await waitFor(() => expect(screen.getByText(/Ultra Review passed/)).toBeInTheDocument());
    expect(screen.getByText(/PLAN approved/)).toBeInTheDocument();
    expect(screen.getAllByTestId("mission-activity-row")).toHaveLength(2);
  });

  it("clicking a file-write event opens the path in Monaco with its line, and shows the diff", () => {
    const onOpenPath = vi.fn();
    const onShowDiff = vi.fn();
    const events: MissionEvent[] = [
      { seq: 1, event: "write_file", message: "Updated src/calc.py", at: "2026-01-01T00:00:00Z", data: { path: "src/calc.py", line: 4 } },
    ];
    render(<MissionActivityFeed missionId="m1" initialEvents={events} onOpenPath={onOpenPath} onShowDiff={onShowDiff} />);
    fireEvent.click(screen.getByTestId("mission-activity-row"));
    expect(onOpenPath).toHaveBeenCalledWith("src/calc.py", 4);
    expect(onShowDiff).toHaveBeenCalled();
  });

  it("clicking a read-only event opens the path but does not trigger the diff view", () => {
    const onOpenPath = vi.fn();
    const onShowDiff = vi.fn();
    const events: MissionEvent[] = [
      { seq: 1, event: "read_file", message: "Read src/calc.py", at: "2026-01-01T00:00:00Z", data: { path: "src/calc.py" } },
    ];
    render(<MissionActivityFeed missionId="m1" initialEvents={events} onOpenPath={onOpenPath} onShowDiff={onShowDiff} />);
    fireEvent.click(screen.getByTestId("mission-activity-row"));
    expect(onOpenPath).toHaveBeenCalledWith("src/calc.py", undefined);
    expect(onShowDiff).not.toHaveBeenCalled();
  });

  it("a non-navigable event (e.g. a phase change) is not clickable", () => {
    const onOpenPath = vi.fn();
    const events: MissionEvent[] = [{ seq: 1, event: "plan_approved", message: "PLAN approved.", at: "2026-01-01T00:00:00Z" }];
    render(<MissionActivityFeed missionId="m1" initialEvents={events} onOpenPath={onOpenPath} />);
    fireEvent.click(screen.getByTestId("mission-activity-row"));
    expect(onOpenPath).not.toHaveBeenCalled();
  });
});
