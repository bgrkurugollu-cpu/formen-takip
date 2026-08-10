import { CalendarDays, Lightbulb, Repeat, ScatterChart, X } from "lucide-react";
import type { ShiftAnomalyCard as ShiftAnomalyCardData } from "../api/types";
import { useShiftAnalysisDetail } from "../api/hooks";
import { LoadingState, ErrorState } from "./StateViews";
import { ShiftAnomalySeverityBadge } from "./ShiftAnomalyCard";
import { ShiftComparisonMiniChart } from "./charts/ShiftComparisonMiniChart";
import { ShiftWeeklyTrendChart } from "./charts/ShiftWeeklyTrendChart";
import { thClass, thStyle, theadRowStyle, tdClass, rowStyle } from "../lib/tableStyles";

function decimalPlacesFor(unit: string): number {
  return unit === "%" ? 1 : 2;
}

export function ShiftAnomalyDetailModal({ card, onClose }: { card: ShiftAnomalyCardData; onClose: () => void }) {
  const detail = useShiftAnalysisDetail({ plant_id: card.plant_id, shift_id: card.shift_id, kpi_id: card.kpi_id });
  const decimalPlaces = decimalPlacesFor(card.kpi_unit);

  const nameById = detail.data
    ? { [detail.data.better.id]: detail.data.better.name, [detail.data.worse.id]: detail.data.worse.name }
    : {};

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={onClose}>
      <div
        onClick={(e) => e.stopPropagation()}
        className="max-h-[90vh] w-full max-w-3xl overflow-y-auto rounded-lg p-5 shadow-xl"
        style={{ background: "var(--surface)" }}
      >
        <div className="mb-4 flex items-start justify-between gap-3">
          <div>
            <div className="mb-1.5 flex items-center gap-2">
              <ShiftAnomalySeverityBadge severity={card.severity} />
              <span className="text-xs" style={{ color: "var(--text-muted)" }}>
                {card.factory_code} · {card.plant_name} · {card.shift_name} · {card.kpi_name}
              </span>
            </div>
            <h3 className="text-[15px] font-semibold leading-snug" style={{ color: "var(--text-primary)" }}>
              {card.title}
            </h3>
          </div>
          <button type="button" onClick={onClose} style={{ color: "var(--text-muted)" }}>
            <X size={18} strokeWidth={2} />
          </button>
        </div>

        {detail.isLoading && <LoadingState label="Detay yükleniyor..." />}
        {detail.isError && <ErrorState message="Detay verisi yüklenemedi." />}

        {detail.data && (
          <div className="flex flex-col gap-5">
            <section>
              <h4 className="mb-2 flex items-center gap-1.5 text-[12px] font-semibold uppercase tracking-wide" style={{ color: "var(--text-secondary)" }}>
                <ScatterChart size={13} strokeWidth={2.25} />
                Vardiya Ortalaması Karşılaştırması
              </h4>
              <div className="rounded-md p-3" style={{ background: "var(--page-bg)", border: "1px solid var(--border)" }}>
                <ShiftComparisonMiniChart better={detail.data.better} worse={detail.data.worse} unit={detail.data.kpi_unit} decimalPlaces={decimalPlaces} />
              </div>
            </section>

            <section>
              <h4 className="mb-2 flex items-center gap-1.5 text-[12px] font-semibold uppercase tracking-wide" style={{ color: "var(--text-secondary)" }}>
                <CalendarDays size={13} strokeWidth={2.25} />
                Dönemsel Kırılım — Haftalık Vardiya Ataması ve KPI Değeri
              </h4>
              <div className="overflow-x-auto rounded-md" style={{ border: "1px solid var(--border)" }}>
                <table className="w-full text-left text-[13px]">
                  <thead>
                    <tr style={theadRowStyle}>
                      <th className={thClass} style={thStyle}>Hafta</th>
                      <th className={thClass} style={thStyle}>{detail.data.shift_name}'da Görevli Formen</th>
                      <th className={thClass} style={thStyle}>{detail.data.kpi_name} Ortalaması</th>
                      <th className={thClass} style={thStyle}>Gün Sayısı</th>
                    </tr>
                  </thead>
                  <tbody>
                    {[...detail.data.weekly_breakdown]
                      .sort((a, b) => a.week_index - b.week_index)
                      .map((p, i) => (
                        <tr key={i} style={rowStyle}>
                          <td className={tdClass} style={{ color: "var(--text-secondary)" }}>{p.week_label}</td>
                          <td className={tdClass} style={{ color: "var(--text-primary)" }}>{nameById[p.foreman_id] ?? "-"}</td>
                          <td className={`${tdClass} tabular-nums`} style={{ color: "var(--text-primary)" }}>
                            {p.avg_actual.toFixed(decimalPlaces)}
                          </td>
                          <td className={`${tdClass} tabular-nums`} style={{ color: "var(--text-secondary)" }}>{p.day_count}</td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
            </section>

            <section>
              <h4 className="mb-2 text-[12px] font-semibold uppercase tracking-wide" style={{ color: "var(--text-secondary)" }}>
                Haftalık Trend
              </h4>
              <div className="rounded-md p-3" style={{ background: "var(--page-bg)", border: "1px solid var(--border)" }}>
                <ShiftWeeklyTrendChart
                  points={detail.data.weekly_breakdown}
                  better={detail.data.better}
                  worse={detail.data.worse}
                  unit={detail.data.kpi_unit}
                  decimalPlaces={decimalPlaces}
                />
              </div>
            </section>

            <section>
              <h4 className="mb-2 flex items-center gap-1.5 text-[12px] font-semibold uppercase tracking-wide" style={{ color: "var(--text-secondary)" }}>
                <Repeat size={13} strokeWidth={2.25} />
                Diğer KPI'larda Aynı Formen Çiftinde Gözlemlenen Farklar
              </h4>
              {detail.data.cross_kpi_signals.length === 0 && (
                <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                  Bu formen çifti arasında başka bir KPI'da eşik üstü bir fark gözlemlenmedi.
                </p>
              )}
              {detail.data.cross_kpi_signals.length > 0 && (
                <div className="flex flex-col gap-1.5">
                  {detail.data.cross_kpi_signals.map((s) => (
                    <div
                      key={s.kpi_id}
                      className="flex items-center justify-between rounded-md px-3 py-2 text-[13px]"
                      style={{ background: "var(--page-bg)", border: "1px solid var(--border)" }}
                    >
                      <span style={{ color: "var(--text-primary)" }}>{s.kpi_name}</span>
                      <span className="flex items-center gap-2">
                        <ShiftAnomalySeverityBadge severity={s.severity} />
                        <span className="tabular-nums font-medium" style={{ color: "var(--text-secondary)" }}>%{s.pct_diff.toFixed(1)}</span>
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </section>

            <section className="rounded-md p-3" style={{ background: "var(--page-bg)", border: "1px solid var(--border)" }}>
              <h4 className="mb-1.5 flex items-center gap-1.5 text-[12px] font-semibold uppercase tracking-wide" style={{ color: "var(--text-secondary)" }}>
                <Lightbulb size={13} strokeWidth={2.25} />
                Sistem Yorumu
              </h4>
              <p className="text-[13px] leading-relaxed" style={{ color: "var(--text-primary)" }}>
                {detail.data.pattern_commentary}
              </p>
            </section>
          </div>
        )}
      </div>
    </div>
  );
}
