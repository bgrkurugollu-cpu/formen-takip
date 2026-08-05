import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { AlertTriangle, ChevronLeft, X } from "lucide-react";
import { FilterBar } from "../components/FilterBar";
import { Card, EmptyState, ErrorState, LoadingState } from "../components/StateViews";
import { PerformanceLevelBadge } from "../components/PerformanceLevelBadge";
import { TrendChart } from "../components/charts/TrendChart";
import { KpiRadarChart } from "../components/charts/KpiRadarChart";
import { RelatedActionPlans } from "../components/RelatedActionPlans";
import { ForemanContributionSummary } from "../components/ForemanContributionSummary";
import {
  useForemanAssignmentHistory, useForemanCalculationDetail, useForemanDetail,
  useForemanKpis, useForemanTrend,
} from "../api/hooks";
import { useFilters } from "../hooks/useFilters";
import type { ForemanKpiItem } from "../api/types";

function CalculationDetailModal({ foremanId, kpi, onClose }: { foremanId: string; kpi: ForemanKpiItem; onClose: () => void }) {
  const detail = useForemanCalculationDetail(foremanId, kpi.kpi_id);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={onClose}>
      <div
        className="max-h-[85vh] w-full max-w-md overflow-y-auto rounded-lg p-5 shadow-xl"
        style={{ background: "var(--surface)" }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>{kpi.name} — Hesaplama Detayı</h3>
          <button onClick={onClose} style={{ color: "var(--text-muted)" }}>
            <X size={16} strokeWidth={2} />
          </button>
        </div>
        {detail.isLoading && <LoadingState />}
        {detail.isError && <ErrorState />}
        {detail.data && (
          <dl className="grid grid-cols-2 gap-x-4 gap-y-2.5 text-[13px]">
            <dt style={{ color: "var(--text-muted)" }}>Tarih</dt>
            <dd className="text-right font-medium tabular-nums" style={{ color: "var(--text-primary)" }}>{detail.data.performance_date}</dd>
            <dt style={{ color: "var(--text-muted)" }}>Hedef Değer</dt>
            <dd className="text-right font-medium tabular-nums" style={{ color: "var(--text-primary)" }}>{detail.data.target_value?.toFixed(2)} {detail.data.unit}</dd>
            <dt style={{ color: "var(--text-muted)" }}>Gerçekleşen Değer</dt>
            <dd className="text-right font-medium tabular-nums" style={{ color: "var(--text-primary)" }}>{detail.data.actual_value?.toFixed(2)} {detail.data.unit}</dd>
            <dt style={{ color: "var(--text-muted)" }}>Hesaplama Türü</dt>
            <dd className="text-right font-medium" style={{ color: "var(--text-primary)" }}>{detail.data.calculation_type}</dd>
            <dt style={{ color: "var(--text-muted)" }}>Ham Puan</dt>
            <dd className="text-right font-medium tabular-nums" style={{ color: "var(--text-primary)" }}>{detail.data.raw_score.toFixed(2)}</dd>
            <dt style={{ color: "var(--text-muted)" }}>Sınırlandırılmış Puan</dt>
            <dd className="text-right font-medium tabular-nums" style={{ color: "var(--text-primary)" }}>{detail.data.capped_score.toFixed(2)}</dd>
            <dt style={{ color: "var(--text-muted)" }}>Min / Maks Puan</dt>
            <dd className="text-right font-medium tabular-nums" style={{ color: "var(--text-primary)" }}>{detail.data.min_score} / {detail.data.max_score}</dd>
            <dt style={{ color: "var(--text-muted)" }}>KPI Ağırlığı</dt>
            <dd className="text-right font-medium tabular-nums" style={{ color: "var(--text-primary)" }}>%{detail.data.kpi_weight}</dd>
            <dt style={{ color: "var(--text-muted)" }}>Toplam Puana Katkı</dt>
            <dd className="text-right font-medium tabular-nums" style={{ color: "var(--text-primary)" }}>{detail.data.weighted_contribution.toFixed(2)}</dd>
            <dt style={{ color: "var(--text-muted)" }}>Hesaplama Kuralı Versiyonu</dt>
            <dd className="text-right font-medium" style={{ color: "var(--text-primary)" }}>v{detail.data.calculation_version}</dd>
            <dt style={{ color: "var(--text-muted)" }}>Veri Kaynağı</dt>
            <dd className="text-right font-medium" style={{ color: "var(--text-primary)" }}>{detail.data.data_source}</dd>
            <dt style={{ color: "var(--text-muted)" }}>Kaynak Kayıt ID</dt>
            <dd className="truncate text-right font-mono text-xs" style={{ color: "var(--text-secondary)" }}>{detail.data.source_record_id}</dd>
          </dl>
        )}
      </div>
    </div>
  );
}

