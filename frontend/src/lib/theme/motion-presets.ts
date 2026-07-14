/** Shared Framer Motion presets for the SIMI design system. */
export const SIMI_EASE = [0.22, 1, 0.36, 1] as const;

export const simiPageEnter = {
  initial: { opacity: 0, y: 24 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.55, ease: SIMI_EASE },
};

export const simiCardEnter = (delay = 0) => ({
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.45, delay, ease: SIMI_EASE },
});

export const simiKpiEnter = (delay = 0) => ({
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.4, delay, ease: SIMI_EASE },
});
