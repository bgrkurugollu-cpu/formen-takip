import { useMemo } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import { ChevronLeft } from "lucide-react";
import { FilterBar } from "../components/FilterBar";
import { Card, EmptyState, ErrorState, LoadingState } from "../components/StateViews";
import { PerformanceLevelBadge } from "../components/PerformanceLevelBadge";
import { KpiBarChart } from "../components/charts/KpiBarChart";
import { RankingBarChart } from "../components/charts/RankingBarChart";
import { useFilterOptions, useForemanRanking, useKpiSummary, usePlantRanking, useShiftComparison } from "../api/hooks";
import { useFilters } from "../hooks/useFilters";
import { withSearchParam } from "../lib/chartDrilldown";
import { rowHoverClass, rowStyle, tdClass, thClass, theadRowStyle, thStyle } from "../lib/tableStyles";

export function ShiftDetailPage() {
  const { shiftId } = useParams<{ shiftId: string }>();
  const { filters, setFilters, clearFilters, asQueryParams } = useFilters();
  const navigate = useNavigate();
  const location = useLocation();

  // Bu sayfa belirli bir vardiyaya sabitlenmiştir: aktif filtrelerin üzerine (varsa)
  // FilterBar'daki Vardiya seçimini değil, her zaman rota parametresindeki vardiyayı uygular.
  const scopedParams = useMemo(() => ({ ...asQueryParams, shift_ids: shiftId }), [asQueryParams, shiftId]);
  // Bu sayfadan çıkışta ("Tesis"e / "Formen"e git) vardiya bağlamının kaybolmaması için taşınır.
  const searchWithShift = withSearchParam(location.search, "shift_ids", shiftId ?? "");

  const filterOptions = useFilterOptions();
  const shift = filterOptions.data?.shifts.find((s) => s.id === shiftId);

  const shiftComparison = useShiftComparison(scopedParams);
  const shiftScore = shiftComparison.data?.items.find((s) => s.shift_id === shiftId);

  const kpiSummary = useKpiSummary(scopedParams);
  const plantRanking = usePlantRanking(scopedParams, "desc", 50);
  const foremanRanking = useForemanRanking(scopedParams, "desc", 100);

  const strongestKpi = kpiSummary.data?.items.length
    ? kpiSummary.data.items.reduce((best, k) => (k.avg_score > best.avg_score ? k : best))
    : null;
  const weakestKpi = kpiSummary.data?.items.length
    ? kpiSummary.data.items.reduce((worst, k) => (k.avg_score < worst.avg_score ? k : worst))
    : null;
  const criticalForemanCount = foremanRanking.data?.items.filter((f) => f.level.name === "Kritik").length ?? 0;

  if (filterOptions.isLoading) return <LoadingState />;
  if (!shift) return <ErrorState message="Vardiya bulunamadı." />;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div>
          <button
            onClick={() => navigate({ pathname: "/", search: location.search })}
            className="flex items-center gap-1 text-xs font-medium hover:underline"
            style={{ color: "var(--accent)" }}
          >
            <ChevronLeft size={13} strokeWidth={2} />
            Genel Bakış
          </button>
          <h1 className="mt-1 text-lg font-semibold" style={{ color: "var(--text-primary)" }}>{shift.name}</h1>
        </div>
        {shiftScore && (
          <div className="text-right">
            <div className="text-2xl font-semibold tabular-nums" style={{ color: "var(--text-primary)" }}>{shiftScore.total_score.toFixed(1)}</div>
            <div className="mt-1"><PerformanceLevelBadge level={shiftScore.level} /></div>
          </div>
        )}
      </div>

      <FilterBar filters={filters} setFilters={setFilters} clearFilters={clearFilters} />

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Card title="Aktif Formen"><p className="text-xl font-semibold tabular-nums" style={{ color: "var(--text-primary)" }}>{foremanRanking.data?.items.length ?? 0}</p></Card>
        <Card title="Kritik Formen"><p className="text-xl font-semibold tabular-nums text-red-600">{criticalForemanCount}</p></Card>
        <Card title="En Güçlü KPI">
          <p className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>{strongestKpi?.name ?? "-"}</p>
          <p className="text-xs" style={{ color: "var(--text-muted)" }}>{strongestKpi ? `${strongestKpi.avg_score.toFixed(1)} puan` : ""}</p>
        </Card>
        <Card title="En Düşük KPI">
          <p className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>{weakestKpi?.name ?? "-"}</p>
          <p className="text-xs" style={{ color: "var(--text-muted)" }}>{weakestKpi ? `${weakestKpi.avg_score.toFixed(1)} puan` : ""}</p>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <Card title="KPI Bazlı Vardiya Performansı">
          {kpiSummary.isLoading ? (
            <LoadingState />
          ) : kpiSummary.data ? (
            <KpiBarChart
              items={kpiSummary.data.items}
              onSelect={(item) =>
                navigate({ pathname: "/kpis", search: withSearchParam(searchWithShift, "kpi", item.id) })
              }
            />
          ) : (
            <ErrorState />
          )}
        </Card>
        <Card title="Tesis Bazlı Sonuçlar">
          {plantRanking.isLoading ? (
            <LoadingState />
          ) : plantRanking.data ? (
            <RankingBarChart
              items={plantRanking.data.items.map((p) => ({ id: p.plant_id, name: p.name, score: p.total_score, color: p.level.color }))}
              onSelect={(item) => navigate({ pathname: `/plants/${item.id}`, search: searchWithShift })}
            />
          ) : (
            <ErrorState />
          )}
        </Card>
      </div>

      <Card title="Formen Bazlı Sonuçlar">
        {foremanRanking.isLoading && <LoadingState />}
        {foremanRanking.data && foremanRanking.data.items.length === 0 && <EmptyState />}
        {foremanRanking.data && foremanRanking.data.items.length > 0 && (
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
                {foremanRanking.data.items.map((f) => (
                  <tr
                    key={f.foreman_id}
                    onClick={() => navigate({ pathname: `/foremen/${f.foreman_id}`, search: searchWithShift })}
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
    </div>
  );
}
