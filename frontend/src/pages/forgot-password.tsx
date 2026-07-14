import React, { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { LOGIN_PATH } from "../lib/auth/routes";

const SIMI_LOGO_URL = "https://superintellimachines.ai/lovable-uploads/ICON.png";
const loginCardClassName = "login-card w-full px-6 py-8 sm:px-10 sm:py-10";
const loginInputClassName = "login-input w-full px-4 text-[15px] text-white placeholder:text-slate-500";
const loginPrimaryButtonClassName =
  "login-btn-primary mt-6 w-full text-[15px] font-semibold text-slate-950";

type RequestResponse = {
  detail?: string;
  reset_token?: string | null;
  reset_url?: string | null;
};

export function ForgotPasswordPage() {
  const [searchParams] = useSearchParams();
  const [email, setEmail] = useState(() => searchParams.get("email")?.trim() || "");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [devResetUrl, setDevResetUrl] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    setDevResetUrl(null);

    const normalized = email.trim().toLowerCase();
    if (!normalized || !normalized.includes("@")) {
      setError("Enter a valid email address");
      return;
    }

    setIsSubmitting(true);
    try {
      const res = await fetch("/api/v1/auth/password-reset/request", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: normalized }),
      });
      const body = (await res.json().catch(() => ({}))) as RequestResponse & { detail?: string };
      if (!res.ok) {
        setError(body.detail || "Unable to request a password reset");
        return;
      }

      setSuccess(body.detail || "If the account exists, a reset link has been sent.");
      if (body.reset_url) {
        setDevResetUrl(body.reset_url);
      } else if (body.reset_token) {
        setDevResetUrl(`/reset-password?token=${encodeURIComponent(body.reset_token)}`);
      }
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
            Reset your account password
          </p>
        </div>

        <form onSubmit={handleSubmit} className={loginCardClassName}>
          <h2 className="text-2xl sm:text-[1.75rem] font-bold text-white text-center tracking-tight">
            Forgot password
          </h2>
          <p className="text-sm sm:text-[15px] text-slate-400 text-center mt-2 mb-7 sm:mb-8">
            Enter your email and we&apos;ll send a secure reset link.
          </p>

          {error && <div className="login-error mb-4">{error}</div>}
          {success && (
            <div className="mb-4 rounded-xl border border-emerald-400/30 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-200">
              {success}
            </div>
          )}

          <label className="block text-sm font-medium text-slate-300 mb-2">Email address</label>
          <input
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            type="email"
            placeholder="you@company.com"
            className={loginInputClassName}
            autoComplete="email"
            required
          />

          <button type="submit" className={loginPrimaryButtonClassName} disabled={isSubmitting}>
            {isSubmitting ? "Sending..." : "Send reset link →"}
          </button>

          {devResetUrl ? (
            <div className="mt-5 rounded-xl border border-cyan-400/20 bg-cyan-500/10 px-4 py-3 text-sm text-cyan-100">
              <p className="font-medium text-cyan-200">Development reset link</p>
              {devResetUrl.startsWith("http") ? (
                <a href={devResetUrl} className="mt-2 block break-all underline underline-offset-2 hover:text-white">
                  {devResetUrl}
                </a>
              ) : (
                <Link to={devResetUrl} className="mt-2 block break-all underline underline-offset-2 hover:text-white">
                  {devResetUrl}
                </Link>
              )}
            </div>
          ) : null}

          <p className="text-sm text-slate-500 text-center mt-7">
            Remembered your password?{" "}
            <Link to={LOGIN_PATH} className="text-cyan-400/90 hover:text-cyan-300 underline underline-offset-2">
              Back to sign in
            </Link>
          </p>
        </form>
      </div>
    </div>
  );
}

export default ForgotPasswordPage;
