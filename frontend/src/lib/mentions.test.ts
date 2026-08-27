import { describe, expect, it } from "vitest";
import { applyMention, detectMentionTrigger, hasMentions } from "./mentions";

describe("hasMentions", () => {
  it("detects a recognized mention type", () => {
    expect(hasMentions("check @file:calc.py")).toBe(true);
  });
  it("does not false-positive on emails or unrelated @ usage", () => {
    expect(hasMentions("contact me at a@b.com")).toBe(false);
    expect(hasMentions("no mentions here")).toBe(false);
  });
  it("gives the same answer on repeated calls with the same text (regex lastIndex regression)", () => {
    const text = "check @file:calc.py";
    expect(hasMentions(text)).toBe(true);
    expect(hasMentions(text)).toBe(true);
    expect(hasMentions(text)).toBe(true);
  });
});

describe("detectMentionTrigger", () => {
  it("detects an in-progress mention right before the cursor", () => {
    const text = "please check @fi";
    const trigger = detectMentionTrigger(text, text.length);
    expect(trigger).toEqual({ query: "fi", start: 13 });
  });
  it("returns null once the cursor has moved past the mention (whitespace typed)", () => {
    const text = "please check @file done";
    expect(detectMentionTrigger(text, text.length)).toBeNull();
  });
  it("returns null when there is no @ at all", () => {
    expect(detectMentionTrigger("nothing here", 5)).toBeNull();
  });
});

describe("applyMention", () => {
  it("inserts a colon-suffixed mention for types that need a value", () => {
    const { text, cursor } = applyMention("please check @fi", 13, 16, "file", true);
    expect(text).toBe("please check @file:");
    expect(cursor).toBe(text.length);
  });
  it("inserts a space-suffixed mention for value-less types", () => {
    const { text } = applyMention("show @di", 5, 8, "diff", false);
    expect(text).toBe("show @diff ");
  });
});
