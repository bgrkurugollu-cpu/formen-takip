import { useState } from "react";
import { Card, EmptyState, ErrorState, LoadingState } from "../components/StateViews";
import { Pagination } from "../components/Pagination";
import { useDataQualitySummary, useDataQualityIssues } from "../api/hooks";
import { rowStyle, tdClass, thClass, theadRowStyle, thStyle } from "../lib/tableStyles";

const ISSUE_TYPE_LABELS: Record<string, string> = {
  missing: "Eksik",
  invalid: "Hatalı",
  suspicious: "Şüpheli",
  duplicate: "Tekrarlı",
  needs_source_correction: "Kaynakta Düzeltilmeli",
  pending_resync: "Yeniden Senkronizasyon Bekliyor",
  reprocessed: "Yeniden İşlendi",
};

export function DataQualityPage() {
  const [issueType, setIssueType] = useState<string>("");
  const [page, setPage] = useState(1);
  const pageSize = 20;

  const summary = useDataQualitySummary();
  const issues = useDataQualityIssues({ issue_type: issueType || undefined, page, page_size: pageSize });

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-lg font-semibold" style={{ color: "var(--text-primary)" }}>Veri Kalitesi</h1>
        <p className="text-[13px]" style={{ color: "var(--text-muted)" }}>
          Eksik, hatalı, tekrarlı veya kaynakta düzeltilmesi gereken performans kayıtları. Bu kayıtlar sessizce
          düzeltilmez — kaynak sistemde (SAP/sentetik üretici) düzeltilip yeniden senkronize edilmesi gerekir.
        </p>
      </div>

      {summary.isLoading && <LoadingState />}
      {summary.isError && <ErrorState />}
      {summary.data && (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          {summary.data.by_type.map((t) => {
            const active = issueType === t.issue_type;
            return (
              <button
                key={t.issue_type}
                onClick={() => {
                  setIssueType(t.issue_type);
                  setPage(1);
                }}
                className="rounded-lg p-4 text-left transition-colors"
                style={{
                  background: "var(--surface)",
                  border: active ? "1px solid var(--accent)" : "1px solid var(--border)",
                }}
              >
                <p className="text-[11px] font-semibold uppercase tracking-wide" style={{ color: "var(--text-muted)" }}>
                  {ISSUE_TYPE_LABELS[t.issue_type] ?? t.issue_type}
                </p>
                <p className="mt-1.5 text-2xl font-semibold tabular-nums" style={{ color: "var(--text-primary)" }}>{t.count}</p>
              </button>
            );
          })}
        </div>
      )}

      <Card title="En Çok Sorunlu Tesisler">
        {summary.data && summary.data.top_plants.length === 0 && <EmptyState message="Sorunlu tesis bulunamadı." />}
        {summary.data && summary.data.top_plants.length > 0 && (
          <ul className="flex flex-col gap-1.5 text-[13px]">
            {summary.data.top_plants.map((p) => (
              <li key={p.plant_id} className="flex justify-between py-1 last:pb-0" style={{ borderBottom: "1px solid var(--border)" }}>
                <span style={{ color: "var(--text-primary)" }}>{p.plant_name}</span>
                <span className="font-medium tabular-nums" style={{ color: "var(--text-secondary)" }}>{p.issue_count} sorun</span>
              </li>
            ))}
          </ul>
        )}
      </Card>

      <Card
        title="Sorun Listesi"
        action={
          issueType ? (
            <button
              onClick={() => {
                setIssueType("");
                setPage(1);
              }}
              className="text-xs font-medium hover:underline"
              style={{ color: "var(--accent)" }}
            >
              Filtreyi temizle
            </button>
          ) : undefined
        }
      >
        {issues.isLoading && <LoadingState />}
        {issues.isError && <ErrorState />}
        {issues.data && issues.data.items.length === 0 && <EmptyState />}
        {issues.data && issues.data.items.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-[13px]">
              <thead>
                <tr style={theadRowStyle}>
                  <th className={thClass} style={thStyle}>Tarih</th>
                  <th className={thClass} style={thStyle}>Tesis</th>
                  <th className={thClass} style={thStyle}>Formen</th>
                  <th className={thClass} style={thStyle}>KPI</th>
                  <th className={thClass} style={thStyle}>Sorun Türü</th>
                  <th className={thClass} style={thStyle}>Açıklama</th>
                </tr>
              </thead>
              <tbody>
                {issues.data.items.map((i) => (
                  <tr key={i.id} style={rowStyle}>
                    <td className={tdClass} style={{ color: "var(--text-secondary)" }}>{i.performance_date ?? "-"}</td>
                    <td className={tdClass} style={{ color: "var(--text-primary)" }}>{i.plant_name ?? "-"}</td>
                    <td className={tdClass} style={{ color: "var(--text-primary)" }}>{i.foreman_name ?? "-"}</td>
                    <td className={tdClass} style={{ color: "var(--text-primary)" }}>{i.kpi_name ?? "-"}</td>
                    <td className={tdClass}>
                      <span
                        className="rounded px-2 py-0.5 text-xs font-medium"
                        style={{ background: "#fef3c7", color: "#92400e" }}
                      >
                        {ISSUE_TYPE_LABELS[i.issue_type] ?? i.issue_type}
                      </span>
                    </td>
                    <td className={`${tdClass} max-w-xs truncate`} style={{ color: "var(--text-muted)" }} title={i.description}>
                      {i.description}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <Pagination page={page} pageSize={pageSize} total={issues.data.total} onPageChange={setPage} itemLabel="sorun" />
          </div>
        )}
      </Card>
    </div>
  );
}
