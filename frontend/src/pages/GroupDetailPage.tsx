import { useNavigate, useParams } from "react-router-dom";
import { AlertTriangle, ChevronLeft } from "lucide-react";
import { FilterBar } from "../components/FilterBar";
import { Card, EmptyState, ErrorState, LoadingState } from "../components/StateViews";
import { PerformanceLevelBadge } from "../components/PerformanceLevelBadge";
import { TrendChart } from "../components/charts/TrendChart";
import { KpiRadarChart } from "../components/charts/KpiRadarChart";
import { RelatedActionPlans } from "../components/RelatedActionPlans";
import { useChiefDetail, useChiefForemen, useChiefKpis, useChiefTrend } from "../api/hooks";
import { useFilters } from "../hooks/useFilters";
import { rowHoverClass, rowStyle, tdClass, thClass, theadRowStyle, thStyle } from "../lib/tableStyles";

export function GroupDetailPage() {
  const { chiefId } = useParams<{ chiefId: string }>();
  const { filters, setFilters, clearFilters, asQueryParams } = useFilters();
  const navigate = useNavigate();

  const chief = useChiefDetail(chiefId, asQueryParams);
  const team = useChiefForemen(chiefId, asQueryParams);
  const kpis = useChiefKpis(chiefId, asQueryParams);
  const trend = useChiefTrend(chiefId, asQueryParams, "day");

  if (chief.isLoading) return <LoadingState />;
  if (chief.isError || !chief.data) return <ErrorState message="Şef bulunamadı." />;

  const c = chief.data;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div>
          <button
            onClick={() => navigate("/groups")}
            className="mb-1.5 flex items-center gap-1 text-xs font-medium hover:underline"
            style={{ color: "var(--accent)" }}
          >
            <ChevronLeft size={13} strokeWidth={2} />
            Gruplar
          </button>
          <h1 className="text-lg font-semibold" style={{ color: "var(--text-primary)" }}>{c.full_name}</h1>
          <p className="text-[13px]" style={{ color: "var(--text-muted)" }}>
            {c.employee_number} · {c.factory?.name} · {c.plant?.name} · {c.foreman_count} formen
          </p>
        </div>
        <div className="text-right">
          <div className="text-2xl font-semibold tabular-nums" style={{ color: "var(--text-primary)" }}>{c.total_score.toFixed(1)}</div>
          <div className="mt-1"><PerformanceLevelBadge level={c.level} /></div>
          {!c.is_reliable && (
            <p className="mt-1.5 flex items-center justify-end gap-1 text-xs font-medium text-amber-600">
              <AlertTriangle size={12} strokeWidth={2} />
              Ekipte eksik KPI verisi
            </p>
          )}
        </div>
      </div>

      <FilterBar filters={filters} setFilters={setFilters} clearFilters={clearFilters} />

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Card title="Şirket Sıralaması"><p className="text-xl font-semibold tabular-nums" style={{ color: "var(--text-primary)" }}>{c.company_rank ?? "-"} / {c.company_total}</p></Card>
        <Card title="Tesis İçi Sıralaması"><p className="text-xl font-semibold tabular-nums" style={{ color: "var(--text-primary)" }}>{c.plant_rank ?? "-"} / {c.plant_total}</p></Card>
        <Card title="Göreve Başlama"><p className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>{c.hire_date}</p></Card>
        <Card title="Durum"><p className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>{c.is_active ? "Aktif" : "Pasif"}</p></Card>
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <Card title="Grup Performans Trendi">
          {trend.isLoading ? <LoadingState /> : trend.data ? <TrendChart points={trend.data.points} /> : <ErrorState />}
        </Card>
        <Card title="KPI Radar Grafiği">
          {kpis.isLoading ? <LoadingState /> : kpis.data ? <KpiRadarChart items={kpis.data.items} /> : <ErrorState />}
        </Card>
      </div>

      <Card title="Ekip — grup puanı bu formenlerin ortalamasıdır">
        {team.isLoading && <LoadingState />}
        {team.isError && <ErrorState />}
        {team.data && team.data.items.length === 0 && <EmptyState />}
        {team.data && team.data.items.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-[13px]">
              <thead>
                <tr style={theadRowStyle}>
                  {["Formen", "Sicil No", "Vardiya", "Toplam Puan", "Seviye", "Veri Güvenilirliği"].map((label) => (
                    <th key={label} className={thClass} style={thStyle}>{label}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {team.data.items.map((f) => (
                  <tr
                    key={f.id}
                    onClick={() => navigate(`/foremen/${f.id}`)}
                    className={`cursor-pointer ${rowHoverClass}`}
                    style={rowStyle}
                  >
                    <td className={`${tdClass} font-medium`} style={{ color: "var(--text-primary)" }}>{f.full_name ?? "-"}</td>
                    <td className={tdClass} style={{ color: "var(--text-muted)" }}>{f.employee_number ?? "-"}</td>
                    <td className={tdClass} style={{ color: "var(--text-secondary)" }}>{f.shift?.name ?? "-"}</td>
                    <td className={`${tdClass} font-medium tabular-nums`} style={{ color: "var(--text-primary)" }}>{f.total_score.toFixed(1)}</td>
                    <td className={tdClass}><PerformanceLevelBadge level={f.level} /></td>
                    <td className={tdClass}>
                      {f.is_reliable ? (
                        <span className="text-xs" style={{ color: "var(--text-muted)" }}>Tam</span>
                      ) : (
                        <span className="flex items-center gap-1 text-xs font-medium text-amber-600">
                          <AlertTriangle size={12} strokeWidth={2} />
                          Eksik veri
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Card title="KPI Detayları">
        {kpis.isLoading && <LoadingState />}
        {kpis.data && kpis.data.items.length === 0 && <EmptyState />}
        {kpis.data && kpis.data.items.length > 0 && (
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-5">
            {kpis.data.items.map((k) => (
              <div key={k.kpi_id} className="rounded-md p-3" style={{ border: "1px solid var(--border)" }}>
                <p className="text-xs font-medium" style={{ color: "var(--text-muted)" }}>{k.name}</p>
                <p className="mt-1 text-lg font-semibold tabular-nums" style={{ color: "var(--text-primary)" }}>{k.avg_capped_score.toFixed(1)}</p>
                <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                  Hedef: {k.avg_target?.toFixed(1)} {k.unit} · Gerç.: {k.avg_actual?.toFixed(1)} {k.unit}
                </p>
                <p className="text-xs" style={{ color: "var(--text-muted)" }}>Ağırlık: %{k.weight}</p>
              </div>
            ))}
          </div>
        )}
      </Card>

      {chiefId && <RelatedActionPlans chiefId={chiefId} />}
    </div>
  );
}
