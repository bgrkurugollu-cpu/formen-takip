import { useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  AlertTriangle, Building2, ChevronLeft, CircleCheck, CircleAlert,
  Download, FileText, Mail, Phone, Users, X,
} from "lucide-react";
import { FilterBar } from "../components/FilterBar";
import { Card, EmptyState, ErrorState, LoadingState } from "../components/StateViews";
import { PerformanceLevelBadge } from "../components/PerformanceLevelBadge";
import { TrendChart } from "../components/charts/TrendChart";
import { KpiRadarChart } from "../components/charts/KpiRadarChart";
import { ForemanContributionSummary } from "../components/ForemanContributionSummary";
import { apiClient } from "../api/client";
import {
  useForemanAssignmentHistory, useForemanCalculationDetail, useForemanDetail,
  useForemanKpis, useForemanMonthlyReportLatest, useForemanMonthlyReports, useForemanTrend,
  useFilterOptions, useKpiSummary,
} from "../api/hooks";
import { useFilters } from "../hooks/useFilters";
import type { ForemanKpiItem } from "../api/types";
import { fieldClass, fieldStyle } from "../lib/formStyles";

const TR_MONTHS = [
  "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
  "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık",
];

function monthlyReportLabel(year: number, month: number): string {
  return `${TR_MONTHS[month - 1]} ${year}`;
}

async function downloadMonthlyReportPdf(foremanId: string, year: number, month: number, employeeNumber: string) {
  const resp = await apiClient.get(`/foremen/${foremanId}/monthly-reports/${year}/${month}/pdf`, { responseType: "blob" });
  const url = window.URL.createObjectURL(new Blob([resp.data]));
  const a = document.createElement("a");
  a.href = url;
  a.download = `formen-performans-raporu-${employeeNumber}-${year}-${String(month).padStart(2, "0")}.pdf`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);
}

