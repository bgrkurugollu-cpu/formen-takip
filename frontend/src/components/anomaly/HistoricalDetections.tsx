import { useNavigate } from "react-router-dom";
import { CheckCircle2, CircleDot } from "lucide-react";
import type { SimilarCase } from "../../api/types";
import { EmptyState } from "../StateViews";
import { formatDateTR } from "../../lib/dateFormat";

export function HistoricalDetections({ cases }: { cases: SimilarCase[] }) {
  const navigate = useNavigate();

  if (cases.length === 0) return <EmptyState message="Benzer geçmiş tespit bulunamadı." />;

  return (
    <div className="flex flex-col gap-3">
      <p className="text-xs" style={{ color: "var(--text-muted)" }}>{cases.length} benzer geçmiş tespit bulundu.</p>
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
        {cases.map((c) => (
          <button
            key={c.anomaly_id}
            type="button"
            onClick={() => navigate(`/anomalies/${c.anomaly_id}`)}
            className="flex flex-col gap-1.5 rounded-md p-3 text-left transition-colors hover:bg-[var(--page-bg)]"
            style={{ border: "1px solid var(--border)" }}
          >
            <div className="flex items-center justify-between gap-2">
              <span className="text-xs font-medium" style={{ color: "var(--text-muted)" }}>{formatDateTR(c.detected_at)}</span>
              <span
                className="flex items-center gap-1 rounded px-1.5 py-0.5 text-[11px] font-medium"
                style={
                  c.resolution_status === "resolved"
                    ? { background: "#dcfce7", color: "#15803d" }
                    : { background: "#dbeafe", color: "#1d4ed8" }
                }
              >
                {c.resolution_status === "resolved" ? <CheckCircle2 size={11} strokeWidth={2} /> : <CircleDot size={11} strokeWidth={2} />}
                {c.resolution_status === "resolved" ? "Çözüldü" : "Açık"}
              </span>
            </div>
            <p className="text-[13px] font-medium" style={{ color: "var(--text-primary)" }}>{c.title}</p>
            <p className="text-xs" style={{ color: "var(--text-secondary)" }}>{c.plant_name} · {c.kpi_name ?? c.anomaly_type_label}</p>
            {c.resolution_status === "resolved" && c.verified_root_cause && (
              <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                Kök neden: {c.verified_root_cause}
                {c.action_taken && ` · Aksiyon: ${c.action_taken}`}
              </p>
            )}
          </button>
        ))}
      </div>
    </div>
  );
}
