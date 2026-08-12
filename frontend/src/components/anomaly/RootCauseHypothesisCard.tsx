import { Database } from "lucide-react";
import type { AnalysisPossibleCause } from "../../api/types";

const CONFIDENCE_LABELS: Record<string, string> = { low: "Düşük", medium: "Orta", high: "Yüksek" };
const CONFIDENCE_COLORS: Record<string, string> = { low: "#64748b", medium: "#1d4ed8", high: "#b45309" };

export function RootCauseHypothesisCard({ cause, toolLabels }: { cause: AnalysisPossibleCause; toolLabels: Record<string, string> }) {
  const confidenceColor = CONFIDENCE_COLORS[cause.confidence] ?? "#64748b";

  return (
    <div className="rounded-md p-3.5" style={{ border: "1px solid var(--border)" }}>
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          <span
            className="rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide"
            style={{ background: "#fef3c722", color: "#b45309", border: "1px solid #b4530933" }}
          >
            AI Hipotezi
          </span>
          <span className="font-semibold" style={{ color: "var(--text-primary)" }}>{cause.cause}</span>
        </div>
        <span
          className="shrink-0 rounded px-1.5 py-0.5 text-[11px] font-medium"
          style={{ background: `${confidenceColor}14`, color: confidenceColor, border: `1px solid ${confidenceColor}33` }}
        >
          Olasılık: {CONFIDENCE_LABELS[cause.confidence] ?? cause.confidence}
        </span>
      </div>

      {cause.supporting_evidence.length > 0 && (
        <div className="mt-2 text-xs" style={{ color: "var(--text-secondary)" }}>
          <span className="font-medium" style={{ color: "var(--text-primary)" }}>Destekleyen:</span>
          <ul className="mt-0.5 flex flex-col gap-0.5 pl-3">
            {cause.supporting_evidence.map((e, i) => <li key={i} className="list-disc">{e}</li>)}
          </ul>
        </div>
      )}

      {cause.contradicting_evidence.length > 0 && (
        <div className="mt-2 text-xs" style={{ color: "var(--text-secondary)" }}>
          <span className="font-medium" style={{ color: "var(--text-primary)" }}>Çelişen:</span>
          <ul className="mt-0.5 flex flex-col gap-0.5 pl-3">
            {cause.contradicting_evidence.map((e, i) => <li key={i} className="list-disc">{e}</li>)}
          </ul>
        </div>
      )}

      <p className="mt-2 text-xs" style={{ color: "var(--text-secondary)" }}>
        <span className="font-medium" style={{ color: "var(--text-primary)" }}>Kontrol edilmesi gereken:</span> {cause.verification_required}
      </p>
      <p className="mt-1 text-xs italic" style={{ color: "var(--text-muted)" }}>Durum: Doğrulanmayı bekliyor</p>

      {(cause.source_refs ?? []).length > 0 && (
        <span className="mt-1.5 flex w-fit items-center gap-1 text-[11px]" style={{ color: "var(--accent)" }}>
          <Database size={10} strokeWidth={2} />
          Kaynak: {cause.source_refs.map((r) => toolLabels[r.tool_name] ?? r.tool_name).join(", ")}
        </span>
      )}
    </div>
  );
}
