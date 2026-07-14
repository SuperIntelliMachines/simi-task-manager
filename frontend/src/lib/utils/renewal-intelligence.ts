import { DEFAULT_GRACE_PERIOD_DAYS, daysUntilUTC } from "./policy-classifier";
import { RENEWAL_FREQUENCY_DEFAULT } from "../insurance/renewal-frequency";

export const RENEWAL_STATUS_DUE_SOON = "due_soon";
export const RENEWAL_STATUS_FUTURE = "future_renewal";
export const RENEWAL_STATUS_GRACE_PERIOD = "grace_period";
export const RENEWAL_STATUS_LAPSED = "lapsed";

export type RenewalIntelligenceStatus =
  | typeof RENEWAL_STATUS_DUE_SOON
  | typeof RENEWAL_STATUS_FUTURE
  | typeof RENEWAL_STATUS_GRACE_PERIOD
  | typeof RENEWAL_STATUS_LAPSED;

export const RENEWAL_STATUS_LABELS: Record<RenewalIntelligenceStatus, string> = {
  [RENEWAL_STATUS_FUTURE]: "Future Renewal",
  [RENEWAL_STATUS_DUE_SOON]: "Due Soon",
  [RENEWAL_STATUS_GRACE_PERIOD]: "Grace Period",
  [RENEWAL_STATUS_LAPSED]: "Lapsed",
};

export const RENEWAL_STATUS_COLORS: Record<RenewalIntelligenceStatus, string> = {
  [RENEWAL_STATUS_FUTURE]: "#3B82F6",
  [RENEWAL_STATUS_DUE_SOON]: "#F97316",
  [RENEWAL_STATUS_GRACE_PERIOD]: "#EF4444",
  [RENEWAL_STATUS_LAPSED]: "#111827",
};

export const RENEWAL_STATUS_LEGEND: Array<{
  status: RenewalIntelligenceStatus;
  description: string;
}> = [
  {
    status: RENEWAL_STATUS_FUTURE,
    description: "More than 10 days until expiry — upcoming renewal pipeline.",
  },
  {
    status: RENEWAL_STATUS_DUE_SOON,
    description: "Expiring within the next 10 days — prepare renewal outreach.",
  },
  {
    status: RENEWAL_STATUS_GRACE_PERIOD,
    description: "Renewal date passed — still within grace period.",
  },
  {
    status: RENEWAL_STATUS_LAPSED,
    description: "Grace period ended — policy lapsed.",
  },
];

const DAY_MS = 24 * 60 * 60 * 1000;

export type RenewalIntelligencePoint = {
  policy_id: number;
  customer_name: string;
  policy_number: string;
  product_type: string | null;
  renewal_frequency: string | null;
  expiry_date: string;
  premium: number;
  renewal_status: RenewalIntelligenceStatus;
  renewal_status_label: string;
  days_until_due: number | null;
  days_overdue: number | null;
  assigned_agent_user_id: number | string | null;
  assigned_agent_name: string | null;
  reminders_sent_count?: number;
  grace_period_days?: number | null;
};

export type RenewalIntelligenceChart = {
  points: RenewalIntelligencePoint[];
  filters: {
    agents: Array<{ value: string; label: string }>;
    product_types: string[];
  };
};

type PolicyRecord = {
  id: number;
  policy_number: string;
  policyholder_name?: string;
  policy_type?: string | null;
  renewal_frequency?: string | null;
  expiry_date: string;
  premium?: number | string | null;
  status?: string;
  assigned_agent_user_id?: number | string | null;
  grace_period_days?: number | null;
};

const DUE_SOON_MAX_DAYS = 10;
const POST_RENEWAL_WINDOW_DAYS = 90;
const RENEWAL_INTELLIGENCE_MAX_DAYS_UNTIL_EXPIRY = 30;

