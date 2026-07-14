import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useGetPolicy, useUpdatePolicy } from "../../lib/api/hooks";
import { useWorkbench } from "../../app/providers/workbench-provider";
import { Loading } from "../../components/ui/Loading";
import { ErrorState } from "../../components/ui/ErrorState";
import { InsuranceDatePicker } from "../../components/ui/insurance-date-picker";
import { formatDate } from "../../lib/utils/formatDate";
import { isoDateFromDisplay, validateDisplayDate } from "../../lib/utils/date-display";

export function EditPolicyPage() {
  const { policyId } = useParams();
  const id = policyId ? Number(policyId) : undefined;
  const { organizationId } = useWorkbench();
  const navigate = useNavigate();
  const q = useGetPolicy(id);
  const updater = useUpdatePolicy(organizationId);
  const [form, setForm] = useState<any>(null);
  const [expiryDateError, setExpiryDateError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (q.data) {
      setForm({
        ...q.data,
        expiry_date: formatDate(q.data.expiry_date),
      });
    }
  }, [q.data]);

  if (q.isLoading) return <Loading label="Loading policy..." />;
  if (q.isError) return <ErrorState message="Failed to load policy" />;
  if (!form) return null;

  function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setExpiryDateError(null);

    const expiryValidationError = validateDisplayDate(form.expiry_date);
    if (expiryValidationError) {
      setExpiryDateError(expiryValidationError);
      return;
    }

    const expiryIso = isoDateFromDisplay(form.expiry_date);
    if (!expiryIso) {
      setExpiryDateError("Please enter a valid expiry date.");
      return;
    }

    updater.mutate(
      {
        policyId: form.id,
        updates: {
          ...form,
          expiry_date: new Date(`${expiryIso}T12:00:00.000Z`).toISOString(),
        },
      },
      {
        onSuccess: () => navigate(`/app/insurance/policies/${form.id}`),
        onError: () => setError("Failed to update policy."),
      }
    );
  }

  return (
    <div>
      <h2 className="text-xl font-semibold">Edit Policy</h2>
      {error ? <p className="mt-2 text-sm text-red-600 dark:text-red-400">{error}</p> : null}
      <form className="mt-4 space-y-3" onSubmit={submit}>
        <input
          value={form.policyholder_name}
          onChange={(e) => setForm({ ...form, policyholder_name: e.target.value })}
          className="input"
        />
        <input
          value={form.policy_number}
          onChange={(e) => setForm({ ...form, policy_number: e.target.value })}
          className="input"
        />
        <InsuranceDatePicker
          label="Expiry Date"
          value={form.expiry_date ?? ""}
          onChange={(expiry_date) => {
            setExpiryDateError(null);
            setForm({ ...form, expiry_date });
          }}
          onBlur={() => setExpiryDateError(validateDisplayDate(form.expiry_date))}
          error={expiryDateError}
        />
        <div>
          <button className="btn" type="submit" disabled={updater.isPending}>
            Save
          </button>
        </div>
      </form>
    </div>
  );
}

export default EditPolicyPage;
