import { useNavigate, useParams } from "react-router-dom";
import { ChevronLeft } from "lucide-react";
import { FilterBar } from "../components/FilterBar";
import { Card, EmptyState, ErrorState, LoadingState } from "../components/StateViews";
import { PerformanceLevelBadge } from "../components/PerformanceLevelBadge";
import { KpiBarChart } from "../components/charts/KpiBarChart";
import { RankingBarChart } from "../components/charts/RankingBarChart";
import { RelatedActionPlans } from "../components/RelatedActionPlans";
import {
  usePlantChiefs, usePlantDetail, usePlantForemen, usePlantKpis, usePlantShifts, usePlantSummary,
} from "../api/hooks";
import { useFilters } from "../hooks/useFilters";
import { rowHoverClass, rowStyle, tdClass, thClass, theadRowStyle, thStyle } from "../lib/tableStyles";

export function PlantDetailPage() {
  const { plantId } = useParams<{ plantId: string }>();
  const { filters, setFilters, clearFilters, asQueryParams } = useFilters();
  const navigate = useNavigate();

  const plant = usePlantDetail(plantId);
  const summary = usePlantSummary(plantId, asQueryParams);
  const kpis = usePlantKpis(plantId, asQueryParams);
  const shifts = usePlantShifts(plantId, asQueryParams);
  const foremen = usePlantForemen(plantId, { ...asQueryParams, page_size: 100 });
  const chiefs = usePlantChiefs(plantId, asQueryParams);

  if (plant.isLoading) return <LoadingState />;
  if (plant.isError || !plant.data) return <ErrorState message="Tesis bulunamadı." />;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div>
          <button
            onClick={() => navigate("/plants")}
            className="flex items-center gap-1 text-xs font-medium hover:underline"
            style={{ color: "var(--accent)" }}
          >
            <ChevronLeft size={13} strokeWidth={2} />
            Tesisler
          </button>
        </div>
        {summary.data && (
          <div className="text-right">
            <div className="text-2xl font-semibold tabular-nums" style={{ color: "var(--text-primary)" }}>{summary.data.total_score.toFixed(1)}</div>
            <div className="mt-1"><PerformanceLevelBadge level={summary.data.level} /></div>
          </div>
        )}
      </div>

      <FilterBar filters={filters} setFilters={setFilters} clearFilters={clearFilters} />

      {summary.data && (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <Card title="Aktif Formen"><p className="text-xl font-semibold tabular-nums" style={{ color: "var(--text-primary)" }}>{summary.data.active_foreman_count}</p></Card>
          <Card title="Kritik Formen"><p className="text-xl font-semibold tabular-nums text-red-600">{summary.data.critical_foreman_count}</p></Card>
          <Card title="En Güçlü KPI">
            <p className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>{summary.data.strongest_kpi?.name ?? "-"}</p>
            <p className="text-xs" style={{ color: "var(--text-muted)" }}>{summary.data.strongest_kpi?.avg_score.toFixed(1)} puan</p>
          </Card>
          <Card title="En Düşük KPI">
            <p className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>{summary.data.weakest_kpi?.name ?? "-"}</p>
            <p className="text-xs" style={{ color: "var(--text-muted)" }}>{summary.data.weakest_kpi?.avg_score.toFixed(1)} puan</p>
          </Card>
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <Card title="KPI Bazlı Performans">
          {kpis.isLoading ? <LoadingState /> : kpis.data ? <KpiBarChart items={kpis.data.items} /> : <ErrorState />}
        </Card>
        <Card title="Vardiya Karşılaştırması">
          {shifts.isLoading ? (
            <LoadingState />
          ) : shifts.data ? (
            <RankingBarChart items={shifts.data.items.map((s) => ({ name: s.name, score: s.total_score, color: s.level.color }))} />
          ) : (
            <ErrorState />
          )}
        </Card>
      </div>

      <Card title="Şefler">
        {chiefs.isLoading && <LoadingState />}
        {chiefs.data && chiefs.data.items.length === 0 && <EmptyState />}
        {chiefs.data && chiefs.data.items.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-[13px]">
              <thead>
                <tr style={theadRowStyle}>
                  <th className={thClass} style={thStyle}>Şef</th>
                  <th className={thClass} style={thStyle}>Sicil No</th>
                  <th className={thClass} style={thStyle}>Formen Sayısı</th>
                  <th className={thClass} style={thStyle}>Toplam Puan</th>
                  <th className={thClass} style={thStyle}>Seviye</th>
                </tr>
              </thead>
              <tbody>
                {chiefs.data.items.map((c) => (
                  <tr key={c.id} style={rowStyle}>
                    <td className={`${tdClass} font-medium`} style={{ color: "var(--text-primary)" }}>{c.full_name}</td>
                    <td className={tdClass} style={{ color: "var(--text-muted)" }}>{c.employee_number}</td>
                    <td className={`${tdClass} tabular-nums`} style={{ color: "var(--text-secondary)" }}>{c.foreman_count}</td>
                    <td className={`${tdClass} tabular-nums`} style={{ color: "var(--text-primary)" }}>{c.total_score.toFixed(1)}</td>
                    <td className={tdClass}>
                      <PerformanceLevelBadge level={c.level} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Card title="Formen Performans Listesi">
        {foremen.isLoading && <LoadingState />}
        {foremen.data && foremen.data.items.length === 0 && <EmptyState />}
        {foremen.data && foremen.data.items.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-[13px]">
              <thead>
                <tr style={theadRowStyle}>
                  <th className={thClass} style={thStyle}>Formen</th>
                  <th className={thClass} style={thStyle}>Sicil No</th>
                  <th className={thClass} style={thStyle}>Toplam Puan</th>
                  <th className={thClass} style={thStyle}>Seviye</th>
                </tr>
              </thead>
              <tbody>
                {foremen.data.items.map((f) => (
                  <tr
                    key={f.foreman_id}
                    onClick={() => navigate(`/foremen/${f.foreman_id}`)}
                    className={`cursor-pointer ${rowHoverClass}`}
                    style={rowStyle}
                  >
                    <td className={`${tdClass} font-medium`} style={{ color: "var(--text-primary)" }}>{f.full_name}</td>
                    <td className={tdClass} style={{ color: "var(--text-muted)" }}>{f.employee_number}</td>
                    <td className={`${tdClass} tabular-nums`} style={{ color: "var(--text-primary)" }}>{f.total_score.toFixed(1)}</td>
                    <td className={tdClass}>
                      <PerformanceLevelBadge level={f.level} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {plantId && <RelatedActionPlans plantId={plantId} />}
    </div>
  );
}
