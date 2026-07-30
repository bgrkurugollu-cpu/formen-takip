import { useState } from "react";
import { CheckCircle2, Download, XCircle } from "lucide-react";
import { Card, EmptyState, ErrorState, LoadingState } from "../components/StateViews";
import { useFilters } from "../hooks/useFilters";
import { FilterBar } from "../components/FilterBar";
import { Pagination } from "../components/Pagination";
import { apiClient } from "../api/client";
import { useGenerateReport, useReportHistory } from "../api/hooks";
import type { ReportFormat, ReportType } from "../api/types";
import { fieldClass, fieldStyle, labelClass, labelStyle } from "../lib/formStyles";
import { rowStyle, tdClass, thClass, theadRowStyle, thStyle } from "../lib/tableStyles";

const REPORT_TYPE_LABELS: Record<ReportType, string> = {
  company_summary: "Şirket Genel Performans",
  plant_comparison: "Tesis Karşılaştırma",
  shift_comparison: "Vardiya Karşılaştırma",
  foreman_performance: "Formen Performans",
  kpi_analysis: "KPI Analiz",
  critical_performance: "Kritik Performans",
  missing_data: "Eksik Veri",
};
const FORMAT_LABELS: Record<ReportFormat, string> = { csv: "CSV", xlsx: "Excel", pdf: "PDF" };

export function ReportsPage() {
  const { filters, setFilters, clearFilters } = useFilters();
  const [reportType, setReportType] = useState<ReportType>("plant_comparison");
  const [format, setFormat] = useState<ReportFormat>("xlsx");
  const [page, setPage] = useState(1);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);

  const generate = useGenerateReport();
  const history = useReportHistory({ page, page_size: 10 });

  const handleGenerate = () => {
    generate.mutate({
      report_type: reportType, format,
      date_from: filters.dateFrom, date_to: filters.dateTo,
      plant_ids: filters.plantIds.length ? filters.plantIds : undefined,
      factory_ids: filters.factoryIds.length ? filters.factoryIds : undefined,
      chief_ids: filters.chiefIds.length ? filters.chiefIds : undefined,
      shift_ids: filters.shiftIds.length ? filters.shiftIds : undefined,
      kpi_ids: filters.kpiIds.length ? filters.kpiIds : undefined,
    });
  };

  const handleDownload = async (id: string, fileName: string) => {
    setDownloadingId(id);
    try {
      const resp = await apiClient.get(`/reports/${id}/download`, { responseType: "blob" });
      const url = window.URL.createObjectURL(new Blob([resp.data]));
      const a = document.createElement("a");
      a.href = url;
      a.download = fileName;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } finally {
      setDownloadingId(null);
    }
  };

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-lg font-semibold" style={{ color: "var(--text-primary)" }}>Raporlar</h1>
        <p className="text-[13px]" style={{ color: "var(--text-muted)" }}>
          Filtrelenmiş sonuçları Excel, CSV veya PDF olarak dışa aktarın.
        </p>
      </div>

      <FilterBar filters={filters} setFilters={setFilters} clearFilters={clearFilters} />

      <Card title="Yeni Rapor Oluştur">
        <div className="flex flex-wrap items-end gap-3">
          <div>
            <label className={labelClass} style={labelStyle}>Rapor Türü</label>
            <select
              value={reportType}
              onChange={(e) => setReportType(e.target.value as ReportType)}
              className={fieldClass}
              style={fieldStyle}
            >
              {Object.entries(REPORT_TYPE_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
          </div>
          <div>
            <label className={labelClass} style={labelStyle}>Format</label>
            <select
              value={format}
              onChange={(e) => setFormat(e.target.value as ReportFormat)}
              className={fieldClass}
              style={fieldStyle}
            >
              {Object.entries(FORMAT_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
          </div>
          <button
            onClick={handleGenerate}
            disabled={generate.isPending}
            className="rounded-md px-4 py-2 text-[13px] font-medium text-white disabled:opacity-60"
            style={{ background: "var(--accent)" }}
          >
            {generate.isPending ? "Oluşturuluyor..." : "Rapor Oluştur"}
          </button>
        </div>
        {generate.isSuccess && (
          <p className="mt-3 flex items-center gap-1.5 text-xs font-medium text-emerald-700">
            <CheckCircle2 size={13} strokeWidth={2} />
            "{generate.data.file_name}" oluşturuldu ({generate.data.row_count} satır) — aşağıdaki geçmişten indirebilirsiniz.
          </p>
        )}
        {generate.isError && (
          <p className="mt-3 flex items-center gap-1.5 text-xs font-medium text-red-600">
            <XCircle size={13} strokeWidth={2} />
            Rapor oluşturulamadı.
          </p>
        )}
      </Card>

      <Card title="Rapor Geçmişi">
        {history.isLoading && <LoadingState />}
        {history.isError && <ErrorState />}
        {history.data && history.data.items.length === 0 && <EmptyState message="Henüz rapor oluşturulmadı." />}
        {history.data && history.data.items.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-[13px]">
              <thead>
                <tr style={theadRowStyle}>
                  <th className={thClass} style={thStyle}>Dosya</th>
                  <th className={thClass} style={thStyle}>Tür</th>
                  <th className={thClass} style={thStyle}>Format</th>
                  <th className={thClass} style={thStyle}>Satır</th>
                  <th className={thClass} style={thStyle}>Oluşturan</th>
                  <th className={thClass} style={thStyle}>Tarih</th>
                  <th className={thClass} style={thStyle} />
                </tr>
              </thead>
              <tbody>
                {history.data.items.map((r) => (
                  <tr key={r.id} style={rowStyle}>
                    <td className={`${tdClass} font-medium`} style={{ color: "var(--text-primary)" }}>{r.file_name}</td>
                    <td className={tdClass} style={{ color: "var(--text-secondary)" }}>{REPORT_TYPE_LABELS[r.report_type as ReportType] ?? r.report_type}</td>
                    <td className={`${tdClass} uppercase`} style={{ color: "var(--text-secondary)" }}>{r.format}</td>
                    <td className={`${tdClass} tabular-nums`} style={{ color: "var(--text-secondary)" }}>{r.row_count}</td>
                    <td className={tdClass} style={{ color: "var(--text-secondary)" }}>{r.requested_by ?? "-"}</td>
                    <td className={tdClass} style={{ color: "var(--text-muted)" }}>{new Date(r.created_at).toLocaleString("tr-TR")}</td>
                    <td className={tdClass}>
                      <button
                        onClick={() => handleDownload(r.id, r.file_name)}
                        disabled={downloadingId === r.id}
                        className="flex items-center gap-1 text-xs font-medium hover:underline disabled:opacity-50"
                        style={{ color: "var(--accent)" }}
                      >
                        <Download size={12} strokeWidth={2} />
                        {downloadingId === r.id ? "İndiriliyor..." : "İndir"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <Pagination page={page} pageSize={10} total={history.data.total} onPageChange={setPage} itemLabel="rapor" />
          </div>
        )}
      </Card>
    </div>
  );
}
