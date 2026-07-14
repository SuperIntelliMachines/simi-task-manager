import { motion } from "framer-motion";
import type { PropsWithChildren, ReactNode } from "react";

import { simiCardEnter } from "../../lib/theme/motion-presets";
import { SIMI_GLASS_CARD_CLASS } from "../../lib/theme/simi-tokens";

type GlassCardProps = PropsWithChildren<{
  className?: string;
  hover?: boolean;
  delay?: number;
  header?: ReactNode;
}>;

export function GlassCard({ children, className = "", hover = false, delay = 0, header }: GlassCardProps) {
  return (
    <motion.div
      {...simiCardEnter(delay)}
      whileHover={hover ? { y: -6, transition: { duration: 0.2 } } : undefined}
      className={`${SIMI_GLASS_CARD_CLASS} ${hover ? "cursor-pointer" : ""} ${className}`}
    >
      {header}
      {children}
    </motion.div>
  );
}
