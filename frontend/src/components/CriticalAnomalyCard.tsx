import { useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { useAnomalies, useAnomaly, useForemen } from "../api/hooks";
import { SeverityBadge, SEVERITY_CONFIG } from "./AnomalyBadges";
import type { AnomalyListItem, AnomalySeverity, AnomalyStatus } from "../api/types";

const SEVERITY_RANK: Record<AnomalySeverity, number> = { critical: 4, high: 3, medium: 2, low: 1 };
const OPEN_STATUSES: ReadonlySet<AnomalyStatus> = new Set(["new", "in_review", "action_pending"]);

function pickMostCritical(items: AnomalyListItem[]): AnomalyListItem | null {
  const open = items.filter((a) => OPEN_STATUSES.has(a.status));
  if (open.length === 0) return null;
  return [...open].sort((a, b) => {
    const bySeverity = SEVERITY_RANK[b.severity] - SEVERITY_RANK[a.severity];
    if (bySeverity !== 0) return bySeverity;
    return Math.abs(b.deviation_percent) - Math.abs(a.deviation_percent);
  })[0];
}

function ForemanLabel({ code }: { code: string }) {
  const result = useForemen({ search: code, page_size: 1 });
  return <>{result.data?.items[0]?.full_name ?? code}</>;
}

export function CriticalAnomalyCard() {
  const navigate = useNavigate();
  const list = useAnomalies({ page_size: 50, page: 1 });
  const candidate = useMemo(() => (list.data ? pickMostCritical(list.data.items) : null), [list.data]);
  const detail = useAnomaly(candidate?.id);

  if (list.isLoading || list.isError || !candidate) return null;

  const cfg = SEVERITY_CONFIG[candidate.severity];
  const foremanCodes = detail.data?.foreman_codes ?? [];

  return (
    <button
      type="button"
      onClick={() => navigate(`/anomalies/${candidate.id}`)}
      className="block w-full rounded-lg p-4 text-left transition-transform duration-150 hover:-translate-y-0.5"
      style={{ background: "var(--surface)", border: `1px solid ${cfg.color}40`, borderLeft: `4px solid ${cfg.color}` }}
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <SeverityBadge severity={candidate.severity} />
          <span className="text-xs font-medium" style={{ color: "var(--text-muted)" }}>
            {candidate.plant_name ?? "-"} · {candidate.kpi_name ?? candidate.anomaly_type_label}
          </span>
        </div>
        <span className="text-[11px] font-medium" style={{ color: "var(--text-muted)" }}>
          {new Date(candidate.detected_at).toLocaleDateString("tr-TR")}
        </span>
      </div>

      <p className="mt-2 text-sm font-semibold" style={{ color: "var(--text-primary)" }}>{candidate.title}</p>

      <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs" style={{ color: "var(--text-secondary)" }}>
        {foremanCodes.length > 0 && (
          <span>
            Formen: {foremanCodes.length === 1 ? <ForemanLabel code={foremanCodes[0]} /> : `${foremanCodes.length} formen`}
          </span>
        )}
        <span>
          Sapma: {candidate.deviation_percent >= 0 ? "+" : ""}%{candidate.deviation_percent.toFixed(1)}
        </span>
      </div>

      <span className="mt-3 inline-flex items-center gap-1 text-xs font-medium hover:underline" style={{ color: "var(--accent)" }}>
        Analizi Gör
        <ArrowRight size={13} strokeWidth={2} />
      </span>
    </button>
  );
}
