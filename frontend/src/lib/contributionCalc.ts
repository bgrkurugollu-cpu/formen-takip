import type { ContributionTimeUnit, RepeatPeriod } from "../api/types";

const MINUTES_PER_UNIT: Record<ContributionTimeUnit, number> = {
  second: 1 / 60,
  minute: 1,
  hour: 60,
};

const OCCURRENCES_PER_MONTH: Record<RepeatPeriod, number> = {
  daily: 30,
  weekly: 4.345,
  monthly: 1,
};

export function durationToMinutes(value: number | null | undefined, unit: ContributionTimeUnit | null | undefined): number | null {
  if (value == null || !unit) return null;
  return Math.round(value * MINUTES_PER_UNIT[unit] * 10000) / 10000;
}

/** Önceki - yeni süre; yeni süre öncekinden büyük/eşitse kazanç yok (null döner). */
export function computeTimeSaving(previousDuration: number | null | undefined, newDuration: number | null | undefined): number | null {
  if (previousDuration == null || newDuration == null) return null;
  if (newDuration >= previousDuration) return null;
  return Math.round((previousDuration - newDuration) * 100) / 100;
}

export function computeMonthlyTotal(
  perOccurrenceMinutes: number | null | undefined,
  repeatPeriod: RepeatPeriod | null | undefined,
  repeatCount: number | null | undefined
): number | null {
  if (perOccurrenceMinutes == null || !repeatPeriod || repeatCount == null) return null;
  return Math.round(perOccurrenceMinutes * repeatCount * OCCURRENCES_PER_MONTH[repeatPeriod] * 100) / 100;
}

/** (değişim miktarı, değişim yüzdesi). previous null/0 ise yüzde null döner. */
export function computeChange(
  previous: number | null | undefined, next: number | null | undefined
): { amount: number | null; percent: number | null } {
  if (previous == null || next == null) return { amount: null, percent: null };
  const amount = Math.round((next - previous) * 10000) / 10000;
  if (previous === 0) return { amount, percent: null };
  const percent = Math.round((amount / Math.abs(previous)) * 100 * 1000) / 1000;
  return { amount, percent };
}

export function formatMoney(value: number | null | undefined, currency: string | null | undefined): string {
  if (value == null) return "-";
  const formatted = new Intl.NumberFormat("tr-TR", { maximumFractionDigits: 2 }).format(value);
  return currency ? `${formatted} ${currency}` : formatted;
}

export function formatPercent(value: number | null | undefined): string {
  if (value == null) return "-";
  return `%${new Intl.NumberFormat("tr-TR", { maximumFractionDigits: 2 }).format(Math.abs(value))}`;
}

export function formatMinutes(value: number | null | undefined): string {
  if (value == null) return "-";
  return `${new Intl.NumberFormat("tr-TR", { maximumFractionDigits: 1 }).format(value)} dakika`;
}
