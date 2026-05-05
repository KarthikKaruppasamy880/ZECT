import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import ModelSelector from "@/components/ModelSelector";

describe("ModelSelector", () => {
  it("renders with default value", () => {
    const onChange = vi.fn();
    render(<ModelSelector value="gpt-4o-mini" onChange={onChange} />);
    expect(screen.getByText("Model Selection")).toBeInTheDocument();
  });

  it("shows model options in the select dropdown", () => {
    const onChange = vi.fn();
    render(<ModelSelector value="gpt-4o-mini" onChange={onChange} />);
    const select = screen.getByRole("combobox");
    expect(select).toBeInTheDocument();
  });

  it("calls onChange when a model is selected", () => {
    const onChange = vi.fn();
    render(<ModelSelector value="gpt-4o-mini" onChange={onChange} />);
    const select = screen.getByRole("combobox");
    fireEvent.change(select, { target: { value: "gpt-4o" } });
    expect(onChange).toHaveBeenCalledWith("gpt-4o");
  });

  it("renders in compact mode", () => {
    const onChange = vi.fn();
    render(<ModelSelector value="gpt-4o-mini" onChange={onChange} compact />);
    const select = screen.getByRole("combobox");
    expect(select).toBeInTheDocument();
  });

  it("shows pricing info", () => {
    const onChange = vi.fn();
    render(<ModelSelector value="gpt-4o-mini" onChange={onChange} />);
    expect(screen.getByText(/\$0\.00015/)).toBeInTheDocument();
  });
});
