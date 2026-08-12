import { Square } from "lucide-react";
import type { AnalysisImmediateAction, AnalysisMediumTermAction } from "../../api/types";

const PRIORITY_LABELS: Record<string, string> = { low: "Düşük", medium: "Orta", high: "Yüksek", critical: "Kritik" };
const PRIORITY_COLORS: Record<string, string> = { low: "#64748b", medium: "#1d4ed8", high: "#b45309", critical: "#b91c1c" };

function PriorityBadge({ priority }: { priority: string }) {
  const color = PRIORITY_COLORS[priority] ?? "#64748b";
  return (
    <span
      className="shrink-0 rounded px-1.5 py-0.5 text-[11px] font-semibold uppercase tracking-wide"
      style={{ background: `${color}14`, color, border: `1px solid ${color}33` }}
    >
      {PRIORITY_LABELS[priority] ?? priority}
    </span>
  );
}

export function RecommendedActions({
  immediateActions, mediumTermActions,
}: {
  immediateActions: AnalysisImmediateAction[];
  mediumTermActions: AnalysisMediumTermAction[];
}) {
  return (
    <div className="flex flex-col gap-4">
      <div>
        <h4 className="mb-1.5 text-xs font-semibold uppercase tracking-wide" style={{ color: "var(--text-secondary)" }}>Hızlı Aksiyonlar</h4>
        <ul className="flex flex-col gap-2">
          {immediateActions.map((act, i) => (
            <li key={i} className="flex items-start gap-2.5 rounded-md p-3 text-[13px]" style={{ border: "1px solid var(--border)" }}>
              <Square size={13} strokeWidth={2} className="mt-0.5 shrink-0" style={{ color: "var(--text-muted)" }} />
              <div className="flex-1">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p style={{ color: "var(--text-primary)" }}>{act.action}</p>
                  <PriorityBadge priority={act.priority} />
                </div>
                <p className="mt-1 text-xs" style={{ color: "var(--text-muted)" }}>
                  Sorumlu: {act.responsible_unit} · Önerilen süre: {act.timeframe} · Beklenen etki: {act.expected_impact}
                  {act.requires_approval && " · Yönetici onayı gerekir"}
                </p>
              </div>
            </li>
          ))}
        </ul>
      </div>

      <div>
        <h4 className="mb-1.5 text-xs font-semibold uppercase tracking-wide" style={{ color: "var(--text-secondary)" }}>Orta Vadeli İyileştirmeler</h4>
        <ul className="flex flex-col gap-2">
          {mediumTermActions.map((act, i) => (
            <li key={i} className="rounded-md p-3 text-[13px]" style={{ border: "1px solid var(--border)" }}>
              <p style={{ color: "var(--text-primary)" }}>{act.action}</p>
              <p className="mt-0.5 text-xs" style={{ color: "var(--text-muted)" }}>Sorumlu: {act.responsible_unit} · Beklenen etki: {act.expected_impact}</p>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
