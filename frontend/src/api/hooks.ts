import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "./client";
import type {
  ActionPlanCreatePayload,
  ActionPlanItem,
  ActionPlanUpdatePayload,
  AnalysisMode,
  AnomalyDetail,
  AnomalyListItem,
  AnomalyStatus,
  AnomalySummary,
  AnomalyToolCallItem,
  AssignmentHistoryItem,
  AuditLogEntry,
  CalculationDetail,
  ChiefDetail,
  ChiefForemanItem,
  ChiefListItem,
  ContributionSummary,
  ContributionWorkCreatePayload,
  ContributionWorkItem,
  ContributionWorkUpdatePayload,
  DashboardSummary,
  DataQualityIssue,
  DataQualitySummary,
  DistributionItem,
  FilterOptionsResponse,
  ForemanContributionSummary,
  ForemanDetail,
  ForemanKpiItem,
  ForemanListItem,
  IntegrationRunItem,
  KpiAnalysis,
  KpiListItem,
  KpiSummaryItem,
  PagedResponse,
  PlantListItem,
  PlantRankingItem,
  ReportExportMeta,
  ReportFormat,
  ReportType,
  ShiftComparisonItem,
  TrendPoint,
} from "./types";

type Params = Record<string, string | number | undefined>;

export function useFilterOptions(plantIds?: string, factoryIds?: string) {
  return useQuery({
    queryKey: ["meta", "filters", plantIds, factoryIds],
    queryFn: async () => {
      const { data } = await apiClient.get<FilterOptionsResponse>("/meta/filters", {
        params: { plant_ids: plantIds, factory_ids: factoryIds },
      });
      return data;
    },
  });
}

export function useDashboardSummary(params: Params) {
  return useQuery({
    queryKey: ["dashboard", "summary", params],
    queryFn: async () => (await apiClient.get<DashboardSummary>("/dashboard/summary", { params })).data,
  });
}

export function useDashboardTrend(params: Params, granularity: string) {
  return useQuery({
    queryKey: ["dashboard", "trend", params, granularity],
    queryFn: async () =>
      (await apiClient.get<{ granularity: string; points: TrendPoint[] }>("/dashboard/trend", { params: { ...params, granularity } })).data,
  });
}

export function useKpiSummary(params: Params) {
  return useQuery({
    queryKey: ["dashboard", "kpi-summary", params],
    queryFn: async () => (await apiClient.get<{ items: KpiSummaryItem[] }>("/dashboard/kpi-summary", { params })).data,
  });
}

export function usePlantRanking(params: Params, order: "asc" | "desc", limit: number) {
  return useQuery({
    queryKey: ["dashboard", "plant-ranking", params, order, limit],
    queryFn: async () =>
      (await apiClient.get<{ items: PlantRankingItem[] }>("/dashboard/plant-ranking", { params: { ...params, order, limit } })).data,
  });
}

export function useShiftComparison(params: Params) {
  return useQuery({
    queryKey: ["dashboard", "shift-comparison", params],
    queryFn: async () => (await apiClient.get<{ items: ShiftComparisonItem[] }>("/dashboard/shift-comparison", { params })).data,
  });
}

export function useForemanRanking(params: Params, order: "asc" | "desc", limit: number) {
  return useQuery({
    queryKey: ["dashboard", "foreman-ranking", params, order, limit],
    queryFn: async () =>
      (await apiClient.get<{ items: import("./types").ForemanRankingItem[] }>("/dashboard/foreman-ranking", { params: { ...params, order, limit } })).data,
  });
}

export function usePerformanceDistribution(params: Params) {
  return useQuery({
    queryKey: ["dashboard", "distribution", params],
    queryFn: async () => (await apiClient.get<{ items: DistributionItem[] }>("/dashboard/performance-distribution", { params })).data,
  });
}

export function usePlants(params: Params) {
  return useQuery({
    queryKey: ["plants", params],
    queryFn: async () => (await apiClient.get<PagedResponse<PlantListItem>>("/plants", { params })).data,
  });
}

export function usePlantDetail(plantId: string | undefined) {
  return useQuery({
    enabled: !!plantId,
    queryKey: ["plants", plantId],
    queryFn: async () => (await apiClient.get(`/plants/${plantId}`)).data,
  });
}

