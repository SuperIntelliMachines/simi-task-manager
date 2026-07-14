import { describe, expect, it } from "vitest";
import {
  RENEWAL_STATUS_DUE_SOON,
  RENEWAL_STATUS_FUTURE,
  RENEWAL_STATUS_GRACE_PERIOD,
  RENEWAL_STATUS_LAPSED,
  buildRenewalIntelligenceChart,
  buildExpiryAxisTicks,
  buildPremiumBubbleRadii,
  applyBubbleVisualJitter,
  classifyRenewalIntelligenceStatus,
  expiryTimeToX,
  filterRenewalIntelligencePoints,
  filterRenewalIntelligenceTablePoints,
  formatAxisMonthLabel,
  resolveExpiryTimeScale,
  resolvePremiumScale,
  premiumToY,
  yToPremium,
  computeRenewalTooltipPlacement,
  formatDaysToRenewal,
  renewalIntelligencePolicyStatus,
  sortRenewalIntelligencePointsByExpiry,
  RENEWAL_CHART_LAYOUT,
  type RenewalIntelligencePoint,
} from "./renewal-intelligence";

describe("renewal-intelligence", () => {
  it("classifies renewal intelligence statuses", () => {
    const now = Date.now();
    const iso = (offsetDays: number) => new Date(now + offsetDays * 24 * 60 * 60 * 1000).toISOString();

    expect(
      classifyRenewalIntelligenceStatus({
        id: 1,
        policy_number: "P-2",
        expiry_date: iso(-5),
        status: "active",
        grace_period_days: 30,
      })
    ).toBe(RENEWAL_STATUS_GRACE_PERIOD);
    expect(
      classifyRenewalIntelligenceStatus({
        id: 2,
        policy_number: "P-3",
        expiry_date: iso(4),
        status: "active",
      })
    ).toBe(RENEWAL_STATUS_DUE_SOON);
    expect(
      classifyRenewalIntelligenceStatus({
        id: 3,
        policy_number: "P-4",
        expiry_date: iso(20),
        status: "active",
      })
    ).toBe(RENEWAL_STATUS_FUTURE);
    expect(
      classifyRenewalIntelligenceStatus({
        id: 4,
        policy_number: "P-5",
        expiry_date: iso(-35),
        status: "active",
        grace_period_days: 30,
      }),
    ).toBe(RENEWAL_STATUS_LAPSED);
  });

  it("builds chart points and filters", () => {
    const now = Date.now();
    const iso = (offsetDays: number) => new Date(now + offsetDays * 24 * 60 * 60 * 1000).toISOString();
    const chart = buildRenewalIntelligenceChart([
      {
        id: 1,
        policy_number: "P-1",
        policyholder_name: "Ravi",
        policy_type: "Auto",
        expiry_date: iso(5),
        premium: 18000,
        status: "active",
        assigned_agent_user_id: "Kumar",
      },
      {
        id: 2,
        policy_number: "P-2",
        policyholder_name: "Asha",
        policy_type: "Health",
        expiry_date: iso(-2),
        premium: 15000,
        status: "active",
        assigned_agent_user_id: "Leo",
      },
    ]);

    expect(chart.points).toHaveLength(2);
    expect(chart.filters.product_types).toEqual(["Auto", "Health"]);
    expect(chart.points[0]?.renewal_frequency).toBe("yearly");
    expect(filterRenewalIntelligencePoints(chart.points, "Health")).toHaveLength(1);
    expect(filterRenewalIntelligencePoints(chart.points, "")).toHaveLength(2);
  });

  it("excludes policies outside the renewal intelligence chart window", () => {
    const now = Date.now();
    const iso = (offsetDays: number) => new Date(now + offsetDays * 24 * 60 * 60 * 1000).toISOString();
    const chart = buildRenewalIntelligenceChart([
      {
        id: 1,
        policy_number: "P-IN-WINDOW",
        expiry_date: iso(20),
        status: "active",
      },
      {
        id: 2,
        policy_number: "P-FAR-FUTURE",
        expiry_date: iso(45),
        status: "active",
      },
      {
        id: 3,
        policy_number: "P-OLD-EXPIRED",
        expiry_date: iso(-120),
        status: "active",
      },
      {
        id: 4,
        policy_number: "P-RECENT-EXPIRED",
        expiry_date: iso(-30),
        status: "active",
      },
    ]);

    expect(chart.points.map((point) => point.policy_number)).toEqual(["P-IN-WINDOW", "P-RECENT-EXPIRED"]);
  });

  it("filters table rows by policy type and status together", () => {
    const now = Date.now();
    const iso = (offsetDays: number) => new Date(now + offsetDays * 24 * 60 * 60 * 1000).toISOString();
    const points: RenewalIntelligencePoint[] = [
      {
        policy_id: 1,
        customer_name: "Ravi",
        policy_number: "H-EXP",
        product_type: "Health",
        renewal_frequency: "yearly",
        expiry_date: iso(-5),
        premium: 10000,
        renewal_status: "grace_period",
        renewal_status_label: "Grace Period",
        days_until_due: null,
        days_overdue: 5,
        assigned_agent_user_id: null,
        assigned_agent_name: null,
      },
      {
        policy_id: 2,
        customer_name: "Asha",
        policy_number: "A-ACT",
        product_type: "Auto",
        renewal_frequency: "yearly",
        expiry_date: iso(20),
        premium: 12000,
        renewal_status: "future_renewal",
        renewal_status_label: "Future Renewal",
        days_until_due: 20,
        days_overdue: null,
        assigned_agent_user_id: null,
        assigned_agent_name: null,
      },
      {
        policy_id: 3,
        customer_name: "Vikram",
        policy_number: "H-ACT",
        product_type: "Health",
        renewal_frequency: "yearly",
        expiry_date: iso(20),
        premium: 9000,
        renewal_status: "future_renewal",
        renewal_status_label: "Future Renewal",
        days_until_due: 20,
        days_overdue: null,
        assigned_agent_user_id: null,
        assigned_agent_name: null,
      },
    ];

    expect(filterRenewalIntelligenceTablePoints(points, "Health", "Grace Period")).toHaveLength(1);
    expect(filterRenewalIntelligenceTablePoints(points, "Health", "Grace Period")[0]?.policy_number).toBe("H-EXP");
    expect(filterRenewalIntelligenceTablePoints(points, "Auto", "Active")).toHaveLength(1);
    expect(filterRenewalIntelligenceTablePoints(points, "Auto", "Active")[0]?.policy_number).toBe("A-ACT");
    expect(filterRenewalIntelligenceTablePoints(points, "", "")).toHaveLength(3);
  });

  it("formats axis month labels and builds non-overlapping monthly ticks", () => {
    const minTime = new Date(2026, 5, 15).getTime();
    const maxTime = new Date(2026, 9, 20).getTime();

    expect(formatAxisMonthLabel(minTime)).toBe("Jun 2026");
    expect(formatAxisMonthLabel(new Date(2026, 6, 1).getTime())).toBe("Jul 2026");

    const ticks = buildExpiryAxisTicks({
      minTime,
      scaleMaxTime: maxTime,
      paddingLeft: 72,
      innerWidth: 824,
    });

    expect(ticks.length).toBeGreaterThanOrEqual(4);
    expect(ticks[0]?.label).toBe("Jun 2026");
    expect(ticks.some((tick) => tick.label === "Oct 2026")).toBe(true);
    expect(ticks.every((tick, index) => index === 0 || tick.x - ticks[index - 1].x >= 44)).toBe(true);
  });

  it("focuses the timeline when a far-future outlier would compress the chart", () => {
    const now = Date.now();
    const cluster = [now, now + 5 * 24 * 60 * 60 * 1000, now + 10 * 24 * 60 * 60 * 1000];
    const outlier = now + 400 * 24 * 60 * 60 * 1000;
    const scale = resolveExpiryTimeScale([...cluster, outlier]);

    expect(scale.hasFarFutureOutlier).toBe(true);
    expect(scale.scaleMaxTime).toBeLessThan(scale.maxTime);

    const innerWidth = 824;
    const clusterX = expiryTimeToX(cluster[1], scale, 72, innerWidth);
    const outlierX = expiryTimeToX(outlier, scale, 72, innerWidth);
    expect(clusterX).toBeGreaterThan(200);
    expect(outlierX).toBe(72 + innerWidth);
  });

  it("sizes bubbles proportionally to actual premium amounts", () => {
    const premiums = [12000, 80000, 150000, 1500000];
    const radii = buildPremiumBubbleRadii(premiums);

    expect(radii[0]).toBeLessThan(radii[1]);
    expect(radii[1]).toBeLessThan(radii[2]);
    expect(radii[2]).toBeLessThan(radii[3]);
    expect(Math.min(...radii)).toBeGreaterThanOrEqual(4);
    expect(Math.max(...radii)).toBeLessThanOrEqual(12);
  });

  it("plots every premium at the correct vertical position for the full dataset", () => {
    const paddingTop = 20;
    const innerHeight = 308;
    const policies = [
      { policy_id: 1, customer_name: "Low Premium", premium: 12000 },
      { policy_id: 2, customer_name: "Mid Premium A", premium: 80000 },
      { policy_id: 3, customer_name: "Mid Premium B", premium: 150000 },
      { policy_id: 4, customer_name: "High Premium", premium: 1500000 },
      { policy_id: 5, customer_name: "Another Low", premium: 15000 },
      { policy_id: 6, customer_name: "Another High", premium: 1200000 },
    ];
    const premiums = policies.map((policy) => policy.premium);
    const scale = resolvePremiumScale(premiums);

    const plotted = policies.map((policy) => ({
      ...policy,
      baseY: premiumToY(policy.premium, scale, paddingTop, innerHeight),
    }));

    for (let i = 0; i < plotted.length; i += 1) {
      for (let j = i + 1; j < plotted.length; j += 1) {
        if (policies[i].premium < policies[j].premium) {
          expect(plotted[i].baseY).toBeGreaterThan(plotted[j].baseY);
        } else if (policies[i].premium > policies[j].premium) {
          expect(plotted[i].baseY).toBeLessThan(plotted[j].baseY);
        } else {
          expect(plotted[i].baseY).toBe(plotted[j].baseY);
        }
      }
    }

    plotted.forEach((point) => {
      const inferredPremium = yToPremium(point.baseY, scale, paddingTop, innerHeight);
      expect(Math.abs(inferredPremium - point.premium)).toBeLessThan(1);
    });
  });

  it("separates overlapping bubbles visually without changing source data", () => {
    const bounds = { left: 76, right: 892, top: 20, bottom: 328 };
    const sharedExpiry = "2026-06-13T00:00:00.000Z";
    const sharedPremium = 25000;
    const baseX = 420;
    const baseY = 180;

    const inputs = Array.from({ length: 5 }, (_, index) => ({
      policy_id: index + 1,
      expiry_date: sharedExpiry,
      premium: sharedPremium,
      baseX,
      baseY,
      r: 5,
    }));

    const jittered = applyBubbleVisualJitter(inputs, bounds);

    expect(jittered).toHaveLength(5);
    expect(jittered.every((item) => item.expiry_date === sharedExpiry)).toBe(true);
    expect(jittered.every((item) => item.premium === sharedPremium)).toBe(true);

    const positions = jittered.map((item) => `${item.x.toFixed(2)},${item.y.toFixed(2)}`);
    expect(new Set(positions).size).toBe(5);

    for (let i = 0; i < jittered.length; i += 1) {
      for (let j = i + 1; j < jittered.length; j += 1) {
        const distance = Math.hypot(jittered[i].x - jittered[j].x, jittered[i].y - jittered[j].y);
        expect(distance).toBeGreaterThan(jittered[i].r + jittered[j].r);
      }
    }

    jittered.forEach((item) => {
      expect(Math.abs(item.y - baseY)).toBeLessThanOrEqual(4);
      expect(Math.abs(item.offsetY)).toBeLessThanOrEqual(4);
    });
  });

  it("preserves distinct premium heights when policies share an expiry date", () => {
    const bounds = { left: 76, right: 892, top: 20, bottom: 328 };
    const sharedExpiry = "2026-06-13T00:00:00.000Z";
    const baseX = 420;
    const paddingTop = 20;
    const innerHeight = 308;
    const premiums = [12000, 80000, 150000, 1500000];
    const scale = resolvePremiumScale(premiums);

    const inputs = premiums.map((premium, index) => ({
      policy_id: index + 1,
      expiry_date: sharedExpiry,
      premium,
      baseX,
      baseY: premiumToY(premium, scale, paddingTop, innerHeight),
      r: buildPremiumBubbleRadii(premiums)[index],
    }));

    const jittered = applyBubbleVisualJitter(inputs, bounds);

    expect(jittered.map((item) => item.y)).toEqual(inputs.map((item) => item.baseY));
    expect(jittered.every((item) => Math.abs(item.offsetY) <= 4)).toBe(true);

    for (let i = 0; i < jittered.length; i += 1) {
      for (let j = i + 1; j < jittered.length; j += 1) {
        if (premiums[i] < premiums[j]) {
          expect(jittered[i].y).toBeGreaterThan(jittered[j].y);
        }
      }
    }
  });

  it("leaves isolated bubbles at their base coordinates", () => {
    const bounds = { left: 76, right: 892, top: 20, bottom: 328 };
    const [single] = applyBubbleVisualJitter(
      [
        {
          policy_id: 99,
          expiry_date: "2026-08-01T00:00:00.000Z",
          premium: 42000,
          baseX: 300,
          baseY: 120,
          r: 5,
        },
      ],
      bounds
    );

    expect(single.x).toBe(300);
    expect(single.y).toBe(120);
    expect(single.offsetX).toBe(0);
    expect(single.offsetY).toBe(0);
  });

  it("positions tooltips away from chart edges and axis labels", () => {
    const { width, height, padding } = RENEWAL_CHART_LAYOUT;
    const scaleX = 1;
    const scaleY = 1;

    const leftPlacement = computeRenewalTooltipPlacement({
      bubbleX: padding.left + 10,
      bubbleY: height / 2,
      bubbleRadius: 6,
      containerWidth: width,
      containerHeight: height,
      scaleX,
      scaleY,
    });
    expect(leftPlacement.x).toBeGreaterThan(padding.left);

    const rightPlacement = computeRenewalTooltipPlacement({
      bubbleX: width - padding.right - 10,
      bubbleY: height / 2,
      bubbleRadius: 6,
      containerWidth: width,
      containerHeight: height,
      scaleX,
      scaleY,
    });
    expect(rightPlacement.x + 248).toBeLessThan(width);

    const bottomPlacement = computeRenewalTooltipPlacement({
      bubbleX: width / 2,
      bubbleY: height - padding.bottom - 8,
      bubbleRadius: 6,
      containerWidth: width,
      containerHeight: height,
      scaleX,
      scaleY,
    });
    expect(bottomPlacement.y + 210).toBeLessThanOrEqual(height);
  });

  it("sorts renewal intelligence table rows by expiry date ascending", () => {
    const points: RenewalIntelligencePoint[] = [
      {
        policy_id: 1,
        customer_name: "Later",
        policy_number: "P-1",
        product_type: "Health",
        renewal_frequency: "yearly",
        expiry_date: "2026-12-01T00:00:00.000Z",
        premium: 10000,
        renewal_status: RENEWAL_STATUS_FUTURE,
        renewal_status_label: "Future Renewal",
        days_until_due: 120,
        days_overdue: null,
        assigned_agent_user_id: null,
        assigned_agent_name: null,
      },
      {
        policy_id: 2,
        customer_name: "Sooner",
        policy_number: "P-2",
        product_type: "Health",
        renewal_frequency: "quarterly",
        expiry_date: "2026-06-01T00:00:00.000Z",
        premium: 20000,
        renewal_status: RENEWAL_STATUS_DUE_SOON,
        renewal_status_label: "Due Soon",
        days_until_due: 5,
        days_overdue: null,
        assigned_agent_user_id: null,
        assigned_agent_name: null,
      },
    ];

    const sorted = sortRenewalIntelligencePointsByExpiry(points);
    expect(sorted.map((point) => point.policy_id)).toEqual([2, 1]);
  });

  it("maps table lifecycle status from days + grace period", () => {
    expect(
      renewalIntelligencePolicyStatus({
        policy_id: 1,
        customer_name: "A",
        policy_number: "P-1",
        product_type: "Health",
        renewal_frequency: "yearly",
        expiry_date: "2026-06-01",
        premium: 1000,
        renewal_status: RENEWAL_STATUS_GRACE_PERIOD,
        renewal_status_label: "Grace Period",
        days_until_due: 0,
        days_overdue: null,
        assigned_agent_user_id: null,
        assigned_agent_name: null,
      }),
    ).toBe("Active");
    expect(
      renewalIntelligencePolicyStatus({
        policy_id: 2,
        customer_name: "B",
        policy_number: "P-2",
        product_type: "Health",
        renewal_frequency: "yearly",
        expiry_date: "2026-06-01",
        premium: 1000,
        renewal_status: RENEWAL_STATUS_FUTURE,
        renewal_status_label: "Future Renewal",
        days_until_due: null,
        days_overdue: 22,
        grace_period_days: 30,
        assigned_agent_user_id: null,
        assigned_agent_name: null,
      }),
    ).toBe("Grace Period");
    expect(
      renewalIntelligencePolicyStatus({
        policy_id: 3,
        customer_name: "C",
        policy_number: "P-3",
        product_type: "Health",
        renewal_frequency: "yearly",
        expiry_date: "2026-06-01",
        premium: 1000,
        renewal_status: RENEWAL_STATUS_DUE_SOON,
        renewal_status_label: "Due Soon",
        days_until_due: null,
        days_overdue: 31,
        grace_period_days: 30,
        assigned_agent_user_id: null,
        assigned_agent_name: null,
      }),
    ).toBe("Lapsed");
  });

  it("formats days to renewal for upcoming and overdue policies", () => {
    expect(
      formatDaysToRenewal({
        policy_id: 1,
        customer_name: "A",
        policy_number: "P-1",
        product_type: null,
        renewal_frequency: null,
        expiry_date: "2026-06-01",
        premium: 1000,
        renewal_status: RENEWAL_STATUS_DUE_SOON,
        renewal_status_label: "Due Soon",
        days_until_due: 7,
        days_overdue: null,
        assigned_agent_user_id: null,
        assigned_agent_name: null,
      })
    ).toBe("7");

    expect(
      formatDaysToRenewal({
        policy_id: 2,
        customer_name: "B",
        policy_number: "P-2",
        product_type: null,
        renewal_frequency: null,
        expiry_date: "2026-05-01",
        premium: 1000,
        renewal_status: RENEWAL_STATUS_GRACE_PERIOD,
        renewal_status_label: "Grace Period",
        days_until_due: null,
        days_overdue: 12,
        assigned_agent_user_id: null,
        assigned_agent_name: null,
      })
    ).toBe("-12");
  });
});
