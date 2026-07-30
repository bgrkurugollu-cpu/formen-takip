import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowRight, Plus } from "lucide-react";
import { Card, EmptyState, LoadingState } from "./StateViews";
import { ActionPlanFormModal } from "./ActionPlanFormModal";
import { useActionPlans } from "../api/hooks";

const STATUS_COLORS: Record<string, string> = {
  open: "#1d4ed8", in_progress: "#b45309", on_hold: "#64748b",
  completed: "#15803d", cancelled: "#94a3b8", delayed: "#b91c1c",
};

interface Props {
  plantId?: string;
  chiefId?: string;
  foremanId?: string;
  kpiId?: string;
  title?: string;
}

export function RelatedActionPlans({ plantId, chiefId, foremanId, kpiId, title = "İlgili Aksiyon Planları" }: Props) {
  const [modalOpen, setModalOpen] = useState(false);
  const plans = useActionPlans({
    plant_id: plantId, chief_id: chiefId, foreman_id: foremanId, kpi_id: kpiId, page_size: 5,
  });
  const navigate = useNavigate();

  return (
    <Card
      title={title}
      action={
        <button
          onClick={() => setModalOpen(true)}
          className="flex items-center gap-1 text-xs font-medium hover:underline"
          style={{ color: "var(--accent)" }}
        >
          <Plus size={13} strokeWidth={2} />
          Yeni
        </button>
      }
    >
      {plans.isLoading && <LoadingState />}
      {plans.data && plans.data.items.length === 0 && <EmptyState message="Açık aksiyon planı yok." />}
      {plans.data && plans.data.items.length > 0 && (
        <ul className="flex flex-col gap-2 text-[13px]">
          {plans.data.items.map((p) => (
            <li key={p.id} className="flex items-center justify-between gap-2 pb-2 last:pb-0" style={{ borderBottom: "1px solid var(--border)" }}>
              <span className="truncate" style={{ color: "var(--text-primary)" }}>{p.title}</span>
              <span className="shrink-0 text-xs font-medium tabular-nums" style={{ color: STATUS_COLORS[p.status] }}>
                %{p.completion_percentage}
              </span>
            </li>
          ))}
        </ul>
      )}
      {plans.data && plans.data.total > 5 && (
        <button
          onClick={() => navigate("/action-plans")}
          className="mt-3 inline-flex items-center gap-1 text-xs font-medium hover:underline"
          style={{ color: "var(--accent)" }}
        >
          Tümünü görüntüle ({plans.data.total})
          <ArrowRight size={13} strokeWidth={2} />
        </button>
      )}
      {modalOpen && (
        <ActionPlanFormModal
          onClose={() => setModalOpen(false)}
          defaultPlantId={plantId}
          defaultChiefId={chiefId}
          defaultForemanId={foremanId}
          defaultKpiId={kpiId}
        />
      )}
    </Card>
  );
}
