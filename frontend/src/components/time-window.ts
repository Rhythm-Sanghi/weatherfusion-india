export const WINDOWS = ["1h", "3h", "6h", "12h", "24h", "all"] as const;

export type TimeWindowValue = (typeof WINDOWS)[number];

export function timeFilter(value: TimeWindowValue): { date_from?: string } {
  if (value === "all") return {};

  return {
    date_from: new Date(Date.now() - Number.parseInt(value) * 60 * 60 * 1000).toISOString(),
  };
}
