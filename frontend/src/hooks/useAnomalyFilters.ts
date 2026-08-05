import { useCallback, useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import type { AnomalyAnalysisStatus, AnomalySeverity, AnomalyStatus } from "../api/types";

export interface AnomalyFilterState {
  dateFrom: string;
  dateTo: string;
  factory: string;
  plantIds: string[];
  shiftIds: string[];
  kpiIds: string[];
  severity: AnomalySeverity | "";
  status: AnomalyStatus | "";
  analysisStatus: AnomalyAnalysisStatus | "";
}

const DEFAULTS: AnomalyFilterState = {
  dateFrom: "",
  dateTo: "",
  factory: "",
  plantIds: [],
  shiftIds: [],
  kpiIds: [],
  severity: "",
  status: "",
  analysisStatus: "",
};

function parseList(value: string | null): string[] {
  return value ? value.split(",").filter(Boolean) : [];
}

export function useAnomalyFilters() {
  const [searchParams, setSearchParams] = useSearchParams();

  const filters = useMemo<AnomalyFilterState>(
    () => ({
      dateFrom: searchParams.get("date_from") || DEFAULTS.dateFrom,
      dateTo: searchParams.get("date_to") || DEFAULTS.dateTo,
      factory: searchParams.get("factory") || DEFAULTS.factory,
      plantIds: parseList(searchParams.get("plant_ids")),
      shiftIds: parseList(searchParams.get("shift_ids")),
      kpiIds: parseList(searchParams.get("kpi_ids")),
      severity: (searchParams.get("severity") as AnomalySeverity | null) || "",
      status: (searchParams.get("status") as AnomalyStatus | null) || "",
      analysisStatus: (searchParams.get("analysis_status") as AnomalyAnalysisStatus | null) || "",
    }),
    [searchParams]
  );

  const setFilters = useCallback(
    (partial: Partial<AnomalyFilterState>) => {
      const next = { ...filters, ...partial };
      const params = new URLSearchParams();
      if (next.dateFrom) params.set("date_from", next.dateFrom);
      if (next.dateTo) params.set("date_to", next.dateTo);
      if (next.factory) params.set("factory", next.factory);
      if (next.plantIds.length) params.set("plant_ids", next.plantIds.join(","));
      if (next.shiftIds.length) params.set("shift_ids", next.shiftIds.join(","));
      if (next.kpiIds.length) params.set("kpi_ids", next.kpiIds.join(","));
      if (next.severity) params.set("severity", next.severity);
      if (next.status) params.set("status", next.status);
      if (next.analysisStatus) params.set("analysis_status", next.analysisStatus);
      setSearchParams(params, { replace: true });
    },
    [filters, setSearchParams]
  );

  const clearFilters = useCallback(() => {
    setSearchParams(new URLSearchParams(), { replace: true });
  }, [setSearchParams]);

  const asQueryParams = useMemo(
    () => ({
      start_date: filters.dateFrom || undefined,
      end_date: filters.dateTo || undefined,
      factory: filters.factory || undefined,
      plant_id: filters.plantIds[0],
      shift_id: filters.shiftIds[0],
      kpi_id: filters.kpiIds[0],
      severity: filters.severity || undefined,
      status: filters.status || undefined,
      analysis_status: filters.analysisStatus || undefined,
    }),
    [filters]
  );

  const activeFilterCount = useMemo(
    () =>
      [
        filters.dateFrom, filters.dateTo, filters.factory, filters.severity, filters.status, filters.analysisStatus,
      ].filter(Boolean).length + filters.plantIds.length + filters.shiftIds.length + filters.kpiIds.length,
    [filters]
  );

  return { filters, setFilters, clearFilters, asQueryParams, activeFilterCount };
}
