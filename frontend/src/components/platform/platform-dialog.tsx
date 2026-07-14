import type { PropsWithChildren, ReactNode } from "react";

type PlatformDialogProps = PropsWithChildren<{
  open: boolean;
  title: string;
  description?: string;
  onClose: () => void;
  footer?: ReactNode;
  size?: "md" | "lg" | "xl";
}>;

const SIZE_CLASS = {
  md: "max-w-lg",
  lg: "max-w-2xl",
  xl: "max-w-4xl",
};

export function PlatformDialog({
  open,
  title,
  description,
  onClose,
  footer,
  size = "md",
  children,
}: PlatformDialogProps) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <button
        type="button"
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        aria-label="Close dialog"
        onClick={onClose}
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="platform-dialog-title"
        className={`relative w-full ${SIZE_CLASS[size]} rounded-2xl border border-slate-200 bg-white/90 p-6 shadow-xl backdrop-blur-xl dark:border-slate-700 dark:bg-slate-900/90 glass-card`}
      >
        <h2 id="platform-dialog-title" className="text-lg font-semibold text-slate-900 dark:text-white">
          {title}
        </h2>
        {description ? <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">{description}</p> : null}
        <div className="mt-5">{children}</div>
        {footer ? <div className="mt-6 flex justify-end gap-3">{footer}</div> : null}
      </div>
    </div>
  );
}
