export type KpiDirection = "high" | "low" | null;
export type PerformanceDirection = "improved" | "worsened" | "unknown";

export function isHigherBetter(direction: KpiDirection): boolean | null {
  if (direction === "high") return true;
  if (direction === "low") return false;
  return null;
}

export function performanceDirection(direction: KpiDirection, deltaPositive: boolean): PerformanceDirection {
  const higherBetter = isHigherBetter(direction);
  if (higherBetter === null) return "unknown";
  return deltaPositive === higherBetter ? "improved" : "worsened";
}

export const PERFORMANCE_COLORS: Record<PerformanceDirection, string> = {
  improved: "#15803d",
  worsened: "#b91c1c",
  unknown: "var(--text-muted)",
};

export const PERFORMANCE_LABELS: Record<PerformanceDirection, string> = {
  improved: "İyileşme",
  worsened: "Kötüleşme",
  unknown: "Yön belirlenemedi",
};

export function formatSignedPct(value: number, decimals = 1): string {
  const sign = value > 0 ? "+" : "";
  return `${sign}%${value.toFixed(decimals)}`;
}

export function formatSignedPoints(value: number, decimals = 2): string {
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(decimals)} puan`;
}

export function formatPct(value: number, decimals = 2): string {
  return `%${value.toFixed(decimals)}`;
}