function isInRenewalIntelligenceChartWindow(days: number | null): boolean {
  if (days == null || Number.isNaN(days)) {
    return false;
  }
  return days >= -POST_RENEWAL_WINDOW_DAYS && days <= RENEWAL_INTELLIGENCE_MAX_DAYS_UNTIL_EXPIRY;
}

function toPremium(value: number | string | null | undefined): number {
  if (value == null || value === "") return 0;
  const parsed = typeof value === "number" ? value : Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function timingFields(days: number | null): Pick<RenewalIntelligencePoint, "days_until_due" | "days_overdue"> {
  if (days == null || Number.isNaN(days)) {
    return { days_until_due: null, days_overdue: null };
  }
  if (days < 0) {
    return { days_until_due: null, days_overdue: Math.abs(days) };
  }
  return { days_until_due: days, days_overdue: null };
}

export function classifyRenewalIntelligenceStatus(policy: PolicyRecord): RenewalIntelligenceStatus {
  const days = daysUntilUTC(policy.expiry_date);
  if (Number.isNaN(days)) {
    return RENEWAL_STATUS_FUTURE;
  }
  if (days > DUE_SOON_MAX_DAYS) {
    return RENEWAL_STATUS_FUTURE;
  }
  if (days >= 0 && days <= DUE_SOON_MAX_DAYS) {
    return RENEWAL_STATUS_DUE_SOON;
  }
  const graceDays = Math.max(Number(policy.grace_period_days ?? DEFAULT_GRACE_PERIOD_DAYS), 0);
  return Math.abs(days) <= graceDays ? RENEWAL_STATUS_GRACE_PERIOD : RENEWAL_STATUS_LAPSED;
}

export function buildRenewalIntelligenceChart(policies: PolicyRecord[]): RenewalIntelligenceChart {
  const agentOptions = new Map<string, string>();
  const productTypes = new Set<string>();
  const points: RenewalIntelligencePoint[] = policies
    .filter((policy) => isInRenewalIntelligenceChartWindow(daysUntilUTC(policy.expiry_date)))
    .map((policy) => {
    const days = daysUntilUTC(policy.expiry_date);
    const renewalStatus = classifyRenewalIntelligenceStatus(policy);
    const timing = timingFields(days);
    const agentKey =
      policy.assigned_agent_user_id != null && policy.assigned_agent_user_id !== ""
        ? String(policy.assigned_agent_user_id)
        : "";
    const agentLabel = agentKey || "Unassigned";

    agentOptions.set(agentKey, agentKey ? agentLabel : "Unassigned");
    if (policy.policy_type) {
      productTypes.add(policy.policy_type);
    }

    return {
      policy_id: policy.id,
      customer_name: policy.policyholder_name ?? policy.policy_number,
      policy_number: policy.policy_number,
      product_type: policy.policy_type ?? null,
      renewal_frequency: policy.renewal_frequency?.trim() || RENEWAL_FREQUENCY_DEFAULT,
      expiry_date: policy.expiry_date,
      premium: toPremium(policy.premium),
      renewal_status: renewalStatus,
      renewal_status_label: RENEWAL_STATUS_LABELS[renewalStatus],
      days_until_due: timing.days_until_due,
      days_overdue: timing.days_overdue,
      assigned_agent_user_id: policy.assigned_agent_user_id ?? null,
      assigned_agent_name: agentKey ? agentLabel : null,
      reminders_sent_count: 0,
      grace_period_days: policy.grace_period_days ?? null,
    };
  });

  return {
    points,
    filters: {
      agents: [...agentOptions.entries()]
        .map(([value, label]) => ({ value, label }))
        .sort((a, b) => a.label.localeCompare(b.label)),
      product_types: [...productTypes].sort((a, b) => a.localeCompare(b)),
    },
  };
}

export function filterRenewalIntelligencePoints(
  points: RenewalIntelligencePoint[],
  productFilter: string
): RenewalIntelligencePoint[] {
  return points.filter((point) => !productFilter || point.product_type === productFilter);
}

export type RenewalIntelligencePolicyStatus = "Active" | "Grace Period" | "Lapsed";

export const RENEWAL_INTELLIGENCE_TABLE_POLICY_TYPES = ["Health", "Life", "Auto"] as const;

export const RENEWAL_INTELLIGENCE_TABLE_POLICY_STATUSES: RenewalIntelligencePolicyStatus[] = [
  "Active",
  "Grace Period",
  "Lapsed",
];

export function filterRenewalIntelligenceTablePoints(
  points: RenewalIntelligencePoint[],
  policyTypeFilter: string,
  policyStatusFilter: string
): RenewalIntelligencePoint[] {
  return points.filter((point) => {
    const matchesType =
      !policyTypeFilter ||
      (point.product_type ?? "").trim().toLowerCase() === policyTypeFilter.trim().toLowerCase();
    const policyStatus = renewalIntelligencePolicyStatus(point);
    const matchesStatus = !policyStatusFilter || policyStatus === policyStatusFilter;
    return matchesType && matchesStatus;
  });
}

function daysToRenewal(point: RenewalIntelligencePoint): number | null {
  if (point.days_until_due != null && !Number.isNaN(point.days_until_due)) {
    return point.days_until_due;
  }
  if (point.days_overdue != null && !Number.isNaN(point.days_overdue)) {
    return -Math.abs(point.days_overdue);
  }
  const fallback = daysUntilUTC(point.expiry_date);
  return Number.isNaN(fallback) ? null : fallback;
}

export function renewalIntelligencePolicyStatus(point: RenewalIntelligencePoint): RenewalIntelligencePolicyStatus {
  const days = daysToRenewal(point);
  if (days == null || days >= 0) {
    return "Active";
  }

  const gracePeriodDays = Math.max(Number(point.grace_period_days ?? DEFAULT_GRACE_PERIOD_DAYS), 0);
  return Math.abs(days) <= gracePeriodDays ? "Grace Period" : "Lapsed";
}

export function renewalStatusForPoint(point: RenewalIntelligencePoint): RenewalIntelligenceStatus {
  const days = daysToRenewal(point);
  if (days == null) return RENEWAL_STATUS_FUTURE;
  if (days > DUE_SOON_MAX_DAYS) return RENEWAL_STATUS_FUTURE;
  if (days >= 0) return RENEWAL_STATUS_DUE_SOON;
  const gracePeriodDays = Math.max(Number(point.grace_period_days ?? DEFAULT_GRACE_PERIOD_DAYS), 0);
  return Math.abs(days) <= gracePeriodDays ? RENEWAL_STATUS_GRACE_PERIOD : RENEWAL_STATUS_LAPSED;
}

export function renewalStatusLabelForPoint(point: RenewalIntelligencePoint): string {
  return RENEWAL_STATUS_LABELS[renewalStatusForPoint(point)];
}

export function formatDaysToRenewal(point: RenewalIntelligencePoint): string {
  if (point.days_until_due != null) {
    return String(point.days_until_due);
  }
  if (point.days_overdue != null) {
    return `-${point.days_overdue}`;
  }
  return "—";
}

export function sortRenewalIntelligencePointsByExpiry(
  points: RenewalIntelligencePoint[]
): RenewalIntelligencePoint[] {
  return [...points].sort((a, b) => {
    const timeA = new Date(a.expiry_date).getTime();
    const timeB = new Date(b.expiry_date).getTime();
    if (Number.isNaN(timeA) && Number.isNaN(timeB)) {
      return a.policy_number.localeCompare(b.policy_number);
    }
    if (Number.isNaN(timeA)) return 1;
    if (Number.isNaN(timeB)) return -1;
    return timeA - timeB;
  });
}

export function formatPremiumInr(amount: number): string {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(amount);
}

export function formatExpiryLabel(isoDate: string): string {
  const date = new Date(isoDate);
  if (Number.isNaN(date.getTime())) return isoDate;
  return date.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
}

/** Compact month label for chart X-axis, e.g. "Jun 2026". */
export function formatAxisMonthLabel(timestamp: number): string {
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleDateString("en-US", { month: "short", year: "numeric" });
}

function startOfMonth(timestamp: number): number {
  const date = new Date(timestamp);
  return new Date(date.getFullYear(), date.getMonth(), 1).getTime();
}

function addMonths(timestamp: number, months: number): number {
  const date = new Date(timestamp);
  return new Date(date.getFullYear(), date.getMonth() + months, 1).getTime();
}

function monthSpanInclusive(minTime: number, maxTime: number): number {
  const minDate = new Date(minTime);
  const maxDate = new Date(maxTime);
  return (
    (maxDate.getFullYear() - minDate.getFullYear()) * 12 +
    (maxDate.getMonth() - minDate.getMonth()) +
    1
  );
}

export type ExpiryAxisTick = {
  x: number;
  label: string;
};

export type ExpiryTimeScale = {
  minTime: number;
  maxTime: number;
  scaleMaxTime: number;
  hasFarFutureOutlier: boolean;
};

export type PremiumScale = {
  min: number;
  max: number;
  displayMin: number;
  displayMax: number;
  radiusMax: number;
};

/** Focus the visible timeline when a far-future expiry would compress the chart. */
export function resolveExpiryTimeScale(times: number[]): ExpiryTimeScale {
  const valid = times.filter((time) => !Number.isNaN(time));
  if (valid.length === 0) {
    return { minTime: 0, maxTime: 1, scaleMaxTime: 1, hasFarFutureOutlier: false };
  }

  const sorted = [...valid].sort((a, b) => a - b);
  const minTime = sorted[0];
  const maxTime = sorted[sorted.length - 1];

  if (valid.length === 1 || maxTime === minTime) {
    return {
      minTime,
      maxTime,
      scaleMaxTime: minTime + 30 * DAY_MS,
      hasFarFutureOutlier: false,
    };
  }

  const referenceTimes = sorted.length > 2 ? sorted.slice(0, -1) : sorted;
  const referenceIndex = Math.min(referenceTimes.length - 1, Math.floor(referenceTimes.length * 0.9));
  const referenceTime = referenceTimes[referenceIndex];
  const tailGap = maxTime - referenceTime;
  const coreSpan = Math.max(referenceTime - minTime, 14 * DAY_MS);
  const hasFarFutureOutlier =
    sorted.length >= 3 && maxTime > referenceTime && tailGap > Math.max(coreSpan * 0.75, 90 * DAY_MS);
  const scaleMaxTime = hasFarFutureOutlier
    ? referenceTime + Math.max(21 * DAY_MS, coreSpan * 0.12)
    : maxTime;

  return { minTime, maxTime, scaleMaxTime, hasFarFutureOutlier };
}

export function expiryTimeToX(
  time: number,
  scale: ExpiryTimeScale,
  paddingLeft: number,
  innerWidth: number
): number {
  const span = Math.max(scale.scaleMaxTime - scale.minTime, 1);
  const raw = paddingLeft + ((time - scale.minTime) / span) * innerWidth;
  const maxX = paddingLeft + innerWidth;
  return Math.min(raw, maxX);
}

export function resolvePremiumScale(premiums: number[]): PremiumScale {
  const valid = premiums.filter((value) => Number.isFinite(value) && value >= 0);
  if (valid.length === 0) {
    return { min: 0, max: 1, displayMin: 0, displayMax: 1, radiusMax: 1 };
  }

  const sorted = [...valid].sort((a, b) => a - b);
  const min = sorted[0];
  const max = sorted[sorted.length - 1];
  const p90Index = Math.min(sorted.length - 1, Math.floor(sorted.length * 0.9));
  const p90 = sorted[p90Index];
  const radiusMax = sorted.length >= 3 && max > p90 * 1.35 ? p90 : max;
  const span = Math.max(max - min, 1);
  const padding = span * 0.1;

  return {
    min,
    max,
    displayMin: Math.max(0, min - padding),
    displayMax: max + padding,
    radiusMax,
  };
}

export function premiumToY(
  premium: number,
  scale: PremiumScale,
  paddingTop: number,
  innerHeight: number
): number {
  const span = Math.max(scale.displayMax - scale.displayMin, 1);
  return paddingTop + innerHeight - ((premium - scale.displayMin) / span) * innerHeight;
}

/** Inverse of premiumToY for validating plotted bubble positions. */
export function yToPremium(
  y: number,
  scale: PremiumScale,
  paddingTop: number,
  innerHeight: number
): number {
  const span = Math.max(scale.displayMax - scale.displayMin, 1);
  const ratio = (paddingTop + innerHeight - y) / innerHeight;
  return scale.displayMin + ratio * span;
}

export function buildPremiumAxisTicks(scale: PremiumScale, count = 4): number[] {
  if (scale.displayMax <= scale.displayMin) {
    return [scale.displayMin];
  }

  const step = (scale.displayMax - scale.displayMin) / Math.max(count - 1, 1);
  return Array.from({ length: count }, (_, index) => scale.displayMin + step * index);
}

/** Compact day label for short timelines, e.g. "01 Jun". */
export function formatAxisDayLabel(timestamp: number): string {
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) return "";
  const day = String(date.getDate()).padStart(2, "0");
  const month = date.toLocaleDateString("en-US", { month: "short" });
  return `${day} ${month}`;
}

