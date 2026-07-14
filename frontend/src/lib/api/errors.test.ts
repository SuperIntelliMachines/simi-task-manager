import { describe, expect, it } from "vitest";

import { parseApiErrorResponse, resolveCreatePolicyErrorMessage } from "./errors";

describe("parseApiErrorResponse", () => {
  it("maps 422 validation errors to readable messages", () => {
    const error = parseApiErrorResponse(422, {
      detail: [{ loc: ["body", "organization_id"], msg: "Input should be a valid integer", type: "int_type" }],
    });
    expect(error.kind).toBe("validation");
    expect(error.message).toContain("organization_id");
  });

  it("maps duplicate policy number responses", () => {
    const error = parseApiErrorResponse(409, { detail: "Policy number already exists." });
    expect(error.kind).toBe("duplicate_policy_number");
    expect(error.message).toBe("Policy number already exists.");
  });

  it("maps unknown failures to a generic message", () => {
    const error = parseApiErrorResponse(500, { detail: null });
    expect(error.message).toBe("Something went wrong. Please try again.");
  });
});

describe("resolveCreatePolicyErrorMessage", () => {
  it("returns duplicate policy message for 409 errors", () => {
    const message = resolveCreatePolicyErrorMessage(parseApiErrorResponse(409, { detail: "Policy number already exists." }));
    expect(message).toBe("Policy number already exists.");
  });
});
