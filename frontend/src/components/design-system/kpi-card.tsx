import { motion, useSpring, useTransform } from "framer-motion";
import { useEffect, type ReactNode } from "react";

import { simiKpiEnter } from "../../lib/theme/motion-presets";

export type KpiAccent = "teal" | "blue" | "orange" | "amber" | "purple" | "red" | "pink" | "cyan";

const ACCENT: Record<KpiAccent, { iconClass: string }> = {
  teal: { iconClass: "bg-teal-100 text-teal-600 dark:bg-teal-500/20 dark:text-teal-400" },
  blue: { iconClass: "bg-blue-100 text-blue-600 dark:bg-blue-500/20 dark:text-blue-400" },
  orange: { iconClass: "bg-orange-100 text-orange-600 dark:bg-orange-500/20 dark:text-orange-400" },
  amber: { iconClass: "bg-amber-100 text-amber-600 dark:bg-amber-500/20 dark:text-amber-400" },
  purple: { iconClass: "bg-indigo-100 text-indigo-600 dark:bg-indigo-500/20 dark:text-indigo-400" },
  red: { iconClass: "bg-red-100 text-red-600 dark:bg-red-500/20 dark:text-red-400" },
  pink: { iconClass: "bg-rose-100 text-rose-600 dark:bg-rose-500/20 dark:text-rose-400" },
  cyan: { iconClass: "bg-cyan-100 text-cyan-600 dark:bg-cyan-500/20 dark:text-cyan-400" },
};

type KpiCardProps = {
  title: string;
  count: number;
  icon: ReactNode;
  accent: KpiAccent;
  onClick?: () => void;
  delay?: number;
};

function AnimatedCount({ value, delay = 0 }: { value: number; delay?: number }) {
  const spring = useSpring(0, { stiffness: 90, damping: 18 });
  const rounded = useTransform(spring, (latest) => Math.round(latest));

  useEffect(() => {
    const timeout = window.setTimeout(() => spring.set(value), delay * 1000 + 150);
    return () => window.clearTimeout(timeout);
  }, [value, spring, delay]);

  return (
    <motion.span
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay: delay + 0.1, ease: [0.22, 1, 0.36, 1] }}
    >
      {rounded}
    </motion.span>
  );
}

export function KpiCard({ title, count, icon, accent, onClick, delay = 0 }: KpiCardProps) {
  const colors = ACCENT[accent];

  return (
    <motion.div {...simiKpiEnter(delay)} className="w-full">
      <button
        type="button"
        onClick={onClick}
        className="group relative w-full overflow-hidden rounded-2xl p-7 text-left transform-gpu bg-white/55 dark:bg-slate-950/70 backdrop-blur-2xl dark:backdrop-blur-xl border border-gray-200/80 dark:border-white/10 shadow-[0_6px_20px_rgba(0,0,0,0.06)] dark:shadow-[0_8px_32px_rgba(0,0,0,0.25)] transition-all duration-300 ease-out hover:-translate-y-2 hover:scale-[1.02] active:scale-[0.98] hover:bg-white/65 dark:hover:bg-slate-950/70 hover:border-cyan-400/20 hover:shadow-[0_10px_30px_rgba(0,0,0,0.08)] dark:hover:shadow-[0_0_30px_rgba(34,211,238,0.08)] before:absolute before:inset-0 before:rounded-[inherit] before:bg-white/20 dark:before:bg-white/5 before:opacity-40 before:content-['']"
      >
        <div
          className={`relative z-10 flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-2xl p-4 transition-transform duration-300 group-hover:scale-110 group-hover:rotate-3 dark:backdrop-blur-md dark:border dark:border-white/5 ${colors.iconClass}`}
        >
          {icon}
        </div>
        <p className="relative z-10 mt-4 text-sm font-medium text-gray-700 dark:text-slate-400">{title}</p>
        <p className="relative z-10 mt-1 text-3xl font-bold tracking-tight text-black transition-all duration-300 group-hover:translate-x-1 dark:text-foreground">
          <AnimatedCount value={count} delay={delay} />
        </p>
      </button>
    </motion.div>
  );
}
