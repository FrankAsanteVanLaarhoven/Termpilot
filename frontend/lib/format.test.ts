import { describe, expect, it } from "vitest";
import { stateTone } from "../components/ui";

describe("stateTone", () => {
  it("maps verified to go", () => {
    expect(stateTone("verified")).toBe("go");
  });
  it("maps conflicted to stop", () => {
    expect(stateTone("conflicted")).toBe("stop");
  });
});
