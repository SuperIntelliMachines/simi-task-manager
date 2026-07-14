import { describe, expect, it } from "vitest";
import { LOGIN_PATH } from "./routes";

describe("auth routes", () => {
  it("uses a single canonical login path", () => {
    expect(LOGIN_PATH).toBe("/login");
  });
});
