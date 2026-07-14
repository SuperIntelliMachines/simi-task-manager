import React, { useMemo, useState } from "react";
import { motion } from "framer-motion";
import { useWorkbench } from "../../app/providers/workbench-provider";
import { formatRoleDisplayLabel } from "../../lib/auth/role-labels";
import { apiClient } from "../../lib/api/client";
import { useToast } from "../../components/ui/toast";
import { ApiRequestError } from "../../lib/api/errors";

const labelClassName = "mb-2 block text-sm font-medium text-gray-800 dark:text-slate-300";
const fieldClassName =
  "w-full rounded-xl border border-slate-300/90 bg-white/90 dark:border-white/10 dark:bg-slate-950/40 px-4 h-12 text-sm font-medium text-black dark:text-white placeholder:text-gray-500 dark:placeholder:text-slate-400 placeholder:font-normal focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#14B8A6]/40 focus-visible:border-[#14B8A6]/30 transition-colors";
const sectionHeadingClassName =
  "mb-5 flex items-center gap-3 text-base font-bold tracking-tight text-black dark:text-white md:text-lg";
const detailLabelClassName = "text-sm font-medium text-gray-600 dark:text-slate-500 sm:w-44 sm:shrink-0";
const detailValueClassName = "mt-1 text-base font-medium text-gray-800 dark:text-white sm:mt-0";
const detailRowClassName =
  "flex flex-col gap-1 border-b border-white/[0.06] py-3.5 last:border-b-0 sm:flex-row sm:items-center sm:gap-4";

function SettingsSection({
  title,
  children,
  first = false,
}: {
  title: string;
  children: React.ReactNode;
  first?: boolean;
}) {
  return (
    <section className={first ? "" : "mt-8 border-t border-white/[0.08] pt-8"}>
      <h2 className={sectionHeadingClassName}>
        <span className="inline-block h-4 w-1 shrink-0 rounded-full bg-[#14B8A6]" aria-hidden />
        {title}
      </h2>
      {children}
    </section>
  );
}

function displayNameFromEmail(email: string | undefined | null): string {
  if (!email) return "—";
  const raw = email.split("@")[0].split(/[._-]/)[0];
  if (!raw) return "—";
  return raw.charAt(0).toUpperCase() + raw.slice(1);
}

function ProfileDetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div className={detailRowClassName}>
      <span className={detailLabelClassName}>{label}</span>
      <span className={detailValueClassName}>{value}</span>
    </div>
  );
}

