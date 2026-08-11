import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  ArrowUpRight,
  ArrowDownRight,
  Bot,
  ChevronLeft,
  ClipboardList,
  Database,
  Factory,
  Gauge,
  ListChecks,
  RefreshCw,
  Search,
  ShieldAlert,
  Sparkles,
  Wrench,
} from "lucide-react";
import {
  useAnalysisToolCalls,
  useAnalyzeAnomaly,
  useAnomaly,
  useReanalyzeAnomaly,
  useUpdateAnomalyStatus,
} from "../api/hooks";
import type { AnalysisMode, AnomalyStatus } from "../api/types";
import { Card, EmptyState, ErrorState, LoadingState } from "../components/StateViews";
import { AnalysisStatusBadge, SeverityBadge, StatusBadge } from "../components/AnomalyBadges";
import { AnomalyTrendChart } from "../components/charts/AnomalyTrendChart";
import { AnomalyComparisonChart, type ComparisonBar } from "../components/charts/AnomalyComparisonChart";
import { fieldClass, fieldStyle } from "../lib/formStyles";

const STATUS_OPTIONS: { value: AnomalyStatus; label: string }[] = [
  { value: "new", label: "Yeni" },
  { value: "in_review", label: "İnceleniyor" },
  { value: "action_pending", label: "Aksiyon Bekliyor" },
  { value: "resolved", label: "Çözüldü" },
  { value: "closed", label: "Kapatıldı" },
];

const CONFIDENCE_LABELS: Record<string, string> = { low: "Düşük", medium: "Orta", high: "Yüksek" };
const PRIORITY_LABELS: Record<string, string> = { low: "Düşük", medium: "Orta", high: "Yüksek", critical: "Kritik" };
const RISK_LABELS: Record<string, string> = { low: "Düşük", medium: "Orta", high: "Yüksek", critical: "Kritik" };

const TOOL_LABELS: Record<string, string> = {
  get_anomaly_details: "Tespit Detayları", get_kpi_history: "KPI Geçmişi",
  compare_shifts: "Vardiya Performansı Karşılaştırması", compare_plants: "Tesisler Arası Karşılaştırma",
  get_related_kpis: "İlişkili KPI Değişimleri", get_downtime_breakdown: "Duruş Nedenleri İncelemesi",
  get_maintenance_signals: "Bakım ve Arıza Sinyalleri", get_product_mix: "Ürün Dağılımı İncelemesi",
  get_changeover_records: "Ürün Değişim Kayıtları", get_shift_notes: "Vardiya Notları İncelemesi",
  find_similar_anomalies: "Benzer Geçmiş Tespitler",
};

const TOOL_CALLING_STAGES = [
  "Tespit inceleniyor", "Analiz planı hazırlanıyor", "Vardiya verileri karşılaştırılıyor",
  "KPI geçmişi kontrol ediliyor", "Duruş nedenleri inceleniyor", "Bakım sinyalleri araştırılıyor",
  "Ürün dağılımı değerlendiriliyor", "Geçmiş benzer tespitler kontrol ediliyor", "Aksiyon önerileri hazırlanıyor",
];

const MODE_OPTIONS: { value: AnalysisMode; label: string; description: string }[] = [
  { value: "single_context", label: "Hızlı Analiz", description: "Tüm bağlam tek seferde gönderilir" },
  { value: "tool_calling", label: "Derinlemesine Analiz", description: "Yapay zekâ gerektikçe araç çağırarak araştırır" },
];

function comparisonLabel(key: string): string {
  if (key === "plant_average") return "Tesis Ortalaması";
  if (key === "factory_average") return "Fabrika Ortalaması";
  const m = key.match(/^v(\d+)_average$/);
  return m ? `${m[1]}. Vardiya` : key;
}

function StatTile({ label, value, unit }: { label: string; value: string; unit?: string }) {
  return (
    <div className="rounded-lg p-3" style={{ background: "var(--page-bg)", border: "1px solid var(--border)" }}>
      <p className="text-[11px] font-semibold uppercase tracking-wide" style={{ color: "var(--text-muted)" }}>{label}</p>
      <p className="mt-1 text-lg font-semibold tabular-nums" style={{ color: "var(--text-primary)" }}>
        {value}{unit && <span className="ml-1 text-xs font-normal" style={{ color: "var(--text-muted)" }}>{unit}</span>}
      </p>
    </div>
  );
}

function SectionCard({ title, children }: { title: string; children: React.ReactNode }) {
  return <Card title={title}>{children}</Card>;
}

