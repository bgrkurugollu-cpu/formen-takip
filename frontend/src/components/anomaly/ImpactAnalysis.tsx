import type { InvestigationImpact } from "../../api/types";

export function ImpactCard({ label, value, note }: { label: string; value: string | null; note: string | null }) {
  return (
    <div className="rounded-lg p-3.5" style={{ background: "var(--page-bg)", border: "1px solid var(--border)" }}>
      <p className="text-[11px] font-semibold uppercase tracking-wide" style={{ color: "var(--text-muted)" }}>{label}</p>
      {value != null ? (
        <p className="mt-1 text-xl font-bold tabular-nums" style={{ color: "var(--text-primary)" }}>{value}</p>
      ) : (
        <p className="mt-1 text-[13px] italic" style={{ color: "var(--text-muted)" }}>{note}</p>
      )}
    </div>
  );
}

export function ImpactAnalysis({ impact }: { impact: InvestigationImpact }) {
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
      <ImpactCard
        label="Ek Duruş"
        value={impact.additional_downtime_minutes != null ? `${impact.additional_downtime_minutes > 0 ? "+" : ""}${impact.additional_downtime_minutes} dk` : null}
        note={impact.additional_downtime_note}
      />
      <ImpactCard label="Tahmini Üretim Kaybı" value={null} note={impact.production_loss_note} />
      <ImpactCard label="Tahmini Maliyet Etkisi" value={null} note={impact.cost_note} />
    </div>
  );
}
