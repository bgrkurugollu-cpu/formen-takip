import { useNavigate, useSearchParams } from "react-router-dom";
import { FilterBar } from "../components/FilterBar";
import { Card, EmptyState, ErrorState, LoadingState } from "../components/StateViews";
import { RankingBarChart } from "../components/charts/RankingBarChart";
import { TrendChart } from "../components/charts/TrendChart";
import { ForemanKpiTargetChart } from "../components/charts/ForemanKpiTargetChart";
import { ForemanScoreRow } from "../components/ForemanRankingCard";
import { useKpiAnalysis, useKpis } from "../api/hooks";
import { useFilters, type FilterState } from "../hooks/useFilters";
import { categoricalColor } from "../lib/chartColors";
import { useTheme } from "../context/ThemeContext";

function periodLabel(filters: FilterState): string {
  const from = new Date(filters.dateFrom);
  const to = new Date(filters.dateTo);
  const sameMonth = from.getFullYear() === to.getFullYear() && from.getMonth() === to.getMonth();
  if (sameMonth) return to.toLocaleDateString("tr-TR", { month: "long", year: "numeric" });
  const fmt = (d: Date) => d.toLocaleDateString("tr-TR", { day: "2-digit", month: "2-digit", year: "numeric" });
  return `${fmt(from)} – ${fmt(to)}`;
}

function scopeLabel(filters: FilterState): string {
  if (filters.plantIds.length === 1) return "1 Tesis";
  if (filters.plantIds.length > 1) return `${filters.plantIds.length} Tesis`;
  if (filters.factoryIds.length === 1) return "1 Fabrika";
  if (filters.factoryIds.length > 1) return `${filters.factoryIds.length} Fabrika`;
  return "Tüm Tesisler";
}

export function KpiAnalysisPage() {
  const { filters, setFilters, clearFilters, asQueryParams } = useFilters();
  const { theme } = useTheme();
  const isDark = theme === "dark";
  const kpis = useKpis();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const selectedKpiId = searchParams.get("kpi") ?? kpis.data?.items[0]?.id ?? null;

  const selectKpi = (id: string) => {
    const next = new URLSearchParams(searchParams);
    next.set("kpi", id);
    setSearchParams(next, { replace: true });
  };

  const analysis = useKpiAnalysis(selectedKpiId ?? undefined, asQueryParams);

  return (
    <div className="flex flex-col gap-4">
      <FilterBar filters={filters} setFilters={setFilters} clearFilters={clearFilters} />

      <div className="flex flex-wrap gap-2">
        {kpis.data?.items.map((k) => {
          const active = selectedKpiId === k.id;
          return (
            <button
              key={k.id}
              onClick={() => selectKpi(k.id)}
              className="rounded-md px-3 py-1.5 text-[13px] font-medium transition-colors"
              style={
                active
                  ? { background: "var(--accent)", color: "#ffffff" }
                  : { border: "1px solid var(--border-strong)", color: "var(--text-secondary)" }
              }
            >
              {k.name}
            </button>
          );
        })}
      </div>

      {analysis.isLoading && <LoadingState />}
      {analysis.isError && <ErrorState />}
      {analysis.data && (
        <>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
            <Card title="Şirket Ortalama Puanı"><p className="text-2xl font-semibold tabular-nums" style={{ color: "var(--text-primary)" }}>{analysis.data.company_avg_score.toFixed(1)}</p></Card>
            <Card title="Ortalama Hedef"><p className="text-2xl font-semibold tabular-nums" style={{ color: "var(--text-primary)" }}>{analysis.data.company_avg_target?.toFixed(2) ?? "-"}</p></Card>
            <Card title="Ortalama Gerçekleşen"><p className="text-2xl font-semibold tabular-nums" style={{ color: "var(--text-primary)" }}>{analysis.data.company_avg_actual?.toFixed(2) ?? "-"}</p></Card>
          </div>

          <Card title="Haftalık Trend">
            <TrendChart points={analysis.data.trend.map((t) => ({ date: t.date, total_score: t.score, is_reliable: true }))} />
          </Card>

          <Card>
            <ForemanKpiTargetChart
              points={analysis.data.foreman_values}
              target={analysis.data.company_avg_target}
              unit={analysis.data.kpi.unit}
              kpiName={analysis.data.kpi.name}
              decimalPlaces={analysis.data.kpi.decimal_places}
              subtitle={`${periodLabel(filters)} · ${scopeLabel(filters)}`}
            />
          </Card>

          <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
            <Card title="En Başarılı Tesisler">
              <RankingBarChart
                items={analysis.data.best_plants.map((p, i) => ({ name: p.name ?? "-", score: p.score ?? 0, color: categoricalColor(i, isDark) }))}
              />
            </Card>
            <Card title="En Düşük Performanslı Tesisler">
              <RankingBarChart
                items={analysis.data.worst_plants.map((p, i) => ({ name: p.name ?? "-", score: p.score ?? 0, color: categoricalColor(i, isDark) }))}
              />
            </Card>
          </div>

          <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
            <Card title="Vardiya Karşılaştırması">
              <RankingBarChart
                items={analysis.data.shift_comparison.map((s, i) => ({ name: s.name, score: s.score, color: categoricalColor(i, isDark) }))}
              />
            </Card>
            <Card title="En Başarılı Formenler">
              <div className="flex flex-col gap-0.5">
                {analysis.data.best_foremen.length === 0 && <EmptyState message="Veri yok" />}
                {analysis.data.best_foremen.map((f, i) => (
                  <ForemanScoreRow
                    key={f.id}
                    id={f.id}
                    name={f.name ?? "-"}
                    score={f.score ?? 0}
                    rank={i + 1}
                    color="#16a34a"
                    showRankTint
                    onNavigate={(id) => navigate(`/foremen/${id}`)}
                  />
                ))}
              </div>
            </Card>
            <Card title="En Düşük Performanslı Formenler">
              <div className="flex flex-col gap-0.5">
                {analysis.data.worst_foremen.length === 0 && <EmptyState message="Veri yok" />}
                {analysis.data.worst_foremen.map((f, i) => (
                  <ForemanScoreRow
                    key={f.id}
                    id={f.id}
                    name={f.name ?? "-"}
                    score={f.score ?? 0}
                    rank={i + 1}
                    color="#ea580c"
                    showRankTint={false}
                    onNavigate={(id) => navigate(`/foremen/${id}`)}
                  />
                ))}
              </div>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
