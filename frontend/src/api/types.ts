export interface PerformanceLevel {
  name: string;
  description: string;
  color: string;
  icon: string;
}

export interface FactoryOption {
  id: string;
  code: string;
  name: string;
  location: string;
}

export interface PlantOption {
  id: string;
  code: string;
  name: string;
  sequence_number: number;
  factory_id: string;
}

export interface ChiefOption {
  id: string;
  employee_number: string;
  name: string;
  plant_id: string;
}

export interface FilterOption {
  id: string;
  code?: string;
  name: string;
  sequence?: number;
  unit?: string;
  weight?: number;
}

export interface FilterOptionsResponse {
  factories: FactoryOption[];
  plants: PlantOption[];
  chiefs: ChiefOption[];
  shifts: FilterOption[];
  kpis: FilterOption[];
}

export interface EntityRef {
  id: string;
  name: string | null;
  code?: string | null;
  score?: number;
}

export interface DashboardSummary {
  total_plants: number;
  active_plants: number;
  total_active_foremen: number;
  avg_company_score: number;
  foremen_above_target: number;
  foremen_below_target: number;
  foremen_critical: number;
  foremen_excellent: number;
  best_plant: EntityRef | null;
  worst_plant: EntityRef | null;
  best_shift: EntityRef | null;
  worst_shift: EntityRef | null;
  best_foreman: (EntityRef & { employee_number?: string }) | null;
  weakest_kpi: { id: string; name: string; avg_score: number } | null;
  plants_with_missing_data: number;
  last_sync_at: string | null;
  data_source: string;
}

export interface TrendPoint {
  date: string;
  total_score: number;
  is_reliable: boolean;
}

export interface KpiSummaryItem {
  kpi_id: string;
  code: string;
  name: string;
  unit: string;
  avg_score: number;
  avg_target: number | null;
  avg_actual: number | null;
  record_count: number;
}

export interface PlantRankingItem {
  plant_id: string;
  code: string;
  name: string;
  total_score: number;
  is_reliable: boolean;
  level: PerformanceLevel;
}

export interface ShiftComparisonItem {
  shift_id: string;
  code: string;
  name: string;
  total_score: number;
  record_count: number;
  level: PerformanceLevel;
}

export interface ForemanRankingItem {
  foreman_id: string;
  employee_number: string;
  full_name: string;
  total_score: number;
  is_reliable: boolean;
  level: PerformanceLevel;
}

export interface DistributionItem extends PerformanceLevel {
  count: number;
}

export interface PlantListItem {
  id: string;
  code: string;
  name: string;
  sequence_number: number;
  factory: { id: string; code: string; name: string } | null;
  is_active: boolean;
  total_score: number;
  level: PerformanceLevel;
  active_foreman_count: number;
  record_count: number;
}

export interface PlantDetail {
  id: string;
  code: string;
  name: string;
  sequence_number: number;
  factory: { id: string; code: string; name: string } | null;
  description: string | null;
  is_active: boolean;
  sap_plant_code: string | null;
}

export interface PlantChiefItem {
  id: string;
  employee_number: string;
  full_name: string;
  foreman_count: number;
  total_score: number;
  level: PerformanceLevel;
}

export interface PagedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface ForemanListItem {
  id: string;
  employee_number: string;
  full_name: string;
  is_active: boolean;
  plant: { id: string; name: string } | null;
  chief: { id: string; name: string } | null;
  shift: { id: string; name: string } | null;
  total_score: number;
  is_reliable: boolean;
  level: PerformanceLevel;
}

export interface ForemanDetail {
  id: string;
  employee_number: string;
  full_name: string;
  hire_date: string;
  is_active: boolean;
  plant: { id: string; name: string } | null;
  chief: { id: string; name: string } | null;
  shift: { id: string; name: string } | null;
  total_score: number;
  is_reliable: boolean;
  level: PerformanceLevel;
  company_rank: number | null;
  company_total: number;
  plant_rank: number | null;
  plant_total: number;
}

export interface ChiefListItem {
  id: string;
  employee_number: string;
  full_name: string;
  is_active: boolean;
  plant: { id: string; name: string } | null;
  factory: { id: string; code: string; name: string } | null;
  foreman_count: number;
  total_score: number;
  is_reliable: boolean;
  level: PerformanceLevel;
}

export interface ChiefDetail {
  id: string;
  employee_number: string;
  full_name: string;
  hire_date: string;
  is_active: boolean;
  plant: { id: string; name: string } | null;
  factory: { id: string; code: string; name: string } | null;
  foreman_count: number;
  total_score: number;
  is_reliable: boolean;
  level: PerformanceLevel;
  company_rank: number | null;
  company_total: number;
  plant_rank: number | null;
  plant_total: number;
}

