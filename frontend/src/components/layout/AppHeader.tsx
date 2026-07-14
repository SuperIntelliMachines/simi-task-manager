import { useEffect, useRef, useState } from "react";
import { MonitorIcon, MoonIcon, SunIcon } from "../../lib/workspace/nav-icons";
import type { WorkspaceConfig } from "../../lib/workspace/types";
import { NotificationBell } from "../notifications/NotificationBell";

type ThemeMode = "light" | "dark" | "system";

type AppHeaderProps = {
  workspace: WorkspaceConfig;
  orgInitials: string;
  onAskAi: () => void;
  onRefresh: () => void;
  isRefreshing: boolean;
};

export function AppHeader({
  workspace,
  orgInitials,
  onAskAi,
  onRefresh,
  isRefreshing,
}: AppHeaderProps) {
  const themeMenuRef = useRef<HTMLDivElement | null>(null);
  const [themeMenuOpen, setThemeMenuOpen] = useState(false);
  const [themeMode, setThemeMode] = useState<ThemeMode>(() => {
    const saved = window.localStorage.getItem("theme");
    if (saved === "light" || saved === "dark" || saved === "system") return saved;
    return "dark";
  });

  useEffect(() => {
    const resolveDark = () => (themeMode === "system" ? true : themeMode === "dark");
    document.documentElement.classList.toggle("dark", resolveDark());
    window.localStorage.setItem("theme", themeMode);
  }, [themeMode]);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (!themeMenuRef.current) return;
      if (!themeMenuRef.current.contains(event.target as Node)) {
        setThemeMenuOpen(false);
      }
    }
    if (themeMenuOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [themeMenuOpen]);

  const themeIcon =
    themeMode === "light" ? (
      <SunIcon className="h-4 w-4" />
    ) : themeMode === "dark" ? (
      <MoonIcon className="h-4 w-4" />
    ) : (
      <MonitorIcon className="h-4 w-4" />
    );

  return (
    <header className="sticky top-0 z-50 header-glass h-14 gyantra-header">
      <div className="mx-auto flex h-14 max-w-7xl items-center gap-3 px-4 lg:gap-4 lg:px-6">
        <div className="flex shrink-0 items-center gap-2.5">
          <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-[11px] font-bold bg-[#14B8A6] text-[#050816]">
            {orgInitials}
          </div>
          <div className="hidden min-w-0 leading-tight md:block">
            <p className="truncate text-sm font-semibold text-slate-900 dark:text-white">
              {workspace.headerTitle}
            </p>
            <p className="truncate text-[10px] text-gray-700 dark:text-slate-400">
              {workspace.headerSubtitle}
            </p>
          </div>
        </div>

        <div className="flex-1" aria-hidden="true" />

        <div className="flex shrink-0 items-center gap-2">
          <button
            type="button"
            onClick={onAskAi}
            className="gyantra-header-action gyantra-ask-ai inline-flex h-9 items-center gap-1.5 rounded-full px-3 text-[13px] font-medium"
          >
            <span aria-hidden="true">✦</span>
            <span className="hidden sm:inline">Ask AI</span>
          </button>
          <NotificationBell />
          <div className="relative" ref={themeMenuRef}>
            <button
              type="button"
              aria-label="Theme selector"
              onClick={() => setThemeMenuOpen((prev) => !prev)}
              className="gyantra-header-icon-btn"
              title="Theme"
            >
              <span aria-hidden="true">{themeIcon}</span>
            </button>

            {themeMenuOpen ? (
              <div className="absolute right-0 z-50 mt-2 w-44 rounded-xl border border-white/10 bg-black/80 p-2 shadow-xl backdrop-blur-xl">
                {(
                  [
                    { id: "light" as const, label: "Light", icon: <SunIcon className="h-4 w-4" /> },
                    { id: "dark" as const, label: "Dark", icon: <MoonIcon className="h-4 w-4" /> },
                    { id: "system" as const, label: "System", icon: <MonitorIcon className="h-4 w-4" /> },
                  ] as const
                ).map((option) => {
                  const selected = themeMode === option.id;
                  return (
                    <button
                      key={option.id}
                      type="button"
                      onClick={() => {
                        setThemeMode(option.id);
                        setThemeMenuOpen(false);
                      }}
                      className={`flex w-full cursor-pointer items-center justify-between rounded-lg px-3 py-2 text-sm text-slate-100 transition-colors hover:bg-white/10 ${
                        selected ? "border border-purple-400/30 bg-purple-500/20" : "border border-transparent"
                      }`}
                    >
                      <span className="flex items-center gap-2">
                        {option.icon}
                        <span>{option.label}</span>
                      </span>
                      <span className={`text-xs ${selected ? "text-purple-200" : "text-slate-500"}`}>
                        {selected ? "✓" : ""}
                      </span>
                    </button>
                  );
                })}
              </div>
            ) : null}
          </div>
          <button
            type="button"
            aria-label="Refresh"
            onClick={onRefresh}
            disabled={isRefreshing}
            className={`gyantra-header-icon-btn ${isRefreshing ? "opacity-70 cursor-not-allowed" : ""}`}
          >
            <span className={isRefreshing ? "inline-block animate-spin" : "inline-block"} aria-hidden="true">
              ⟳
            </span>
          </button>
        </div>
      </div>
    </header>
  );
}
