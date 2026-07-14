import { Sparkles } from "./icons";
import { HeroBanner, HeroBadge } from "../design-system/hero-banner";

type InsuranceHeroProps = {
  userName?: string;
};

export function InsuranceHero({ userName }: InsuranceHeroProps) {
  return (
    <HeroBanner
      userName={userName}
      badge={
        <HeroBadge
          icon={<Sparkles className="h-3.5 w-3.5 text-[#8B5CF6]" />}
          label="AI-Powered Dashboard"
        />
      }
      subtitle="Monitor renewals, expiries and customer follow-ups in one place."
    />
  );
}
