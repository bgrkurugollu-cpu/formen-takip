import { useCallback, useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import type { ShiftAnomalySeverity } from "../api/types";

export interface ShiftAnalysisFilterState {
  factoryIds: string[];
  plantIds: string[];
  kpiIds: string[];
  shiftIds: string[];
  severity: ShiftAnomalySeverity | "";
}

const DEFAULTS: ShiftAnalysisFilterState = {
  factoryIds: [],
  plantIds: [],
  kpiIds: [],
  shiftIds: [],
  severity: "",
};

function parseList(value: string | null): string[] {
  return value ? value.split(",").filter(Boolean) : [];
}

export function useShiftAnalysisFilters() {
  const [searchParams, setSearchParams] = useSearchParams();

  const filters = useMemo<ShiftAnalysisFilterState>(
    () => ({
      factoryIds: parseList(searchParams.get("factory_ids")),
      plantIds: parseList(searchParams.get("plant_ids")),
      kpiIds: parseList(searchParams.get("kpi_ids")),
      shiftIds: parseList(searchParams.get("shift_ids")),
      severity: (searchParams.get("severity") as ShiftAnomalySeverity | null) || DEFAULTS.severity,
    }),
    [searchParams]
  );

  const setFilters = useCallback(
    (partial: Partial<ShiftAnalysisFilterState>) => {
      const next = { ...filters, ...partial };
      const params = new URLSearchParams();
      if (next.factoryIds.length) params.set("factory_ids", next.factoryIds.join(","));
      if (next.plantIds.length) params.set("plant_ids", next.plantIds.join(","));
      if (next.kpiIds.length) params.set("kpi_ids", next.kpiIds.join(","));
      if (next.shiftIds.length) params.set("shift_ids", next.shiftIds.join(","));
      if (next.severity) params.set("severity", next.severity);
      setSearchParams(params, { replace: true });
    },
    [filters, setSearchParams]
  );

  const clearFilters = useCallback(() => {
    setSearchParams(new URLSearchParams(), { replace: true });
  }, [setSearchParams]);

  const asQueryParams = useMemo(
    () => ({
      factory_ids: filters.factoryIds.join(",") || undefined,
      plant_ids: filters.plantIds.join(",") || undefined,
      kpi_ids: filters.kpiIds.join(",") || undefined,
      shift_ids: filters.shiftIds.join(",") || undefined,
      severity: filters.severity || undefined,
    }),
    [filters]
  );

  const activeFilterCount = useMemo(
    () =>
      filters.factoryIds.length +
      filters.plantIds.length +
      filters.kpiIds.length +
      filters.shiftIds.length +
      (filters.severity ? 1 : 0),
    [filters]
  );

  return { filters, setFilters, clearFilters, asQueryParams, activeFilterCount };
}
