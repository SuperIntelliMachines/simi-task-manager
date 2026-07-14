import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useWorkbench } from "../app/providers/workbench-provider";
import { resolvePostLoginPath } from "../lib/auth/post-login";

const SIMI_LOGO_URL = "https://superintellimachines.ai/lovable-uploads/ICON.png";

const loginCardClassName =
  "login-card w-full px-6 py-8 sm:px-10 sm:py-10";
const loginInputClassName = "login-input w-full px-4 text-[15px] text-white placeholder:text-slate-500";
const loginPrimaryButtonClassName =
  "login-btn-primary mt-6 w-full text-[15px] font-semibold text-slate-950";

function EyeIcon({ className = "h-5 w-5" }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.5}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7Z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  );
}

function EyeOffIcon({ className = "h-5 w-5" }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.5}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M3 3l18 18" />
      <path d="M10.6 10.6a2 2 0 0 0 2.8 2.8" />
      <path d="M9.9 5.1A10.5 10.5 0 0 1 12 5c6.5 0 10 7 10 7a17.4 17.4 0 0 1-3.2 4.1" />
      <path d="M6.1 6.1C3.9 7.6 2 12 2 12s3.5 7 10 7a10.4 10.4 0 0 0 4.2-.9" />
    </svg>
  );
}

export function LoginPage() {
  const [id, setId] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [step, setStep] = useState<"email" | "password">("email");
  const navigate = useNavigate();
  const { refreshSession } = useWorkbench();

  async function handleSubmit(e?: React.FormEvent<HTMLFormElement>) {
    if (e) e.preventDefault();
    setError(null);
    try {
      const res = await fetch("/api/v1/auth/token", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: id, password }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        setError(err.detail || "Login failed");
        return;
      }
      const data = await res.json();
      localStorage.setItem("atm:token", data.access_token);
      if (data.refresh_token) {
        localStorage.setItem("atm:refreshToken", data.refresh_token);
      }

      const profile = await refreshSession();
      if (!profile) {
        setError("Login failed. Could not load your account.");
        return;
      }

      navigate(resolvePostLoginPath(profile));
    } catch {
      setError("Network error");
    }
  }

  useEffect(() => {
    try {
      const params = new URLSearchParams(window.location.search);
      const invitedEmail = params.get("invited_email");
      if (invitedEmail) {
        setId(invitedEmail);
        setStep("password");
      }
    } catch {
      // ignore
    }
  }, []);

  function handleContinue(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (!id || !id.includes("@")) {
      setError("Enter a valid email address");
      return;
    }
    setStep("password");
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
            Intelligence that runs your organization
          </p>
        </div>

        {step === "email" && (
          <form onSubmit={handleContinue} className={loginCardClassName}>
            <h2 className="text-2xl sm:text-[1.75rem] font-bold text-white text-center tracking-tight">
              Welcome back
            </h2>
            <p className="text-sm sm:text-[15px] text-slate-400 text-center mt-2 mb-7 sm:mb-8">
              Sign in to continue to your workspace
            </p>

            {error && <div className="login-error mb-4">{error}</div>}

            <label className="block text-sm font-medium text-slate-300 mb-2">Email address</label>
            <input
              value={id}
              onChange={(e) => setId(e.target.value)}
              type="email"
              placeholder="you@company.com"
              className={loginInputClassName}
              autoComplete="email"
            />

            <button type="submit" className={loginPrimaryButtonClassName}>
              Continue →
            </button>

            <p className="text-xs text-slate-500 text-center mt-7 sm:mt-8 leading-relaxed">
              By signing in, you agree to our{" "}
              <span className="text-slate-400 underline underline-offset-2 cursor-pointer hover:text-slate-300 transition-colors">
                Terms of Service
              </span>{" "}
              and{" "}
              <span className="text-slate-400 underline underline-offset-2 cursor-pointer hover:text-slate-300 transition-colors">
                Privacy Policy
              </span>
            </p>
          </form>
        )}

        {step === "password" && (
          <form onSubmit={handleSubmit} className={loginCardClassName}>
            <h2 className="text-2xl sm:text-[1.75rem] font-bold text-white text-center tracking-tight">
              Enter your password
            </h2>
            <p className="text-sm sm:text-[15px] text-slate-400 text-center mt-2 mb-7 sm:mb-8">
              Signing in as{" "}
              <span className="text-cyan-300/90 font-medium">{id}</span>
            </p>

            <label className="block">
              <div className="flex justify-between items-center mb-2">
                <span className="text-sm font-medium text-slate-300">Password</span>
                <a
                  className="text-sm text-cyan-400/90 hover:text-cyan-300 underline underline-offset-2 transition-colors"
                  href={`/forgot-password${id ? `?email=${encodeURIComponent(id)}` : ""}`}
                  onClick={(e) => {
                    e.preventDefault();
                    navigate(`/forgot-password${id ? `?email=${encodeURIComponent(id)}` : ""}`);
                  }}
                >
                  Forgot password?
                </a>
              </div>
              <div className="relative">
                <input
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  type={showPassword ? "text" : "password"}
                  required
                  className={`${loginInputClassName} pr-12`}
                  autoComplete="current-password"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((current) => !current)}
                  className="absolute inset-y-0 right-0 flex items-center justify-center px-3.5 text-slate-400 transition-colors hover:text-slate-200 focus-visible:outline-none focus-visible:text-cyan-300"
                  aria-label={showPassword ? "Hide password" : "Show password"}
                  aria-pressed={showPassword}
                >
                  {showPassword ? (
                    <EyeOffIcon className="h-5 w-5" />
                  ) : (
                    <EyeIcon className="h-5 w-5" />
                  )}
                </button>
              </div>
            </label>

            {error && <div className="login-error mt-4">{error}</div>}

            <div className="flex items-center gap-3 mt-6">
              <button
                type="button"
                onClick={() => {
                  setShowPassword(false);
                  setStep("email");
                }}
                className="login-btn-secondary flex-1 h-14 text-[15px] font-medium"
              >
                ← Back
              </button>
              <button type="submit" className="login-btn-primary flex-1 h-14 text-[15px] font-semibold text-slate-950">
                Sign in →
              </button>
            </div>

            <p className="text-xs text-slate-500 text-center mt-7 sm:mt-8 leading-relaxed">
              By signing in, you agree to our{" "}
              <span className="text-slate-400 underline underline-offset-2 cursor-pointer hover:text-slate-300 transition-colors">
                Terms of Service
              </span>{" "}
              and{" "}
              <span className="text-slate-400 underline underline-offset-2 cursor-pointer hover:text-slate-300 transition-colors">
                Privacy Policy
              </span>
            </p>
          </form>
        )}
      </div>

      <p className="relative z-10 mt-10 text-xs text-slate-600 tracking-wide">
        Powered by AI • Built for the future
      </p>
    </div>
  );
}