function MonthlyReportsCard({ foremanId, employeeNumber }: { foremanId: string; employeeNumber: string }) {
  const navigate = useNavigate();
  const [showAll, setShowAll] = useState(false);
  const [downloadingKey, setDownloadingKey] = useState<string | null>(null);
  const latest = useForemanMonthlyReportLatest(foremanId);
  const history = useForemanMonthlyReports(foremanId);

  const handleDownload = async (year: number, month: number) => {
    const key = `${year}-${month}`;
    setDownloadingKey(key);
    try {
      await downloadMonthlyReportPdf(foremanId, year, month, employeeNumber);
    } finally {
      setDownloadingKey(null);
    }
  };

  return (
    <Card title="Aylık Değerlendirme Raporları">
      {latest.isLoading && <LoadingState />}
      {latest.isError && <ErrorState />}
      {latest.data && !latest.data.available && (
        <EmptyState message="Bu formen için henüz tamamlanmış bir ay bulunmuyor." />
      )}
      {latest.data?.available && latest.data.year && latest.data.month && (
        <div className="flex flex-col gap-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
                {monthlyReportLabel(latest.data.year, latest.data.month)} Aylık Performans Raporu
              </p>
              <div className="mt-1 flex items-center gap-2">
                {latest.data.is_reliable && latest.data.overall_score !== null && latest.data.overall_score !== undefined ? (
                  <>
                    <span className="text-lg font-semibold tabular-nums" style={{ color: "var(--text-primary)" }}>
                      {latest.data.overall_score.toFixed(1)}
                    </span>
                    {latest.data.report_data?.overall && <PerformanceLevelBadge level={latest.data.report_data.overall.level} />}
                  </>
                ) : (
                  <span className="text-xs" style={{ color: "var(--text-muted)" }}>
                    {latest.data.report_data?.insufficient_data_reason ?? "Yeterli veri bulunmuyor."}
                  </span>
                )}
              </div>
              <p className="mt-1 text-xs" style={{ color: "var(--text-muted)" }}>
                Oluşturulma: {new Date(latest.data.generated_at ?? "").toLocaleDateString("tr-TR")}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => navigate(`/foremen/${foremanId}/reports/${latest.data!.year}/${latest.data!.month}`)}
                className="flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium text-white"
                style={{ background: "var(--accent)" }}
              >
                <FileText size={13} strokeWidth={2} />
                Raporu Görüntüle
              </button>
              <button
                onClick={() => handleDownload(latest.data!.year!, latest.data!.month!)}
                disabled={downloadingKey === `${latest.data.year}-${latest.data.month}`}
                className="flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium disabled:opacity-50"
                style={{ border: "1px solid var(--border)", color: "var(--text-primary)" }}
              >
                <Download size={13} strokeWidth={2} />
                {downloadingKey === `${latest.data.year}-${latest.data.month}` ? "İndiriliyor..." : "PDF İndir"}
              </button>
            </div>
          </div>

          {history.data && history.data.items.length > 1 && (
            <div>
              <button
                onClick={() => setShowAll((v) => !v)}
                className="text-xs font-medium hover:underline"
                style={{ color: "var(--accent)" }}
              >
                {showAll ? "Tüm Raporları Gizle" : "Tüm Raporlar"}
              </button>
              {showAll && (
                <ul className="mt-2 flex flex-col gap-1.5 text-[13px]">
                  {history.data.items.map((r) => (
                    <li
                      key={`${r.year}-${r.month}`}
                      className="flex items-center justify-between pb-1.5 last:pb-0"
                      style={{ borderBottom: "1px solid var(--border)" }}
                    >
                      <button
                        onClick={() => navigate(`/foremen/${foremanId}/reports/${r.year}/${r.month}`)}
                        className="hover:underline"
                        style={{ color: "var(--text-primary)" }}
                      >
                        {monthlyReportLabel(r.year, r.month)}
                        {!r.is_reliable && <span className="ml-1 text-xs" style={{ color: "var(--text-muted)" }}>(yetersiz veri)</span>}
                      </button>
                      <button
                        onClick={() => handleDownload(r.year, r.month)}
                        disabled={downloadingKey === `${r.year}-${r.month}`}
                        className="flex items-center gap-1 text-xs font-medium hover:underline disabled:opacity-50"
                        style={{ color: "var(--accent)" }}
                      >
                        <Download size={12} strokeWidth={2} />
                        PDF
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </div>
      )}
    </Card>
  );
}

const PLAN_STATUS_LABEL: Record<"ABOVE_PLAN" | "BELOW_PLAN" | "ON_PLAN", string> = {
  ABOVE_PLAN: "Planın Üzerinde",
  BELOW_PLAN: "Planın Altında",
  ON_PLAN: "Plana Uygun",
};

const PLAN_STATUS_COLOR: Record<"ABOVE_PLAN" | "BELOW_PLAN" | "ON_PLAN", string> = {
  ABOVE_PLAN: "#16a34a",
  BELOW_PLAN: "#dc2626",
  ON_PLAN: "var(--text-primary)",
};

const STRONG_SCORE_THRESHOLD = 90;
const WEAK_SCORE_THRESHOLD = 80;

type PeriodParams = ReturnType<typeof useFilters>["asQueryParams"];

function previousPeriodParams(params: PeriodParams): PeriodParams {
  const from = new Date(params.date_from);
  const to = new Date(params.date_to);
  const periodDays = Math.round((to.getTime() - from.getTime()) / 86_400_000) + 1;
  const prevTo = new Date(from);
  prevTo.setDate(prevTo.getDate() - 1);
  const prevFrom = new Date(prevTo);
  prevFrom.setDate(prevFrom.getDate() - periodDays + 1);
  const iso = (d: Date) => d.toISOString().slice(0, 10);
  return { ...params, date_from: iso(prevFrom), date_to: iso(prevTo) };
}

function kpiDeviation(k: ForemanKpiItem): number {
  return k.avg_capped_score - 100;
}

function kpiInsightSentence(k: ForemanKpiItem, previous: ForemanKpiItem | undefined, tone: "strong" | "weak"): string {
  const deviation = kpiDeviation(k);
  const deviationText =
    tone === "strong"
      ? deviation >= 0
        ? `Hedefin %${deviation.toFixed(0)} üzerinde gerçekleşti.`
        : `Güçlü bir performansla hedefe yakın gerçekleşti (${k.avg_capped_score.toFixed(1)} puan).`
      : `Hedefin %${Math.abs(deviation).toFixed(0)} altında gerçekleşti.`;
  if (previous && previous.record_count > 0) {
    const delta = k.avg_capped_score - previous.avg_capped_score;
    if (Math.abs(delta) >= 3) {
      return `${deviationText} Önceki döneme göre ${delta >= 0 ? "belirgin iyileşme" : "belirgin gerileme"} gösterdi.`;
    }
  }
  return deviationText;
}

function KpiPerformanceCard({
  kpi,
  previous,
  onClick,
}: {
  kpi: ForemanKpiItem;
  previous: ForemanKpiItem | undefined;
  onClick: () => void;
}) {
  const deviation = kpiDeviation(kpi);
  const deviationColor = deviation >= 0 ? "#16a34a" : "#dc2626";
  const delta = previous && previous.record_count > 0 ? kpi.avg_capped_score - previous.avg_capped_score : null;

  return (
    <button
      onClick={onClick}
      title={kpi.description ?? undefined}
      className="rounded-md p-3 text-left transition-colors hover:border-[var(--accent)]"
      style={{ border: "1px solid var(--border)" }}
    >
      <p className="text-xs font-medium" style={{ color: "var(--text-muted)" }}>{kpi.name}</p>
      <div className="mt-1 flex items-baseline gap-2">
        <p className="text-lg font-semibold tabular-nums" style={{ color: "var(--text-primary)" }}>{kpi.avg_capped_score.toFixed(1)}</p>
        <span className="text-[11px] font-semibold tabular-nums" style={{ color: deviationColor }}>
          {deviation >= 0 ? "+" : ""}{deviation.toFixed(1)}
        </span>
        {delta !== null && (
          <span className="text-[11px] font-medium tabular-nums" style={{ color: "var(--text-muted)" }}>
            (önceki: {delta >= 0 ? "+" : ""}{delta.toFixed(1)})
          </span>
        )}
      </div>
      <p className="text-xs" style={{ color: "var(--text-muted)" }}>
        Hedef: {kpi.avg_target?.toFixed(1)} {kpi.unit} · Gerç.: {kpi.avg_actual?.toFixed(1)} {kpi.unit}
      </p>
      <p className="text-xs" style={{ color: "var(--text-muted)" }}>Ağırlık: %{kpi.weight}</p>
      {kpi.agir_gitme && (
        <p className="mt-1 text-xs font-medium" style={{ color: "var(--text-secondary)" }}>
          {kpi.agir_gitme.direction === "OVERWEIGHT" ? "Üst gramaj yönünde" : kpi.agir_gitme.direction === "UNDERWEIGHT" ? "Alt gramaj yönünde" : "Hedefte"} sapma
        </p>
      )}
      {kpi.inkita && (
        <p className="mt-1 text-xs" style={{ color: "var(--text-secondary)" }}>Diğer duruş puana dahil değil</p>
      )}
      {kpi.plana_uyum && (
        <p className="mt-1 text-xs font-medium" style={{ color: PLAN_STATUS_COLOR[kpi.plana_uyum.direction] }}>
          {PLAN_STATUS_LABEL[kpi.plana_uyum.direction]} üretim
        </p>
      )}
    </button>
  );
}

function StrengthWeaknessList({
  title,
  icon: Icon,
  color,
  items,
  previousByCode,
  tone,
}: {
  title: string;
  icon: typeof CircleCheck;
  color: string;
  items: ForemanKpiItem[];
  previousByCode: Map<string, ForemanKpiItem>;
  tone: "strong" | "weak";
}) {
  return (
    <Card title={title}>
      {items.length === 0 ? (
        <EmptyState message="Bu dönem için belirgin bir alan bulunamadı." />
      ) : (
        <ul className="flex flex-col gap-2.5">
          {items.map((k) => (
            <li key={k.kpi_id} className="flex items-start gap-2 text-[13px]">
              <Icon size={15} strokeWidth={2} className="mt-0.5 shrink-0" style={{ color }} />
              <div className="min-w-0">
                <p className="font-medium" style={{ color: "var(--text-primary)" }}>{k.name}</p>
                <p className="text-xs" style={{ color: "var(--text-muted)" }}>{kpiInsightSentence(k, previousByCode.get(k.code), tone)}</p>
              </div>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

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
            {detail.data.plana_uyum && (
              <>
                <dt className="col-span-2 mt-1 pt-2 text-[11px] font-semibold uppercase tracking-wide" style={{ color: "var(--text-muted)", borderTop: "1px solid var(--border)" }}>
                  Plana Uyum Detayı
                </dt>
                <dt style={{ color: "var(--text-muted)" }}>Planlanan Üretim</dt>
                <dd className="text-right font-medium tabular-nums" style={{ color: "var(--text-primary)" }}>{detail.data.plana_uyum.planned_qty?.toFixed(2)} KG</dd>
                <dt style={{ color: "var(--text-muted)" }}>Fiili Üretim</dt>
                <dd className="text-right font-medium tabular-nums" style={{ color: "var(--text-primary)" }}>{detail.data.plana_uyum.actual_qty?.toFixed(2)} KG</dd>
                <dt style={{ color: "var(--text-muted)" }}>KG Farkı</dt>
                <dd className="text-right font-medium tabular-nums" style={{ color: "var(--text-primary)" }}>
                  {detail.data.plana_uyum.kg_diff !== null && detail.data.plana_uyum.kg_diff >= 0 ? "+" : ""}{detail.data.plana_uyum.kg_diff?.toFixed(2)} KG
                </dd>
                <dt style={{ color: "var(--text-muted)" }}>Yönlü Sapma</dt>
                <dd className="text-right font-medium tabular-nums" style={{ color: "var(--text-primary)" }}>
                  {detail.data.plana_uyum.signed_pct_deviation !== null && detail.data.plana_uyum.signed_pct_deviation >= 0 ? "+" : ""}%{detail.data.plana_uyum.signed_pct_deviation?.toFixed(2)}
                </dd>
                <dt style={{ color: "var(--text-muted)" }}>Durum</dt>
                <dd className="text-right font-medium" style={{ color: PLAN_STATUS_COLOR[detail.data.plana_uyum.status] }}>
                  {PLAN_STATUS_LABEL[detail.data.plana_uyum.status]}
                </dd>
              </>
            )}
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
  const [trendKpiId, setTrendKpiId] = useState<string>("overall");

  const foreman = useForemanDetail(foremanId, asQueryParams);
  const kpis = useForemanKpis(foremanId, asQueryParams);
  const history = useForemanAssignmentHistory(foremanId);
  const metaOptions = useFilterOptions();

  const previousParams = useMemo(() => previousPeriodParams(asQueryParams), [asQueryParams]);
  const previousKpis = useForemanKpis(foremanId, previousParams);
  const previousKpiByCode = useMemo(
    () => new Map((previousKpis.data?.items ?? []).map((k) => [k.code, k])),
    [previousKpis.data]
  );

  const trendParams = trendKpiId === "overall" ? asQueryParams : { ...asQueryParams, kpi_ids: trendKpiId };
  const trend = useForemanTrend(foremanId, trendParams, "day");

  const primaryPlantId = foreman.data?.assignments[0]?.plant.id;
  const compareScope = useKpiSummary(primaryPlantId ? { ...asQueryParams, plant_ids: primaryPlantId } : asQueryParams);

  if (foreman.isLoading) return <LoadingState />;
  if (foreman.isError || !foreman.data) return <ErrorState message="Formen bulunamadı." />;

  const f = foreman.data;

  const activeAssignments = history.data?.items.filter((a) => a.is_active) ?? [];
  const responsiblePlants = [...new Set(activeAssignments.map((a) => a.plant).filter((p): p is string => !!p))];
  const currentChief = activeAssignments[0]?.chief ?? null;
  const currentShift = activeAssignments[0]?.shift ?? null;
  const primaryPlantMeta = metaOptions.data?.plants.find((p) => p.id === primaryPlantId);
  const primaryFactory = metaOptions.data?.factories.find((fa) => fa.id === primaryPlantMeta?.factory_id);

  const reliableKpis = (kpis.data?.items ?? []).filter((k) => k.record_count > 0);
  const rankedByScore = [...reliableKpis].sort((a, b) => b.avg_capped_score - a.avg_capped_score);
  const strongKpis = rankedByScore.filter((k) => k.avg_capped_score >= STRONG_SCORE_THRESHOLD).slice(0, 3);
  const weakKpis = [...rankedByScore].reverse().filter((k) => k.avg_capped_score < WEAK_SCORE_THRESHOLD).slice(0, 3);

  return (
    <div className="flex flex-col gap-4">
      <button
        onClick={() => navigate("/foremen")}
        className="flex w-fit items-center gap-1 text-xs font-medium hover:underline"
        style={{ color: "var(--accent)" }}
      >
        <ChevronLeft size={13} strokeWidth={2} />
        Formenler
      </button>

      <div className="rounded-lg p-5" style={{ background: "var(--surface)", border: "1px solid var(--border)" }}>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs font-medium uppercase tracking-wide" style={{ color: "var(--text-muted)" }}>Formen</p>
            <h1 className="mt-0.5 text-xl font-semibold" style={{ color: "var(--text-primary)" }}>{f.full_name}</h1>
            <p className="mt-0.5 text-xs" style={{ color: "var(--text-muted)" }}>Sicil No: {f.employee_number}</p>
          </div>
          <div className="text-right">
            <div className="text-2xl font-semibold tabular-nums" style={{ color: "var(--text-primary)" }}>
              {f.total_score.toFixed(1)} <span className="text-sm font-normal" style={{ color: "var(--text-muted)" }}>/ 100</span>
            </div>
            <div className="mt-1"><PerformanceLevelBadge level={f.level} /></div>
            {!f.is_reliable && (
              <p className="mt-1.5 flex items-center justify-end gap-1 text-xs font-medium text-amber-600">
                <AlertTriangle size={12} strokeWidth={2} />
                Eksik KPI verisi
              </p>
            )}
          </div>
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-x-6 gap-y-2 border-t pt-4 text-[13px]" style={{ borderColor: "var(--border)" }}>
          {primaryFactory && (
            <span className="flex items-center gap-1.5" style={{ color: "var(--text-secondary)" }}>
              <Building2 size={14} strokeWidth={2} style={{ color: "var(--text-muted)" }} />
              {primaryFactory.code}
            </span>
          )}
          <span className="flex items-center gap-1.5" style={{ color: "var(--text-secondary)" }}>
            <span style={{ color: "var(--text-muted)" }}>Sorumlu Tesisler:</span> {responsiblePlants.length > 0 ? responsiblePlants.join(", ") : "-"}
          </span>
          {currentShift && (
            <span className="flex items-center gap-1.5" style={{ color: "var(--text-secondary)" }}>
              <span style={{ color: "var(--text-muted)" }}>Vardiya:</span> {currentShift}
            </span>
          )}
          {currentChief && (
            <span className="flex items-center gap-1.5" style={{ color: "var(--text-secondary)" }}>
              <Users size={14} strokeWidth={2} style={{ color: "var(--text-muted)" }} />
              <span style={{ color: "var(--text-muted)" }}>Şef:</span> {currentChief}
            </span>
          )}
          <span className="flex items-center gap-1.5" style={{ color: "var(--text-secondary)" }}>
            <span style={{ color: "var(--text-muted)" }}>Göreve Başlama:</span> {f.hire_date}
          </span>
          {f.phone_number && (
            <a href={`tel:${f.phone_number}`} className="flex items-center gap-1.5 hover:underline" style={{ color: "var(--text-secondary)" }}>
              <Phone size={14} strokeWidth={2} style={{ color: "var(--text-muted)" }} />
              {f.phone_number}
            </a>
          )}
          {f.email && (
            <a href={`mailto:${f.email}`} className="flex items-center gap-1.5 hover:underline" style={{ color: "var(--text-secondary)" }}>
              <Mail size={14} strokeWidth={2} style={{ color: "var(--text-muted)" }} />
              {f.email}
            </a>
          )}
        </div>
      </div>

      <FilterBar filters={filters} setFilters={setFilters} clearFilters={clearFilters} />

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Card title="Şirket Sıralaması"><p className="text-xl font-semibold tabular-nums" style={{ color: "var(--text-primary)" }}>{f.company_rank ?? "-"} / {f.company_total}</p></Card>
        <Card title="Tesis İçi Sıralaması"><p className="text-xl font-semibold tabular-nums" style={{ color: "var(--text-primary)" }}>{f.plant_rank ?? "-"} / {f.plant_total}</p></Card>
        <Card title="Durum"><p className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>{f.is_active ? "Aktif" : "Pasif"}</p></Card>
        <Card title="Veri Güvenilirliği"><p className="text-sm font-medium" style={{ color: f.is_reliable ? "var(--text-primary)" : "#b45309" }}>{f.is_reliable ? "Yeterli" : "Yetersiz"}</p></Card>
      </div>

      <Card title="Bu Dönem Performansı (kart üzerine tıklayarak hesaplama detayını görüntüleyin)">
        {kpis.isLoading && <LoadingState />}
        {kpis.data && kpis.data.items.length === 0 && <EmptyState />}
        {kpis.data && kpis.data.items.length > 0 && (
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-5">
            {kpis.data.items.map((k) => (
              <KpiPerformanceCard
                key={k.kpi_id}
                kpi={k}
                previous={previousKpiByCode.get(k.code)}
                onClick={() => setSelectedKpi(k)}
              />
            ))}
          </div>
        )}
      </Card>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <StrengthWeaknessList
          title="Güçlü Alanlar"
          icon={CircleCheck}
          color="#16a34a"
          items={strongKpis}
          previousByCode={previousKpiByCode}
          tone="strong"
        />
        <StrengthWeaknessList
          title="Geliştirilmesi Gereken Alanlar"
          icon={CircleAlert}
          color="#dc2626"
          items={weakKpis}
          previousByCode={previousKpiByCode}
          tone="weak"
        />
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <Card
          title="Performans Trendi"
          action={
            <select
              value={trendKpiId}
              onChange={(e) => setTrendKpiId(e.target.value)}
              className={fieldClass}
              style={{ ...fieldStyle, width: "auto" }}
            >
              <option value="overall">Genel Skor</option>
              {kpis.data?.items.map((k) => (
                <option key={k.kpi_id} value={k.kpi_id}>{k.name}</option>
              ))}
            </select>
          }
        >
          {trend.isLoading ? <LoadingState /> : trend.data ? <TrendChart points={trend.data.points} /> : <ErrorState />}
        </Card>
        <Card title="KPI Karşılaştırması">
          {kpis.isLoading ? (
            <LoadingState />
          ) : kpis.data ? (
            <KpiRadarChart
              items={kpis.data.items}
              compareItems={compareScope.data?.items}
              compareLabel={primaryPlantMeta ? "Tesis Ortalaması" : "Şirket Ortalaması"}
              seriesLabel="Formen"
            />
          ) : (
            <ErrorState />
          )}
        </Card>
      </div>

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

      {foremanId && <MonthlyReportsCard foremanId={foremanId} employeeNumber={f.employee_number} />}

      {selectedKpi && foremanId && (
        <CalculationDetailModal foremanId={foremanId} kpi={selectedKpi} onClose={() => setSelectedKpi(null)} />
      )}
    </div>
  );
}
