import type { AnomalyDetail, AnomalyInvestigation } from "../../api/types";
import { EmptyState } from "../StateViews";
import { formatDateRangeTR } from "../../lib/dateFormat";
import { formatSignedPct, performanceDirection, PERFORMANCE_COLORS } from "../../lib/kpiDirection";

interface Row {
  label: string;
  before: string;
  after: string;
  changeLabel: string;
  color: string;
}

export function BaselineComparisonCard({ anomaly, investigation }: { anomaly: AnomalyDetail; investigation: AnomalyInvestigation }) {
  const a = anomaly;
  const baseline = investigation.baseline_comparison;

  if (!baseline.available) {
    return <EmptyState message={baseline.reason ?? "Karşılaştırma için yeterli geçmiş veri bulunmuyor."} />;
  }

  const rows: Row[] = [];

  const kpiDir = performanceDirection(a.kpi_definition.desired_direction, (baseline.abs_change ?? 0) > 0);
  rows.push({
    label: a.kpi_name ?? "KPI",
    before: `%${baseline.baseline_avg?.toFixed(2)}`,
    after: `%${baseline.current_avg?.toFixed(2)}`,
    changeLabel: baseline.pct_change != null ? formatSignedPct(baseline.pct_change) : "-",
    color: PERFORMANCE_COLORS[kpiDir],
  });

  const downtime = investigation.downtime_breakdown;
  if (downtime) {
    const days = downtime.period_days || 1;
    const beforePerDay = downtime.previous_period_total_minutes / days;
    const afterPerDay = downtime.total_downtime_minutes / days;
    const pct = beforePerDay !== 0 ? ((afterPerDay - beforePerDay) / beforePerDay) * 100 : null;
    const dir = performanceDirection("low", afterPerDay - beforePerDay > 0);
    rows.push({
      label: "Duruş Süresi (dk/gün)",
      before: `${beforePerDay.toFixed(0)} dk/gün`,
      after: `${afterPerDay.toFixed(0)} dk/gün`,
      changeLabel: pct != null ? formatSignedPct(pct) : "-",
      color: PERFORMANCE_COLORS[dir],
    });
  }

  for (const rel of investigation.related_kpi_changes) {
    const dir = rel.performance_direction ?? "unknown";
    rows.push({
      label: rel.kpi,
      before: `%${rel.baseline_value.toFixed(2)}`,
      after: `%${rel.current_value.toFixed(2)}`,
      changeLabel: formatSignedPct(rel.change_percent),
      color: PERFORMANCE_COLORS[dir],
    });
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-2 text-xs" style={{ color: "var(--text-muted)" }}>
        <span>Normal Dönem: {baseline.baseline_period && formatDateRangeTR(baseline.baseline_period.start, baseline.baseline_period.end)}</span>
        <span>→</span>
        <span>Tespit Dönemi: {baseline.current_period && formatDateRangeTR(baseline.current_period.start, baseline.current_period.end)}</span>
      </div>
      <div className="flex flex-col gap-2">
        {rows.map((row) => (
          <div key={row.label} className="grid grid-cols-[1fr_auto_auto_auto] items-center gap-3 rounded-md p-2.5 text-[13px]" style={{ border: "1px solid var(--border)" }}>
            <span style={{ color: "var(--text-primary)" }}>{row.label}</span>
            <span className="tabular-nums" style={{ color: "var(--text-secondary)" }}>{row.before}</span>
            <span style={{ color: "var(--text-muted)" }}>→</span>
            <span className="tabular-nums font-medium" style={{ color: row.color }}>{row.after} ({row.changeLabel})</span>
          </div>
        ))}
      </div>
    </div>
  );
}
