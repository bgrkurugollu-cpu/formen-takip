import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  AlertOctagon,
  AlertTriangle,
  CheckCircle2,
  Clock,
  ListChecks,
  Search,
  SearchCheck,
  X,
} from "lucide-react";
import { useAnomalies, useAnomalySummary, useFilterOptions } from "../api/hooks";
import { useAnomalyFilters } from "../hooks/useAnomalyFilters";
import { DATE_PRESETS } from "../hooks/useFilters";
import { Card, EmptyState, ErrorState, LoadingState } from "../components/StateViews";
import { Pagination } from "../components/Pagination";
import { AnalysisStatusBadge, SeverityBadge, StatusBadge } from "../components/AnomalyBadges";
import { rowStyle, tdClass, thClass, theadRowStyle, thStyle } from "../lib/tableStyles";
import { fieldClass, fieldStyle, labelClass, labelStyle } from "../lib/formStyles";

const SEVERITY_OPTIONS: { value: string; label: string }[] = [
  { value: "low", label: "Düşük" },
  { value: "medium", label: "Orta" },
  { value: "high", label: "Yüksek" },
  { value: "critical", label: "Kritik" },
];
const STATUS_OPTIONS: { value: string; label: string }[] = [
  { value: "new", label: "Yeni" },
  { value: "in_review", label: "İnceleniyor" },
  { value: "action_pending", label: "Aksiyon Bekliyor" },
  { value: "resolved", label: "Çözüldü" },
  { value: "closed", label: "Kapatıldı" },
];
const ANALYSIS_STATUS_OPTIONS: { value: string; label: string }[] = [
  { value: "not_analyzed", label: "Analiz Edilmedi" },
  { value: "analyzing", label: "Analiz Ediliyor" },
  { value: "completed", label: "Analiz Tamamlandı" },
  { value: "failed", label: "Analiz Başarısız" },
];

function SummaryTile({
  label, value, icon: Icon, accent,
}: { label: string; value: number; icon: typeof Search; accent?: string }) {
  return (
    <div
      className="rounded-lg p-4"
      style={{ background: "var(--surface)", border: "1px solid var(--border)", borderTop: `2px solid ${accent ?? "var(--accent)"}` }}
    >
      <div className="flex items-center gap-1.5">
        <Icon size={13} strokeWidth={2} style={{ color: accent ?? "var(--text-muted)" }} />
        <p className="text-[11px] font-semibold uppercase tracking-wide" style={{ color: "var(--text-muted)" }}>{label}</p>
      </div>
      <p className="mt-1.5 text-2xl font-semibold tabular-nums" style={{ color: "var(--text-primary)" }}>{value}</p>
    </div>
  );
}

