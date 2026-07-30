import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { FilterBar } from "../components/FilterBar";
import { Card, ErrorState, LoadingState } from "../components/StateViews";
import { RankingBarChart } from "../components/charts/RankingBarChart";
import { TrendChart } from "../components/charts/TrendChart";
import { RelatedActionPlans } from "../components/RelatedActionPlans";
import { useKpiAnalysis, useKpis } from "../api/hooks";
import { useFilters } from "../hooks/useFilters";
import { categoricalColor } from "../lib/chartColors";
import { useTheme } from "../context/ThemeContext";

export function KpiAnalysisPage() {
  const { filters, setFilters, clearFilters, asQueryParams } = useFilters();
  const { theme } = useTheme();
  const isDark = theme === "dark";
  const kpis = useKpis();
  const [selectedKpiId, setSelectedKpiId] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    if (!selectedKpiId && kpis.data?.items.length) {
      setSelectedKpiId(kpis.data.items[0].id);
    }
  }, [kpis.data, selectedKpiId]);

  const analysis = useKpiAnalysis(selectedKpiId ?? undefined, asQueryParams);

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-lg font-semibold" style={{ color: "var(--text-primary)" }}>KPI Analizi</h1>
        <p className="text-[13px]" style={{ color: "var(--text-muted)" }}>Her KPI için tesis, vardiya ve formen bazlı derinlemesine analiz.</p>
      </div>

      <FilterBar filters={filters} setFilters={setFilters} clearFilters={clearFilters} />

      <div className="flex flex-wrap gap-2">
        {kpis.data?.items.map((k) => {
          const active = selectedKpiId === k.id;
          return (
            <button
              key={k.id}
              onClick={() => setSelectedKpiId(k.id)}
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
              <ul className="flex flex-col gap-2 text-[13px]">
                {analysis.data.best_foremen.map((f) => (
                  <li key={f.id} className="flex justify-between">
                    <button onClick={() => navigate(`/foremen/${f.id}`)} className="text-left hover:underline" style={{ color: "var(--text-secondary)" }}>{f.name}</button>
                    <span className="font-semibold tabular-nums" style={{ color: "var(--accent)" }}>{f.score?.toFixed(1)}</span>
                  </li>
                ))}
              </ul>
            </Card>
            <Card title="En Düşük Performanslı Formenler">
              <ul className="flex flex-col gap-2 text-[13px]">
                {analysis.data.worst_foremen.map((f) => (
                  <li key={f.id} className="flex justify-between">
                    <button onClick={() => navigate(`/foremen/${f.id}`)} className="text-left hover:underline" style={{ color: "var(--text-secondary)" }}>{f.name}</button>
                    <span className="font-medium tabular-nums" style={{ color: "var(--text-primary)" }}>{f.score?.toFixed(1)}</span>
                  </li>
                ))}
              </ul>
            </Card>
          </div>

          {selectedKpiId && <RelatedActionPlans kpiId={selectedKpiId} />}
        </>
      )}
    </div>
  );
}
