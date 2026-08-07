import { useNavigate } from "react-router-dom";
import { ArrowRight, HardHat, ShieldAlert, Trophy } from "lucide-react";
import { FilterBar } from "../components/FilterBar";
import { StatCard } from "../components/StatCard";
import { Card } from "../components/StateViews";
import { LoadingState, ErrorState } from "../components/StateViews";
import { TrendChart } from "../components/charts/TrendChart";
import { KpiBarChart } from "../components/charts/KpiBarChart";
import { RankingBarChart } from "../components/charts/RankingBarChart";
import { DistributionChart } from "../components/charts/DistributionChart";
import { RelatedActionPlans } from "../components/RelatedActionPlans";
import {
  useDashboardSummary, useDashboardTrend, useKpiSummary, usePlantRanking,
  useShiftComparison, useForemanRanking, usePerformanceDistribution,
} from "../api/hooks";
import { useFilters } from "../hooks/useFilters";

function ViewAllLink({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="mt-3 inline-flex items-center gap-1 text-xs font-medium hover:underline"
      style={{ color: "var(--accent)" }}
    >
      {label}
      <ArrowRight size={13} strokeWidth={2} />
    </button>
  );
}

export function DashboardPage() {
  const { filters, setFilters, clearFilters, asQueryParams } = useFilters();
  const navigate = useNavigate();

  const summary = useDashboardSummary(asQueryParams);
  const trend = useDashboardTrend(asQueryParams, "day");
  const kpiSummary = useKpiSummary(asQueryParams);
  const plantRanking = usePlantRanking(asQueryParams, "desc", 10);
  const shiftComparison = useShiftComparison(asQueryParams);
  const foremanRankingTop = useForemanRanking(asQueryParams, "desc", 5);
  const foremanRankingBottom = useForemanRanking(asQueryParams, "asc", 5);
  const distribution = usePerformanceDistribution(asQueryParams);

  return (
    <div className="flex flex-col gap-4">
      <FilterBar filters={filters} setFilters={setFilters} clearFilters={clearFilters} />

      {summary.isLoading && <LoadingState />}
      {summary.isError && <ErrorState />}
      {summary.data && (
        <div className="grid grid-cols-6 gap-3">
          <StatCard label="Aktif Formen" value={summary.data.total_active_foremen} icon={HardHat} to="/foremen" />
          <StatCard label="Mükemmel Formen" value={summary.data.foremen_excellent} icon={Trophy} />
          <StatCard label="Kritik Formen" value={summary.data.foremen_critical} icon={ShieldAlert} />
          <StatCard
            label="En Başarılı Tesis"
            value={summary.data.best_plant?.name ?? "-"}
            sub={summary.data.best_plant ? `${summary.data.best_plant.score?.toFixed(1)} puan` : undefined}
            to={summary.data.best_plant ? `/plants/${summary.data.best_plant.id}` : undefined}
          />
          <StatCard
            label="En Düşük Performanslı Tesis"
            value={summary.data.worst_plant?.name ?? "-"}
            sub={summary.data.worst_plant ? `${summary.data.worst_plant.score?.toFixed(1)} puan` : undefined}
            to={summary.data.worst_plant ? `/plants/${summary.data.worst_plant.id}` : undefined}
          />
          <StatCard
            label="En Fazla İyileştirme Gereken KPI"
            value={summary.data.weakest_kpi?.name ?? "-"}
            sub={summary.data.weakest_kpi ? `${summary.data.weakest_kpi.avg_score.toFixed(1)} puan` : undefined}
          />
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
        <div className="xl:col-span-2">
          <Card title="Genel Performans Trendi">
            {trend.isLoading ? (
              <LoadingState />
            ) : trend.data ? (
              <TrendChart
                points={trend.data.points}
                yAxisFloor={
                  foremanRankingBottom.data && foremanRankingBottom.data.items.length > 0
                    ? Math.min(...foremanRankingBottom.data.items.map((f) => f.total_score)) - 20
                    : undefined
                }
              />
            ) : (
              <ErrorState />
            )}
          </Card>
        </div>
        <Card title="Performans Dağılımı">
          {distribution.isLoading ? <LoadingState /> : distribution.data ? <DistributionChart items={distribution.data.items} /> : <ErrorState />}
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <Card title="KPI Bazlı Ortalama Puan">
          {kpiSummary.isLoading ? <LoadingState /> : kpiSummary.data ? <KpiBarChart items={kpiSummary.data.items} /> : <ErrorState />}
        </Card>
        <Card title="Vardiya Karşılaştırması">
          {shiftComparison.isLoading ? (
            <LoadingState />
          ) : shiftComparison.data ? (
            <RankingBarChart
              items={shiftComparison.data.items.map((s) => ({ name: s.name, score: s.total_score, color: s.level.color }))}
            />
          ) : (
            <ErrorState />
          )}
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <Card title="Tesis Sıralaması (İlk 10)">
          {plantRanking.isLoading ? (
            <LoadingState />
          ) : plantRanking.data ? (
            <div>
              <RankingBarChart
                items={plantRanking.data.items.map((p) => ({ name: p.name, score: p.total_score, color: p.level.color }))}
              />
              <ViewAllLink label="Tüm tesisleri görüntüle" onClick={() => navigate("/plants")} />
            </div>
          ) : (
            <ErrorState />
          )}
        </Card>

        <Card title="Formen Sıralaması">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <p className="mb-2 text-[11px] font-semibold uppercase tracking-wide" style={{ color: "var(--text-muted)" }}>En Yüksek 5</p>
              {foremanRankingTop.data?.items.map((f) => (
                <div key={f.foreman_id} className="mb-2 flex items-center justify-between gap-2 text-xs">
                  <button onClick={() => navigate(`/foremen/${f.foreman_id}`)} className="truncate text-left hover:underline" style={{ color: "var(--text-secondary)" }}>
                    {f.full_name}
                  </button>
                  <span className="font-semibold tabular-nums" style={{ color: "var(--accent)" }}>{f.total_score.toFixed(1)}</span>
                </div>
              ))}
            </div>
            <div>
              <p className="mb-2 text-[11px] font-semibold uppercase tracking-wide" style={{ color: "var(--text-muted)" }}>En Düşük 5</p>
              {foremanRankingBottom.data?.items.map((f) => (
                <div key={f.foreman_id} className="mb-2 flex items-center justify-between gap-2 text-xs">
                  <button onClick={() => navigate(`/foremen/${f.foreman_id}`)} className="truncate text-left hover:underline" style={{ color: "var(--text-secondary)" }}>
                    {f.full_name}
                  </button>
                  <span className="font-semibold tabular-nums" style={{ color: "var(--accent)" }}>{f.total_score.toFixed(1)}</span>
                </div>
              ))}
            </div>
          </div>
          <ViewAllLink label="Tüm formenleri görüntüle" onClick={() => navigate("/foremen")} />
        </Card>
      </div>

      <RelatedActionPlans title="Açık Aksiyon Planları" />
    </div>
  );
}