export function usePlantSummary(plantId: string | undefined, params: Params) {
  return useQuery({
    enabled: !!plantId,
    queryKey: ["plants", plantId, "summary", params],
    queryFn: async () => (await apiClient.get(`/plants/${plantId}/summary`, { params })).data,
  });
}

export function usePlantKpis(plantId: string | undefined, params: Params) {
  return useQuery({
    enabled: !!plantId,
    queryKey: ["plants", plantId, "kpis", params],
    queryFn: async () => (await apiClient.get<{ items: KpiSummaryItem[] }>(`/plants/${plantId}/kpis`, { params })).data,
  });
}

export function usePlantShifts(plantId: string | undefined, params: Params) {
  return useQuery({
    enabled: !!plantId,
    queryKey: ["plants", plantId, "shifts", params],
    queryFn: async () => (await apiClient.get<{ items: ShiftComparisonItem[] }>(`/plants/${plantId}/shifts`, { params })).data,
  });
}

export function usePlantForemen(plantId: string | undefined, params: Params) {
  return useQuery({
    enabled: !!plantId,
    queryKey: ["plants", plantId, "foremen", params],
    queryFn: async () => (await apiClient.get<PagedResponse<import("./types").ForemanRankingItem>>(`/plants/${plantId}/foremen`, { params })).data,
  });
}

export function usePlantChiefs(plantId: string | undefined, params: Params) {
  return useQuery({
    enabled: !!plantId,
    queryKey: ["plants", plantId, "chiefs", params],
    queryFn: async () => (await apiClient.get<{ items: import("./types").PlantChiefItem[] }>(`/plants/${plantId}/chiefs`, { params })).data,
  });
}

export function useForemen(params: Params) {
  return useQuery({
    queryKey: ["foremen", params],
    queryFn: async () => (await apiClient.get<PagedResponse<ForemanListItem>>("/foremen", { params })).data,
  });
}

export function useForemanDetail(foremanId: string | undefined, params: Params) {
  return useQuery({
    enabled: !!foremanId,
    queryKey: ["foremen", foremanId, params],
    queryFn: async () => (await apiClient.get<ForemanDetail>(`/foremen/${foremanId}`, { params })).data,
  });
}

export function useForemanKpis(foremanId: string | undefined, params: Params) {
  return useQuery({
    enabled: !!foremanId,
    queryKey: ["foremen", foremanId, "kpis", params],
    queryFn: async () => (await apiClient.get<{ items: ForemanKpiItem[] }>(`/foremen/${foremanId}/kpis`, { params })).data,
  });
}

export function useForemanCalculationDetail(foremanId: string | undefined, kpiId: string | undefined) {
  return useQuery({
    enabled: !!foremanId && !!kpiId,
    queryKey: ["foremen", foremanId, "kpis", kpiId, "calculation-detail"],
    queryFn: async () => (await apiClient.get<CalculationDetail>(`/foremen/${foremanId}/kpis/${kpiId}/calculation-detail`)).data,
  });
}

export function useForemanTrend(foremanId: string | undefined, params: Params, granularity: string) {
  return useQuery({
    enabled: !!foremanId,
    queryKey: ["foremen", foremanId, "trend", params, granularity],
    queryFn: async () =>
      (await apiClient.get<{ granularity: string; points: TrendPoint[] }>(`/foremen/${foremanId}/trend`, { params: { ...params, granularity } })).data,
  });
}

export function useForemanAssignmentHistory(foremanId: string | undefined) {
  return useQuery({
    enabled: !!foremanId,
    queryKey: ["foremen", foremanId, "assignment-history"],
    queryFn: async () => (await apiClient.get<{ items: AssignmentHistoryItem[] }>(`/foremen/${foremanId}/assignment-history`)).data,
  });
}

export function useForemanContributionSummary(foremanId: string | undefined) {
  return useQuery({
    enabled: !!foremanId,
    queryKey: ["foremen", foremanId, "contribution-summary"],
    queryFn: async () =>
      (await apiClient.get<ForemanContributionSummary>(`/foremen/${foremanId}/contribution-summary`)).data,
  });
}

