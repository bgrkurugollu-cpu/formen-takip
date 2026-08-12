import { CalendarClock, History, Repeat, TrendingUp } from "lucide-react";
import type { AnomalyDetail, AnomalyInvestigation } from "../../api/types";
import { formatSignedPct } from "../../lib/kpiDirection";

type ThresholdStatus = "critical" | "warning" | "normal" | "unknown";

function thresholdStatus(a: AnomalyDetail): ThresholdStatus {
  const { desired_direction, critical_threshold, warning_threshold } = a.kpi_definition;
  if (desired_direction == null || critical_threshold == null || warning_threshold == null) return "unknown";
  const observed = a.observed_value;
  if (desired_direction === "low") {
    if (observed >= critical_threshold) return "critical";
    if (observed >= warning_threshold) return "warning";
    return "normal";
  }
  if (observed <= critical_threshold) return "critical";
  if (observed <= warning_threshold) return "warning";
  return "normal";
}

const THRESHOLD_TEXT: Record<ThresholdStatus, string> = {
  critical: "Kritik eşik aşıldı",
  warning: "Uyarı eşiği aşıldı",
  normal: "Eşiklerin içinde",
  unknown: "Bu kriter için eşik verisi mevcut değil.",
};

function shiftDeviationNote(a: AnomalyDetail): string {
  if (!a.shift_id || !a.shift_name) return "Tespit belirli bir vardiyaya özgü değil.";
  const shiftEntries = Object.entries(a.comparison).filter(([key]) => /_average$/.test(key) && key !== "plant_average" && key !== "factory_average");
  if (shiftEntries.length < 2) return "Vardiya karşılaştırma verisi mevcut değil.";
  const values = shiftEntries.map(([, v]) => Number(v));
  const spread = Math.max(...values) - Math.min(...values);
  const plantAvg = a.comparison.plant_average;
  if (plantAvg == null || spread === 0) return "Vardiyalar arasında belirgin bir fark tespit edilmedi.";
  const higherIsBetter = a.kpi_definition.desired_direction === "high";
  const isWorstShift = higherIsBetter ? a.observed_value === Math.min(...values) : a.observed_value === Math.max(...values);
  return isWorstShift
    ? `${a.shift_name} diğer vardiyalara göre belirgin şekilde daha kötü.`
    : "Bu vardiya diğerlerine göre öne çıkmıyor; sapma vardiyalar geneline yayılmış olabilir.";
}

function ReasonCard({ icon, title, value, note }: { icon: React.ReactNode; title: string; value: string; note: string }) {
  return (
    <div className="rounded-lg p-3.5" style={{ background: "var(--page-bg)", border: "1px solid var(--border)" }}>
      <div className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide" style={{ color: "var(--text-muted)" }}>
        {icon}
        {title}
      </div>
      <p className="mt-1.5 text-lg font-bold tabular-nums" style={{ color: "var(--text-primary)" }}>{value}</p>
      <p className="mt-0.5 text-xs" style={{ color: "var(--text-secondary)" }}>{note}</p>
    </div>
  );
}

export function DetectionReasonCards({ anomaly, investigation }: { anomaly: AnomalyDetail; investigation?: AnomalyInvestigation }) {
  const a = anomaly;
  const status = thresholdStatus(a);
  const persistenceRatio = a.affected_days != null && a.total_days ? a.affected_days / a.total_days : null;

  const baseline = investigation?.baseline_comparison;
  let historicalNote = "Hesaplanıyor...";
  let historicalValue = "-";
  if (investigation) {
    if (baseline?.available && baseline.pct_change != null) {
      historicalValue = formatSignedPct(baseline.pct_change);
      historicalNote = baseline.direction === "worsened"
        ? "Önceki döneme göre kötüleşme gözlendi."
        : baseline.direction === "improved"
        ? "Önceki döneme göre iyileşme gözlendi."
        : "Önceki döneme göre belirgin bir değişim yok.";
    } else {
      historicalValue = "-";
      historicalNote = baseline?.reason ?? "Bu kriter için açıklama verisi mevcut değil.";
    }
  }

  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
      <ReasonCard
        icon={<TrendingUp size={13} strokeWidth={2} />}
        title="Sapma Büyüklüğü"
        value={formatSignedPct(a.deviation_percent)}
        note={THRESHOLD_TEXT[status]}
      />
      <ReasonCard
        icon={<Repeat size={13} strokeWidth={2} />}
        title="Süreklilik"
        value={a.affected_days != null && a.total_days != null ? `${a.affected_days} / ${a.total_days} gün` : "-"}
        note={
          persistenceRatio == null
            ? "Bu kriter için açıklama verisi mevcut değil."
            : persistenceRatio >= 0.6
            ? "Tek günlük bir rastlantı değil, dönem boyunca tekrarlanmış."
            : persistenceRatio <= 0.2
            ? "Sınırlı sayıda günde gözlenmiş."
            : "Dönemin bir bölümünde gözlenmiş."
        }
      />
      <ReasonCard
        icon={<CalendarClock size={13} strokeWidth={2} />}
        title="Vardiya Farkı"
        value={a.shift_name ?? "Vardiyaya özgü değil"}
        note={shiftDeviationNote(a)}
      />
      <ReasonCard
        icon={<History size={13} strokeWidth={2} />}
        title="Tarihsel Sapma"
        value={historicalValue}
        note={historicalNote}
      />
    </div>
  );
}
