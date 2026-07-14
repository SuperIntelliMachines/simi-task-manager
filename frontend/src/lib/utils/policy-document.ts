const ALLOWED_POLICY_DOCUMENT_EXTENSIONS = new Set(["pdf", "jpg", "jpeg", "png"]);

export function validatePolicyDocumentFile(file: File): string | null {
  const parts = file.name.split(".");
  const extension = parts.length > 1 ? parts.pop()?.toLowerCase() ?? "" : "";
  if (!ALLOWED_POLICY_DOCUMENT_EXTENSIONS.has(extension)) {
    return "Unsupported file type";
  }
  return null;
}

export const POLICY_DOCUMENT_ACCEPT = ".pdf,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png";
