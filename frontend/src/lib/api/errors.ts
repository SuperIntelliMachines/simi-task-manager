export type ApiErrorKind = "validation" | "duplicate_policy_number" | "generic";

export class ApiRequestError extends Error {
  readonly status: number;
  readonly detail: unknown;
  readonly kind: ApiErrorKind;

  constructor(message: string, status: number, detail: unknown, kind: ApiErrorKind = "generic") {
    super(message);
    this.name = "ApiRequestError";
    this.status = status;
    this.detail = detail;
    this.kind = kind;
  }
}

function formatValidationDetail(detail: unknown): string {
  if (typeof detail === "string" && detail.trim()) {
    return detail;
  }
  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => {
        if (typeof item === "string") return item;
        if (item && typeof item === "object" && "msg" in item) {
          const record = item as { loc?: unknown; msg?: string };
          const loc = Array.isArray(record.loc)
            ? record.loc.filter((part) => part !== "body").join(" ")
            : "";
          const msg = record.msg ?? "Invalid value";
          return loc ? `${loc}: ${msg}` : msg;
        }
        return null;
      })
      .filter((value): value is string => Boolean(value));
    if (messages.length > 0) {
      return messages.join(" ");
    }
  }
  return "Please check the form and try again.";
}

const DUPLICATE_POLICY_MESSAGE = "Policy number already exists.";

export function parseApiErrorResponse(status: number, body: unknown): ApiRequestError {
  const detail = (body as { detail?: unknown } | null)?.detail;

  if (status === 409) {
    const message =
      typeof detail === "string" && detail.trim() ? detail : DUPLICATE_POLICY_MESSAGE;
    return new ApiRequestError(message, status, detail, "duplicate_policy_number");
  }

  if (status === 422) {
    return new ApiRequestError(formatValidationDetail(detail), status, detail, "validation");
  }

  if (status === 400 && typeof detail === "string" && detail.toLowerCase().includes("policy number")) {
    return new ApiRequestError(DUPLICATE_POLICY_MESSAGE, status, detail, "duplicate_policy_number");
  }

  if (typeof detail === "string" && detail.trim()) {
    return new ApiRequestError(detail, status, detail);
  }

  if (status === 401) {
    return new ApiRequestError("Your session has expired. Please sign in again.", status, detail);
  }
  if (status === 403) {
    return new ApiRequestError("You do not have permission to perform this action.", status, detail);
  }
  if (status === 404) {
    return new ApiRequestError("The requested reminder was not found.", status, detail);
  }
  if (status >= 500) {
    return new ApiRequestError("Something went wrong on the server. Please try again later.", status, detail);
  }

  return new ApiRequestError("Something went wrong. Please try again.", status, detail);
}

/** User-facing message for Reminder Management and other CRUD flows. */
export function resolveApiErrorMessage(error: unknown, fallback = "Something went wrong. Please try again."): string {
  if (error instanceof ApiRequestError) {
    return error.message || fallback;
  }
  if (error instanceof Error && error.message.trim()) {
    return error.message;
  }
  return fallback;
}

export function resolveCreatePolicyErrorMessage(error: unknown): string {
  if (error instanceof ApiRequestError) {
    if (error.kind === "duplicate_policy_number") {
      return DUPLICATE_POLICY_MESSAGE;
    }
    if (error.kind === "validation") {
      return error.message;
    }
    return error.message || "Something went wrong. Please try again.";
  }
  if (error instanceof Error && error.message.trim()) {
    return error.message;
  }
  return "Something went wrong. Please try again.";
}