export function InsuranceSettingsPage() {
  const { showToast } = useToast();
  const { currentUser, role, apiRole, organizationName, tenantLabel, signOut } = useWorkbench();

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [confirmPasswordError, setConfirmPasswordError] = useState<string | null>(null);
  const [isUpdatingPassword, setIsUpdatingPassword] = useState(false);

  const email = currentUser?.email ?? "—";
  const fullName = useMemo(() => displayNameFromEmail(currentUser?.email), [currentUser?.email]);
  const roleLabel = formatRoleDisplayLabel(apiRole || role);
  const organization = organizationName || tenantLabel || "—";

  function handleEditProfile() {
    showToast("Profile editing will be available soon.", "success");
  }

  function validateConfirmPassword(nextConfirm = confirmPassword, nextNew = newPassword): string | null {
    if (!nextConfirm) return null;
    if (nextConfirm !== nextNew) return "New password and confirm password must match.";
    return null;
  }

  async function handleUpdatePassword(event: React.FormEvent) {
    event.preventDefault();
    setConfirmPasswordError(null);

    if (!currentPassword.trim()) {
      showToast("Please enter your current password.", "error");
      return;
    }
    if (!newPassword.trim()) {
      showToast("Please enter a new password.", "error");
      return;
    }
    if (newPassword.length < 6) {
      showToast("New password must be at least 6 characters.", "error");
      return;
    }

    const mismatchError = validateConfirmPassword();
    if (mismatchError) {
      setConfirmPasswordError(mismatchError);
      return;
    }

    setIsUpdatingPassword(true);
    try {
      await apiClient.changePassword({
        current_password: currentPassword,
        new_password: newPassword,
      });
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      showToast("Password updated successfully.", "success");
    } catch (error) {
      const message =
        error instanceof ApiRequestError
          ? error.message
          : error instanceof Error
            ? error.message
            : "Failed to update password.";
      showToast(message, "error");
    } finally {
      setIsUpdatingPassword(false);
    }
  }

  async function handleLogout() {
    await signOut();
  }

  return (
    <div className="relative pb-10">
      <div className="pointer-events-none absolute inset-x-0 top-0 h-80 overflow-hidden" aria-hidden>
        <div className="absolute -right-16 top-0 h-64 w-64 rounded-full bg-[#8B5CF6]/15 blur-3xl" />
        <div className="absolute left-1/4 top-16 h-48 w-48 rounded-full bg-[#14B8A6]/10 blur-3xl" />
      </div>

      <div className="relative flex justify-center px-1">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
          className="gyantra-glass-card w-full max-w-[820px] rounded-[20px] border border-white/[0.08] p-6 shadow-[0_8px_40px_rgba(0,0,0,0.45),0_0_32px_rgba(20,184,166,0.06)] md:p-8"
        >
          <header className="mb-8 border-b border-white/[0.08] pb-6">
            <h1 className="text-3xl font-extrabold tracking-tight text-black dark:text-white md:text-4xl">Settings</h1>
            <p className="mt-2 max-w-2xl text-sm leading-relaxed text-gray-700 dark:text-slate-400 md:text-base">
              Manage your profile, security preferences, and account session.
            </p>
          </header>

          <SettingsSection title="Profile Information" first>
            <div className="rounded-xl border border-white/[0.06] bg-slate-950/20 px-4 py-1 sm:px-5">
              <ProfileDetailRow label="Full Name" value={fullName} />
              <ProfileDetailRow label="Email" value={email} />
              <ProfileDetailRow label="Role" value={roleLabel} />
              <ProfileDetailRow label="Phone Number" value="—" />
              <ProfileDetailRow label="Organization / Tenant" value={organization} />
            </div>
            <div className="mt-5">
              <button
                type="button"
                onClick={handleEditProfile}
                className="inline-flex items-center rounded-xl border border-white/10 bg-slate-950/40 px-4 py-2.5 text-sm font-medium text-slate-200 transition hover:border-[#14B8A6]/40 hover:bg-[#14B8A6]/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#14B8A6]/40"
              >
                Edit Profile
              </button>
            </div>
          </SettingsSection>

          <SettingsSection title="Change Password">
            <form className="space-y-5" onSubmit={handleUpdatePassword}>
              <label className="block" htmlFor="settings-current-password">
                <span className={labelClassName}>Current Password</span>
                <input
                  id="settings-current-password"
                  name="current_password"
                  type="password"
                  autoComplete="current-password"
                  value={currentPassword}
                  onChange={(event) => setCurrentPassword(event.target.value)}
                  className={fieldClassName}
                  required
                />
              </label>

              <label className="block" htmlFor="settings-new-password">
                <span className={labelClassName}>New Password</span>
                <input
                  id="settings-new-password"
                  name="new_password"
                  type="password"
                  autoComplete="new-password"
                  value={newPassword}
                  onChange={(event) => {
                    setNewPassword(event.target.value);
                    setConfirmPasswordError(validateConfirmPassword(confirmPassword, event.target.value));
                  }}
                  className={fieldClassName}
                  required
                />
              </label>

              <label className="block" htmlFor="settings-confirm-password">
                <span className={labelClassName}>Confirm Password</span>
                <input
                  id="settings-confirm-password"
                  name="confirm_password"
                  type="password"
                  autoComplete="new-password"
                  value={confirmPassword}
                  onChange={(event) => {
                    setConfirmPassword(event.target.value);
                    setConfirmPasswordError(validateConfirmPassword(event.target.value, newPassword));
                  }}
                  onBlur={() => setConfirmPasswordError(validateConfirmPassword())}
                  className={`${fieldClassName}${confirmPasswordError ? " border-red-500/70 focus-visible:ring-red-500/30" : ""}`}
                  required
                />
                {confirmPasswordError ? (
                  <p className="mt-2 text-sm text-red-400">{confirmPasswordError}</p>
                ) : null}
              </label>

              <div>
                <button className="btn" type="submit" disabled={isUpdatingPassword}>
                  {isUpdatingPassword ? "Updating..." : "Update Password"}
                </button>
              </div>
            </form>
          </SettingsSection>

          <SettingsSection title="Logout">
            <p className="mb-5 text-sm leading-relaxed text-slate-400">
              Sign out of your account on this device. You will need to sign in again to access the
              Insurance module.
            </p>
            <button
              type="button"
              onClick={handleLogout}
              className="inline-flex items-center rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-2.5 text-sm font-semibold text-red-300 transition hover:border-red-400/40 hover:bg-red-500/15 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-500/40"
            >
              Log Out
            </button>
          </SettingsSection>
        </motion.div>
      </div>
    </div>
  );
}

export default InsuranceSettingsPage;
