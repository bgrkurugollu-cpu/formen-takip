import { useState } from "react";
import { X } from "lucide-react";
import { useCreateActionPlan, useFilterOptions, useForemen, useUpdateActionPlan } from "../api/hooks";
import type { ActionPlanItem, ActionPlanPriority, ActionPlanStatus } from "../api/types";
import { fieldClass, fieldStyle, labelClass, labelStyle } from "../lib/formStyles";

const PRIORITY_LABELS: Record<ActionPlanPriority, string> = {
  low: "Düşük", normal: "Normal", high: "Yüksek", critical: "Kritik",
};
const STATUS_LABELS: Record<ActionPlanStatus, string> = {
  open: "Açık", in_progress: "Devam Ediyor", on_hold: "Beklemede",
  completed: "Tamamlandı", cancelled: "İptal Edildi", delayed: "Gecikti",
};

interface Props {
  onClose: () => void;
  existing?: ActionPlanItem;
  defaultPlantId?: string;
  defaultChiefId?: string;
  defaultForemanId?: string;
  defaultKpiId?: string;
}

export function ActionPlanFormModal({ onClose, existing, defaultPlantId, defaultChiefId, defaultForemanId, defaultKpiId }: Props) {
  const isEdit = !!existing;
  const [title, setTitle] = useState(existing?.title ?? "");
  const [description, setDescription] = useState(existing?.description ?? "");
  const [plantId, setPlantId] = useState(existing?.plant?.id ?? defaultPlantId ?? "");
  const [kpiId, setKpiId] = useState(existing?.kpi?.id ?? defaultKpiId ?? "");
  const [foremanSearch, setForemanSearch] = useState("");
  const [foremanId, setForemanId] = useState(existing?.foreman?.id ?? defaultForemanId ?? "");
  const [owner, setOwner] = useState(existing?.owner ?? "");
  const [priority, setPriority] = useState<ActionPlanPriority>(existing?.priority ?? "normal");
  const [status, setStatus] = useState<ActionPlanStatus>(existing?.status ?? "open");
  const [startDate, setStartDate] = useState(existing?.start_date ?? new Date().toISOString().slice(0, 10));
  const [targetEndDate, setTargetEndDate] = useState(
    existing?.target_end_date ?? new Date(Date.now() + 30 * 86400000).toISOString().slice(0, 10)
  );
  const [completion, setCompletion] = useState(existing?.completion_percentage ?? 0);
  const [outcomeNotes, setOutcomeNotes] = useState(existing?.outcome_notes ?? "");
  const [error, setError] = useState<string | null>(null);

  const filterOptions = useFilterOptions();
  const foremenResults = useForemen({ search: foremanSearch || undefined, page_size: 8 });
  const createMutation = useCreateActionPlan();
  const updateMutation = useUpdateActionPlan();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (targetEndDate < startDate) {
      setError("Hedef bitiş tarihi, başlangıç tarihinden önce olamaz.");
      return;
    }
    try {
      if (isEdit) {
        await updateMutation.mutateAsync({
          id: existing.id,
          payload: { title, description, owner, priority, status, target_end_date: targetEndDate, completion_percentage: completion, outcome_notes: outcomeNotes },
        });
      } else {
        await createMutation.mutateAsync({
          title, description: description || undefined,
          plant_id: plantId || undefined, kpi_id: kpiId || undefined, foreman_id: foremanId || undefined,
          chief_id: defaultChiefId || undefined,
          owner, priority, status, start_date: startDate, target_end_date: targetEndDate,
          completion_percentage: completion, outcome_notes: outcomeNotes || undefined,
        });
      }
      onClose();
    } catch {
      setError("Kaydedilemedi. Lütfen tekrar deneyin.");
    }
  };

  const isPending = createMutation.isPending || updateMutation.isPending;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={onClose}>
      <form
        onSubmit={handleSubmit}
        onClick={(e) => e.stopPropagation()}
        className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-lg p-5 shadow-xl"
        style={{ background: "var(--surface)" }}
      >
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
            {isEdit ? "Aksiyon Planını Güncelle" : "Yeni Aksiyon Planı"}
          </h3>
          <button type="button" onClick={onClose} style={{ color: "var(--text-muted)" }}>
            <X size={16} strokeWidth={2} />
          </button>
        </div>

        <div className="flex flex-col gap-3">
          <div>
            <label className={labelClass} style={labelStyle}>Başlık</label>
            <input required value={title} onChange={(e) => setTitle(e.target.value)} className={fieldClass} style={fieldStyle} />
          </div>
          <div>
            <label className={labelClass} style={labelStyle}>Açıklama</label>
            <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={2} className={fieldClass} style={fieldStyle} />
          </div>

          {!isEdit && (
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className={labelClass} style={labelStyle}>Tesis (opsiyonel)</label>
                <select value={plantId} onChange={(e) => setPlantId(e.target.value)} className={fieldClass} style={fieldStyle}>
                  <option value="">-</option>
                  {filterOptions.data?.plants.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
                </select>
              </div>
              <div>
                <label className={labelClass} style={labelStyle}>KPI (opsiyonel)</label>
                <select value={kpiId} onChange={(e) => setKpiId(e.target.value)} className={fieldClass} style={fieldStyle}>
                  <option value="">-</option>
                  {filterOptions.data?.kpis.map((k) => <option key={k.id} value={k.id}>{k.name}</option>)}
                </select>
              </div>
              <div className="col-span-2">
                <label className={labelClass} style={labelStyle}>Formen ara (opsiyonel)</label>
                <input
                  value={foremanSearch}
                  onChange={(e) => setForemanSearch(e.target.value)}
                  placeholder="Ad soyad veya sicil no..."
                  className={fieldClass}
                  style={fieldStyle}
                />
                {foremanSearch && foremenResults.data && (
                  <div className="mt-1 max-h-32 overflow-y-auto rounded-md" style={{ border: "1px solid var(--border)" }}>
                    {foremenResults.data.items.map((f) => (
                      <button
                        type="button"
                        key={f.id}
                        onClick={() => {
                          setForemanId(f.id);
                          setForemanSearch(f.full_name);
                        }}
                        className="block w-full px-2 py-1 text-left text-xs hover:bg-[var(--page-bg)]"
                        style={foremanId === f.id ? { background: "var(--accent-subtle)", color: "var(--accent)" } : { color: "var(--text-secondary)" }}
                      >
                        {f.full_name} — {f.employee_number}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          <div>
            <label className={labelClass} style={labelStyle}>Sorumlu Kişi/Ekip</label>
            <input required value={owner} onChange={(e) => setOwner(e.target.value)} className={fieldClass} style={fieldStyle} />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className={labelClass} style={labelStyle}>Öncelik</label>
              <select value={priority} onChange={(e) => setPriority(e.target.value as ActionPlanPriority)} className={fieldClass} style={fieldStyle}>
                {Object.entries(PRIORITY_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </select>
            </div>
            <div>
              <label className={labelClass} style={labelStyle}>Durum</label>
              <select value={status} onChange={(e) => setStatus(e.target.value as ActionPlanStatus)} className={fieldClass} style={fieldStyle}>
                {Object.entries(STATUS_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className={labelClass} style={labelStyle}>Başlangıç Tarihi</label>
              <input type="date" required disabled={isEdit} value={startDate} onChange={(e) => setStartDate(e.target.value)} className={`${fieldClass} disabled:opacity-50`} style={fieldStyle} />
            </div>
            <div>
              <label className={labelClass} style={labelStyle}>Hedef Bitiş</label>
              <input type="date" required value={targetEndDate} onChange={(e) => setTargetEndDate(e.target.value)} className={fieldClass} style={fieldStyle} />
            </div>
          </div>

          <div>
            <label className={labelClass} style={labelStyle}>Tamamlanma Oranı: %{completion}</label>
            <input type="range" min={0} max={100} value={completion} onChange={(e) => setCompletion(Number(e.target.value))} className="w-full" />
          </div>

          <div>
            <label className={labelClass} style={labelStyle}>Sonuç Notu</label>
            <textarea value={outcomeNotes} onChange={(e) => setOutcomeNotes(e.target.value)} rows={2} className={fieldClass} style={fieldStyle} />
          </div>

          {error && <p className="text-xs font-medium text-red-600">{error}</p>}

          <button
            type="submit"
            disabled={isPending}
            className="mt-1 rounded-md py-2 text-sm font-medium text-white disabled:opacity-60"
            style={{ background: "var(--accent)" }}
          >
            {isPending ? "Kaydediliyor..." : isEdit ? "Güncelle" : "Oluştur"}
          </button>
        </div>
      </form>
    </div>
  );
}
