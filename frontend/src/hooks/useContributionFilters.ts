import { useCallback, useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import type { ContributionWorkType, FinancialGainStatus, ImpactLevel } from "../api/types";

export interface ContributionFilterState {
  dateFrom: string;
  dateTo: string;
  plantIds: string[];
  factoryIds: string[];
  foremanIds: string[];
  workType: ContributionWorkType | "";
  status: "draft" | "published" | "";
  impactLevel: ImpactLevel | "";
  financialGainStatus: FinancialGainStatus | "";
}

const DEFAULTS: ContributionFilterState = {
  dateFrom: "",
  dateTo: "",
  plantIds: [],
  factoryIds: [],
  foremanIds: [],
  workType: "",
  status: "",
  impactLevel: "",
  financialGainStatus: "",
};

function parseList(value: string | null): string[] {
  return value ? value.split(",").filter(Boolean) : [];
}

export function useContributionFilters() {
  const [searchParams, setSearchParams] = useSearchParams();

  const filters = useMemo<ContributionFilterState>(
    () => ({
      dateFrom: searchParams.get("date_from") || DEFAULTS.dateFrom,
      dateTo: searchParams.get("date_to") || DEFAULTS.dateTo,
      plantIds: parseList(searchParams.get("plant_ids")),
      factoryIds: parseList(searchParams.get("factory_ids")),
      foremanIds: parseList(searchParams.get("foreman_ids")),
      workType: (searchParams.get("work_type") as ContributionWorkType | null) || "",
      status: (searchParams.get("status") as "draft" | "published" | null) || "",
      impactLevel: (searchParams.get("impact_level") as ImpactLevel | null) || "",
      financialGainStatus: (searchParams.get("financial_gain_status") as FinancialGainStatus | null) || "",
    }),
    [searchParams]
  );

  const setFilters = useCallback(
    (partial: Partial<ContributionFilterState>) => {
      const next = { ...filters, ...partial };
      const params = new URLSearchParams();
      if (next.dateFrom) params.set("date_from", next.dateFrom);
      if (next.dateTo) params.set("date_to", next.dateTo);
      if (next.plantIds.length) params.set("plant_ids", next.plantIds.join(","));
      if (next.factoryIds.length) params.set("factory_ids", next.factoryIds.join(","));
      if (next.foremanIds.length) params.set("foreman_ids", next.foremanIds.join(","));
      if (next.workType) params.set("work_type", next.workType);
      if (next.status) params.set("status", next.status);
      if (next.impactLevel) params.set("impact_level", next.impactLevel);
      if (next.financialGainStatus) params.set("financial_gain_status", next.financialGainStatus);
      setSearchParams(params, { replace: true });
    },
    [filters, setSearchParams]
  );

  const clearFilters = useCallback(() => {
    setSearchParams(new URLSearchParams(), { replace: true });
  }, [setSearchParams]);

  const asQueryParams = useMemo(
    () => ({
      date_from: filters.dateFrom || undefined,
      date_to: filters.dateTo || undefined,
      plant_ids: filters.plantIds.join(",") || undefined,
      factory_ids: filters.factoryIds.join(",") || undefined,
      foreman_ids: filters.foremanIds.join(",") || undefined,
      work_type: filters.workType || undefined,
      status: filters.status || undefined,
      impact_level: filters.impactLevel || undefined,
      financial_gain_status: filters.financialGainStatus || undefined,
    }),
    [filters]
  );

  return { filters, setFilters, clearFilters, asQueryParams };
}
