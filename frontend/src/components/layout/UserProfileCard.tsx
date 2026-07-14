type UserProfileCardProps = {
  displayName: string;
  email: string;
  initials: string;
  size?: "md" | "sm";
  collapsed?: boolean;
};

function ProfileAvatar({ initials, size = "md" }: { initials: string; size?: "md" | "sm" }) {
  const dim = size === "sm" ? "w-11 h-11" : "w-10 h-10";
  return (
    <div className="profile-avatar-wrap">
      <div className={`${dim} rounded-full flex items-center justify-center font-bold gyantra-profile-avatar`}>
        {initials}
      </div>
      <span className="profile-online-dot profile-online-dot-gyantra" aria-label="Online" title="Active" />
    </div>
  );
}

export function UserProfileCard({
  displayName,
  email,
  initials,
  size = "md",
  collapsed = false,
}: UserProfileCardProps) {
  if (collapsed) {
    return <ProfileAvatar initials={initials} size="sm" />;
  }

  return (
    <div className="sidebar-footer-card glass rounded-2xl p-3 w-full min-w-0 overflow-hidden gyantra-profile-card">
      <div className="flex items-center gap-3 w-full min-w-0">
        <ProfileAvatar initials={initials} size={size} />
        <div className="flex-1 min-w-0">
          <div className="text-sm font-semibold truncate text-slate-900 dark:text-white">{displayName}</div>
          <div className="text-xs truncate text-gray-700 dark:text-slate-400">{email}</div>
        </div>
      </div>
    </div>
  );
}
