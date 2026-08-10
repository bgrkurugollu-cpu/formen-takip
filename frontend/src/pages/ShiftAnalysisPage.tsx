import { useMemo, useState } from "react";
import { CalendarRange, Factory, Gauge, SearchCheck, TrendingUp } from "lucide-react";
import { useFilterOptions, useShiftAnalysisCards } from "../api/hooks";
import { useShiftAnalysisFilters } from "../hooks/useShiftAnalysisFilters";
import { Card, EmptyState, ErrorState, LoadingState } from "../components/StateViews";
import { ShiftAnomalyCard } from "../components/ShiftAnomalyCard";
import { ShiftAnomalyDetailModal } from "../components/ShiftAnomalyDetailModal";
import { MultiSelect } from "../components/FilterBar";
import type { ShiftAnomalyCard as ShiftAnomalyCardData } from "../api/types";
import { fieldClass, fieldStyle, labelClass, labelStyle } from "../lib/formStyles";

function SummaryTile({
  label, value, icon: Icon, accent,
}: { label: string; value: string; icon: typeof SearchCheck; accent?: string }) {
  return (
    <div
      className="rounded-lg p-4"
      style={{ background: "var(--surface)", border: "1px solid var(--border)", borderTop: `2px solid ${accent ?? "var(--accent)"}` }}
    >
      <div className="flex items-center gap-1.5">
        <Icon size={13} strokeWidth={2} style={{ color: accent ?? "var(--text-muted)" }} />
        <p className="text-[11px] font-semibold uppercase tracking-wide" style={{ color: "var(--text-muted)" }}>{label}</p>
      </div>
      <p className="mt-1.5 text-xl font-semibold tabular-nums" style={{ color: "var(--text-primary)" }}>{value}</p>
    </div>
  );
}

export function ShiftAnalysisPage() {
  const { filters, setFilters, clearFilters, asQueryParams, activeFilterCount } = useShiftAnalysisFilters();
  const [selectedCard, setSelectedCard] = useState<ShiftAnomalyCardData | null>(null);

  const filterOptions = useFilterOptions();
  const cards = useShiftAnalysisCards(asQueryParams);
  const summary = cards.data?.summary;

  const plantsForFactory = useMemo(() => {
    const plants = filterOptions.data?.plants ?? [];
    if (filters.factoryIds.length === 0) return plants;
    const allowed = new Set(filters.factoryIds);
    return plants.filter((p) => allowed.has(p.factory_id));
  }, [filterOptions.data, filters.factoryIds]);

  const handleFactoryChange = (ids: string[]) => {
    const allowed = new Set(ids);
    const factoryIdByPlant = new Map((filterOptions.data?.plants ?? []).map((p) => [p.id, p.factory_id]));
    setFilters({
      factoryIds: ids,
      plantIds:
        allowed.size === 0
          ? filters.plantIds
          : filters.plantIds.filter((plantId) => allowed.has(factoryIdByPlant.get(plantId) ?? "")),
    });
  };

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h2 className="text-lg font-semibold" style={{ color: "var(--text-primary)" }}>Vardiya Analizi</h2>
        <p className="mt-0.5 text-sm" style={{ color: "var(--text-muted)" }}>
          Bir önce tamamlanan ay içindeki vardiya bazlı anormal performans farklarını otomatik tespit eden analiz ekranı.
        </p>
      </div>

      {summary && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-5">
          <SummaryTile label="İncelenen Dönem" value={summary.period.label} icon={CalendarRange} />
          <SummaryTile label="Toplam Tespit Edilen Anomali" value={String(summary.total_anomalies)} icon={SearchCheck} />
          <SummaryTile label="En Çok Anomali Görülen Tesis" value={summary.top_plant?.name ?? "-"} icon={Factory} accent="#1d4ed8" />
          <SummaryTile label="En Çok Anomali Görülen KPI" value={summary.top_kpi?.name ?? "-"} icon={Gauge} accent="#7c3aed" />
          <SummaryTile
            label="En Yüksek Fark Oranı"
            value={summary.max_pct_diff !== null ? `%${summary.max_pct_diff.toFixed(1)}` : "-"}
            icon={TrendingUp}
            accent="#b91c1c"
          />
        </div>
      )}

      <div className="flex flex-wrap items-end gap-2 rounded-lg p-3" style={{ background: "var(--surface)", border: "1px solid var(--border)" }}>
        <MultiSelect
          label="Fabrika"
          options={(filterOptions.data?.factories ?? []).map((f) => ({ id: f.id, name: f.code }))}
          selected={filters.factoryIds}
          onChange={handleFactoryChange}
          disabled={filterOptions.isLoading}
        />
        <MultiSelect
          label="Tesis"
          options={plantsForFactory.map((p) => ({ id: p.id, name: p.name }))}
          selected={filters.plantIds}
          onChange={(ids) => setFilters({ plantIds: ids })}
          disabled={filterOptions.isLoading}
        />
        <MultiSelect
          label="KPI"
          options={(filterOptions.data?.kpis ?? []).map((k) => ({ id: k.id, name: k.name }))}
          selected={filters.kpiIds}
          onChange={(ids) => setFilters({ kpiIds: ids })}
          disabled={filterOptions.isLoading}
        />
        <MultiSelect
          label="Vardiya"
          options={(filterOptions.data?.shifts ?? []).map((s) => ({ id: s.id, name: s.name }))}
          selected={filters.shiftIds}
          onChange={(ids) => setFilters({ shiftIds: ids })}
          disabled={filterOptions.isLoading}
        />
        <div>
          <label className={labelClass} style={labelStyle}>Anomali Seviyesi</label>
          <select
            className={fieldClass}
            style={fieldStyle}
            value={filters.severity}
            onChange={(e) => setFilters({ severity: e.target.value as never })}
          >
            <option value="">Tümü</option>
            <option value="high">Yüksek</option>
            <option value="medium">Orta</option>
          </select>
        </div>
        {activeFilterCount > 0 && (
          <button
            onClick={clearFilters}
            className="ml-auto flex items-center gap-1 rounded-md px-2.5 py-1.5 text-xs font-medium hover:bg-[var(--page-bg)]"
            style={{ color: "var(--accent)" }}
          >
            Filtreleri temizle ({activeFilterCount})
          </button>
        )}
      </div>

      <Card>
        {cards.isLoading && <LoadingState label="Tespit kartları yükleniyor..." />}
        {cards.isError && <ErrorState />}
        {cards.data && cards.data.items.length === 0 && (
          <EmptyState message="Seçilen filtrelerle eşleşen bir vardiya anomalisi bulunamadı." />
        )}
        {cards.data && cards.data.items.length > 0 && (
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2 xl:grid-cols-3">
            {cards.data.items.map((card) => (
              <ShiftAnomalyCard key={card.id} card={card} onViewDetail={setSelectedCard} />
            ))}
          </div>
        )}
      </Card>

      {selectedCard && <ShiftAnomalyDetailModal card={selectedCard} onClose={() => setSelectedCard(null)} />}
    </div>
  );
}
