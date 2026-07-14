import { Link } from "react-router-dom";

import { Button } from "../ui/button";

type QuickAction = {
  label: string;
  to: string;
  variant?: "default" | "outline";
};

type QuickActionsProps = {
  actions: QuickAction[];
};

export function QuickActions({ actions }: QuickActionsProps) {
  return (
    <div className="flex flex-wrap gap-3">
      {actions.map((action) => (
        <Button key={action.to} asChild variant={action.variant ?? "default"}>
          <Link to={action.to}>{action.label}</Link>
        </Button>
      ))}
    </div>
  );
}