export function ForemanDetailPage() {
  const { foremanId } = useParams<{ foremanId: string }>();
  const { filters, setFilters, clearFilters, asQueryParams } = useFilters();
  const navigate = useNavigate();
  const [selectedKpi, setSelectedKpi] = useState<ForemanKpiItem | null>(null);

  const foreman = useForemanDetail(foremanId, asQueryParams);
  const kpis = useForemanKpis(foremanId, asQueryParams);
  const trend = useForemanTrend(foremanId, asQueryParams, "day");
  const history = useForemanAssignmentHistory(foremanId);

  if (foreman.isLoading) return <LoadingState />;
  if (foreman.isError || !foreman.data) return <ErrorState message="Formen bulunamadı." />;

  const f = foreman.data;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div>
          <button
            onClick={() => navigate("/foremen")}
            className="mb-1.5 flex items-center gap-1 text-xs font-medium hover:underline"
            style={{ color: "var(--accent)" }}
          >
            <ChevronLeft size={13} strokeWidth={2} />
            Formenler
          </button>
          <h1 className="text-lg font-semibold" style={{ color: "var(--text-primary)" }}>{f.full_name}</h1>
          <p className="text-[13px]" style={{ color: "var(--text-muted)" }}>
            {f.employee_number} · {f.plant?.name} · {f.chief?.name} · {f.shift?.name}
          </p>
        </div>
        <div className="text-right">
          <div className="text-2xl font-semibold tabular-nums" style={{ color: "var(--text-primary)" }}>{f.total_score.toFixed(1)}</div>
          <div className="mt-1"><PerformanceLevelBadge level={f.level} /></div>
          {!f.is_reliable && (
            <p className="mt-1.5 flex items-center justify-end gap-1 text-xs font-medium text-amber-600">
              <AlertTriangle size={12} strokeWidth={2} />
              Eksik KPI verisi
            </p>
          )}
        </div>
      </div>

      <FilterBar filters={filters} setFilters={setFilters} clearFilters={clearFilters} />

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Card title="Şirket Sıralaması"><p className="text-xl font-semibold tabular-nums" style={{ color: "var(--text-primary)" }}>{f.company_rank ?? "-"} / {f.company_total}</p></Card>
        <Card title="Tesis İçi Sıralaması"><p className="text-xl font-semibold tabular-nums" style={{ color: "var(--text-primary)" }}>{f.plant_rank ?? "-"} / {f.plant_total}</p></Card>
        <Card title="Göreve Başlama"><p className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>{f.hire_date}</p></Card>
        <Card title="Durum"><p className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>{f.is_active ? "Aktif" : "Pasif"}</p></Card>
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <Card title="Performans Trendi">
          {trend.isLoading ? <LoadingState /> : trend.data ? <TrendChart points={trend.data.points} /> : <ErrorState />}
        </Card>
        <Card title="KPI Radar Grafiği">
          {kpis.isLoading ? <LoadingState /> : kpis.data ? <KpiRadarChart items={kpis.data.items} /> : <ErrorState />}
        </Card>
      </div>

      <Card title="KPI Detayları (kart üzerine tıklayarak hesaplama detayını görüntüleyin)">
        {kpis.isLoading && <LoadingState />}
        {kpis.data && kpis.data.items.length === 0 && <EmptyState />}
        {kpis.data && kpis.data.items.length > 0 && (
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-5">
            {kpis.data.items.map((k) => (
              <button
                key={k.kpi_id}
                onClick={() => setSelectedKpi(k)}
                title={k.description ?? undefined}
                className="rounded-md p-3 text-left transition-colors hover:border-[var(--accent)]"
                style={{ border: "1px solid var(--border)" }}
              >
                <p className="text-xs font-medium" style={{ color: "var(--text-muted)" }}>{k.name}</p>
                <p className="mt-1 text-lg font-semibold tabular-nums" style={{ color: "var(--text-primary)" }}>{k.avg_capped_score.toFixed(1)}</p>
                <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                  Hedef: {k.avg_target?.toFixed(1)} {k.unit} · Gerç.: {k.avg_actual?.toFixed(1)} {k.unit}
                </p>
                <p className="text-xs" style={{ color: "var(--text-muted)" }}>Ağırlık: %{k.weight}</p>
                {k.agir_gitme && (
                  <p className="mt-1 text-xs font-medium" style={{ color: "var(--text-secondary)" }}>
                    {k.agir_gitme.direction === "OVERWEIGHT" ? "Üst gramaj yönünde" : k.agir_gitme.direction === "UNDERWEIGHT" ? "Alt gramaj yönünde" : "Hedefte"} sapma
                  </p>
                )}
                {k.inkita && (
                  <p className="mt-1 text-xs" style={{ color: "var(--text-secondary)" }}>Diğer duruş puana dahil değil</p>
                )}
                {k.plana_uyum && (
                  <p className="mt-1 text-xs font-medium" style={{ color: "var(--text-secondary)" }}>
                    {k.plana_uyum.direction === "OVER_PLAN" ? "Plan üstü" : k.plana_uyum.direction === "UNDER_PLAN" ? "Plan altı" : "Plana uygun"} üretim
                  </p>
                )}
              </button>
            ))}
          </div>
        )}
      </Card>

      {foremanId && <ForemanContributionSummary foremanId={foremanId} />}

      <Card title="Tesis / Şef / Vardiya Atama Geçmişi">
        {history.isLoading && <LoadingState />}
        {history.data && (
          <ul className="flex flex-col gap-2 text-[13px]">
            {history.data.items.map((item, idx) => (
              <li key={idx} className="flex items-center justify-between pb-2 last:pb-0" style={idx < history.data!.items.length - 1 ? { borderBottom: "1px solid var(--border)" } : undefined}>
                <span style={{ color: "var(--text-primary)" }}>
                  {item.plant} · {item.chief} · {item.shift}
                </span>
                <span className="text-xs tabular-nums" style={{ color: "var(--text-muted)" }}>
                  {item.start_date} — {item.end_date ?? "devam ediyor"}
                </span>
              </li>
            ))}
          </ul>
        )}
      </Card>

      {foremanId && <RelatedActionPlans foremanId={foremanId} />}

      {selectedKpi && foremanId && (
        <CalculationDetailModal foremanId={foremanId} kpi={selectedKpi} onClose={() => setSelectedKpi(null)} />
      )}
    </div>
  );
}
