import enum


class CalculationType(str, enum.Enum):
    HIGHER_IS_BETTER = "higher_is_better"
    LOWER_IS_BETTER = "lower_is_better"
    RANGE_TARGET = "range_target"
    DIRECT_SCORE = "direct_score"
    PROPORTIONAL_PENALTY = "proportional_penalty"
    CUSTOM_FORMULA = "custom_formula"


class AggregationMethod(str, enum.Enum):
    SUM = "sum"
    AVERAGE = "average"
    WEIGHTED_AVERAGE = "weighted_average"
    MIN = "min"
    MAX = "max"
    LAST_VALUE = "last_value"
    RATIO_RECOMPUTE = "ratio_recompute"


class TargetScopeType(str, enum.Enum):
    COMPANY = "company"
    PLANT = "plant"
    CHIEF = "chief"
    FOREMAN = "foreman"


class DataQualityStatus(str, enum.Enum):
    COMPLETE = "complete"
    MISSING = "missing"
    INVALID = "invalid"
    SUSPICIOUS = "suspicious"
    DUPLICATE = "duplicate"
    NEEDS_SOURCE_CORRECTION = "needs_source_correction"
    PENDING_RESYNC = "pending_resync"
    REPROCESSED = "reprocessed"


class IntegrationStatus(str, enum.Enum):
    RUNNING = "running"
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"


class SourceSystem(str, enum.Enum):
    SYNTHETIC = "SYNTHETIC"
    SAP = "SAP"


class SuccessDirection(str, enum.Enum):
    HIGHER_IS_BETTER = "higher_is_better"
    LOWER_IS_BETTER = "lower_is_better"


class ActionPlanStatus(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    DELAYED = "delayed"


class ActionPlanPriority(str, enum.Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class ReportType(str, enum.Enum):
    COMPANY_SUMMARY = "company_summary"
    PLANT_COMPARISON = "plant_comparison"
    SHIFT_COMPARISON = "shift_comparison"
    FOREMAN_PERFORMANCE = "foreman_performance"
    KPI_ANALYSIS = "kpi_analysis"
    CRITICAL_PERFORMANCE = "critical_performance"
    MISSING_DATA = "missing_data"


class ReportFormat(str, enum.Enum):
    CSV = "csv"
    XLSX = "xlsx"
    PDF = "pdf"


class ReportStatus(str, enum.Enum):
    COMPLETED = "completed"
    FAILED = "failed"