/**
 * Build readable timeline ticks using the same expiry-date scale as bubble positioning.
 */
export function buildExpiryAxisTicks(params: {
  minTime: number;
  scaleMaxTime: number;
  paddingLeft: number;
  innerWidth: number;
}): ExpiryAxisTick[] {
  const { minTime, scaleMaxTime, paddingLeft, innerWidth } = params;
  const xSpan = Math.max(scaleMaxTime - minTime, 1);
  const minLabelWidth = 52;
  const maxTicks = Math.max(3, Math.floor(innerWidth / minLabelWidth));
  const spanDays = xSpan / DAY_MS;

  let tickTimes: number[] = [];

  if (spanDays <= 45) {
    const dayStep = spanDays <= 14 ? 2 : spanDays <= 28 ? 5 : 7;
    const start = new Date(minTime);
    start.setHours(0, 0, 0, 0);
    let cursor = start.getTime();
    while (cursor <= scaleMaxTime + DAY_MS) {
      tickTimes.push(cursor);
      cursor += dayStep * DAY_MS;
    }
  } else {
    const spanMonths = monthSpanInclusive(minTime, scaleMaxTime);
    let monthStep = spanMonths <= 7 ? 1 : 2;

    for (let attempt = 0; attempt < 3; attempt += 1) {
      tickTimes = [];
      let cursor = startOfMonth(minTime);
      const end = addMonths(startOfMonth(scaleMaxTime), 1);

      while (cursor < end) {
        tickTimes.push(cursor);
        cursor = addMonths(cursor, monthStep);
      }

      if (tickTimes.length <= maxTicks || monthStep >= 2) {
        break;
      }
      monthStep = 2;
    }
  }

  if (tickTimes.length === 0) {
    tickTimes = [minTime];
  }

  const useDayLabels = spanDays <= 45;
  const positioned = tickTimes.map((time) => ({
    time,
    x: paddingLeft + ((time - minTime) / xSpan) * innerWidth,
    label: useDayLabels ? formatAxisDayLabel(time) : formatAxisMonthLabel(time),
  }));

  const filtered: ExpiryAxisTick[] = [];
  let lastX = Number.NEGATIVE_INFINITY;
  for (const tick of positioned) {
    if (filtered.length === 0 || tick.x - lastX >= minLabelWidth * 0.85) {
      filtered.push({ x: tick.x, label: tick.label });
      lastX = tick.x;
    }
  }

  return filtered;
}

