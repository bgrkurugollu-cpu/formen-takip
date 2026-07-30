import { useState } from "react";
import { Plus } from "lucide-react";
import { Card, EmptyState, ErrorState, LoadingState } from "../components/StateViews";
import { ActionPlanFormModal } from "../components/ActionPlanFormModal";
import { Pagination } from "../components/Pagination";
import { useActionPlans } from "../api/hooks";
import type { ActionPlanItem, ActionPlanPriority, ActionPlanStatus } from "../api/types";
import { rowHoverClass, rowStyle, searchInputClass, searchInputStyle, tdClass, thClass, theadRowStyle, thStyle } from "../lib/tableStyles";

const STATUS_LABELS: Record<ActionPlanStatus, { label: string; color: string }> = {
  open: { label: "Açık", color: "#1d4ed8" },
  in_progress: { label: "Devam Ediyor", color: "#b45309" },
  on_hold: { label: "Beklemede", color: "#64748b" },
  completed: { label: "Tamamlandı", color: "#15803d" },
  cancelled: { label: "İptal Edildi", color: "#94a3b8" },
  delayed: { label: "Gecikti", color: "#b91c1c" },
};
const PRIORITY_LABELS: Record<ActionPlanPriority, string> = {
  low: "Düşük", normal: "Normal", high: "Yüksek", critical: "Kritik",
};

export function ActionPlansPage() {
  const [status, setStatus] = useState("");
  const [priority, setPriority] = useState("");
  const [page, setPage] = useState(1);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<ActionPlanItem | null>(null);
  const pageSize = 15;

  const plans = useActionPlans({ status: status || undefined, priority: priority || undefined, page, page_size: pageSize });

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold" style={{ color: "var(--text-primary)" }}>Aksiyon Planları</h1>
          <p className="text-[13px]" style={{ color: "var(--text-muted)" }}>
            Düşük performanslı tesis/formen/KPI'lar için takip amaçlı planlar. Performans verisini değiştirmez.
          </p>
        </div>
        <button
          onClick={() => {
            setEditing(null);
            setModalOpen(true);
          }}
          className="flex items-center gap-1.5 rounded-md px-3.5 py-2 text-[13px] font-medium text-white"
          style={{ background: "var(--accent)" }}
        >
          <Plus size={14} strokeWidth={2} />
          Yeni Aksiyon Planı
        </button>
      </div>

      <div className="flex gap-2">
        <select value={status} onChange={(e) => { setStatus(e.target.value); setPage(1); }} className={searchInputClass} style={{ ...searchInputStyle, maxWidth: "12rem" }}>
          <option value="">Tüm durumlar</option>
          {Object.entries(STATUS_LABELS).map(([v, o]) => <option key={v} value={v}>{o.label}</option>)}
        </select>
        <select value={priority} onChange={(e) => { setPriority(e.target.value); setPage(1); }} className={searchInputClass} style={{ ...searchInputStyle, maxWidth: "12rem" }}>
          <option value="">Tüm öncelikler</option>
          {Object.entries(PRIORITY_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
        </select>
      </div>

      <Card>
        {plans.isLoading && <LoadingState />}
        {plans.isError && <ErrorState />}
        {plans.data && plans.data.items.length === 0 && <EmptyState message="Aksiyon planı bulunamadı." />}
        {plans.data && plans.data.items.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-[13px]">
              <thead>
                <tr style={theadRowStyle}>
                  <th className={thClass} style={thStyle}>Başlık</th>
                  <th className={thClass} style={thStyle}>Kapsam</th>
                  <th className={thClass} style={thStyle}>Sorumlu</th>
                  <th className={thClass} style={thStyle}>Öncelik</th>
                  <th className={thClass} style={thStyle}>Durum</th>
                  <th className={thClass} style={thStyle}>İlerleme</th>
                  <th className={thClass} style={thStyle}>Hedef Bitiş</th>
                </tr>
              </thead>
              <tbody>
                {plans.data.items.map((p) => (
                  <tr
                    key={p.id}
                    onClick={() => {
                      setEditing(p);
                      setModalOpen(true);
                    }}
                    className={`cursor-pointer ${rowHoverClass}`}
                    style={rowStyle}
                  >
                    <td className={`${tdClass} font-medium`} style={{ color: "var(--text-primary)" }}>{p.title}</td>
                    <td className={tdClass} style={{ color: "var(--text-muted)" }}>
                      {[p.plant?.name, p.foreman?.name, p.kpi?.name].filter(Boolean).join(" · ") || "Genel"}
                    </td>
                    <td className={tdClass} style={{ color: "var(--text-secondary)" }}>{p.owner}</td>
                    <td className={tdClass} style={{ color: "var(--text-secondary)" }}>{PRIORITY_LABELS[p.priority]}</td>
                    <td className={tdClass}>
                      <span style={{ color: STATUS_LABELS[p.status].color }} className="font-medium">
                        {STATUS_LABELS[p.status].label}
                      </span>
                    </td>
                    <td className={tdClass}>
                      <div className="h-1.5 w-24 rounded-full" style={{ background: "var(--border)" }}>
                        <div className="h-1.5 rounded-full" style={{ width: `${p.completion_percentage}%`, background: "var(--accent)" }} />
                      </div>
                    </td>
                    <td className={tdClass} style={{ color: "var(--text-muted)" }}>{p.target_end_date}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <Pagination page={page} pageSize={pageSize} total={plans.data.total} onPageChange={setPage} itemLabel="plan" />
          </div>
        )}
      </Card>

      {modalOpen && (
        <ActionPlanFormModal existing={editing ?? undefined} onClose={() => setModalOpen(false)} />
      )}
    </div>
  );
}
