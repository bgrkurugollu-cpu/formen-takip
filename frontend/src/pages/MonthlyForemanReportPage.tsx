import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { AlertTriangle, ChevronLeft, Download, PartyPopper } from "lucide-react";
import { apiClient } from "../api/client";
import { useForemanMonthlyReport } from "../api/hooks";
import { Card, EmptyState, ErrorState, LoadingState } from "../components/StateViews";
import { PerformanceLevelBadge } from "../components/PerformanceLevelBadge";
import { TrendChart } from "../components/charts/TrendChart";
import type { MonthlyReportComparison, MonthlyReportKpiEntry } from "../api/types";

function comparisonStatusText(label: string, comparison: MonthlyReportComparison): string {
  const pos = comparison.status === "at" ? `${label}te` : comparison.status === "above" ? `${label}nin üzerinde` : `${label}nin altında`;
  return pos;
}

function ComparisonRow({ label, comparison, unit }: { label: string; comparison: MonthlyReportComparison; unit: string }) {
  return (
    <div className="flex items-center justify-between text-xs">
      <span style={{ color: "var(--text-muted)" }}>{label}: {comparison.value.toFixed(2)} {unit}</span>
      <span className="font-medium" style={{ color: comparison.is_favorable ? "#16a34a" : "#dc2626" }}>
        {comparisonStatusText(label, comparison)}
      </span>
    </div>
  );
}

function ProgressBar({ score, color }: { score: number | null; color: string }) {
  const pct = Math.max(0, Math.min(100, ((score ?? 0) / 120) * 100));
  return (
    <div className="h-1.5 w-full rounded-full" style={{ background: "var(--border)" }}>
      <div className="h-1.5 rounded-full" style={{ width: `${pct}%`, background: color }} />
    </div>
  );
}

function KpiCard({ kpi }: { kpi: MonthlyReportKpiEntry }) {
  if (!kpi.has_data) {
    return (
      <div className="rounded-md p-3" style={{ border: "1px solid var(--border)" }}>
        <p className="text-xs font-medium" style={{ color: "var(--text-muted)" }}>{kpi.name}</p>
        <p className="mt-1 text-xs" style={{ color: "var(--text-muted)" }}>Bu ay için veri bulunmuyor.</p>
      </div>
    );
  }
  return (
    <div className="rounded-md p-3" style={{ border: "1px solid var(--border)" }}>
      <div className="flex items-center justify-between">
        <p className="text-xs font-medium" style={{ color: "var(--text-muted)" }}>{kpi.name}</p>
        {kpi.level && <PerformanceLevelBadge level={kpi.level} />}
      </div>
      <p className="mt-1 text-lg font-semibold tabular-nums" style={{ color: "var(--text-primary)" }}>
        {kpi.actual?.toFixed(2)} {kpi.unit}
      </p>
      <div className="mt-1.5">
        <ProgressBar score={kpi.score} color={kpi.level?.color ?? "var(--accent)"} />
      </div>
      <div className="mt-2 flex flex-col gap-1">
        {kpi.vs_personal_target && <ComparisonRow label="Kişisel/Tesis Hedefi" comparison={kpi.vs_personal_target} unit={kpi.unit} />}
        {kpi.vs_factory_average && <ComparisonRow label="Fabrika Ortalaması" comparison={kpi.vs_factory_average} unit={kpi.unit} />}
      </div>
    </div>
  );
}