export type BubbleJitterInput = {
  policy_id: number;
  expiry_date: string;
  premium: number;
  baseX: number;
  baseY: number;
  r: number;
};

export type BubbleJitterOutput = BubbleJitterInput & {
  x: number;
  y: number;
  offsetX: number;
  offsetY: number;
};

const BUBBLE_JITTER_MIN_GAP = 3;
const BUBBLE_JITTER_MAX_X = 24;
const BUBBLE_JITTER_MAX_Y = 4;

function bubbleOverlapDistance(a: BubbleJitterInput, b: BubbleJitterInput): number {
  const dx = a.baseX - b.baseX;
  const dy = a.baseY - b.baseY;
  return Math.hypot(dx, dy);
}

function bubblesOverlapAtBase(a: BubbleJitterInput, b: BubbleJitterInput): boolean {
  const overlapThreshold = a.r + b.r + BUBBLE_JITTER_MIN_GAP;
  return bubbleOverlapDistance(a, b) <= overlapThreshold;
}

function clampBubbleCenter(
  x: number,
  y: number,
  radius: number,
  bounds: { left: number; right: number; top: number; bottom: number }
): { x: number; y: number } {
  return {
    x: Math.max(bounds.left + radius, Math.min(x, bounds.right - radius)),
    y: Math.max(bounds.top + radius, Math.min(y, bounds.bottom - radius)),
  };
}

