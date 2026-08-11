import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ChevronLeft, ShieldAlert } from "lucide-react";
import {
  useAnalysisToolCalls,
  useAnalyzeAnomaly,
  useAnomaly,
  useAnomalyInvestigation,
  useReanalyzeAnomaly,
  useUpdateAnomalyStatus,
} from "../api/hooks";
import type { AnalysisMode, AnomalyStatus } from "../api/types";
import { Card, ErrorState, LoadingState } from "../components/StateViews";
import { DetectionHero } from "../components/anomaly/DetectionHero";
import { DetectionReasonCards } from "../components/anomaly/DetectionReasonCards";
import { BenchmarkComparison } from "../components/anomaly/BenchmarkComparison";
import { DetectionScope } from "../components/anomaly/DetectionScope";
import { ForemanContext } from "../components/anomaly/ForemanContext";
import { KpiBreakdownCard } from "../components/anomaly/KpiBreakdownCard";
import { BaselineComparisonCard } from "../components/anomaly/BaselineComparisonCard";
import { RelatedKpiChanges } from "../components/anomaly/RelatedKpiChanges";
import { ImpactAnalysis } from "../components/anomaly/ImpactAnalysis";
import { HistoricalDetections } from "../components/anomaly/HistoricalDetections";
import { AIInvestigationPanel } from "../components/anomaly/AIInvestigationPanel";
import { KpiTrendInvestigationChart } from "../components/charts/KpiTrendInvestigationChart";

export function AnomalyDetailPage() {
  const { anomalyId } = useParams<{ anomalyId: string }>();
  const navigate = useNavigate();
  const anomaly = useAnomaly(anomalyId);
  const investigation = useAnomalyInvestigation(anomalyId);
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

  const runAnalysis = (endpoint: "analyze" | "reanalyze") => {
    if (isBusy) return;
    setActionError(null);
    const mutation = endpoint === "analyze" ? analyzeMutation : reanalyzeMutation;
    mutation.mutate(
      { id: a.id, mode: selectedMode, force_refresh: true },
      { onError: () => setActionError("Yapay zekâ analizi oluşturulamadı. Daha sonra yeniden deneyebilirsiniz.") }
    );
  };

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

      <DetectionHero
        anomaly={a}
        statusPending={statusMutation.isPending}
        onStatusChange={(status: AnomalyStatus) => statusMutation.mutate({ id: a.id, status })}
      />

      {a.data_quality_warnings.length > 0 && (
        <div className="flex flex-col gap-1 rounded-lg p-3" style={{ background: "#fef3c722", border: "1px solid #b4530933" }}>
          {a.data_quality_warnings.map((w) => (
            <span key={w} className="flex items-center gap-1.5 text-xs" style={{ color: "#b45309" }}>
              <ShieldAlert size={12} strokeWidth={2} />
              {w}
            </span>
          ))}
        </div>
      )}

      <Card title="Neden Bu Tespit Oluştu?">
        <DetectionReasonCards anomaly={a} investigation={investigation.data} />
      </Card>

      <Card title="KPI Trendi">
        <KpiTrendInvestigationChart
          points={a.daily_history}
          expectedValue={a.expected_value}
          desiredDirection={a.kpi_definition.desired_direction}
          baselineAvg={investigation.data?.baseline_comparison.available ? investigation.data.baseline_comparison.baseline_avg : null}
        />
      </Card>

      <Card title="Neye Göre Anormal? — Karşılaştırma">
        <BenchmarkComparison anomaly={a} />
      </Card>

      <Card title="Sorunun Kapsamı">
        <DetectionScope anomaly={a} investigation={investigation.data} />
      </Card>

      <Card title="Sorumlu Formen">
        {investigation.isLoading && <LoadingState label="Yükleniyor..." />}
        {investigation.isError && <ErrorState message="Formen bilgisi yüklenemedi." />}
        {investigation.data && <ForemanContext anomaly={a} foreman={investigation.data.responsible_foreman} />}
      </Card>

      {investigation.data?.downtime_breakdown && (
        <Card title={`${a.kpi_name} Dağılımı`}>
          <KpiBreakdownCard breakdown={investigation.data.downtime_breakdown} />
        </Card>
      )}

      <Card title="Öncesi / Anomali Dönemi Karşılaştırması">
        {investigation.isLoading && <LoadingState label="Yükleniyor..." />}
        {investigation.isError && <ErrorState message="Karşılaştırma verisi yüklenemedi." />}
        {investigation.data && <BaselineComparisonCard anomaly={a} investigation={investigation.data} />}
      </Card>

      <Card title="Aynı Dönemde Değişen KPI'lar">
        {investigation.isLoading && <LoadingState label="Yükleniyor..." />}
        {investigation.isError && <ErrorState message="İlişkili KPI verisi yüklenemedi." />}
        {investigation.data && <RelatedKpiChanges items={investigation.data.related_kpi_changes} />}
      </Card>

      <Card title="Operasyonel Etki">
        {investigation.isLoading && <LoadingState label="Yükleniyor..." />}
        {investigation.isError && <ErrorState message="Etki verisi yüklenemedi." />}
        {investigation.data && <ImpactAnalysis impact={investigation.data.impact} />}
      </Card>

      <Card title="Benzer Geçmiş Tespitler">
        {investigation.isLoading && <LoadingState label="Yükleniyor..." />}
        {investigation.isError && <ErrorState message="Benzer tespitler yüklenemedi." />}
        {investigation.data && <HistoricalDetections cases={investigation.data.similar_cases} />}
      </Card>

      <AIInvestigationPanel
        anomaly={a}
        isBusy={isBusy}
        selectedMode={selectedMode}
        onSelectMode={setSelectedMode}
        onRunAnalysis={runAnalysis}
        actionError={actionError}
        toolCallsData={toolCalls.data}
        toolCallsLoading={toolCalls.isLoading}
        toolCallsError={toolCalls.isError}
        stepsOpen={stepsOpen}
        onToggleSteps={() => setStepsOpen((v) => !v)}
      />
    </div>
  );
}