export function useForemanRecentContributions(foremanId: string | undefined, enabled: boolean) {
  return useQuery({
    enabled: !!foremanId && enabled,
    queryKey: ["foremen", foremanId, "contributions", "recent"],
    queryFn: async () =>
      (
        await apiClient.get<PagedResponse<ContributionWorkItem>>("/contribution-works", {
          params: { foreman_ids: foremanId, status: "published", page: 1, page_size: 3 },
        })
      ).data,
  });
}

export function useChiefs(params: Params) {
  return useQuery({
    queryKey: ["chiefs", params],
    queryFn: async () => (await apiClient.get<PagedResponse<ChiefListItem>>("/chiefs", { params })).data,
  });
}

export function useChiefDetail(chiefId: string | undefined, params: Params) {
  return useQuery({
    enabled: !!chiefId,
    queryKey: ["chiefs", chiefId, params],
    queryFn: async () => (await apiClient.get<ChiefDetail>(`/chiefs/${chiefId}`, { params })).data,
  });
}

export function useChiefForemen(chiefId: string | undefined, params: Params) {
  return useQuery({
    enabled: !!chiefId,
    queryKey: ["chiefs", chiefId, "foremen", params],
    queryFn: async () => (await apiClient.get<{ items: ChiefForemanItem[] }>(`/chiefs/${chiefId}/foremen`, { params })).data,
  });
}

export function useChiefKpis(chiefId: string | undefined, params: Params) {
  return useQuery({
    enabled: !!chiefId,
    queryKey: ["chiefs", chiefId, "kpis", params],
    queryFn: async () => (await apiClient.get<{ items: ForemanKpiItem[] }>(`/chiefs/${chiefId}/kpis`, { params })).data,
  });
}

export function useChiefTrend(chiefId: string | undefined, params: Params, granularity: string) {
  return useQuery({
    enabled: !!chiefId,
    queryKey: ["chiefs", chiefId, "trend", params, granularity],
    queryFn: async () =>
      (await apiClient.get<{ granularity: string; points: TrendPoint[] }>(`/chiefs/${chiefId}/trend`, { params: { ...params, granularity } })).data,
  });
}

export function useKpis() {
  return useQuery({
    queryKey: ["kpis"],
    queryFn: async () => (await apiClient.get<{ items: KpiListItem[] }>("/kpis")).data,
  });
}

export function useKpiAnalysis(kpiId: string | undefined, params: Params) {
  return useQuery({
    enabled: !!kpiId,
    queryKey: ["kpis", kpiId, "analysis", params],
    queryFn: async () => (await apiClient.get<KpiAnalysis>(`/kpis/${kpiId}/analysis`, { params })).data,
  });
}


export function useDataQualityIssues(params: Params) {
  return useQuery({
    queryKey: ["data-quality", "issues", params],
    queryFn: async () => (await apiClient.get<PagedResponse<DataQualityIssue>>("/data-quality/issues", { params })).data,
  });
}

export function useDataQualitySummary() {
  return useQuery({
    queryKey: ["data-quality", "summary"],
    queryFn: async () => (await apiClient.get<DataQualitySummary>("/data-quality/summary")).data,
  });
}

export function useIntegrationRuns(params: Params) {
  return useQuery({
    queryKey: ["integration", "runs", params],
    queryFn: async () => (await apiClient.get<PagedResponse<IntegrationRunItem>>("/integration/runs", { params })).data,
  });
}

export function useTriggerResync() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { date_from: string; date_to: string; plant_codes?: string[] }) =>
      (await apiClient.post<IntegrationRunItem>("/integration/resync", payload)).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["integration", "runs"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}

export function useAuditLogs(params: Params) {
  return useQuery({
    queryKey: ["audit-logs", params],
    queryFn: async () => (await apiClient.get<PagedResponse<AuditLogEntry>>("/audit-logs", { params })).data,
  });
}

export function useActionPlans(params: Params) {
  return useQuery({
    queryKey: ["action-plans", params],
    queryFn: async () => (await apiClient.get<PagedResponse<ActionPlanItem>>("/action-plans", { params })).data,
  });
}

export function useCreateActionPlan() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: ActionPlanCreatePayload) =>
      (await apiClient.post<ActionPlanItem>("/action-plans", payload)).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["action-plans"] });
    },
  });
}

