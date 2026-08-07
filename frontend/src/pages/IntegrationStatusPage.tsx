import { useState } from "react";
import { AlertTriangle, CheckCircle2, XCircle } from "lucide-react";
import { Card, EmptyState, ErrorState, LoadingState } from "../components/StateViews";
import { Pagination } from "../components/Pagination";
import { useIntegrationRuns, useTriggerResync } from "../api/hooks";
import { fieldClass, fieldStyle, labelClass, labelStyle } from "../lib/formStyles";
import { rowStyle, tdClass, thClass, theadRowStyle, thStyle } from "../lib/tableStyles";

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}
function daysAgoIso(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() - days);
  return d.toISOString().slice(0, 10);
}

const STATUS_LABELS: Record<string, { label: string; color: string }> = {
  success: { label: "Başarılı", color: "#15803d" },
  partial_success: { label: "Kısmen Başarılı", color: "#b45309" },
  failed: { label: "Başarısız", color: "#b91c1c" },
  running: { label: "Çalışıyor", color: "#1d4ed8" },
};

export function IntegrationStatusPage() {
  const [page, setPage] = useState(1);
  const [dateFrom, setDateFrom] = useState(daysAgoIso(7));
  const [dateTo, setDateTo] = useState(todayIso());
  const [confirming, setConfirming] = useState(false);

  const runs = useIntegrationRuns({ page, page_size: 15 });
  const resync = useTriggerResync();

  const handleResync = () => {
    resync.mutate({ date_from: dateFrom, date_to: dateTo });
    setConfirming(false);
  };

  return (
    <div className="flex flex-col gap-4">
      <Card title="Manuel Yeniden Senkronizasyon">
        <div className="flex flex-wrap items-end gap-3">
          <div>
            <label className={labelClass} style={labelStyle}>Başlangıç</label>
            <input
              type="date" value={dateFrom} max={dateTo}
              onChange={(e) => setDateFrom(e.target.value)}
              className={fieldClass}
              style={fieldStyle}
            />
          </div>
          <div>
            <label className={labelClass} style={labelStyle}>Bitiş</label>
            <input
              type="date" value={dateTo} min={dateFrom} max={todayIso()}
              onChange={(e) => setDateTo(e.target.value)}
              className={fieldClass}
              style={fieldStyle}
            />
          </div>
          {!confirming ? (
            <button
              onClick={() => setConfirming(true)}
              className="rounded-md px-4 py-2 text-[13px] font-medium text-white"
              style={{ background: "var(--accent)" }}
            >
              Yeniden Senkronize Et
            </button>
          ) : (
            <div
              className="flex items-center gap-2 rounded-md px-3 py-2 text-[13px]"
              style={{ background: "#fffbeb", border: "1px solid #fcd34d", color: "#92400e" }}
            >
              <AlertTriangle size={14} strokeWidth={2} className="shrink-0" />
              <span>{dateFrom} — {dateTo} aralığı için sentetik sağlayıcı yeniden çalıştırılacak. Onaylıyor musunuz?</span>
              <button onClick={handleResync} className="font-semibold hover:underline">Evet</button>
              <button onClick={() => setConfirming(false)} className="hover:underline">Vazgeç</button>
            </div>
          )}
        </div>
        {resync.isPending && <p className="mt-3 text-xs" style={{ color: "var(--text-muted)" }}>Senkronizasyon çalışıyor, bu biraz sürebilir...</p>}
        {resync.isSuccess && (
          <p className="mt-3 flex items-center gap-1.5 text-xs font-medium text-emerald-700">
            <CheckCircle2 size={13} strokeWidth={2} />
            Tamamlandı — işlenen: {resync.data.processed_count}, başarılı: {resync.data.success_count}, atlanan: {resync.data.skipped_count}
          </p>
        )}
        {resync.isError && (
          <p className="mt-3 flex items-center gap-1.5 text-xs font-medium text-red-600">
            <XCircle size={13} strokeWidth={2} />
            Senkronizasyon başarısız oldu.
          </p>
        )}
      </Card>

      <Card title="Senkronizasyon Geçmişi">
        {runs.isLoading && <LoadingState />}
        {runs.isError && <ErrorState />}
        {runs.data && runs.data.items.length === 0 && <EmptyState />}
        {runs.data && runs.data.items.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-[13px]">
              <thead>
                <tr style={theadRowStyle}>
                  <th className={thClass} style={thStyle}>Başlangıç</th>
                  <th className={thClass} style={thStyle}>Kaynak</th>
                  <th className={thClass} style={thStyle}>Durum</th>
                  <th className={thClass} style={thStyle}>İşlenen</th>
                  <th className={thClass} style={thStyle}>Başarılı</th>
                  <th className={thClass} style={thStyle}>Atlanan</th>
                  <th className={thClass} style={thStyle}>Hatalı</th>
                  <th className={thClass} style={thStyle}>Süre (sn)</th>
                </tr>
              </thead>
              <tbody>
                {runs.data.items.map((r) => (
                  <tr key={r.id} style={rowStyle}>
                    <td className={tdClass} style={{ color: "var(--text-secondary)" }}>{new Date(r.started_at).toLocaleString("tr-TR")}</td>
                    <td className={tdClass} style={{ color: "var(--text-secondary)" }}>{r.source_system}</td>
                    <td className={`${tdClass} font-medium`} style={{ color: STATUS_LABELS[r.status]?.color ?? "var(--text-primary)" }}>
                      {STATUS_LABELS[r.status]?.label ?? r.status}
                    </td>
                    <td className={`${tdClass} tabular-nums`} style={{ color: "var(--text-secondary)" }}>{r.processed_count}</td>
                    <td className={`${tdClass} tabular-nums`} style={{ color: "var(--text-secondary)" }}>{r.success_count}</td>
                    <td className={`${tdClass} tabular-nums`} style={{ color: "var(--text-secondary)" }}>{r.skipped_count}</td>
                    <td className={`${tdClass} tabular-nums`} style={{ color: "var(--text-secondary)" }}>{r.error_count}</td>
                    <td className={`${tdClass} tabular-nums`} style={{ color: "var(--text-secondary)" }}>{r.duration_seconds != null ? r.duration_seconds.toFixed(1) : "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <Pagination page={page} pageSize={15} total={runs.data.total} onPageChange={setPage} itemLabel="koşu" />
          </div>
        )}
      </Card>
    </div>
  );
}
