import React, { useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { LOGIN_PATH } from "../lib/auth/routes";

const SIMI_LOGO_URL = "https://superintellimachines.ai/lovable-uploads/ICON.png";
const loginCardClassName = "login-card w-full px-6 py-8 sm:px-10 sm:py-10";
const loginInputClassName = "login-input w-full px-4 text-[15px] text-white placeholder:text-slate-500";
const loginPrimaryButtonClassName =
  "login-btn-primary mt-6 w-full text-[15px] font-semibold text-slate-950";

const MIN_PASSWORD_LENGTH = 8;

function validateNewPassword(password: string, confirmPassword: string): string | null {
  if (!password) return "Enter a new password";
  if (password.length < MIN_PASSWORD_LENGTH) {
    return `Password must be at least ${MIN_PASSWORD_LENGTH} characters`;
  }
  if (password.trim() !== password) {
    return "Password cannot start or end with whitespace";
  }
  if (!/[A-Za-z]/.test(password) || !/\d/.test(password)) {
    return "Password must include at least one letter and one number";
  }
  if (password !== confirmPassword) {
    return "New password and confirm password must match";
  }
  return null;
}

export function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const token = useMemo(() => searchParams.get("token")?.trim() || "", [searchParams]);

  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSuccess(null);

    if (!token) {
      setError("This reset link is missing a token. Request a new password reset.");
      return;
    }

    const validationError = validateNewPassword(password, confirmPassword);
    if (validationError) {
      setError(validationError);
      return;
    }

    setIsSubmitting(true);
    try {
      const res = await fetch("/api/v1/auth/password-reset/confirm", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, new_password: password }),
      });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) {
        setError(body.detail || "Unable to reset password");
        return;
      }

      setSuccess(body.detail || "Password reset successfully");
      setTimeout(() => navigate(LOGIN_PATH), 1200);
    } catch {
      setError("Network error. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="login-page min-h-screen font-sans flex flex-col items-center justify-center px-4 py-10 sm:px-6 relative">
      <div className="login-page-bg" aria-hidden="true">
        <div className="login-glow login-glow-left" />
        <div className="login-glow login-glow-right" />
        <div className="login-particles" />
      </div>

      <div className="relative z-10 w-full max-w-[440px] flex flex-col items-center">
        <div className="login-brand mb-8 sm:mb-10 text-center">
          <img
            src={SIMI_LOGO_URL}
            alt="SIMI logo"
            className="mx-auto h-16 w-16 sm:h-20 sm:w-20 mb-4 sm:mb-5 drop-shadow-[0_0_24px_rgba(34,211,238,0.25)]"
          />
          <h1 className="login-brand-title text-4xl sm:text-[2.75rem] leading-tight font-bold tracking-tight">
            SIMI
          </h1>
          <p className="login-brand-subtitle mt-2 sm:mt-3 text-sm sm:text-base text-slate-400 font-normal">
            Choose a new password
          </p>
        </div>

        <form onSubmit={handleSubmit} className={loginCardClassName}>
          <h2 className="text-2xl sm:text-[1.75rem] font-bold text-white text-center tracking-tight">
            Reset password
          </h2>
          <p className="text-sm sm:text-[15px] text-slate-400 text-center mt-2 mb-7 sm:mb-8">
            Enter and confirm your new password to finish resetting your account.
          </p>

          {!token ? (
            <div className="login-error mb-4">
              This reset link is invalid or incomplete.{" "}
              <Link to="/forgot-password" className="underline underline-offset-2">
                Request a new link
              </Link>
              .
            </div>
          ) : null}

          {error && <div className="login-error mb-4">{error}</div>}
          {success && (
            <div className="mb-4 rounded-xl border border-emerald-400/30 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-200">
              {success} Redirecting to sign in...
            </div>
          )}

          <label className="block text-sm font-medium text-slate-300 mb-2">New password</label>
          <input
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            type="password"
            className={loginInputClassName}
            autoComplete="new-password"
            required
            disabled={!token || isSubmitting}
          />

          <label className="block text-sm font-medium text-slate-300 mb-2 mt-5">Confirm password</label>
          <input
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            type="password"
            className={loginInputClassName}
            autoComplete="new-password"
            required
            disabled={!token || isSubmitting}
          />

          <p className="mt-3 text-xs text-slate-500">
            Use at least {MIN_PASSWORD_LENGTH} characters with at least one letter and one number.
          </p>

          <button
            type="submit"
            className={loginPrimaryButtonClassName}
            disabled={!token || isSubmitting}
          >
            {isSubmitting ? "Updating..." : "Update password →"}
          </button>

          <p className="text-sm text-slate-500 text-center mt-7">
            <Link to={LOGIN_PATH} className="text-cyan-400/90 hover:text-cyan-300 underline underline-offset-2">
              Back to sign in
            </Link>
          </p>
        </form>
      </div>
    </div>
  );
}

export default ResetPasswordPage;
