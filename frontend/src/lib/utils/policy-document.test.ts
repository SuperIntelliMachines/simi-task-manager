import { describe, expect, it } from "vitest";

import { validatePolicyDocumentFile } from "./policy-document";

describe("validatePolicyDocumentFile", () => {
  it("accepts supported policy document types", () => {
    expect(validatePolicyDocumentFile(new File(["x"], "policy.pdf"))).toBeNull();
    expect(validatePolicyDocumentFile(new File(["x"], "photo.jpg"))).toBeNull();
    expect(validatePolicyDocumentFile(new File(["x"], "photo.jpeg"))).toBeNull();
    expect(validatePolicyDocumentFile(new File(["x"], "photo.png"))).toBeNull();
  });

  it("rejects unsupported policy document types", () => {
    expect(validatePolicyDocumentFile(new File(["x"], "notes.txt"))).toBe("Unsupported file type");
  });
});
