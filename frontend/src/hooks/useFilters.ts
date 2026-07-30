import { useCallback, useMemo } from "react";
import { useSearchParams } from "react-router-dom";

export interface FilterState {
  dateFrom: string;
  dateTo: string;
  plantIds: string[];
  factoryIds: string[];
  chiefIds: string[];
  shiftIds: string[];
  kpiIds: string[];
}

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

function daysAgoIso(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() - days);
  return d.toISOString().slice(0, 10);
}

const DEFAULTS: FilterState = {
  dateFrom: daysAgoIso(30),
  dateTo: todayIso(),
  plantIds: [],
  factoryIds: [],
  chiefIds: [],
  shiftIds: [],
  kpiIds: [],
};

function parseList(value: string | null): string[] {
  return value ? value.split(",").filter(Boolean) : [];
}

export function useFilters() {
  const [searchParams, setSearchParams] = useSearchParams();

  const filters = useMemo<FilterState>(
    () => ({
      dateFrom: searchParams.get("date_from") || DEFAULTS.dateFrom,
      dateTo: searchParams.get("date_to") || DEFAULTS.dateTo,
      plantIds: parseList(searchParams.get("plant_ids")),
      factoryIds: parseList(searchParams.get("factory_ids")),
      chiefIds: parseList(searchParams.get("chief_ids")),
      shiftIds: parseList(searchParams.get("shift_ids")),
      kpiIds: parseList(searchParams.get("kpi_ids")),
    }),
    [searchParams]
  );

  const setFilters = useCallback(
    (partial: Partial<FilterState>) => {
      const next = { ...filters, ...partial };
      const params = new URLSearchParams();
      params.set("date_from", next.dateFrom);
      params.set("date_to", next.dateTo);
      if (next.plantIds.length) params.set("plant_ids", next.plantIds.join(","));
      if (next.factoryIds.length) params.set("factory_ids", next.factoryIds.join(","));
      if (next.chiefIds.length) params.set("chief_ids", next.chiefIds.join(","));
      if (next.shiftIds.length) params.set("shift_ids", next.shiftIds.join(","));
      if (next.kpiIds.length) params.set("kpi_ids", next.kpiIds.join(","));
      setSearchParams(params, { replace: true });
    },
    [filters, setSearchParams]
  );

  const clearFilters = useCallback(() => {
    setSearchParams(new URLSearchParams(), { replace: true });
  }, [setSearchParams]);

  const asQueryParams = useMemo(
    () => ({
      date_from: filters.dateFrom,
      date_to: filters.dateTo,
      plant_ids: filters.plantIds.join(",") || undefined,
      factory_ids: filters.factoryIds.join(",") || undefined,
      chief_ids: filters.chiefIds.join(",") || undefined,
      shift_ids: filters.shiftIds.join(",") || undefined,
      kpi_ids: filters.kpiIds.join(",") || undefined,
    }),
    [filters]
  );

  return { filters, setFilters, clearFilters, asQueryParams };
}

export const DATE_PRESETS: { label: string; getRange: () => [string, string] }[] = [
  { label: "Bugün", getRange: () => [todayIso(), todayIso()] },
  { label: "Dün", getRange: () => [daysAgoIso(1), daysAgoIso(1)] },
  { label: "Son 7 Gün", getRange: () => [daysAgoIso(7), todayIso()] },
  { label: "Son 30 Gün", getRange: () => [daysAgoIso(30), todayIso()] },
  { label: "Son 3 Ay", getRange: () => [daysAgoIso(90), todayIso()] },
  { label: "Son 6 Ay", getRange: () => [daysAgoIso(180), todayIso()] },
  { label: "Bu Yıl", getRange: () => [`${new Date().getFullYear()}-01-01`, todayIso()] },
  { label: "Son 12 Ay", getRange: () => [daysAgoIso(365), todayIso()] },
];
