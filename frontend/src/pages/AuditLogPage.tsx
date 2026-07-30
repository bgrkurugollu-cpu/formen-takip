import { useState } from "react";
import { Card, EmptyState, ErrorState, LoadingState } from "../components/StateViews";
import { Pagination } from "../components/Pagination";
import { useAuditLogs } from "../api/hooks";
import { fieldClass, fieldStyle } from "../lib/formStyles";
import { rowStyle, tdClass, thClass, theadRowStyle, thStyle } from "../lib/tableStyles";

const ACTION_LABELS: Record<string, string> = {
  login_success: "Giriş Başarılı",
  login_failed: "Giriş Başarısız",
  resync_triggered: "Yeniden Senkronizasyon",
  action_plan_created: "Aksiyon Planı Oluşturuldu",
  action_plan_updated: "Aksiyon Planı Güncellendi",
  report_generated: "Rapor Oluşturuldu",
  report_downloaded: "Rapor İndirildi",
};

export function AuditLogPage() {
  const [action, setAction] = useState("");
  const [page, setPage] = useState(1);
  const pageSize = 25;

  const logs = useAuditLogs({ action: action || undefined, page, page_size: pageSize });

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-lg font-semibold" style={{ color: "var(--text-primary)" }}>Denetim Kayıtları</h1>
        <p className="text-[13px]" style={{ color: "var(--text-muted)" }}>
          Giriş/çıkış denemeleri, rapor üretimi/indirme, aksiyon planı değişiklikleri ve senkronizasyon tetikleme
          olaylarının salt-okunur kaydı.
        </p>
      </div>

      <select
        value={action}
        onChange={(e) => {
          setAction(e.target.value);
          setPage(1);
        }}
        className={fieldClass}
        style={{ ...fieldStyle, maxWidth: "18rem" }}
      >
        <option value="">Tüm eylemler</option>
        {Object.entries(ACTION_LABELS).map(([value, label]) => (
          <option key={value} value={value}>{label}</option>
        ))}
      </select>

      <Card>
        {logs.isLoading && <LoadingState />}
        {logs.isError && <ErrorState />}
        {logs.data && logs.data.items.length === 0 && <EmptyState />}
        {logs.data && logs.data.items.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-[13px]">
              <thead>
                <tr style={theadRowStyle}>
                  <th className={thClass} style={thStyle}>Zaman</th>
                  <th className={thClass} style={thStyle}>Eylem</th>
                  <th className={thClass} style={thStyle}>Kullanıcı</th>
                  <th className={thClass} style={thStyle}>Detay</th>
                  <th className={thClass} style={thStyle}>IP</th>
                  <th className={thClass} style={thStyle}>Sonuç</th>
                </tr>
              </thead>
              <tbody>
                {logs.data.items.map((l) => (
                  <tr key={l.id} style={rowStyle}>
                    <td className={tdClass} style={{ color: "var(--text-secondary)" }}>{new Date(l.created_at).toLocaleString("tr-TR")}</td>
                    <td className={`${tdClass} font-medium`} style={{ color: "var(--text-primary)" }}>{ACTION_LABELS[l.action] ?? l.action}</td>
                    <td className={tdClass} style={{ color: "var(--text-secondary)" }}>{l.user_name ?? "-"}</td>
                    <td className={`${tdClass} max-w-xs truncate`} style={{ color: "var(--text-muted)" }} title={l.new_value ?? l.error_message ?? undefined}>
                      {l.new_value ?? l.error_message ?? "-"}
                    </td>
                    <td className={tdClass} style={{ color: "var(--text-muted)" }}>{l.ip_address ?? "-"}</td>
                    <td className={tdClass}>
                      {l.success ? (
                        <span className="font-medium text-emerald-700">Başarılı</span>
                      ) : (
                        <span className="font-medium text-red-600">Başarısız</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <Pagination page={page} pageSize={pageSize} total={logs.data.total} onPageChange={setPage} itemLabel="kayıt" />
          </div>
        )}
      </Card>
    </div>
  );
}
