import { Link } from "react-router-dom";
import type { AnomalyDetail, AnomalyInvestigation } from "../../api/types";
import { formatDateRangeTR, formatDateTR } from "../../lib/dateFormat";
import { isHigherBetter } from "../../lib/kpiDirection";

function ScopeField({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <p className="text-[11px] font-semibold uppercase tracking-wide" style={{ color: "var(--text-muted)" }}>{label}</p>
      <div className="mt-0.5 text-[13px]" style={{ color: "var(--text-primary)" }}>{children}</div>
    </div>
  );
}

const NOT_AVAILABLE = <span style={{ color: "var(--text-muted)" }}>Veri mevcut değil</span>;

export function DetectionScope({ anomaly, investigation }: { anomaly: AnomalyDetail; investigation?: AnomalyInvestigation }) {
  const a = anomaly;
  const higherIsBetter = isHigherBetter(a.kpi_definition.desired_direction);

  let worstDay: { date: string; value: number } | null = null;
  let bestValue: number | null = null;
  let worstValue: number | null = null;
  if (a.daily_history.length > 0) {
    bestValue = a.daily_history[0].value;
    worstValue = a.daily_history[0].value;
    worstDay = a.daily_history[0];
    for (const p of a.daily_history) {
      if (bestValue == null || (higherIsBetter ? p.value > bestValue : p.value < bestValue)) bestValue = p.value;
      if (worstValue == null || (higherIsBetter ? p.value < worstValue : p.value > worstValue)) {
        worstValue = p.value;
        worstDay = p;
      }
    }
  }

  const foreman = investigation?.responsible_foreman;

  return (
    <div className="grid grid-cols-2 gap-x-4 gap-y-4 sm:grid-cols-3 lg:grid-cols-4">
      <ScopeField label="Fabrika">{a.factory_code ?? NOT_AVAILABLE}</ScopeField>
      <ScopeField label="Tesis">
        <Link to={`/plants/${a.plant_id}`} className="hover:underline" style={{ color: "var(--accent)" }}>{a.plant_name}</Link>
      </ScopeField>
      <ScopeField label="Vardiya">{a.shift_name ?? <span style={{ color: "var(--text-muted)" }}>Vardiyaya özgü değil</span>}</ScopeField>
      <ScopeField label="Dönem">{formatDateRangeTR(a.period_start, a.period_end)}</ScopeField>

      <ScopeField label="Sorumlu Formen">
        {!investigation && "Yükleniyor..."}
        {investigation && foreman?.resolved && foreman.primary && (
          <Link to={`/foremen/${foreman.primary.id}`} className="hover:underline" style={{ color: "var(--accent)" }}>
            {foreman.primary.name}
          </Link>
        )}
        {investigation && !foreman?.resolved && (foreman?.reason ? <span style={{ color: "var(--text-muted)" }}>{foreman.reason}</span> : NOT_AVAILABLE)}
      </ScopeField>
      <ScopeField label="Etkilenen Gün Sayısı">
        {a.affected_days != null && a.total_days != null ? `${a.affected_days} / ${a.total_days} gün` : NOT_AVAILABLE}
      </ScopeField>
      <ScopeField label="En Kötü Gün">
        {worstDay ? `${formatDateTR(worstDay.date)} (%${worstDay.value.toFixed(2)})` : NOT_AVAILABLE}
      </ScopeField>
      <ScopeField label="En Yüksek / En Düşük Değer">
        {bestValue != null && worstValue != null ? `%${Math.max(bestValue, worstValue).toFixed(2)} / %${Math.min(bestValue, worstValue).toFixed(2)}` : NOT_AVAILABLE}
      </ScopeField>

      <ScopeField label="İlgili Ürün / Ürün Grubu">{NOT_AVAILABLE}</ScopeField>
      <ScopeField label="İlgili Hat / Makine">{NOT_AVAILABLE}</ScopeField>
      <ScopeField label="İlgili KPI">{a.kpi_name}</ScopeField>
      <ScopeField label="Tespit Türü">{a.anomaly_type_label}</ScopeField>
    </div>
  );
}