export function AnomaliesPage() {
  const navigate = useNavigate();
  const { filters, setFilters, clearFilters, asQueryParams, activeFilterCount } = useAnomalyFilters();
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const pageSize = 20;

  const filterOptions = useFilterOptions();
  const summary = useAnomalySummary();
  const anomalies = useAnomalies({ ...asQueryParams, search: search || undefined, page, page_size: pageSize });

  const plantsForFactory = useMemo(() => {
    const plants = filterOptions.data?.plants ?? [];
    if (!filters.factory) return plants;
    const factory = filterOptions.data?.factories.find((f) => f.code === filters.factory);
    return factory ? plants.filter((p) => p.factory_id === factory.id) : plants;
  }, [filterOptions.data, filters.factory]);

  return (
    <div className="flex flex-col gap-4">
      {summary.isLoading && <LoadingState />}
      {summary.isError && <ErrorState />}
      {summary.data && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-6">
          <SummaryTile label="Toplam Aktif Tespit" value={summary.data.total_active} icon={SearchCheck} />
          <SummaryTile label="Kritik" value={summary.data.critical_count} icon={AlertOctagon} accent="#b91c1c" />
          <SummaryTile label="Yüksek Önem" value={summary.data.high_count} icon={AlertTriangle} accent="#b45309" />
          <SummaryTile label="Analiz Bekliyor" value={summary.data.pending_analysis_count} icon={Clock} accent="#1d4ed8" />
          <SummaryTile label="Son 7 Günde Açılan" value={summary.data.opened_last_7_days} icon={ListChecks} />
          <SummaryTile label="Çözülen" value={summary.data.resolved_count} icon={CheckCircle2} accent="#15803d" />
        </div>
      )}

      <div className="flex flex-wrap items-end gap-2 rounded-lg p-3" style={{ background: "var(--surface)", border: "1px solid var(--border)" }}>
        <div>
          <label className={labelClass} style={labelStyle}>Hazır tarih aralığı</label>
          <select
            className={fieldClass}
            style={fieldStyle}
            onChange={(e) => {
              const preset = DATE_PRESETS.find((p) => p.label === e.target.value);
              if (preset) {
                const [from, to] = preset.getRange();
                setFilters({ dateFrom: from, dateTo: to });
                setPage(1);
              }
            }}
            defaultValue=""
          >
            <option value="" disabled>Seçiniz</option>
            {DATE_PRESETS.map((p) => <option key={p.label} value={p.label}>{p.label}</option>)}
          </select>
        </div>
        <div>
          <label className={labelClass} style={labelStyle}>Başlangıç</label>
          <input type="date" className={fieldClass} style={fieldStyle} value={filters.dateFrom}
            onChange={(e) => { setFilters({ dateFrom: e.target.value }); setPage(1); }} />
        </div>
        <div>
          <label className={labelClass} style={labelStyle}>Bitiş</label>
          <input type="date" className={fieldClass} style={fieldStyle} value={filters.dateTo}
            onChange={(e) => { setFilters({ dateTo: e.target.value }); setPage(1); }} />
        </div>
        <div>
          <label className={labelClass} style={labelStyle}>Fabrika</label>
          <select className={fieldClass} style={fieldStyle} value={filters.factory}
            onChange={(e) => { setFilters({ factory: e.target.value, plantIds: [] }); setPage(1); }}>
            <option value="">Tümü</option>
            {filterOptions.data?.factories.map((f) => (
              <option key={f.id} value={f.code}>{f.code}</option>
            ))}
          </select>
        </div>
        <div>
          <label className={labelClass} style={labelStyle}>Tesis</label>
          <select className={fieldClass} style={fieldStyle} value={filters.plantIds[0] ?? ""}
            onChange={(e) => { setFilters({ plantIds: e.target.value ? [e.target.value] : [] }); setPage(1); }}>
            <option value="">Tümü</option>
            {plantsForFactory.map((p) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
        </div>
        <div>
          <label className={labelClass} style={labelStyle}>Vardiya</label>
          <select className={fieldClass} style={fieldStyle} value={filters.shiftIds[0] ?? ""}
            onChange={(e) => { setFilters({ shiftIds: e.target.value ? [e.target.value] : [] }); setPage(1); }}>
            <option value="">Tümü</option>
            {filterOptions.data?.shifts.map((s) => (
              <option key={s.id} value={s.id}>{s.name}</option>
            ))}
          </select>
        </div>
        <div>
          <label className={labelClass} style={labelStyle}>KPI</label>
          <select className={fieldClass} style={fieldStyle} value={filters.kpiIds[0] ?? ""}
            onChange={(e) => { setFilters({ kpiIds: e.target.value ? [e.target.value] : [] }); setPage(1); }}>
            <option value="">Tümü</option>
            {filterOptions.data?.kpis.map((k) => (
              <option key={k.id} value={k.id}>{k.name}</option>
            ))}
          </select>
        </div>
        <div>
          <label className={labelClass} style={labelStyle}>Önem Seviyesi</label>
          <select className={fieldClass} style={fieldStyle} value={filters.severity}
            onChange={(e) => { setFilters({ severity: e.target.value as never }); setPage(1); }}>
            <option value="">Tümü</option>
            {SEVERITY_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </div>
        <div>
          <label className={labelClass} style={labelStyle}>Tespit Durumu</label>
          <select className={fieldClass} style={fieldStyle} value={filters.status}
            onChange={(e) => { setFilters({ status: e.target.value as never }); setPage(1); }}>
            <option value="">Tümü</option>
            {STATUS_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </div>
        <div>
          <label className={labelClass} style={labelStyle}>YZ Analiz Durumu</label>
          <select className={fieldClass} style={fieldStyle} value={filters.analysisStatus}
            onChange={(e) => { setFilters({ analysisStatus: e.target.value as never }); setPage(1); }}>
            <option value="">Tümü</option>
            {ANALYSIS_STATUS_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </div>
        <div className="relative">
          <label className={labelClass} style={labelStyle}>Ara</label>
          <Search size={13} strokeWidth={2} className="pointer-events-none absolute left-2 top-[30px]" style={{ color: "var(--text-muted)" }} />
          <input
            type="text"
            placeholder="Başlık veya açıklamada ara..."
            className={`${fieldClass} pl-7`}
            style={{ ...fieldStyle, width: 220 }}
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          />
        </div>
        {(activeFilterCount > 0 || search) && (
          <button
            onClick={() => { clearFilters(); setSearch(""); setPage(1); }}
            className="ml-auto flex items-center gap-1 rounded-md px-2 py-1.5 text-xs font-medium hover:underline"
            style={{ color: "var(--accent)" }}
          >
            <X size={12} strokeWidth={2} />
            Filtreleri temizle ({activeFilterCount + (search ? 1 : 0)})
          </button>
        )}
      </div>

      <Card>
        {anomalies.isLoading && <LoadingState label="Tespitler yükleniyor..." />}
        {anomalies.isError && <ErrorState />}
        {anomalies.data && anomalies.data.items.length === 0 && (
          <EmptyState message="Seçilen filtrelerle eşleşen tespit bulunamadı." />
        )}
        {anomalies.data && anomalies.data.items.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-[13px]">
              <thead>
                <tr style={theadRowStyle}>
                  <th className={thClass} style={thStyle}>Tespit</th>
                  <th className={thClass} style={thStyle}>Fabrika / Tesis</th>
                  <th className={thClass} style={thStyle}>Vardiya</th>
                  <th className={thClass} style={thStyle}>KPI</th>
                  <th className={thClass} style={thStyle}>Tespit Tarihi</th>
                  <th className={thClass} style={thStyle}>Sapma</th>
                  <th className={thClass} style={thStyle}>ML Güveni</th>
                  <th className={thClass} style={thStyle}>Önem</th>
                  <th className={thClass} style={thStyle}>Durum</th>
                  <th className={thClass} style={thStyle}>YZ Analizi</th>
                </tr>
              </thead>
              <tbody>
                {anomalies.data.items.map((a) => (
                  <tr
                    key={a.id}
                    style={rowStyle}
                    className="cursor-pointer transition-colors hover:bg-[var(--page-bg)]"
                    onClick={() => navigate(`/anomalies/${a.id}`)}
                  >
                    <td className={tdClass}>
                      <p className="font-medium" style={{ color: "var(--text-primary)" }}>{a.title}</p>
                      <p className="text-xs" style={{ color: "var(--text-muted)" }}>{a.code} · {a.anomaly_type_label}</p>
                    </td>
                    <td className={tdClass} style={{ color: "var(--text-secondary)" }}>
                      {a.factory_code} · {a.plant_name ?? "-"}
                    </td>
                    <td className={tdClass} style={{ color: "var(--text-secondary)" }}>{a.shift_name ?? "Tüm vardiyalar"}</td>
                    <td className={tdClass} style={{ color: "var(--text-secondary)" }}>{a.kpi_name ?? "-"}</td>
                    <td className={tdClass} style={{ color: "var(--text-secondary)" }}>{a.detected_at.slice(0, 10)}</td>
                    <td className={`${tdClass} tabular-nums`} style={{ color: "var(--text-primary)" }}>
                      %{a.deviation_percent.toFixed(1)}
                    </td>
                    <td className={`${tdClass} tabular-nums`} style={{ color: "var(--text-secondary)" }}>
                      {(a.ml_confidence * 100).toFixed(0)}%
                    </td>
                    <td className={tdClass}><SeverityBadge severity={a.severity} /></td>
                    <td className={tdClass}><StatusBadge status={a.status} /></td>
                    <td className={tdClass}><AnalysisStatusBadge status={a.analysis_status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
            <Pagination page={page} pageSize={pageSize} total={anomalies.data.total} onPageChange={setPage} itemLabel="tespit" />
          </div>
        )}
      </Card>
    </div>
  );
}
