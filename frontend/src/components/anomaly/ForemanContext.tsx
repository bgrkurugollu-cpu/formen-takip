import { Link } from "react-router-dom";
import { ChevronRight, User } from "lucide-react";
import type { AnomalyDetail, ResponsibleForeman } from "../../api/types";
import { EmptyState } from "../StateViews";
import { formatDateRangeTR } from "../../lib/dateFormat";

export function ForemanContext({ anomaly, foreman }: { anomaly: AnomalyDetail; foreman: ResponsibleForeman }) {
  if (!foreman.resolved || !foreman.primary) {
    return <EmptyState message={foreman.reason ?? "Sorumlu formen bilgisi bulunamadı."} />;
  }

  const { primary } = foreman;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-start justify-between gap-3 rounded-md p-3.5" style={{ border: "1px solid var(--border)" }}>
        <div className="flex items-start gap-3">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full" style={{ background: "var(--accent-subtle)" }}>
            <User size={16} strokeWidth={2} style={{ color: "var(--accent)" }} />
          </div>
          <div>
            <p className="font-semibold" style={{ color: "var(--text-primary)" }}>{primary.name}</p>
            <p className="text-xs" style={{ color: "var(--text-muted)" }}>
              {primary.employee_number} · {anomaly.shift_name ?? "Vardiyaya özgü değil"} · {formatDateRangeTR(anomaly.period_start, anomaly.period_end)}
            </p>
            {"day_count" in primary && "total_days" in primary && primary.total_days != null && (
              <p className="mt-0.5 text-xs" style={{ color: "var(--text-muted)" }}>
                Dönemin {primary.day_count} / {primary.total_days} gününde bu vardiyada görev yapmıştır.
              </p>
            )}
          </div>
        </div>
        <Link to={`/foremen/${primary.id}`} className="flex shrink-0 items-center gap-1 text-xs font-medium hover:underline" style={{ color: "var(--accent)" }}>
          Formen profilini görüntüle
          <ChevronRight size={13} strokeWidth={2} />
        </Link>
      </div>

      {foreman.note && (
        <p className="text-xs italic" style={{ color: "var(--text-muted)" }}>{foreman.note}</p>
      )}

      {foreman.others.length > 0 && (
        <div className="flex flex-col gap-1.5">
          <p className="text-[11px] font-semibold uppercase tracking-wide" style={{ color: "var(--text-muted)" }}>Dönem İçinde Görev Yapan Diğer Formenler</p>
          {foreman.others.map((o) => (
            <div key={o.id} className="flex items-center justify-between text-xs" style={{ color: "var(--text-secondary)" }}>
              <Link to={`/foremen/${o.id}`} className="hover:underline" style={{ color: "var(--accent)" }}>{o.name}</Link>
              <span>{o.day_count} gün</span>
            </div>
          ))}
        </div>
      )}

      {foreman.kpi_trend.length > 0 && (
        <div>
          <p className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide" style={{ color: "var(--text-muted)" }}>
            {anomaly.kpi_name} — Son 3 Ay
          </p>
          <div className="flex items-center gap-4">
            {foreman.kpi_trend.map((p) => (
              <div key={p.period_label} className="text-center">
                <p className="text-[11px]" style={{ color: "var(--text-muted)" }}>{p.period_label}</p>
                <p className="text-sm font-semibold tabular-nums" style={{ color: "var(--text-primary)" }}>
                  {p.has_data && p.avg_actual != null ? `%${p.avg_actual.toFixed(2)}` : "Veri yok"}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      <p className="text-xs" style={{ color: "var(--text-muted)" }}>
        Bu tespit, {primary.name} adlı formenin sorumlu olduğu vardiya döneminde gözlenmiştir. Bu bilgi bir performans değerlendirmesi değildir.
      </p>
    </div>
  );
}
