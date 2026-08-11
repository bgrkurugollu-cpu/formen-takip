import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { HardHat, ShieldAlert, Trophy } from "lucide-react";
import { FilterBar } from "../components/FilterBar";
import { StatCard } from "../components/StatCard";
import { Card } from "../components/StateViews";
import { LoadingState, ErrorState } from "../components/StateViews";
import { TrendChart } from "../components/charts/TrendChart";
import { KpiBarChart } from "../components/charts/KpiBarChart";
import { RankingBarChart } from "../components/charts/RankingBarChart";
import { DistributionChart } from "../components/charts/DistributionChart";
import { ForemanRankingCard } from "../components/ForemanRankingCard";
import { PerformanceLevelDetailModal } from "../components/PerformanceLevelDetailModal";
import { CriticalAnomalyCard } from "../components/CriticalAnomalyCard";
import { PlantHeatmap } from "../components/PlantHeatmap";
import type { DistributionItem } from "../api/types";
import {
  useDashboardSummary, useDashboardTrend, useKpiSummary,
  useShiftComparison, useForemanRanking, useForemanTrendRanking, usePerformanceDistribution,
} from "../api/hooks";
import { useFilters } from "../hooks/useFilters";
import { withSearchParam } from "../lib/chartDrilldown";

export function DashboardPage() {
  const { filters, setFilters, clearFilters, asQueryParams } = useFilters();
  const navigate = useNavigate();
  const location = useLocation();

  const summary = useDashboardSummary(asQueryParams);
  const trend = useDashboardTrend(asQueryParams, "day");
  const kpiSummary = useKpiSummary(asQueryParams);
  const shiftComparison = useShiftComparison(asQueryParams);
  const foremanRankingTop = useForemanRanking(asQueryParams, "desc", 5);
  const foremanRankingBottom = useForemanRanking(asQueryParams, "asc", 5);
  const foremanTrendImproving = useForemanTrendRanking(asQueryParams, "improving", 5);
  const foremanTrendDeclining = useForemanTrendRanking(asQueryParams, "declining", 5);
  const distribution = usePerformanceDistribution(asQueryParams);
  const [selectedLevel, setSelectedLevel] = useState<DistributionItem | null>(null);

  return (
    <div className="flex flex-col gap-4">
      <FilterBar filters={filters} setFilters={setFilters} clearFilters={clearFilters} />

      {summary.isLoading && <LoadingState />}
      {summary.isError && <ErrorState />}
      {summary.data && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-6">
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

      <CriticalAnomalyCard />

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
          {distribution.isLoading ? (
            <LoadingState />
          ) : distribution.data ? (
            <DistributionChart items={distribution.data.items} onSelect={setSelectedLevel} />
          ) : (
            <ErrorState />
          )}
        </Card>
      </div>

      <PlantHeatmap filters={asQueryParams} levels={distribution.data?.items} />

      {selectedLevel && (
        <PerformanceLevelDetailModal
          level={selectedLevel}
          filterParams={asQueryParams}
          onClose={() => setSelectedLevel(null)}
          onNavigateForeman={(id) => navigate(`/foremen/${id}`)}
        />
      )}

      <ForemanRankingCard
        filters={filters}
        topItems={foremanRankingTop.data?.items}
        topLoading={foremanRankingTop.isLoading}
        bottomItems={foremanRankingBottom.data?.items}
        bottomLoading={foremanRankingBottom.isLoading}
        improvingItems={foremanTrendImproving.data?.items}
        improvingLoading={foremanTrendImproving.isLoading}
        decliningItems={foremanTrendDeclining.data?.items}
        decliningLoading={foremanTrendDeclining.isLoading}
        onNavigateForeman={(id) => navigate(`/foremen/${id}`)}
        onViewAll={() => navigate("/foremen")}
      />

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <Card title="KPI Bazlı Ortalama Puan">
          {kpiSummary.isLoading ? (
            <LoadingState />
          ) : kpiSummary.data ? (
            <KpiBarChart
              items={kpiSummary.data.items}
              onSelect={(item) => navigate({ pathname: "/kpis", search: withSearchParam(location.search, "kpi", item.id) })}
            />
          ) : (
            <ErrorState />
          )}
        </Card>
        <Card title="Vardiya Karşılaştırması">
          {shiftComparison.isLoading ? (
            <LoadingState />
          ) : shiftComparison.data ? (
            <RankingBarChart
              items={shiftComparison.data.items.map((s) => ({ id: s.shift_id, name: s.name, score: s.total_score, color: s.level.color }))}
              onSelect={(item) => navigate({ pathname: `/shifts/${item.id}`, search: location.search })}
            />
          ) : (
            <ErrorState />
          )}
        </Card>
      </div>
    </div>
  );
}