export function useUpdateActionPlan() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, payload }: { id: string; payload: ActionPlanUpdatePayload }) =>
      (await apiClient.patch<ActionPlanItem>(`/action-plans/${id}`, payload)).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["action-plans"] });
    },
  });
}

export function useReportHistory(params: Params) {
  return useQuery({
    queryKey: ["reports", params],
    queryFn: async () => (await apiClient.get<PagedResponse<ReportExportMeta>>("/reports", { params })).data,
  });
}

export function useGenerateReport() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      report_type: ReportType; format: ReportFormat;
      date_from?: string; date_to?: string;
      plant_ids?: string[]; factory_ids?: string[]; chief_ids?: string[]; shift_ids?: string[]; kpi_ids?: string[];
    }) => (await apiClient.post<ReportExportMeta>("/reports/generate", payload)).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["reports"] });
    },
  });
}

export function downloadReportUrl(reportId: string): string {
  return `/api/v1/reports/${reportId}/download`;
}

export function useContributionWorks(params: Params) {
  return useQuery({
    queryKey: ["contribution-works", params],
    queryFn: async () => (await apiClient.get<PagedResponse<ContributionWorkItem>>("/contribution-works", { params })).data,
  });
}

export function useContributionWork(id: string | undefined) {
  return useQuery({
    queryKey: ["contribution-works", id],
    queryFn: async () => (await apiClient.get<ContributionWorkItem>(`/contribution-works/${id}`)).data,
    enabled: !!id,
  });
}

export function useCreateContributionWork() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: ContributionWorkCreatePayload) =>
      (await apiClient.post<ContributionWorkItem>("/contribution-works", payload)).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["contribution-works"] });
    },
  });
}

export function useUpdateContributionWork() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, payload }: { id: string; payload: ContributionWorkUpdatePayload }) =>
      (await apiClient.patch<ContributionWorkItem>(`/contribution-works/${id}`, payload)).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["contribution-works"] });
    },
  });
}

export function useDeleteContributionWork() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await apiClient.delete(`/contribution-works/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["contribution-works"] });
    },
  });
}

export function useContributionSummary(params: Params = {}) {
  return useQuery({
    queryKey: ["contribution-works", "summary", params],
    queryFn: async () => (await apiClient.get<ContributionSummary>("/contribution-works/summary", { params })).data,
  });
}

// --- Tespitler (Anomalies) ---

export function useAnomalies(params: Params) {
  return useQuery({
    queryKey: ["anomalies", params],
    queryFn: async () => (await apiClient.get<PagedResponse<AnomalyListItem>>("/anomalies", { params })).data,
  });
}

export function useAnomalySummary() {
  return useQuery({
    queryKey: ["anomalies", "summary"],
    queryFn: async () => (await apiClient.get<AnomalySummary>("/anomalies/summary")).data,
  });
}

export function useAnomaly(id: string | undefined) {
  return useQuery({
    queryKey: ["anomalies", id],
    queryFn: async () => (await apiClient.get<AnomalyDetail>(`/anomalies/${id}`)).data,
    enabled: !!id,
  });
}

export interface AnalyzeAnomalyPayload {
  id: string;
  mode?: AnalysisMode;
  force_refresh?: boolean;
}

export function useAnalyzeAnomaly() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, ...body }: AnalyzeAnomalyPayload) =>
      (await apiClient.post<AnomalyDetail>(`/anomalies/${id}/analyze`, body)).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["anomalies"] });
    },
  });
}

export function useReanalyzeAnomaly() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, ...body }: AnalyzeAnomalyPayload) =>
      (await apiClient.post<AnomalyDetail>(`/anomalies/${id}/reanalyze`, body)).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["anomalies"] });
    },
  });
}

export function useUpdateAnomalyStatus() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, status }: { id: string; status: AnomalyStatus }) =>
      (await apiClient.patch<AnomalyDetail>(`/anomalies/${id}/status`, { status })).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["anomalies"] });
    },
  });
}

export function useAnalysisToolCalls(analysisId: string | undefined) {
  return useQuery({
    queryKey: ["analyses", analysisId, "tool-calls"],
    queryFn: async () =>
      (await apiClient.get<{ items: AnomalyToolCallItem[]; total: number }>(`/analyses/${analysisId}/tool-calls`)).data,
    enabled: !!analysisId,
  });
}
