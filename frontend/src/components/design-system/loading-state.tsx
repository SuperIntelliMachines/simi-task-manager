import { Loading } from "../ui/Loading";

type LoadingStateProps = {
  label?: string;
};

export function LoadingState({ label = "Loading..." }: LoadingStateProps) {
  return (
    <div className="gyantra-glass-card p-6">
      <Loading label={label} />
    </div>
  );
}
