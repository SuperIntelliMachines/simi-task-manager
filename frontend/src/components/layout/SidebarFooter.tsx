import { NavLink } from "react-router-dom";
import { UserProfileCard } from "./UserProfileCard";

type SidebarFooterProps = {
  collapsed: boolean;
  settingsPath: string;
  displayName: string;
  email: string;
  initials: string;
  onLogout: () => void;
};

export function SidebarFooter({
  collapsed,
  settingsPath,
  displayName,
  email,
  initials,
  onLogout,
}: SidebarFooterProps) {
  return (
    <div className="mt-auto px-3 py-3 border-t sticky bottom-0 bg-transparent border-white/6 sidebar-user-light">
      <div className="w-full min-w-0">
        {!collapsed ? (
          <>
            <UserProfileCard displayName={displayName} email={email} initials={initials} />

            <div className="mt-3 flex gap-3 items-center w-full min-w-0">
              <NavLink to={settingsPath} className={({ isActive: _isActive }) => `flex-1 min-w-0`}>
                <button
                  type="button"
                  className="w-full h-10 flex items-center justify-center glassy-btn glassy-btn-light rounded-lg px-3 text-sm overflow-hidden"
                >
                  ⚙ Settings
                </button>
              </NavLink>

              <button
                type="button"
                onClick={onLogout}
                aria-label="Log out"
                className="w-12 h-10 flex items-center justify-center glassy-btn glassy-btn-light rounded-lg"
              >
                ↪
              </button>
            </div>
          </>
        ) : (
          <div className="w-full flex flex-col items-center justify-center gap-3 py-4">
            <UserProfileCard displayName={displayName} email={email} initials={initials} collapsed />
            <NavLink to={settingsPath} title="Settings">
              <button
                type="button"
                className="w-11 h-11 flex items-center justify-center glassy-btn glassy-btn-light rounded-lg"
              >
                ⚙
              </button>
            </NavLink>
            <button
              type="button"
              onClick={onLogout}
              aria-label="Log out"
              className="w-11 h-11 flex items-center justify-center glassy-btn glassy-btn-light rounded-lg"
            >
              ↪
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
