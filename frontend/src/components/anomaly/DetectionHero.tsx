import { Factory } from "lucide-react";
import type { AnomalyDetail, AnomalyStatus } from "../../api/types";
import { AnalysisStatusBadge, SeverityBadge, StatusBadge } from "../AnomalyBadges";
import { fieldClass, fieldStyle } from "../../lib/formStyles";
import { formatDateRangeTR, formatDateTR } from "../../lib/dateFormat";
import { formatSignedPct, formatSignedPoints } from "../../lib/kpiDirection";

const STATUS_OPTIONS: { value: AnomalyStatus; label: string }[] = [
  { value: "new", label: "Yeni" },
  { value: "in_review", label: "İnceleniyor" },
  { value: "action_pending", label: "Aksiyon Bekliyor" },
  { value: "resolved", label: "Çözüldü" },
  { value: "closed", label: "Kapatıldı" },
];

function HeroStat({ label, value, unit, emphasis }: { label: string; value: string; unit?: string; emphasis?: boolean }) {
  return (
    <div
      className="rounded-lg p-3.5"
      style={{
        background: "var(--page-bg)",
        border: emphasis ? "1px solid var(--accent)" : "1px solid var(--border)",
      }}
    >
      <p className="text-[11px] font-semibold uppercase tracking-wide" style={{ color: "var(--text-muted)" }}>{label}</p>
      <p
        className="mt-1 text-2xl font-bold tabular-nums"
        style={{ color: emphasis ? "var(--accent)" : "var(--text-primary)" }}
      >
        {value}
        {unit && <span className="ml-1 text-xs font-normal" style={{ color: "var(--text-muted)" }}>{unit}</span>}
      </p>
    </div>
  );
}

export function DetectionHero({
  anomaly, statusPending, onStatusChange,
}: {
  anomaly: AnomalyDetail;
  statusPending: boolean;
  onStatusChange: (status: AnomalyStatus) => void;
}) {
  const a = anomaly;
  const aboveBelow = a.deviation_percent >= 0 ? "ÜZERİNDE" : "ALTINDA";
  const headline = `${(a.kpi_name ?? "KPI").toUpperCase()} BEKLENENİN ${aboveBelow}`;
  const summarySentence = `${a.shift_name ? `${a.shift_name} genelinde ` : ""}${a.kpi_name}, beklenen seviyenin ${formatSignedPct(
    a.deviation_percent
  )} ${a.deviation_percent >= 0 ? "üzerinde" : "altında"}.`;
  const absDiff = a.observed_value - a.expected_value;

  return (
    <div className="rounded-lg p-6" style={{ background: "var(--surface)", border: "1px solid var(--border)", borderTop: "3px solid var(--accent)" }}>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <SeverityBadge severity={a.severity} />
          <StatusBadge status={a.status} />
          <AnalysisStatusBadge status={a.analysis_status} />
        </div>
        <div className="flex items-center gap-2">
          <label className="text-xs font-medium" style={{ color: "var(--text-secondary)" }}>Tespit durumu:</label>
          <select
            className={fieldClass}
            style={{ ...fieldStyle, width: 170 }}
            value={a.status}
            disabled={statusPending}
            onChange={(e) => onStatusChange(e.target.value as AnomalyStatus)}
          >
            {STATUS_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </div>
      </div>

      <div className="mt-4 flex items-center gap-1.5 text-xs font-medium" style={{ color: "var(--text-secondary)" }}>
        <Factory size={13} strokeWidth={2} />
        {a.factory_code} → {a.plant_name}
        {a.shift_name && <span> · {a.shift_name}</span>}
      </div>

      <h1 className="mt-1.5 text-xl font-bold tracking-tight" style={{ color: "var(--text-primary)" }}>{headline}</h1>
      <p className="mt-1 text-[13px]" style={{ color: "var(--text-secondary)" }}>{summarySentence}</p>

      <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-5">
        <HeroStat label="Gerçekleşen" value={`%${a.observed_value.toFixed(2)}`} emphasis />
        <HeroStat label="Beklenen" value={`%${a.expected_value.toFixed(2)}`} />
        <HeroStat label="Mutlak Fark" value={formatSignedPoints(absDiff)} />
        <HeroStat label="Göreceli Sapma" value={formatSignedPct(a.deviation_percent)} />
        <HeroStat
          label="Görülme Sıklığı"
          value={a.affected_days != null && a.total_days != null ? `${a.affected_days} / ${a.total_days}` : "-"}
          unit="gün"
        />
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs" style={{ color: "var(--text-muted)" }}>
        <span>Dönem: {formatDateRangeTR(a.period_start, a.period_end)}</span>
        <span>Tespit tarihi: {formatDateTR(a.detected_at)}</span>
        <span>Tespit ID: {a.code}</span>
      </div>
    </div>
  );
}