class UnionFind {
  private parent: number[];

  constructor(size: number) {
    this.parent = Array.from({ length: size }, (_, index) => index);
  }

  find(index: number): number {
    if (this.parent[index] !== index) {
      this.parent[index] = this.find(this.parent[index]);
    }
    return this.parent[index];
  }

  union(a: number, b: number): void {
    const rootA = this.find(a);
    const rootB = this.find(b);
    if (rootA !== rootB) {
      this.parent[rootB] = rootA;
    }
  }
}

/**
 * Spread visually overlapping bubbles while preserving actual expiry/premium data.
 * Y positions always reflect the true premium; only tiny horizontal offsets are applied.
 */
export function applyBubbleVisualJitter(
  inputs: BubbleJitterInput[],
  bounds: { left: number; right: number; top: number; bottom: number }
): BubbleJitterOutput[] {
  if (inputs.length === 0) {
    return [];
  }

  const unionFind = new UnionFind(inputs.length);
  for (let i = 0; i < inputs.length; i += 1) {
    for (let j = i + 1; j < inputs.length; j += 1) {
      if (bubblesOverlapAtBase(inputs[i], inputs[j])) {
        unionFind.union(i, j);
      }
    }
  }

  const clusters = new Map<number, number[]>();
  inputs.forEach((_, index) => {
    const root = unionFind.find(index);
    const members = clusters.get(root) ?? [];
    members.push(index);
    clusters.set(root, members);
  });

  const outputs: BubbleJitterOutput[] = inputs.map((input) => ({
    ...input,
    x: input.baseX,
    y: input.baseY,
    offsetX: 0,
    offsetY: 0,
  }));

  for (const memberIndexes of clusters.values()) {
    if (memberIndexes.length <= 1) {
      continue;
    }

    const sortedIndexes = [...memberIndexes].sort(
      (a, b) => inputs[a].policy_id - inputs[b].policy_id
    );
    const clusterInputs = sortedIndexes.map((index) => inputs[index]);
    const anchorX =
      clusterInputs.every((item) => Math.abs(item.baseX - clusterInputs[0].baseX) < 0.5)
        ? clusterInputs[0].baseX
        : clusterInputs.reduce((sum, item) => sum + item.baseX, 0) / clusterInputs.length;
    const step = Math.min(
      BUBBLE_JITTER_MAX_X,
      Math.max(...clusterInputs.map((item) => item.r)) * 2 + BUBBLE_JITTER_MIN_GAP + 1
    );
    const totalWidth = (sortedIndexes.length - 1) * step;
    const startX = anchorX - totalWidth / 2;

    sortedIndexes.forEach((inputIndex, position) => {
      const input = inputs[inputIndex];
      const targetX = startX + position * step;
      const clampedX = Math.max(
        input.baseX - BUBBLE_JITTER_MAX_X,
        Math.min(targetX, input.baseX + BUBBLE_JITTER_MAX_X)
      );
      const clamped = clampBubbleCenter(clampedX, input.baseY, input.r, bounds);

      outputs[inputIndex] = {
        ...input,
        x: clamped.x,
        y: clamped.y,
        offsetX: clamped.x - input.baseX,
        offsetY: clamped.y - input.baseY,
      };
    });

    // Resolve any remaining overlap with a tiny vertical nudge (never changes premium meaning).
    for (let pass = 0; pass < 3; pass += 1) {
      let adjusted = false;
      for (let i = 0; i < sortedIndexes.length; i += 1) {
        for (let j = i + 1; j < sortedIndexes.length; j += 1) {
          const aIndex = sortedIndexes[i];
          const bIndex = sortedIndexes[j];
          const a = outputs[aIndex];
          const b = outputs[bIndex];
          const minDist = a.r + b.r + BUBBLE_JITTER_MIN_GAP;
          const dx = b.x - a.x;
          const dy = b.y - a.y;
          const dist = Math.hypot(dx, dy) || 1;
          if (dist >= minDist) {
            continue;
          }

          const overlap = minDist - dist;
          const pushY = Math.min(overlap * 0.5, BUBBLE_JITTER_MAX_Y);
          const aTargetY = Math.max(
            inputs[aIndex].baseY - BUBBLE_JITTER_MAX_Y,
            a.y - pushY
          );
          const bTargetY = Math.min(
            inputs[bIndex].baseY + BUBBLE_JITTER_MAX_Y,
            b.y + pushY
          );
          const clampedA = clampBubbleCenter(a.x, aTargetY, a.r, bounds);
          const clampedB = clampBubbleCenter(b.x, bTargetY, b.r, bounds);

          outputs[aIndex] = {
            ...a,
            y: clampedA.y,
            offsetY: clampedA.y - inputs[aIndex].baseY,
          };
          outputs[bIndex] = {
            ...b,
            y: clampedB.y,
            offsetY: clampedB.y - inputs[bIndex].baseY,
          };
          adjusted = true;
        }
      }
      if (!adjusted) {
        break;
      }
    }
  }

  return outputs;
}

