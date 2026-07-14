export function formatLoggedInUserDisplayName(emailOrName: string | null | undefined): string {
  const trimmed = (emailOrName || "").trim();
  if (!trimmed) {
    return "SIMI Insurance";
  }

  const localPart = trimmed.includes("@") ? trimmed.split("@")[0] : trimmed;
  const parts = localPart
    .replace(/[-_]/g, ".")
    .split(".")
    .map((part) => part.trim())
    .filter(Boolean);

  if (parts.length === 0) {
    return "SIMI Insurance";
  }

  return parts.map((part) => part.charAt(0).toUpperCase() + part.slice(1).toLowerCase()).join(" ");
}