export function MonthlyForemanReportPage() {
  const { foremanId, year, month } = useParams<{ foremanId: string; year: string; month: string }>();
  const navigate = useNavigate();
  const [downloading, setDownloading] = useState(false);
  const yearNum = year ? Number(year) : undefined;
  const monthNum = month ? Number(month) : undefined;
  const report = useForemanMonthlyReport(foremanId, yearNum, monthNum);

  const handleDownload = async () => {
    if (!foremanId || !yearNum || !monthNum) return;
    setDownloading(true);
    try {
      const resp = await apiClient.get(`/foremen/${foremanId}/monthly-reports/${yearNum}/${monthNum}/pdf`, { responseType: "blob" });
      const url = window.URL.createObjectURL(new Blob([resp.data]));
      const a = document.createElement("a");
      a.href = url;
      a.download = `formen-performans-raporu-${yearNum}-${String(monthNum).padStart(2, "0")}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } finally {
      setDownloading(false);
    }
  };

  if (report.isLoading) return <LoadingState />;
  if (report.isError || !report.data) return <ErrorState message="Rapor bulunamadı." />;

  const data = report.data.report_data;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <button
          onClick={() => navigate(`/foremen/${foremanId}`)}
          className="flex items-center gap-1 text-xs font-medium hover:underline"
          style={{ color: "var(--accent)" }}
        >
          <ChevronLeft size={13} strokeWidth={2} />
          {data.foreman.full_name}
        </button>
        <button
          onClick={handleDownload}
          disabled={downloading}
          className="flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium text-white disabled:opacity-60"
          style={{ background: "var(--accent)" }}
        >
          <Download size={13} strokeWidth={2} />
          {downloading ? "İndiriliyor..." : "PDF İndir"}
        </button>
      </div>

      <Card>
        <h1 className="text-lg font-semibold" style={{ color: "var(--text-primary)" }}>
          {data.period.label} Aylık Bireysel Formen Değerlendirme Raporu
        </h1>
        <p className="mt-1 text-sm" style={{ color: "var(--text-secondary)" }}>
          {data.foreman.full_name} &middot; Sicil No: {data.foreman.employee_number}
        </p>
        {data.org && (
          <p className="mt-1 text-xs" style={{ color: "var(--text-muted)" }}>
            {data.org.factory_name} &middot; {data.org.plants.map((p) => p.name).join(", ")} &middot; Şef: {data.org.chief_name}
          </p>
        )}
        <p className="mt-1 text-xs" style={{ color: "var(--text-muted)" }}>
          Rapor oluşturulma tarihi: {new Date(data.generated_at).toLocaleDateString("tr-TR")}
        </p>
      </Card>

      {data.insufficient_data ? (
        <Card>
          <EmptyState message={data.insufficient_data_reason ?? "Bu dönem için değerlendirme oluşturmak adına yeterli veri bulunmamaktadır."} />
        </Card>
      ) : (
        <>
          <Card title="Aylık Performans Özeti">
            <div className="flex flex-wrap items-center gap-4">
              <div>
                <p className="text-3xl font-semibold tabular-nums" style={{ color: "var(--text-primary)" }}>{data.overall!.score.toFixed(1)}</p>
                <div className="mt-1"><PerformanceLevelBadge level={data.overall!.level} /></div>
              </div>
              <div className="grid grid-cols-2 gap-3 text-xs sm:grid-cols-4" style={{ color: "var(--text-muted)" }}>
                <div><p className="text-lg font-semibold tabular-nums" style={{ color: "var(--text-primary)" }}>{data.overall!.kpi_count.total}</p>Değerlendirilen KPI</div>
                <div><p className="text-lg font-semibold tabular-nums" style={{ color: "var(--text-primary)" }}>{data.overall!.kpi_count.above_or_at_target}</p>Hedefte/Üzerinde</div>
                <div><p className="text-lg font-semibold tabular-nums" style={{ color: "var(--text-primary)" }}>{data.overall!.kpi_count.below_target}</p>Hedefin Altında</div>
                <div><p className="text-lg font-semibold tabular-nums" style={{ color: "#dc2626" }}>{data.overall!.kpi_count.critical}</p>Kritik</div>
              </div>
            </div>
            {data.summary_text && <p className="mt-3 text-sm" style={{ color: "var(--text-secondary)" }}>{data.summary_text}</p>}
          </Card>

          <Card title="KPI Detayları">
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
              {data.kpis?.map((kpi) => <KpiCard key={kpi.kpi_id} kpi={kpi} />)}
            </div>
          </Card>

          {data.congratulations?.shown && data.congratulations.text && (
            <Card>
              <div className="flex items-start gap-3 rounded-md p-3" style={{ background: "#f0fdf422", border: "1px solid #16a34a55" }}>
                <PartyPopper size={18} strokeWidth={2} style={{ color: "#16a34a" }} className="mt-0.5 shrink-0" />
                <div>
                  <p className="text-sm font-semibold" style={{ color: "#16a34a" }}>Tebrikler!</p>
                  <p className="mt-1 text-sm" style={{ color: "var(--text-secondary)" }}>{data.congratulations.text}</p>
                </div>
              </div>
            </Card>
          )}

          {data.strengths && data.strengths.length > 0 && (
            <Card title="Güçlü Olduğun Alanlar">
              <ul className="flex flex-col gap-2">
                {data.strengths.map((item) => (
                  <li key={item.kpi_code} className="text-sm" style={{ color: "var(--text-secondary)" }}>
                    <span className="font-semibold" style={{ color: "var(--text-primary)" }}>{item.name}</span> — {item.text}
                  </li>
                ))}
              </ul>
            </Card>
          )}

          {data.improvements && data.improvements.length > 0 && (
            <Card title="Geliştirebileceğin Alanlar">
              <ul className="flex flex-col gap-2">
                {data.improvements.map((item) => (
                  <li key={item.kpi_code} className="text-sm" style={{ color: "var(--text-secondary)" }}>
                    <span className="font-semibold" style={{ color: "var(--text-primary)" }}>{item.name}</span> — {item.text}
                  </li>
                ))}
              </ul>
            </Card>
          )}

          {data.critical_attention && data.critical_attention.length > 0 && (
            <Card title="Dikkat Gerektiren Konular">
              <div className="flex flex-col gap-3">
                {data.critical_attention.map((item) => (
                  <div key={item.kpi_code} className="flex items-start gap-3 rounded-md p-3" style={{ background: "#fef2f222", border: "1px solid #dc262655" }}>
                    <AlertTriangle size={18} strokeWidth={2} style={{ color: "#dc2626" }} className="mt-0.5 shrink-0" />
                    <div>
                      <p className="text-sm font-semibold" style={{ color: "#dc2626" }}>{item.name}</p>
                      <p className="mt-1 text-sm" style={{ color: "var(--text-secondary)" }}>{item.text}</p>
                      {item.manager_prompt && <p className="mt-1 text-sm font-semibold" style={{ color: "var(--text-primary)" }}>{item.manager_prompt}</p>}
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          )}

          {data.trend && data.trend.weekly_points.length > 0 && (
            <Card title="Aylık Trend Analizi">
              <TrendChart points={data.trend.weekly_points.map((p) => ({ date: p.bucket, total_score: p.total_score, is_reliable: p.is_reliable }))} />
              {data.trend.text && <p className="mt-2 text-sm" style={{ color: "var(--text-secondary)" }}>{data.trend.text}</p>}
            </Card>
          )}

          {data.previous_month?.available && (
            <Card title={`Geçen Aya Göre (${data.previous_month.label})`}>
              <ul className="flex flex-col gap-1.5 text-sm">
                {data.previous_month.per_kpi?.map((item) => (
                  <li key={item.code} className="flex items-center justify-between">
                    <span style={{ color: "var(--text-secondary)" }}>{item.name}</span>
                    <span className="font-medium tabular-nums" style={{ color: item.is_improvement ? "#16a34a" : "#dc2626" }}>
                      {item.diff >= 0 ? "+" : ""}{item.diff.toFixed(2)} {item.is_improvement ? "(iyileşme)" : "(kötüleşme)"}
                    </span>
                  </li>
                ))}
              </ul>
            </Card>
          )}

          {data.closing_text && (
            <Card title="Aylık Değerlendirme">
              <p className="text-sm" style={{ color: "var(--text-secondary)" }}>{data.closing_text}</p>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
