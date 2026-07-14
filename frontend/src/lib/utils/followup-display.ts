/** Resolve display name for a lead/follow-up record from API or mock payloads. */
export function getFollowupCustomerName(item: {
  customerName?: string | null;
  contact_name?: string | null;
  customer_full_name?: string | null;
  customerFullName?: string | null;
  name?: string | null;
} | null | undefined): string {
  if (!item) return "Unnamed Customer";
  return (
    item.customerName ||
    item.contact_name ||
    item.customer_full_name ||
    item.customerFullName ||
    item.name ||
    "Unnamed Customer"
  );
}
