import {
  useEffect,
  useId,
  useRef,
  useState,
  type KeyboardEvent,
  type ReactNode,
} from "react";
import { createPortal } from "react-dom";

export type ActionMenuItem = {
  id: string;
  label: string;
  icon?: ReactNode;
  onSelect: () => void;
  tone?: "default" | "danger" | "warning";
  disabled?: boolean;
};

type ActionMenuProps = {
  items: ActionMenuItem[];
  label?: string;
  align?: "left" | "right";
};

function MoreVerticalIcon({ className = "h-5 w-5" }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="currentColor"
      aria-hidden="true"
    >
      <circle cx="12" cy="5" r="1.6" />
      <circle cx="12" cy="12" r="1.6" />
      <circle cx="12" cy="19" r="1.6" />
    </svg>
  );
}

function toneClass(tone: ActionMenuItem["tone"]): string {
  if (tone === "danger") return "text-rose-600 dark:text-rose-300";
  if (tone === "warning") return "text-amber-700 dark:text-amber-300";
  return "text-slate-700 dark:text-slate-200";
}

/**
 * Reusable overflow (⋮) action menu for table rows and cards.
 * Uses the same portal + outside-click pattern as Combobox.
 */
export function ActionMenu({ items, label = "More actions", align = "right" }: ActionMenuProps) {
  const reactId = useId();
  const menuId = `action-menu-${reactId.replace(/:/g, "")}`;
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);
  const triggerRef = useRef<HTMLButtonElement | null>(null);
  const menuRef = useRef<HTMLDivElement | null>(null);
  const [coords, setCoords] = useState<{ top: number; left: number; minWidth: number } | null>(null);

  const enabledItems = items.filter((item) => !item.disabled);

  useEffect(() => {
    if (!open) return;

    function updatePosition() {
      if (!triggerRef.current) return;
      const rect = triggerRef.current.getBoundingClientRect();
      const menuWidth = Math.max(rect.width, 200);
      const left =
        align === "right"
          ? Math.max(8, rect.right + window.scrollX - menuWidth)
          : rect.left + window.scrollX;
      setCoords({
        top: rect.bottom + window.scrollY + 6,
        left,
        minWidth: menuWidth,
      });
    }

    updatePosition();
    window.addEventListener("scroll", updatePosition, true);
    window.addEventListener("resize", updatePosition);
    return () => {
      window.removeEventListener("scroll", updatePosition, true);
      window.removeEventListener("resize", updatePosition);
    };
  }, [open, align]);

  useEffect(() => {
    if (!open) return;

    function onPointerDown(event: MouseEvent) {
      const target = event.target as Node;
      if (triggerRef.current?.contains(target) || menuRef.current?.contains(target)) return;
      setOpen(false);
    }

    function onKeyDown(event: globalThis.KeyboardEvent) {
      if (event.key === "Escape") {
        event.preventDefault();
        setOpen(false);
        triggerRef.current?.focus();
      }
    }

    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  useEffect(() => {
    if (open) {
      setActiveIndex(0);
      // Defer so portal content is mounted before focusing.
      requestAnimationFrame(() => menuRef.current?.focus());
    }
  }, [open]);

  function runItem(item: ActionMenuItem) {
    if (item.disabled) return;
    setOpen(false);
    item.onSelect();
    triggerRef.current?.focus();
  }

  function onTriggerKeyDown(event: KeyboardEvent<HTMLButtonElement>) {
    if (event.key === "ArrowDown" || event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      setOpen(true);
    }
  }

  function onMenuKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActiveIndex((index) => Math.min(index + 1, enabledItems.length - 1));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActiveIndex((index) => Math.max(index - 1, 0));
    } else if (event.key === "Home") {
      event.preventDefault();
      setActiveIndex(0);
    } else if (event.key === "End") {
      event.preventDefault();
      setActiveIndex(Math.max(enabledItems.length - 1, 0));
    } else if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      const item = enabledItems[activeIndex];
      if (item) runItem(item);
    } else if (event.key === "Escape") {
      event.preventDefault();
      setOpen(false);
      triggerRef.current?.focus();
    } else if (event.key === "Tab") {
      setOpen(false);
    }
  }

  return (
    <div className="relative inline-flex justify-end">
      <button
        ref={triggerRef}
        type="button"
        className="inline-flex h-9 w-9 items-center justify-center rounded-xl border border-transparent text-slate-500 transition-colors hover:border-slate-200/80 hover:bg-slate-100/80 hover:text-slate-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#14B8A6]/40 dark:text-slate-400 dark:hover:border-white/10 dark:hover:bg-white/5 dark:hover:text-white"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={open ? menuId : undefined}
        aria-label={label}
        onClick={() => setOpen((current) => !current)}
        onKeyDown={onTriggerKeyDown}
      >
        <MoreVerticalIcon />
      </button>

      {open && coords
        ? createPortal(
            <div
              ref={menuRef}
              id={menuId}
              role="menu"
              tabIndex={-1}
              aria-label={label}
              className="action-menu-panel"
              style={{
                position: "absolute",
                top: coords.top,
                left: coords.left,
                minWidth: coords.minWidth,
                zIndex: 9999,
              }}
              onKeyDown={onMenuKeyDown}
            >
              {items.map((item) => {
                const enabledIndex = enabledItems.findIndex((entry) => entry.id === item.id);
                const isActive = !item.disabled && enabledIndex === activeIndex;
                return (
                  <button
                    key={item.id}
                    type="button"
                    role="menuitem"
                    disabled={item.disabled}
                    className={`action-menu-item ${toneClass(item.tone)}${
                      isActive ? " action-menu-item-active" : ""
                    }`}
                    onMouseEnter={() => {
                      if (!item.disabled && enabledIndex >= 0) setActiveIndex(enabledIndex);
                    }}
                    onClick={() => runItem(item)}
                  >
                    {item.icon ? <span className="action-menu-icon">{item.icon}</span> : null}
                    <span>{item.label}</span>
                  </button>
                );
              })}
            </div>,
            document.body
          )
        : null}
    </div>
  );
}

export function PencilIcon({ className = "h-4 w-4" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M12 20h9" />
      <path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z" />
    </svg>
  );
}

export function KeyIcon({ className = "h-4 w-4" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="8" cy="15" r="4" />
      <path d="m11.5 11.5 8-8" />
      <path d="M17 5.5 19.5 8" />
      <path d="M15 7.5 17.5 10" />
    </svg>
  );
}

export function PlayIcon({ className = "h-4 w-4" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M7 4.5v15l13-7.5Z" />
    </svg>
  );
}

export function PauseIcon({ className = "h-4 w-4" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x="6" y="5" width="4" height="14" rx="1" />
      <rect x="14" y="5" width="4" height="14" rx="1" />
    </svg>
  );
}

export function EyeIcon({ className = "h-4 w-4" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7Z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  );
}

export function TrashIcon({ className = "h-4 w-4" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M3 6h18" />
      <path d="M8 6V4h8v2" />
      <path d="M19 6l-1 14H6L5 6" />
      <path d="M10 11v6" />
      <path d="M14 11v6" />
    </svg>
  );
}
