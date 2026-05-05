import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import PromptHygieneTips from "@/components/PromptHygieneTips";

describe("PromptHygieneTips", () => {
  it("renders the tips header for ask mode", () => {
    render(<PromptHygieneTips mode="ask" />);
    expect(screen.getByText("Prompt Tips")).toBeInTheDocument();
  });

  it("renders the tips header for plan mode", () => {
    render(<PromptHygieneTips mode="plan" />);
    expect(screen.getByText("Prompt Tips")).toBeInTheDocument();
  });

  it("renders the tips header for build mode", () => {
    render(<PromptHygieneTips mode="build" />);
    expect(screen.getByText("Prompt Tips")).toBeInTheDocument();
  });

  it("renders the tips header for review mode", () => {
    render(<PromptHygieneTips mode="review" />);
    expect(screen.getByText("Prompt Tips")).toBeInTheDocument();
  });

  it("expands to show tips when clicked", () => {
    render(<PromptHygieneTips mode="ask" />);
    fireEvent.click(screen.getByText("Prompt Tips"));
    expect(screen.getByText(/Be specific/)).toBeInTheDocument();
    expect(screen.getByText(/Provide context/)).toBeInTheDocument();
  });

  it("collapses when clicked again", () => {
    render(<PromptHygieneTips mode="ask" />);
    const header = screen.getByText("Prompt Tips");
    fireEvent.click(header);
    expect(screen.getByText(/Be specific/)).toBeInTheDocument();
    fireEvent.click(header);
    expect(screen.queryByText(/Be specific/)).not.toBeInTheDocument();
  });

  it("dismisses when X button clicked", () => {
    render(<PromptHygieneTips mode="ask" />);
    expect(screen.getByText("Prompt Tips")).toBeInTheDocument();
    fireEvent.click(screen.getByTitle("Dismiss tips"));
    expect(screen.queryByText("Prompt Tips")).not.toBeInTheDocument();
  });

  it("shows mode-specific tips for plan mode", () => {
    render(<PromptHygieneTips mode="plan" />);
    fireEvent.click(screen.getByText("Prompt Tips"));
    expect(screen.getByText(/Define scope clearly/)).toBeInTheDocument();
    expect(screen.getByText(/List constraints/)).toBeInTheDocument();
  });

  it("shows mode-specific tips for build mode", () => {
    render(<PromptHygieneTips mode="build" />);
    fireEvent.click(screen.getByText("Prompt Tips"));
    expect(screen.getByText(/Describe the feature/)).toBeInTheDocument();
    expect(screen.getByText(/Use templates/)).toBeInTheDocument();
  });

  it("shows example text for tips that have examples", () => {
    render(<PromptHygieneTips mode="ask" />);
    fireEvent.click(screen.getByText("Prompt Tips"));
    expect(
      screen.getByText(/How should I structure auth in a React/)
    ).toBeInTheDocument();
  });

  it("applies custom className", () => {
    const { container } = render(
      <PromptHygieneTips mode="ask" className="mb-4" />
    );
    expect(container.firstChild).toHaveClass("mb-4");
  });
});
