import React from "react";

export function ErrorState({ message = "An error occurred" }: { message?: string }) {
  return <div className="py-6 text-sm text-rose-600">{message}</div>;
}

export default ErrorState;