export interface ChiefForemanItem {
  id: string;
  employee_number: string | null;
  full_name: string | null;
  shift: { id: string; name: string } | null;
  total_score: number;
  is_reliable: boolean;
  level: PerformanceLevel;
}

export interface ForemanKpiItem {
  kpi_id: string;
  code: string;
  name: string;
  unit: string;
  avg_target: number | null;
  avg_actual: number | null;
  avg_raw_score: number;
  avg_capped_score: number;
  weight: number;
  weighted_contribution_sum: number;
  record_count: number;
}

export interface CalculationDetail {
  performance_date: string;
  target_value: number | null;
  actual_value: number | null;
  unit: string;
  calculation_type: string | null;
  calculation_rule_parameters: Record<string, number> | null;
  calculation_version: number;
  raw_score: number;
  capped_score: number;
  min_score: number | null;
  max_score: number | null;
  kpi_weight: number;
  weighted_contribution: number;
  data_source: string;
  source_record_id: string;
}

export interface AssignmentHistoryItem {
  plant: string | null;
  chief: string | null;
  shift: string | null;
  start_date: string;
  end_date: string | null;
  is_active: boolean;
}

export interface KpiListItem {
  id: string;
  code: string;
  name: string;
  description: string;
  unit: string;
  calculation_type: string;
  weight: number;
  default_target_value: number;
  is_critical: boolean;
}

export interface KpiAnalysis {
  kpi: { id: string; code: string; name: string; unit: string };
  company_avg_score: number;
  company_avg_target: number | null;
  company_avg_actual: number | null;
  best_plants: EntityRef[];
  worst_plants: EntityRef[];
  shift_comparison: { id: string; name: string; score: number }[];
  best_foremen: EntityRef[];
  worst_foremen: EntityRef[];
  trend: { date: string; score: number }[];
}


export interface DataQualityIssue {
  id: string;
  issue_type: string;
  description: string;
  detected_at: string;
  status: string;
  performance_date: string | null;
  source_system: string | null;
  source_record_id: string | null;
  plant_name: string | null;
  foreman_name: string | null;
  kpi_name: string | null;
}

export interface DataQualitySummary {
  by_type: { issue_type: string; count: number }[];
  top_plants: { plant_id: string; plant_name: string; issue_count: number }[];
}

export interface IntegrationRunItem {
  id: string;
  source_system: string;
  started_at: string;
  finished_at: string | null;
  status: string;
  processed_count: number;
  success_count: number;
  error_count: number;
  skipped_count: number;
  duration_seconds: number | null;
}

export interface AuditLogEntry {
  id: string;
  action: string;
  entity: string | null;
  old_value: string | null;
  new_value: string | null;
  user_name: string | null;
  ip_address: string | null;
  success: boolean;
  error_message: string | null;
  created_at: string;
}

export type ActionPlanStatus = "open" | "in_progress" | "on_hold" | "completed" | "cancelled" | "delayed";
export type ActionPlanPriority = "low" | "normal" | "high" | "critical";

export interface ActionPlanRef {
  id: string;
  name: string;
}

export interface ActionPlanItem {
  id: string;
  title: string;
  description: string | null;
  plant: ActionPlanRef | null;
  chief: ActionPlanRef | null;
  shift: ActionPlanRef | null;
  foreman: ActionPlanRef | null;
  kpi: ActionPlanRef | null;
  owner: string;
  created_by: string | null;
  priority: ActionPlanPriority;
  status: ActionPlanStatus;
  start_date: string;
  target_end_date: string;
  actual_end_date: string | null;
  completion_percentage: number;
  outcome_notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface ActionPlanCreatePayload {
  title: string;
  description?: string;
  plant_id?: string;
  chief_id?: string;
  shift_id?: string;
  foreman_id?: string;
  kpi_id?: string;
  owner: string;
  priority: ActionPlanPriority;
  status: ActionPlanStatus;
  start_date: string;
  target_end_date: string;
  completion_percentage: number;
  outcome_notes?: string;
}

export type ActionPlanUpdatePayload = Partial<
  Pick<
    ActionPlanCreatePayload,
    "title" | "description" | "owner" | "priority" | "status" | "target_end_date" | "completion_percentage" | "outcome_notes"
  >
> & { actual_end_date?: string };

export type ReportType =
  | "company_summary" | "plant_comparison" | "shift_comparison" | "foreman_performance"
  | "kpi_analysis" | "critical_performance" | "missing_data";
export type ReportFormat = "csv" | "xlsx" | "pdf";

export interface ReportExportMeta {
  id: string;
  file_name: string;
  report_type: string;
  format: string;
  row_count: number;
  status?: string;
  requested_by?: string | null;
  created_at: string;
}
