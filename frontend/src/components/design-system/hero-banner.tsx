import { motion } from "framer-motion";
import type { ReactNode } from "react";

import { simiPageEnter } from "../../lib/theme/motion-presets";
import { SIMI_HERO_CLASS } from "../../lib/theme/simi-tokens";

type HeroBannerProps = {
  userName?: string;
  badge?: ReactNode;
  title?: ReactNode;
  subtitle: string;
};

function formatDisplayName(userName?: string): string {
  const greeting = userName ? userName.split("@")[0].split(/[._-]/)[0] : "there";
  return greeting.charAt(0).toUpperCase() + greeting.slice(1);
}

export function HeroBanner({ userName, badge, title, subtitle }: HeroBannerProps) {
  const displayName = formatDisplayName(userName);

  return (
    <motion.section {...simiPageEnter} className={SIMI_HERO_CLASS}>
      <div className="pointer-events-none absolute -right-16 -top-16 h-64 w-64 rounded-full bg-[#8B5CF6]/30 blur-3xl opacity-40" />
      <div className="pointer-events-none absolute -bottom-8 left-1/3 h-48 w-48 rounded-full bg-[#14B8A6]/25 blur-3xl opacity-40" />

      <div className="relative z-10">
        {badge}
        <h1 className="text-2xl font-bold tracking-tight text-gray-900 dark:text-white md:text-3xl lg:text-4xl">
          {title ?? (
            <>
              Welcome back, <span className="text-[#14B8A6]">{displayName}</span>!
            </>
          )}
        </h1>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-gray-700 dark:text-slate-400 md:text-base">
          {subtitle}
        </p>
      </div>
    </motion.section>
  );
}

export function HeroBadge({ icon, label }: { icon: ReactNode; label: string }) {
  return (
    <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-violet-300/80 bg-violet-100/80 px-3 py-1.5 dark:border-[#8B5CF6]/30 dark:bg-[#8B5CF6]/10">
      {icon}
      <span className="text-xs font-semibold text-violet-700 dark:text-[#C4B5FD]">{label}</span>
    </div>
  );
}
