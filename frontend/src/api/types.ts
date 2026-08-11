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
  plant_ids: string[];
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

export interface ForemanTrendRankingItem {
  foreman_id: string;
  employee_number: string;
  full_name: string;
  total_score: number;
  previous_score: number;
  delta: number;
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

export interface ForemanAssignmentItem {
  plant: { id: string; name: string };
  chief: { id: string; name: string };
}

export interface ForemanListItem {
  id: string;
  employee_number: string;
  full_name: string;
  is_active: boolean;
  assignments: ForemanAssignmentItem[];
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
  phone_number: string | null;
  email: string | null;
  assignments: ForemanAssignmentItem[];
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
  plants: { id: string; name: string }[];
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
  phone_number: string | null;
  email: string | null;
  plants: { id: string; name: string }[];
  factory: { id: string; code: string; name: string } | null;
  foreman_count: number;
  total_score: number;
  is_reliable: boolean;
  level: PerformanceLevel;
  company_rank: number | null;
  company_total: number;
  factory_rank: number | null;
  factory_total: number;
}

export interface ChiefForemanItem {
  id: string;
  employee_number: string | null;
  full_name: string | null;
  total_score: number;
  is_reliable: boolean;
  level: PerformanceLevel;
}

export interface ForemanKpiItem {
  kpi_id: string;
  code: string;
  name: string;
  description: string | null;
  unit: string;
  avg_target: number | null;
  avg_actual: number | null;
  avg_raw_score: number;
  avg_capped_score: number;
  weight: number;
  weighted_contribution_sum: number;
  record_count: number;
  calculation_version: number | null;
  calculation_period: { date_from: string; date_to: string };
  data_quality_status: string;
  source_system: string;
  agir_gitme?: {
    signed_value: number;
    absolute_value: number;
    direction: "OVERWEIGHT" | "UNDERWEIGHT" | "ON_TARGET";
    ratio_to_target: number | null;
  };
  inkita?: {
    included_total: number | null;
    included_components: string[];
    excluded_components: string[];
    note: string;
  };
  plana_uyum?: {
    avg_attainment_pct: number;
    planned_qty: number | null;
    actual_qty: number | null;
    kg_diff: number | null;
    signed_pct_deviation: number | null;
    direction: "ABOVE_PLAN" | "BELOW_PLAN" | "ON_PLAN";
  };
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
  plana_uyum?: {
    planned_qty: number | null;
    actual_qty: number | null;
    kg_diff: number | null;
    signed_pct_deviation: number | null;
    status: "ABOVE_PLAN" | "BELOW_PLAN" | "ON_PLAN";
    formula_version: number | null;
  };
}

export interface AssignmentHistoryItem {
  plant: string | null;
  chief: string | null;
  shift: string | null;
  start_date: string;
  end_date: string | null;
  is_active: boolean;
}

export interface MonthlyReportComparison {
  value: number;
  diff: number;
  diff_pct: number | null;
  status: "above" | "at" | "below";
  is_favorable: boolean;
}

export interface MonthlyReportKpiEntry {
  kpi_id: string;
  code: string;
  name: string;
  unit: string;
  weight: number;
  success_direction_higher: boolean;
  has_data: boolean;
  record_count: number;
  actual: number | null;
  score: number | null;
  level: PerformanceLevel | null;
  vs_personal_target: MonthlyReportComparison | null;
  vs_factory_average: MonthlyReportComparison | null;
}

export interface MonthlyReportNote {
  kpi_code: string;
  name: string;
  text: string;
  manager_prompt?: string;
}

export interface MonthlyReportPreviousMonthKpi {
  code: string;
  name: string;
  diff: number;
  is_improvement: boolean;
}

export interface MonthlyReportData {
  foreman: { id: string; employee_number: string; full_name: string; hire_date: string };
  period: { year: number; month: number; label: string; date_from: string; date_to: string };
  generated_at: string;
  org: { factory_name: string | null; plants: { id: string; name: string }[]; chief_name: string | null } | null;
  insufficient_data: boolean;
  insufficient_data_reason?: string;
  overall: {
    score: number;
    level: PerformanceLevel;
    kpi_count: { total: number; above_or_at_target: number; below_target: number; critical: number };
  } | null;
  summary_text?: string;
  closing_text?: string;
  kpis?: MonthlyReportKpiEntry[];
  strengths?: MonthlyReportNote[];
  improvements?: MonthlyReportNote[];
  critical_attention?: MonthlyReportNote[];
  congratulations?: { shown: boolean; text: string | null; kpi_codes: string[] };
  trend?: {
    weekly_points: { bucket: string; total_score: number; is_reliable: boolean }[];
    shape: "iyileşme" | "kötüleşme" | "stabil" | "dalgalı" | null;
    text: string | null;
  };
  previous_month?: {
    available: boolean;
    label?: string;
    overall_diff?: number;
    per_kpi?: MonthlyReportPreviousMonthKpi[];
  };
}

export interface MonthlyReportSummary {
  year: number;
  month: number;
  generated_at: string;
  overall_score: number | null;
  overall_level_name: string | null;
  is_reliable: boolean;
}

export interface MonthlyReportDetail extends MonthlyReportSummary {
  report_data: MonthlyReportData;
}

export interface MonthlyReportLatest extends Partial<MonthlyReportDetail> {
  available: boolean;
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

export interface KpiForemanValueItem {
  foreman_id: string;
  full_name: string | null;
  avg_actual: number;
  avg_target: number;
  avg_score: number;
  record_count: number;
  tier: "better" | "near" | "worse";
  level: PerformanceLevel | null;
}

export interface KpiAnalysis {
  kpi: { id: string; code: string; name: string; unit: string; decimal_places: number };
  company_avg_score: number;
  company_avg_target: number | null;
  company_avg_actual: number | null;
  best_plants: EntityRef[];
  worst_plants: EntityRef[];
  shift_comparison: { id: string; name: string; score: number }[];
  best_foremen: EntityRef[];
  worst_foremen: EntityRef[];
  foreman_values: KpiForemanValueItem[];
  trend: { date: string; score: number }[];
}


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

export type ContributionWorkType =
  | "smed" | "kaizen" | "problem_solving" | "cost_reduction" | "time_saving"
  | "quality_improvement" | "safety_improvement" | "energy_resource_saving"
  | "production_efficiency" | "digitalization" | "other";
export type ContributionStatus = "draft" | "published";
export type FinancialGainStatus = "yes" | "no" | "not_calculated";
export type ContributionCurrency = "TRY" | "USD" | "EUR";
export type GainPeriod = "one_time" | "monthly" | "yearly";
export type VerifyingDepartment =
  | "finance" | "production" | "maintenance" | "quality" | "safety" | "energy" | "hr" | "other";
export type ContributionTimeUnit = "second" | "minute" | "hour";
export type RepeatPeriod = "daily" | "weekly" | "monthly";
export type ImpactLevel = "low" | "medium" | "high";
export type OtherGainType =
  | "capacity_increase" | "downtime_reduction" | "gsf_reduction" | "scrap_reduction"
  | "slow_running_reduction" | "safety_risk_reduction" | "energy_reduction"
  | "labor_saving" | "quality_defect_reduction" | "other";
export type HighlightedGainMode = "auto" | "manual";

export type ContributionRole = "lead" | "contributor";

export interface ContributionForemanRef {
  id: string;
  name: string;
  employee_number: string;
  role: ContributionRole;
}

export interface ContributionPlantRef {
  id: string;
  name: string;
  code: string;
  factory_id: string;
  factory_name: string;
  factory_code: string;
}

export interface ContributionGain {
  id: string;
  gain_type: OtherGainType;
  gain_type_label: string;
  gain_type_other_note: string | null;
  previous_value: number | null;
  next_value: number | null;
  change_amount: number | null;
  change_percent: number | null;
  is_improvement: boolean | null;
  unit: string | null;
  measurement_period: string | null;
  description: string | null;
}

export interface ContributionGainInput {
  gain_type: OtherGainType;
  gain_type_other_note?: string;
  previous_value?: number;
  next_value?: number;
  unit?: string;
  measurement_period?: string;
  description?: string;
}

export interface ContributionHighlightedGain {
  source: string;
  label: string;
  value: number;
  unit: string | null;
  is_verified: boolean;
}

export interface ContributionBeforeAfter {
  metric_label: string;
  before: string;
  after: string;
  change: string;
  is_improvement: boolean;
}

export interface ContributionWorkItem {
  id: string;
  title: string;
  status: ContributionStatus;
  work_type: ContributionWorkType | null;
  work_type_label: string | null;
  work_type_other_note: string | null;
  summary: string | null;
  detailed_description: string | null;
  problem_description: string | null;
  solution_description: string | null;
  result_description: string | null;
  foremen: ContributionForemanRef[];
  plant: ContributionPlantRef | null;
  work_date: string | null;
  work_date_end: string | null;
  impact_level: ImpactLevel | null;
  created_by: string | null;
  created_by_user_id: string;
  published_at: string | null;
  is_standardized: boolean;
  is_applicable_other_plants: boolean;
  is_permanent_solution: boolean;
  work_instruction_updated: boolean;
  financial_gain_status: FinancialGainStatus;
  estimated_amount: number | null;
  verified_amount: number | null;
  currency: ContributionCurrency | null;
  gain_period: GainPeriod | null;
  calculation_method: string | null;
  is_gain_verified: boolean;
  verified_by_department: VerifyingDepartment | null;
  verified_by_department_other_note: string | null;
  verification_date: string | null;
  verification_note: string | null;
  previous_duration: number | null;
  new_duration: number | null;
  duration_unit: ContributionTimeUnit | null;
  per_occurrence_saving: number | null;
  repeat_period: RepeatPeriod | null;
  repeat_count: number | null;
  monthly_total_saving_minutes: number | null;
  gains: ContributionGain[];
  highlighted_gain_mode: HighlightedGainMode;
  highlighted_gain_ref: string | null;
  highlighted_gain: ContributionHighlightedGain | null;
  before_after: ContributionBeforeAfter | null;
  badges: string[];
  created_at: string;
  updated_at: string;
}

export interface ContributionWorkCreatePayload {
  title: string;
  status?: ContributionStatus;
  work_type?: ContributionWorkType;
  work_type_other_note?: string;
  summary?: string;
  detailed_description?: string;
  problem_description?: string;
  solution_description?: string;
  result_description?: string;
  foreman_ids?: string[];
  plant_id?: string;
  work_date?: string;
  work_date_end?: string;
  impact_level?: ImpactLevel;
  is_standardized?: boolean;
  is_applicable_other_plants?: boolean;
  is_permanent_solution?: boolean;
  work_instruction_updated?: boolean;
  financial_gain_status?: FinancialGainStatus;
  estimated_amount?: number;
  verified_amount?: number;
  currency?: ContributionCurrency;
  gain_period?: GainPeriod;
  calculation_method?: string;
  is_gain_verified?: boolean;
  verified_by_department?: VerifyingDepartment;
  verified_by_department_other_note?: string;
  verification_date?: string;
  verification_note?: string;
  previous_duration?: number;
  new_duration?: number;
  duration_unit?: ContributionTimeUnit;
  repeat_period?: RepeatPeriod;
  repeat_count?: number;
  per_occurrence_saving?: number;
  monthly_total_saving_minutes?: number;
  gains?: ContributionGainInput[];
  highlighted_gain_mode?: HighlightedGainMode;
  highlighted_gain_ref?: string;
}

export type ContributionWorkUpdatePayload = Partial<ContributionWorkCreatePayload>;

export interface ForemanContributionSummary {
  total_contributions: number;
  smed_count: number;
  led_contributions: number;
  verified_financial_gain: Record<string, number>;
  estimated_financial_gain: Record<string, number>;
  total_time_saving_minutes: number;
  last_contribution_date: string | null;
}

export interface ContributionSummary {
  total_works: number;
  added_this_month: number;
  total_estimated_gain: number;
  total_verified_gain: number;
  total_monthly_time_saving_minutes: number;
  by_plant: { name: string; count: number }[];
  by_work_type: { label: string; count: number }[];
  top_foremen: { id: string; name: string; count: number }[];
  applicable_other_plants_count: number;
  standardized_ratio: number;
}


export type AnomalySeverity = "low" | "medium" | "high" | "critical";
export type AnomalyStatus = "new" | "in_review" | "action_pending" | "resolved" | "closed";
export type AnomalyAnalysisStatus =
  | "not_analyzed" | "analyzing" | "queued" | "planning" | "collecting_data" | "generating_analysis"
  | "completed" | "completed_with_warnings" | "failed" | "timed_out" | "cancelled";
export type AnalysisMode = "single_context" | "tool_calling";

export interface AnomalyListItem {
  id: string;
  code: string;
  title: string;
  factory_code: string | null;
  factory_name: string | null;
  plant_id: string;
  plant_name: string | null;
  shift_id: string | null;
  shift_name: string | null;
  kpi_id: string;
  kpi_code: string | null;
  kpi_name: string | null;
  anomaly_type: string;
  anomaly_type_label: string;
  detected_at: string;
  period_start: string;
  period_end: string;
  deviation_percent: number;
  ml_confidence: number;
  severity: AnomalySeverity;
  severity_label: string;
  status: AnomalyStatus;
  status_label: string;
  analysis_status: AnomalyAnalysisStatus;
  analysis_status_label: string;
}

export interface AnomalyEvidenceItem {
  type: string;
  label: string;
  value: number;
  unit: string;
}

export interface AnomalyRelatedSignal {
  kpi: string;
  kpi_code: string;
  value: number;
  change_percent: number;
  direction: "increase" | "decrease";
}

export interface AnomalyDailyPoint {
  date: string;
  value: number;
}

export interface AnomalyKpiDefinition {
  name: string | null;
  description: string | null;
  desired_direction: "high" | "low" | null;
  warning_threshold: number | null;
  critical_threshold: number | null;
}

export type AnalysisConfidence = "low" | "medium" | "high";
export type AnalysisPriority = "low" | "medium" | "high" | "critical";
export type AnalysisRiskLevel = "low" | "medium" | "high" | "critical";

export interface AnalysisSourceRef {
  tool_call_id: string;
  tool_name: string;
}

export interface AnalysisVerifiedFinding {
  finding_id?: string;
  finding: string;
  evidence: string;
  source_refs: AnalysisSourceRef[];
}

export interface AnalysisPossibleCause {
  cause: string;
  confidence: AnalysisConfidence;
  supporting_evidence: string[];
  contradicting_evidence: string[];
  source_refs: AnalysisSourceRef[];
  verification_required: string;
}

export interface AnalysisRecommendedInvestigation {
  step: string;
  responsible_unit: string;
  priority: AnalysisPriority;
  expected_output: string;
}

export interface AnalysisImmediateAction {
  action: string;
  responsible_unit: string;
  priority: AnalysisPriority;
  timeframe: string;
  expected_impact: string;
  requires_approval: boolean;
}

export interface AnalysisMediumTermAction {
  action: string;
  responsible_unit: string;
  expected_impact: string;
}

export interface AnalysisToolUsedRef {
  tool_name: string;
  tool_call_id: string;
  purpose: string;
}

export interface AnalysisDataScope {
  start_date: string;
  end_date: string;
  record_count: number;
  data_quality_status: string;
}

export interface AnalysisResult {
  executive_summary: string;
  verified_findings: AnalysisVerifiedFinding[];
  possible_causes: AnalysisPossibleCause[];
  recommended_investigations: AnalysisRecommendedInvestigation[];
  immediate_actions: AnalysisImmediateAction[];
  medium_term_actions: AnalysisMediumTermAction[];
  missing_information: string[];
  risk_level: AnalysisRiskLevel;
  analysis_confidence: number;
  requires_human_review: boolean;
  tools_used: AnalysisToolUsedRef[];
  data_scope: AnalysisDataScope | null;
  analysis_limitations: string[];
  disclaimer: string;
}

export interface AnomalyAnalysisRecord {
  id: string;
  code: string;
  mode: AnalysisMode;
  status: AnomalyAnalysisStatus;
  status_label: string;
  is_demo: boolean;
  model: string;
  result: AnalysisResult | null;
  investigation_plan: string[] | null;
  tool_call_count: number;
  error_code: string | null;
  error_message: string | null;
  started_at: string;
  completed_at: string | null;
}

export interface AnomalyToolCallItem {
  id: string;
  code: string;
  step_number: number;
  tool_name: string;
  tool_label: string;
  arguments: Record<string, unknown>;
  status: "success" | "error" | "timeout";
  result: Record<string, unknown> | null;
  record_count: number | null;
  error_code: string | null;
  error_message: string | null;
  started_at: string;
  completed_at: string | null;
  duration_ms: number | null;
}

export interface AnomalyDetail extends AnomalyListItem {
  description: string;
  observed_value: number;
  expected_value: number;
  unit: string;
  affected_days: number | null;
  total_days: number | null;
  comparison: Record<string, number>;
  related_signals: AnomalyRelatedSignal[];
  evidence: AnomalyEvidenceItem[];
  foreman_codes: string[];
  data_quality_status: string;
  data_quality_warnings: string[];
  daily_history: AnomalyDailyPoint[];
  kpi_definition: AnomalyKpiDefinition;
  latest_analysis: AnomalyAnalysisRecord | null;
  analysis_history: AnomalyAnalysisRecord[];
}

export interface AnomalySummary {
  total_active: number;
  critical_count: number;
  high_count: number;
  pending_analysis_count: number;
  opened_last_7_days: number;
  resolved_count: number;
}


export type ShiftAnomalySeverity = "medium" | "high";

export interface ShiftAnalysisPeriod {
  month_start: string;
  month_end: string;
  label: string;
}

export interface ShiftAnalysisSummary {
  period: ShiftAnalysisPeriod;
  total_anomalies: number;
  high_count: number;
  medium_count: number;
  top_plant: { id: string; name: string; count: number } | null;
  top_kpi: { id: string; name: string; count: number } | null;
  max_pct_diff: number | null;
}

export interface ShiftAnomalyForemanStat {
  id: string;
  name: string;
  employee_number: string;
  avg_actual: number;
  record_count: number;
  week_count: number;
}

export interface ShiftAnomalyCard {
  id: string;
  plant_id: string;
  plant_name: string;
  plant_sequence: number;
  factory_id: string;
  factory_code: string;
  shift_id: string;
  shift_name: string;
  kpi_id: string;
  kpi_code: string;
  kpi_name: string;
  kpi_unit: string;
  success_direction_higher: boolean;
  severity: ShiftAnomalySeverity;
  title: string;
  better: ShiftAnomalyForemanStat;
  worse: ShiftAnomalyForemanStat;
  abs_diff: number;
  pct_diff: number;
  compared_weeks: number;
  period: ShiftAnalysisPeriod;
}

export interface ShiftAnalysisCardsResponse {
  items: ShiftAnomalyCard[];
  summary: ShiftAnalysisSummary;
}

export interface ShiftAnomalyWeeklyPoint {
  week_index: number;
  week_label: string;
  foreman_id: string;
  avg_actual: number;
  day_count: number;
}

export interface ShiftAnomalyCrossKpiSignal {
  kpi_id: string;
  kpi_code: string;
  kpi_name: string;
  pct_diff: number;
  severity: ShiftAnomalySeverity;
  same_foreman_better: boolean;
}

export interface ShiftAnomalyDetail extends ShiftAnomalyCard {
  weekly_breakdown: ShiftAnomalyWeeklyPoint[];
  cross_kpi_signals: ShiftAnomalyCrossKpiSignal[];
  pattern_commentary: string;
  is_recurring_pattern: boolean;
}


export type HeatmapLevel = "no_data" | "normal" | "attention" | "significant" | "critical";

export interface HeatmapShiftPoint {
  avg_actual: number;
  record_count: number;
}

export interface HeatmapCell {
  plant_id: string;
  kpi_id: string;
  level: HeatmapLevel;
  v1: HeatmapShiftPoint | null;
  v2: HeatmapShiftPoint | null;
  abs_diff: number | null;
  pct_diff: number | null;
  better_shift_id: string | null;
}

export interface HeatmapPlantRef {
  id: string;
  name: string;
  sequence_number: number;
  factory_code: string;
}

export interface HeatmapKpiRef {
  id: string;
  code: string;
  name: string;
  unit: string;
}

export interface ShiftHeatmapSummary {
  anomaly_plant_count: number;
  critical_cell_count: number;
  priority_plant_count: number;
  top_kpi: { id: string; name: string; count: number } | null;
}

export interface ShiftHeatmapResponse {
  period: ShiftAnalysisPeriod;
  shifts: { id: string; code: string; name: string }[];
  plants: HeatmapPlantRef[];
  kpis: HeatmapKpiRef[];
  cells: HeatmapCell[];
  summary: ShiftHeatmapSummary;
}


export interface ForemanShiftMatrixCell {
  avg_actual: number;
  avg_target: number;
  score: number;
  record_count: number;
  deviation_pct: number | null;
  level: PerformanceLevel;
}

export interface ForemanShiftMatrixRow {
  foreman_id: string;
  full_name: string;
  employee_number: string;
  cells: Record<string, ForemanShiftMatrixCell | null>;
}

export interface ForemanShiftMatrixResponse {
  kpi: { id: string; code: string; name: string; unit: string; success_direction_higher: boolean };
  reference_target: number;
  shifts: { id: string; code: string; name: string }[];
  rows: ForemanShiftMatrixRow[];
  insight: string;
}