export function buildPremiumBubbleRadii(premiums: number[]): number[] {
  const minRadius = 4;
  const maxRadius = 12;
  const count = premiums.length;

  if (count === 0) return [];
  if (count === 1) return [(minRadius + maxRadius) / 2];

  const validPremiums = premiums.map((premium) => Math.max(premium, 0));
  const minPremium = Math.min(...validPremiums);
  const maxPremium = Math.max(...validPremiums);

  if (minPremium === maxPremium) {
    return premiums.map(() => (minRadius + maxRadius) / 2);
  }

  const sqrtMin = Math.sqrt(minPremium);
  const sqrtMax = Math.sqrt(maxPremium);
  const sqrtSpan = Math.max(sqrtMax - sqrtMin, 1);

  return validPremiums.map((premium) => {
    const ratio = (Math.sqrt(premium) - sqrtMin) / sqrtSpan;
    return minRadius + ratio * (maxRadius - minRadius);
  });
}

/** @deprecated Use buildPremiumBubbleRadii for chart rendering. */
export function bubbleRadius(premium: number, minPremium: number, effectiveMaxPremium: number): number {
  return buildPremiumBubbleRadii([minPremium, premium, effectiveMaxPremium])[1];
}

export const RENEWAL_TOOLTIP_WIDTH = 248;
export const RENEWAL_TOOLTIP_HEIGHT = 210;
export const RENEWAL_CHART_LAYOUT = {
  width: 920,
  height: 380,
  padding: { top: 20, right: 28, bottom: 52, left: 76 },
} as const;

