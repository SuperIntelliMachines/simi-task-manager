import { useNavigate } from "react-router-dom";
import { InsuranceStatCard } from "./insurance-stat-card";
import { followupListPath } from "../../lib/insurance/followup-list-navigation";
import { Bell, Calendar, Clock, Users } from "./icons";

export type LeadFollowupOverviewCounts = {
  total_leads: number;
  upcoming_followups: number;
  due_in_48_hours: number;
  missed_followups: number;
};

type LeadFollowupOverviewSectionProps = {
  counts: LeadFollowupOverviewCounts;
};

export function LeadFollowupOverviewSection({ counts }: LeadFollowupOverviewSectionProps) {
  const navigate = useNavigate();

  return (
    <section className="space-y-4">
      <h3 className="text-lg font-bold text-black dark:text-foreground">Lead Follow-up Overview</h3>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <InsuranceStatCard
          title="Total Leads"
          count={counts.total_leads}
          accent="cyan"
          icon={<Users className="h-5 w-5" />}
          delay={0.05}
          onClick={() => navigate(followupListPath())}
        />
        <InsuranceStatCard
          title="Upcoming Follow-ups"
          count={counts.upcoming_followups}
          accent="purple"
          icon={<Calendar className="h-5 w-5" />}
          delay={0.1}
          onClick={() => navigate(followupListPath("upcoming"))}
        />
        <InsuranceStatCard
          title="Due in Next 48 Hours"
          count={counts.due_in_48_hours}
          accent="orange"
          icon={<Clock className="h-5 w-5" />}
          delay={0.15}
          onClick={() => navigate(followupListPath("48h"))}
        />
        <InsuranceStatCard
          title="Missed Follow-ups"
          count={counts.missed_followups}
          accent="pink"
          icon={<Bell className="h-5 w-5" />}
          delay={0.2}
          onClick={() => navigate(followupListPath("missed"))}
        />
      </div>
    </section>
  );
}
