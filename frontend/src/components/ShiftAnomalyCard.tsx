import { AlertTriangle, ArrowRight, Factory, Gauge, TrendingUp } from "lucide-react";
import type { ShiftAnomalyCard as ShiftAnomalyCardData } from "../api/types";
import { ShiftComparisonMiniChart } from "./charts/ShiftComparisonMiniChart";

const SEVERITY_CONFIG: Record<ShiftAnomalyCardData["severity"], { label: string; color: string }> = {
  high: { label: "Yüksek", color: "#b91c1c" },
  medium: { label: "Orta", color: "#b45309" },
};

function decimalPlacesFor(unit: string): number {
  return unit === "%" ? 1 : 2;
}

export function ShiftAnomalySeverityBadge({ severity }: { severity: ShiftAnomalyCardData["severity"] }) {
  const c = SEVERITY_CONFIG[severity];
  return (
    <span
      className="inline-flex items-center gap-1 rounded px-2 py-0.5 text-xs font-medium"
      style={{ background: `${c.color}14`, color: c.color, border: `1px solid ${c.color}33` }}
    >
      <AlertTriangle size={12} strokeWidth={2} />
      {c.label} Anomali
    </span>
  );
}

export function ShiftAnomalyCard({
  card, onViewDetail,
}: {
  card: ShiftAnomalyCardData;
  onViewDetail: (card: ShiftAnomalyCardData) => void;
}) {
  const decimalPlaces = decimalPlacesFor(card.kpi_unit);

  return (
    <div
      className="flex flex-col gap-3 rounded-lg p-4"
      style={{
        background: "var(--surface)", border: "1px solid var(--border)",
        borderTop: `2px solid ${SEVERITY_CONFIG[card.severity].color}`,
      }}
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-1.5 text-[13px] font-medium" style={{ color: "var(--text-secondary)" }}>
          <Factory size={13} strokeWidth={2} />
          <span>{card.factory_code}</span>
          <span>·</span>
          <span style={{ color: "var(--text-primary)" }}>{card.plant_name}</span>
          <span>·</span>
          <span>{card.shift_name}</span>
          <span>·</span>
          <span className="inline-flex items-center gap-1">
            <Gauge size={13} strokeWidth={2} />
            {card.kpi_name}
          </span>
        </div>
        <ShiftAnomalySeverityBadge severity={card.severity} />
      </div>

      <ShiftComparisonMiniChart better={card.better} worse={card.worse} unit={card.kpi_unit} decimalPlaces={decimalPlaces} />

      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        <div className="rounded-md p-2" style={{ background: "var(--page-bg)", border: "1px solid var(--border)" }}>
          <p className="text-[10px] font-medium uppercase tracking-wide" style={{ color: "var(--text-muted)" }}>{card.worse.name}</p>
          <p className="mt-0.5 text-sm font-semibold tabular-nums" style={{ color: "#dc2626" }}>
            {card.worse.avg_actual.toFixed(decimalPlaces)}
          </p>
        </div>
        <div className="rounded-md p-2" style={{ background: "var(--page-bg)", border: "1px solid var(--border)" }}>
          <p className="text-[10px] font-medium uppercase tracking-wide" style={{ color: "var(--text-muted)" }}>{card.better.name}</p>
          <p className="mt-0.5 text-sm font-semibold tabular-nums" style={{ color: "#16a34a" }}>
            {card.better.avg_actual.toFixed(decimalPlaces)}
          </p>
        </div>
        <div className="rounded-md p-2" style={{ background: "var(--page-bg)", border: "1px solid var(--border)" }}>
          <p className="text-[10px] font-medium uppercase tracking-wide" style={{ color: "var(--text-muted)" }}>Mutlak Fark</p>
          <p className="mt-0.5 text-sm font-semibold tabular-nums" style={{ color: "var(--text-primary)" }}>
            {card.abs_diff.toFixed(decimalPlaces)}
          </p>
        </div>
        <div className="rounded-md p-2" style={{ background: "var(--page-bg)", border: "1px solid var(--border)" }}>
          <p className="text-[10px] font-medium uppercase tracking-wide" style={{ color: "var(--text-muted)" }}>Yüzdesel Fark</p>
          <p className="mt-0.5 flex items-center gap-1 text-sm font-semibold tabular-nums" style={{ color: SEVERITY_CONFIG[card.severity].color }}>
            <TrendingUp size={13} strokeWidth={2.25} />
            %{card.pct_diff.toFixed(1)}
          </p>
        </div>
      </div>

      <p className="text-[11px]" style={{ color: "var(--text-muted)" }}>
        {card.period.label} · Karşılaştırılan hafta sayısı: {card.compared_weeks}
      </p>

      <button
        onClick={() => onViewDetail(card)}
        className="group mt-1 inline-flex items-center justify-center gap-1.5 rounded-md py-2 text-[13px] font-medium transition-colors hover:bg-[var(--page-bg)]"
        style={{ border: "1px solid var(--border)", color: "var(--accent)" }}
      >
        Detayı Gör
        <ArrowRight size={14} strokeWidth={2} className="transition-transform duration-150 group-hover:translate-x-0.5" />
      </button>
    </div>
  );
}