export type RenewalTooltipPlacement = {
  x: number;
  y: number;
  offsetX: number;
  offsetY: number;
};

type TooltipPlacementInput = {
  bubbleX: number;
  bubbleY: number;
  bubbleRadius: number;
  containerWidth: number;
  containerHeight: number;
  scaleX: number;
  scaleY: number;
};

/** Smart tooltip placement that keeps content inside the chart container. */
export function computeRenewalTooltipPlacement(input: TooltipPlacementInput): RenewalTooltipPlacement {
  const {
    bubbleX,
    bubbleY,
    bubbleRadius,
    containerWidth,
    containerHeight,
    scaleX,
    scaleY,
  } = input;

  const gap = 12;
  const edgePadding = 8;
  const { width, height, padding } = RENEWAL_CHART_LAYOUT;

  const bubblePxX = bubbleX * scaleX;
  const bubblePxY = bubbleY * scaleY;
  const bubblePxR = bubbleRadius * Math.max(scaleX, scaleY);

  const plotLeftPx = padding.left * scaleX;
  const plotRightPx = (width - padding.right) * scaleX;
  const plotTopPx = padding.top * scaleY;
  const plotBottomPx = (height - padding.bottom) * scaleY;
  const plotWidth = plotRightPx - plotLeftPx;
  const plotHeight = plotBottomPx - plotTopPx;

  const nearLeft = bubblePxX <= plotLeftPx + plotWidth * 0.28;
  const nearRight = bubblePxX >= plotLeftPx + plotWidth * 0.72;
  const nearTop = bubblePxY <= plotTopPx + plotHeight * 0.22;
  const nearBottom = bubblePxY >= plotTopPx + plotHeight * 0.78;

  let offsetX = 0;
  let offsetY = 0;
  let x: number;
  let y: number;

  if (nearLeft) {
    x = bubblePxX + bubblePxR + gap;
    offsetX = -8;
  } else if (nearRight) {
    x = bubblePxX - bubblePxR - gap - RENEWAL_TOOLTIP_WIDTH;
    offsetX = 8;
  } else {
    x = bubblePxX - RENEWAL_TOOLTIP_WIDTH / 2;
  }

  if (nearTop) {
    y = bubblePxY + bubblePxR + gap;
    offsetY = -8;
  } else if (nearBottom) {
    y = bubblePxY - bubblePxR - gap - RENEWAL_TOOLTIP_HEIGHT;
    offsetY = 8;
  } else {
    y = bubblePxY - RENEWAL_TOOLTIP_HEIGHT / 2;
  }

  const xAxisLabelBandTop = plotBottomPx;
  if (y + RENEWAL_TOOLTIP_HEIGHT > xAxisLabelBandTop - 4) {
    y = bubblePxY - bubblePxR - gap - RENEWAL_TOOLTIP_HEIGHT;
    offsetY = 8;
  }

  const yAxisLabelBandRight = plotLeftPx;
  if (x < yAxisLabelBandRight + 4) {
    x = bubblePxX + bubblePxR + gap;
    offsetX = -8;
  }

  x = Math.max(edgePadding, Math.min(x, containerWidth - RENEWAL_TOOLTIP_WIDTH - edgePadding));
  y = Math.max(edgePadding, Math.min(y, containerHeight - RENEWAL_TOOLTIP_HEIGHT - edgePadding));

  return { x, y, offsetX, offsetY };
}