export function AnomalyDetailPage() {
  const { anomalyId } = useParams<{ anomalyId: string }>();
  const navigate = useNavigate();
  const anomaly = useAnomaly(anomalyId);
  const analyzeMutation = useAnalyzeAnomaly();
  const reanalyzeMutation = useReanalyzeAnomaly();
  const statusMutation = useUpdateAnomalyStatus();
  const latestAnalysisId = anomaly.data?.latest_analysis?.id;
  const isToolCallingMode = anomaly.data?.latest_analysis?.mode === "tool_calling";
  const toolCalls = useAnalysisToolCalls(isToolCallingMode ? latestAnalysisId : undefined);
  const [actionError, setActionError] = useState<string | null>(null);
  const [selectedMode, setSelectedMode] = useState<AnalysisMode>("single_context");
  const [stepsOpen, setStepsOpen] = useState(false);

  const isBusy = analyzeMutation.isPending || reanalyzeMutation.isPending;

  if (anomaly.isLoading) return <LoadingState label="Tespit yükleniyor..." />;
  if (anomaly.isError || !anomaly.data) return <ErrorState message="Tespit yüklenemedi." />;

  const a = anomaly.data;
  const latest = a.latest_analysis;
  const result = latest?.result;

  const runAnalysis = (endpoint: "analyze" | "reanalyze") => {
    if (isBusy) return;
    setActionError(null);
    const mutation = endpoint === "analyze" ? analyzeMutation : reanalyzeMutation;
    mutation.mutate(
      { id: a.id, mode: selectedMode, force_refresh: true },
      { onError: () => setActionError("Yapay zekâ analizi oluşturulamadı. Daha sonra yeniden deneyebilirsiniz.") }
    );
  };

  const comparisonBars: ComparisonBar[] = Object.entries(a.comparison || {}).map(([key, value]) => ({
    name: comparisonLabel(key),
    value: Number(value),
    highlight: comparisonLabel(key) === a.shift_name,
  }));

  return (
    <div className="flex flex-col gap-4">
      <button
        onClick={() => navigate("/anomalies")}
        className="flex w-fit items-center gap-1 text-xs font-medium hover:underline"
        style={{ color: "var(--accent)" }}
      >
        <ChevronLeft size={13} strokeWidth={2} />
        Tespitler
      </button>

      <div className="rounded-lg p-6" style={{ background: "var(--surface)", border: "1px solid var(--border)", borderTop: "3px solid var(--accent)" }}>
        <div className="flex flex-wrap items-center gap-2">
          <SeverityBadge severity={a.severity} />
          <StatusBadge status={a.status} />
          <AnalysisStatusBadge status={a.analysis_status} />
          <span className="text-xs" style={{ color: "var(--text-muted)" }}>{a.code}</span>
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-4 text-xs" style={{ color: "var(--text-muted)" }}>
          <span className="flex items-center gap-1"><Factory size={13} strokeWidth={2} />{a.factory_code} · {a.plant_name}</span>
          {a.shift_name && <span>{a.shift_name}</span>}
          <span>{a.kpi_name}</span>
          <span>Tespit: {a.detected_at.slice(0, 10)}</span>
          <span>Dönem: {a.period_start} – {a.period_end}</span>
        </div>
        <div className="mt-4 flex items-center gap-2">
          <label className="text-xs font-medium" style={{ color: "var(--text-secondary)" }}>Tespit durumu:</label>
          <select
            className={fieldClass}
            style={{ ...fieldStyle, width: 180 }}
            value={a.status}
            disabled={statusMutation.isPending}
            onChange={(e) => statusMutation.mutate({ id: a.id, status: e.target.value as AnomalyStatus })}
          >
            {STATUS_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </div>
      </div>

      <SectionCard title="Sayısal Veriler">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <StatTile label="Gözlenen Değer" value={`%${a.observed_value.toFixed(1)}`} />
          <StatTile label="Beklenen Değer" value={`%${a.expected_value.toFixed(1)}`} />
          <StatTile label="Sapma Oranı" value={`%${a.deviation_percent.toFixed(1)}`} />
          <StatTile
            label="Görülme Sıklığı"
            value={a.affected_days != null && a.total_days != null ? `${a.affected_days} / ${a.total_days}` : "-"}
            unit="gün"
          />
        </div>
      </SectionCard>

      <SectionCard title="İlgili KPI Trendi">
        <AnomalyTrendChart points={a.daily_history} expectedValue={a.expected_value} />
      </SectionCard>

      <SectionCard title="Vardiya Karşılaştırması">
        <AnomalyComparisonChart items={comparisonBars} />
      </SectionCard>

      <SectionCard title="İlişkili KPI Değişimleri">
        {a.related_signals.length === 0 && <EmptyState message="İlişkili KPI sinyali bulunamadı." />}
        {a.related_signals.length > 0 && (
          <ul className="flex flex-col gap-2">
            {a.related_signals.map((s) => (
              <li key={s.kpi_code} className="flex items-center justify-between rounded-md p-2.5 text-[13px]" style={{ border: "1px solid var(--border)" }}>
                <span style={{ color: "var(--text-primary)" }}>{s.kpi}</span>
                <span className="flex items-center gap-1 font-medium tabular-nums" style={{ color: s.direction === "increase" ? "#b91c1c" : "#15803d" }}>
                  {s.direction === "increase" ? <ArrowUpRight size={14} strokeWidth={2} /> : <ArrowDownRight size={14} strokeWidth={2} />}
                  %{Math.abs(s.change_percent).toFixed(1)}
                </span>
              </li>
            ))}
          </ul>
        )}
      </SectionCard>

      <SectionCard title="ML Tespit Bilgileri">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <StatTile label="Tespit Türü" value={a.anomaly_type_label} />
          <StatTile label="ML Güven Skoru" value={`${(a.ml_confidence * 100).toFixed(0)}%`} />
          <StatTile label="Veri Kalitesi" value={a.data_quality_status === "valid" ? "Geçerli" : "Şüpheli"} />
          <StatTile label="İlgili Formen Sayısı" value={String(a.foreman_codes.length)} />
        </div>
        {a.data_quality_warnings.length > 0 && (
          <ul className="mt-3 flex flex-col gap-1 text-xs" style={{ color: "#b45309" }}>
            {a.data_quality_warnings.map((w) => <li key={w} className="flex items-center gap-1.5"><ShieldAlert size={12} strokeWidth={2} />{w}</li>)}
          </ul>
        )}
      </SectionCard>

      <Card
        title="Yapay Zekâ Analizi"
        action={
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-1 rounded-md p-0.5" style={{ border: "1px solid var(--border-strong)" }}>
              {MODE_OPTIONS.map((o) => (
                <button
                  key={o.value}
                  type="button"
                  disabled={isBusy}
                  title={o.description}
                  onClick={() => setSelectedMode(o.value)}
                  className="rounded px-2 py-1 text-[11px] font-medium transition-colors disabled:opacity-60"
                  style={
                    selectedMode === o.value
                      ? { background: "var(--accent)", color: "#fff" }
                      : { color: "var(--text-secondary)" }
                  }
                >
                  {o.label}
                </button>
              ))}
            </div>
            {!latest && (
              <button
                onClick={() => runAnalysis("analyze")}
                disabled={isBusy}
                className="flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium text-white disabled:opacity-60"
                style={{ background: "var(--accent)" }}
              >
                <Sparkles size={13} strokeWidth={2} />
                Yapay Zeka ile Analiz Et
              </button>
            )}
            {latest && (
              <>
                <button
                  onClick={() => runAnalysis("analyze")}
                  disabled={isBusy}
                  className="flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium disabled:opacity-60"
                  style={{ border: "1px solid var(--border-strong)", color: "var(--text-primary)" }}
                >
                  <RefreshCw size={13} strokeWidth={2} className={isBusy ? "animate-spin" : undefined} />
                  Analizi Yenile
                </button>
                <button
                  onClick={() => runAnalysis("reanalyze")}
                  disabled={isBusy}
                  className="flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium text-white disabled:opacity-60"
                  style={{ background: "var(--accent)" }}
                >
                  <Bot size={13} strokeWidth={2} />
                  Analizi Tekrar Oluştur
                </button>
              </>
            )}
          </div>
        }
      >
        {isBusy && selectedMode === "single_context" && <LoadingState label="Tespit verileri analiz ediliyor..." />}
        {isBusy && selectedMode === "tool_calling" && (
          <div className="flex flex-col items-center gap-3 py-8">
            <LoadingState label="Tespit verileri analiz ediliyor..." />
            <ul className="grid grid-cols-1 gap-1.5 text-xs sm:grid-cols-2" style={{ color: "var(--text-muted)" }}>
              {TOOL_CALLING_STAGES.map((s) => (
                <li key={s} className="flex items-center gap-1.5">
                  <Wrench size={11} strokeWidth={2} />
                  {s}
                </li>
              ))}
            </ul>
          </div>
        )}
        {!isBusy && actionError && <ErrorState message={actionError} />}
        {!isBusy && !actionError && !latest && (
          <EmptyState message="Bu tespit için henüz yapay zekâ analizi oluşturulmadı." />
        )}
        {!isBusy && !actionError && latest && ["failed", "timed_out", "cancelled"].includes(latest.status) && (
          <ErrorState message={latest.error_message ?? "Yapay zekâ analizi oluşturulamadı. Daha sonra yeniden deneyebilirsiniz."} />
        )}
        {!isBusy && !actionError && latest && result && (
          <div className="flex flex-col gap-4">
            <div className="flex flex-wrap items-center gap-2">
              <span
                className="w-fit rounded px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide"
                style={{ background: latest.is_demo ? "#fef3c7" : "#dcfce7", color: latest.is_demo ? "#92400e" : "#15803d" }}
              >
                {latest.is_demo ? "Demo Yapay Zekâ Analizi" : "Yapay Zekâ Analizi"}
              </span>
              <span
                className="w-fit rounded px-2 py-0.5 text-[11px] font-medium"
                style={{ background: "var(--page-bg)", color: "var(--text-muted)", border: "1px solid var(--border)" }}
              >
                {latest.mode === "tool_calling" ? "Derinlemesine Analiz" : "Hızlı Analiz"}
              </span>
            </div>

            <div>
              <h4 className="mb-1 text-xs font-semibold uppercase tracking-wide" style={{ color: "var(--text-secondary)" }}>Yönetici Özeti</h4>
              <p className="text-[13px]" style={{ color: "var(--text-primary)" }}>{result.executive_summary}</p>
            </div>

            <details open className="rounded-md p-3" style={{ border: "1px solid var(--border)" }}>
              <summary className="cursor-pointer text-xs font-semibold uppercase tracking-wide" style={{ color: "var(--text-secondary)" }}>
                Doğrulanmış Bulgular ({result.verified_findings.length})
              </summary>
              <ul className="mt-2 flex flex-col gap-1.5 text-[13px]">
                {result.verified_findings.map((f, i) => (
                  <li key={i} className="flex flex-col gap-1 border-b pb-1.5 last:border-b-0" style={{ borderColor: "var(--border)" }}>
                    <div className="flex justify-between gap-3">
                      <span style={{ color: "var(--text-primary)" }}>{f.finding}</span>
                      <span className="shrink-0 tabular-nums" style={{ color: "var(--text-muted)" }}>{f.evidence}</span>
                    </div>
                    {(f.source_refs ?? []).length > 0 && (
                      <span className="flex w-fit items-center gap-1 text-[11px]" style={{ color: "var(--accent)" }}>
                        <Database size={10} strokeWidth={2} />
                        Kaynak: {(f.source_refs ?? []).map((r) => TOOL_LABELS[r.tool_name] ?? r.tool_name).join(", ")}
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            </details>

            <details className="rounded-md p-3" style={{ border: "1px solid var(--border)" }}>
              <summary className="cursor-pointer text-xs font-semibold uppercase tracking-wide" style={{ color: "var(--text-secondary)" }}>
                Muhtemel Nedenler ({result.possible_causes.length})
              </summary>
              <ul className="mt-2 flex flex-col gap-3 text-[13px]">
                {result.possible_causes.map((c, i) => (
                  <li key={i} className="rounded-md p-2.5" style={{ background: "var(--page-bg)" }}>
                    <div className="flex items-center justify-between">
                      <span className="font-medium" style={{ color: "var(--text-primary)" }}>{c.cause}</span>
                      <span className="rounded px-1.5 py-0.5 text-[11px] font-medium" style={{ background: "var(--accent-subtle)", color: "var(--accent)" }}>
                        Güven: {CONFIDENCE_LABELS[c.confidence] ?? c.confidence}
                      </span>
                    </div>
                    {c.supporting_evidence.length > 0 && (
                      <p className="mt-1 text-xs" style={{ color: "var(--text-secondary)" }}>Destekleyen: {c.supporting_evidence.join(", ")}</p>
                    )}
                    {c.contradicting_evidence.length > 0 && (
                      <p className="mt-1 text-xs" style={{ color: "var(--text-secondary)" }}>Çelişen: {c.contradicting_evidence.join(", ")}</p>
                    )}
                    <p className="mt-1 text-xs italic" style={{ color: "var(--text-muted)" }}>Doğrulama: {c.verification_required}</p>
                    {(c.source_refs ?? []).length > 0 && (
                      <span className="mt-1 flex w-fit items-center gap-1 text-[11px]" style={{ color: "var(--accent)" }}>
                        <Database size={10} strokeWidth={2} />
                        Kaynak: {(c.source_refs ?? []).map((r) => TOOL_LABELS[r.tool_name] ?? r.tool_name).join(", ")}
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            </details>

            <details className="rounded-md p-3" style={{ border: "1px solid var(--border)" }}>
              <summary className="cursor-pointer text-xs font-semibold uppercase tracking-wide" style={{ color: "var(--text-secondary)" }}>
                Önerilen Araştırmalar ({result.recommended_investigations.length})
              </summary>
              <ul className="mt-2 flex flex-col gap-2 text-[13px]">
                {result.recommended_investigations.map((r, i) => (
                  <li key={i} className="flex items-start gap-2">
                    <Search size={13} strokeWidth={2} className="mt-0.5 shrink-0" style={{ color: "var(--text-muted)" }} />
                    <span style={{ color: "var(--text-primary)" }}>
                      {r.step} — <span style={{ color: "var(--text-muted)" }}>{r.responsible_unit}, öncelik: {PRIORITY_LABELS[r.priority] ?? r.priority}, beklenen çıktı: {r.expected_output}</span>
                    </span>
                  </li>
                ))}
              </ul>
            </details>

            <div>
              <h4 className="mb-1.5 text-xs font-semibold uppercase tracking-wide" style={{ color: "var(--text-secondary)" }}>Hızlı Aksiyonlar</h4>
              <ul className="flex flex-col gap-2 text-[13px]">
                {result.immediate_actions.map((act, i) => (
                  <li key={i} className="flex items-start gap-2 rounded-md p-2.5" style={{ border: "1px solid var(--border)" }}>
                    <ClipboardList size={13} strokeWidth={2} className="mt-0.5 shrink-0" style={{ color: "var(--accent)" }} />
                    <div>
                      <p style={{ color: "var(--text-primary)" }}>{act.action}</p>
                      <p className="mt-0.5 text-xs" style={{ color: "var(--text-muted)" }}>
                        {act.responsible_unit} · öncelik: {PRIORITY_LABELS[act.priority] ?? act.priority} · süre: {act.timeframe} · beklenen etki: {act.expected_impact}
                        {act.requires_approval && " · yönetici onayı gerekir"}
                      </p>
                    </div>
                  </li>
                ))}
              </ul>
            </div>

            <div>
              <h4 className="mb-1.5 text-xs font-semibold uppercase tracking-wide" style={{ color: "var(--text-secondary)" }}>Orta Vadeli İyileştirmeler</h4>
              <ul className="flex flex-col gap-2 text-[13px]">
                {result.medium_term_actions.map((act, i) => (
                  <li key={i} className="rounded-md p-2.5" style={{ border: "1px solid var(--border)" }}>
                    <p style={{ color: "var(--text-primary)" }}>{act.action}</p>
                    <p className="mt-0.5 text-xs" style={{ color: "var(--text-muted)" }}>{act.responsible_unit} · beklenen etki: {act.expected_impact}</p>
                  </li>
                ))}
              </ul>
            </div>

            {result.missing_information.length > 0 && (
              <div>
                <h4 className="mb-1.5 text-xs font-semibold uppercase tracking-wide" style={{ color: "var(--text-secondary)" }}>Eksik Bilgiler</h4>
                <ul className="flex flex-col gap-1 text-[13px]" style={{ color: "var(--text-secondary)" }}>
                  {result.missing_information.map((m, i) => <li key={i}>• {m}</li>)}
                </ul>
              </div>
            )}

            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <StatTile label="YZ Analiz Güveni" value={`${Math.round(result.analysis_confidence * 100)}%`} />
              <StatTile label="ML Tespit Güveni" value={`${Math.round(a.ml_confidence * 100)}%`} />
              <StatTile label="Risk Seviyesi" value={RISK_LABELS[result.risk_level] ?? result.risk_level} />
              <StatTile label="İnsan İncelemesi" value={result.requires_human_review ? "Gerekli" : "Gerekli Değil"} />
            </div>

            {latest.mode === "tool_calling" && (
              <div>
                <h4 className="mb-1.5 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide" style={{ color: "var(--text-secondary)" }}>
                  <ListChecks size={13} strokeWidth={2} />
                  Analizde Kullanılan Veriler
                </h4>
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                  <StatTile label="Kullanılan Araç Sayısı" value={String((result.tools_used ?? []).length)} />
                  <StatTile
                    label="İncelenen Tarih Aralığı"
                    value={result.data_scope ? `${result.data_scope.start_date} – ${result.data_scope.end_date}` : "-"}
                  />
                  <StatTile label="İncelenen Kayıt Sayısı" value={result.data_scope ? String(result.data_scope.record_count) : "-"} />
                  <StatTile
                    label="Veri Kalitesi"
                    value={result.data_scope?.data_quality_status === "valid" ? "Geçerli" : (result.data_scope?.data_quality_status ?? "-")}
                  />
                </div>
                {(result.tools_used ?? []).length > 0 && (
                  <ul className="mt-2 flex flex-wrap gap-1.5">
                    {(result.tools_used ?? []).map((t) => (
                      <li
                        key={t.tool_call_id}
                        title={t.purpose}
                        className="rounded px-2 py-0.5 text-[11px] font-medium"
                        style={{ background: "var(--accent-subtle)", color: "var(--accent)" }}
                      >
                        {TOOL_LABELS[t.tool_name] ?? t.tool_name}
                      </li>
                    ))}
                  </ul>
                )}
                {(result.analysis_limitations ?? []).length > 0 && (
                  <ul className="mt-2 flex flex-col gap-1 text-xs" style={{ color: "#b45309" }}>
                    {(result.analysis_limitations ?? []).map((l) => (
                      <li key={l} className="flex items-center gap-1.5"><ShieldAlert size={11} strokeWidth={2} />{l}</li>
                    ))}
                  </ul>
                )}
              </div>
            )}

            <p className="rounded-md p-2.5 text-xs" style={{ background: "var(--page-bg)", color: "var(--text-muted)" }}>
              <Gauge size={12} strokeWidth={2} className="mr-1 inline" />
              {result.disclaimer}
            </p>

            <p className="text-xs" style={{ color: "var(--text-muted)" }}>
              Analiz kaynağı: {latest.model} · Başlangıç: {latest.started_at.replace("T", " ").slice(0, 19)}
              {latest.completed_at && ` · Bitiş: ${latest.completed_at.replace("T", " ").slice(0, 19)}`}
            </p>
          </div>
        )}
      </Card>

      {latest && latest.mode === "tool_calling" && (
        <Card title="Analiz Adımları">
          {toolCalls.isLoading && <LoadingState label="Adımlar yükleniyor..." />}
          {toolCalls.isError && <ErrorState message="Analiz adımları yüklenemedi." />}
          {toolCalls.data && toolCalls.data.items.length === 0 && <EmptyState message="Bu analiz için kayıtlı araç çağrısı yok." />}
          {toolCalls.data && toolCalls.data.items.length > 0 && (
            <button
              type="button"
              onClick={() => setStepsOpen((v) => !v)}
              className="mb-2 text-xs font-medium hover:underline"
              style={{ color: "var(--accent)" }}
            >
              {stepsOpen ? "Adımları gizle" : `${toolCalls.data.total} adımı göster`}
            </button>
          )}
          {stepsOpen && toolCalls.data && (
            <ol className="flex flex-col gap-2">
              {toolCalls.data.items.map((c) => (
                <li key={c.id} className="flex items-start gap-3 rounded-md p-2.5 text-[13px]" style={{ border: "1px solid var(--border)" }}>
                  <span
                    className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[11px] font-semibold"
                    style={{ background: "var(--accent-subtle)", color: "var(--accent)" }}
                  >
                    {c.step_number}
                  </span>
                  <div className="flex-1">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="font-medium" style={{ color: "var(--text-primary)" }}>{c.tool_label}</span>
                      <span
                        className="rounded px-1.5 py-0.5 text-[11px] font-medium"
                        style={
                          c.status === "success"
                            ? { background: "#dcfce7", color: "#15803d" }
                            : { background: "#fee2e2", color: "#b91c1c" }
                        }
                      >
                        {c.status === "success" ? "Başarılı" : c.status === "timeout" ? "Zaman Aşımı" : "Hata"}
                      </span>
                    </div>
                    <p className="mt-0.5 text-xs" style={{ color: "var(--text-muted)" }}>
                      Süre: {c.duration_ms ?? 0} ms
                      {c.record_count != null && ` · Dönen kayıt: ${c.record_count}`}
                      {c.error_message && ` · ${c.error_message}`}
                    </p>
                  </div>
                </li>
              ))}
            </ol>
          )}
        </Card>
      )}
    </div>
  );
}
