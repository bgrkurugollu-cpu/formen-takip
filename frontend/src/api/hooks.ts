import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "./client";
import type {
  AnalysisMode,
  AnomalyDetail,
  AnomalyListItem,
  AnomalyStatus,
  AnomalySummary,
  AnomalyToolCallItem,
  AssignmentHistoryItem,
  CalculationDetail,
  ChiefDetail,
  ChiefForemanItem,
  ChiefListItem,
  ContributionSummary,
  ContributionWorkCreatePayload,
  ContributionWorkItem,
  ContributionWorkUpdatePayload,
  DashboardSummary,
  DistributionItem,
  FilterOptionsResponse,
  ForemanContributionSummary,
  ForemanDetail,
  ForemanKpiItem,
  ForemanListItem,
  KpiAnalysis,
  KpiListItem,
  KpiSummaryItem,
  MonthlyReportDetail,
  MonthlyReportLatest,
  MonthlyReportSummary,
  PagedResponse,
  PlantListItem,
  PlantRankingItem,
  ReportExportMeta,
  ReportFormat,
  ReportType,
  ForemanShiftMatrixResponse,
  ShiftAnalysisCardsResponse,
  ShiftAnomalyDetail,
  ShiftComparisonItem,
  ShiftHeatmapResponse,
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

export function useForemanTrendRanking(params: Params, direction: "improving" | "declining", limit: number) {
  return useQuery({
    queryKey: ["dashboard", "foreman-trend-ranking", params, direction, limit],
    queryFn: async () =>
      (await apiClient.get<{ items: import("./types").ForemanTrendRankingItem[] }>("/dashboard/foreman-trend-ranking", { params: { ...params, direction, limit } })).data,
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

export function useForemenByIds(ids: string[]) {
  return useQuery({
    enabled: ids.length > 0,
    queryKey: ["foremen", "by-ids", ids],
    queryFn: async () =>
      (await apiClient.get<PagedResponse<ForemanListItem>>("/foremen", { params: { ids: ids.join(","), page_size: Math.max(ids.length, 1) } })).data,
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

export function useForemanMonthlyReports(foremanId: string | undefined) {
  return useQuery({
    enabled: !!foremanId,
    queryKey: ["foremen", foremanId, "monthly-reports"],
    queryFn: async () =>
      (await apiClient.get<{ items: MonthlyReportSummary[] }>(`/foremen/${foremanId}/monthly-reports`)).data,
  });
}

export function useForemanMonthlyReportLatest(foremanId: string | undefined) {
  return useQuery({
    enabled: !!foremanId,
    queryKey: ["foremen", foremanId, "monthly-reports", "latest"],
    queryFn: async () =>
      (await apiClient.get<MonthlyReportLatest>(`/foremen/${foremanId}/monthly-reports/latest`)).data,
  });
}

export function useForemanMonthlyReport(foremanId: string | undefined, year: number | undefined, month: number | undefined) {
  return useQuery({
    enabled: !!foremanId && !!year && !!month,
    queryKey: ["foremen", foremanId, "monthly-reports", year, month],
    queryFn: async () =>
      (await apiClient.get<MonthlyReportDetail>(`/foremen/${foremanId}/monthly-reports/${year}/${month}`)).data,
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

// --- Vardiya Analizi ---

// `/cards` tek istekte hem kart listesini hem özeti döner — `summary` ayrı bir endpoint/istek
// olarak tutulsaydı, backend aynı ay/filtre için aylık ham kayıt çekme + hücre gruplama +
// karşılaştırma işini iki ayrı istekte iki kez yapardı (bkz. shift_analysis.py::get_cards).
export function useShiftAnalysisCards(params: Params) {
  return useQuery({
    queryKey: ["shift-analysis", "cards", params],
    queryFn: async () => (await apiClient.get<ShiftAnalysisCardsResponse>("/shift-analysis/cards", { params })).data,
  });
}

export function useShiftAnalysisDetail(params: { plant_id?: string; shift_id?: string; kpi_id?: string; month?: string }) {
  return useQuery({
    queryKey: ["shift-analysis", "detail", params],
    queryFn: async () => (await apiClient.get<ShiftAnomalyDetail>("/shift-analysis/detail", { params })).data,
    enabled: !!(params.plant_id && params.shift_id && params.kpi_id),
  });
}

export function useShiftHeatmap(params: Params) {
  return useQuery({
    queryKey: ["shift-analysis", "heatmap", params],
    queryFn: async () => (await apiClient.get<ShiftHeatmapResponse>("/shift-analysis/heatmap", { params })).data,
  });
}

export function usePlantForemanShiftMatrix(plantId: string | undefined, kpiId: string | undefined, params: Params) {
  return useQuery({
    enabled: !!plantId && !!kpiId,
    queryKey: ["plants", plantId, "foreman-shift-matrix", kpiId, params],
    queryFn: async () =>
      (
        await apiClient.get<ForemanShiftMatrixResponse>(`/plants/${plantId}/foreman-shift-matrix`, {
          params: { ...params, kpi_id: kpiId },
        })
      ).data,
  });
}
