import { useEffect, useMemo, useState, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { ChevronDown, Plus, Trash2, TriangleAlert, X } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { useCreateContributionWork, useFilterOptions, useUpdateContributionWork } from "../api/hooks";
import type {
  ContributionCurrency, ContributionGainInput, ContributionTimeUnit, ContributionWorkCreatePayload,
  ContributionWorkItem, ContributionWorkType, FinancialGainStatus, GainPeriod, ImpactLevel,
  OtherGainType, RepeatPeriod, VerifyingDepartment,
} from "../api/types";
import { computeChange, computeMonthlyTotal, computeTimeSaving, durationToMinutes, formatMinutes } from "../lib/contributionCalc";
import { IMPACT_LEVEL_LABELS, WORK_TYPE_LABELS } from "../lib/contributionTheme";
import { fieldClass, fieldStyle, labelClass, labelStyle } from "../lib/formStyles";
import { ForemanMultiSelect, type SelectedForeman } from "./ForemanMultiSelect";

const WORK_TYPE_OPTIONS = Object.entries(WORK_TYPE_LABELS) as [ContributionWorkType, string][];
const IMPACT_OPTIONS = Object.entries(IMPACT_LEVEL_LABELS) as [ImpactLevel, string][];

const FINANCIAL_STATUS_LABELS: Record<FinancialGainStatus, string> = {
  yes: "Evet", no: "Hayır", not_calculated: "Henüz hesaplanmadı",
};
const GAIN_PERIOD_LABELS: Record<GainPeriod, string> = { one_time: "Tek seferlik", monthly: "Aylık", yearly: "Yıllık" };
const DEPARTMENT_LABELS: Record<VerifyingDepartment, string> = {
  finance: "Finans", production: "Üretim", maintenance: "Bakım", quality: "Kalite",
  safety: "İş Güvenliği", energy: "Enerji", hr: "İnsan Kaynakları", other: "Diğer",
};
const TIME_UNIT_LABELS: Record<ContributionTimeUnit, string> = { second: "Saniye", minute: "Dakika", hour: "Saat" };
const REPEAT_PERIOD_LABELS: Record<RepeatPeriod, string> = { daily: "Günlük", weekly: "Haftalık", monthly: "Aylık" };
const GAIN_TYPE_LABELS: Record<OtherGainType, string> = {
  capacity_increase: "Üretim kapasitesi artışı", downtime_reduction: "Duruş süresi azalması",
  gsf_reduction: "GSF azalması", scrap_reduction: "Iskarta azalması", slow_running_reduction: "Ağır gitme azalması",
  safety_risk_reduction: "İş kazası riskinin azalması", energy_reduction: "Enerji tüketimi azalması",
  labor_saving: "İş gücü tasarrufu", quality_defect_reduction: "Kalite hatası azalması", other: "Diğer",
};

function Section({ title, subtitle, children, defaultOpen = true, hasError }: {
  title: string; subtitle?: string; children: ReactNode; defaultOpen?: boolean; hasError?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="rounded-lg" style={{ border: `1px solid ${hasError ? "#b91c1c" : "var(--border)"}` }}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between px-4 py-3"
      >
        <div className="text-left">
          <div className="flex items-center gap-2 text-[13px] font-semibold" style={{ color: "var(--text-primary)" }}>
            {title}
            {hasError && <TriangleAlert size={13} strokeWidth={2.5} color="#b91c1c" />}
          </div>
          {subtitle && <div className="mt-0.5 text-xs" style={{ color: "var(--text-muted)" }}>{subtitle}</div>}
        </div>
        <ChevronDown size={16} strokeWidth={2} className={open ? "rotate-180 transition-transform" : "transition-transform"} style={{ color: "var(--text-muted)" }} />
      </button>
      {open && <div className="flex flex-col gap-3 border-t px-4 py-4" style={{ borderColor: "var(--border)" }}>{children}</div>}
    </div>
  );
}

function FieldError({ message }: { message?: string }) {
  if (!message) return null;
  return <p className="text-xs font-medium" style={{ color: "#b91c1c" }}>{message}</p>;
}

interface Props {
  existing?: ContributionWorkItem;
  onClose: () => void;
}

export function ContributionWorkForm({ existing, onClose }: Props) {
  const isEdit = !!existing;
  const navigate = useNavigate();
  const { user } = useAuth();
  const filterOptions = useFilterOptions();
  const createMutation = useCreateContributionWork();
  const updateMutation = useUpdateContributionWork();

  const [title, setTitle] = useState(existing?.title ?? "");
  const [workType, setWorkType] = useState<ContributionWorkType | "">(existing?.work_type ?? "");
  const [workTypeOtherNote, setWorkTypeOtherNote] = useState(existing?.work_type_other_note ?? "");
  const [foremen, setForemen] = useState<SelectedForeman[]>(existing?.foremen.map((f) => ({ id: f.id, name: f.name })) ?? []);
  const [factoryId, setFactoryId] = useState(existing?.plant?.factory_id ?? "");
  const [plantId, setPlantId] = useState(existing?.plant?.id ?? "");
  const [dateMode, setDateMode] = useState<"single" | "range">(existing?.work_date_end ? "range" : "single");
  const [workDate, setWorkDate] = useState(existing?.work_date ?? "");
  const [workDateEnd, setWorkDateEnd] = useState(existing?.work_date_end ?? "");
  const [impactLevel, setImpactLevel] = useState<ImpactLevel | "">(existing?.impact_level ?? "medium");

  const [summary, setSummary] = useState(existing?.summary ?? "");
  const [detailedDescription, setDetailedDescription] = useState(existing?.detailed_description ?? "");
  const [problemDescription, setProblemDescription] = useState(existing?.problem_description ?? "");
  const [solutionDescription, setSolutionDescription] = useState(existing?.solution_description ?? "");
  const [resultDescription, setResultDescription] = useState(existing?.result_description ?? "");

  const [financialGainStatus, setFinancialGainStatus] = useState<FinancialGainStatus>(existing?.financial_gain_status ?? "not_calculated");
  const [estimatedAmount, setEstimatedAmount] = useState(existing?.estimated_amount?.toString() ?? "");
  const [verifiedAmount, setVerifiedAmount] = useState(existing?.verified_amount?.toString() ?? "");
  const [currency, setCurrency] = useState<ContributionCurrency>(existing?.currency ?? "TRY");
  const [gainPeriod, setGainPeriod] = useState<GainPeriod | "">(existing?.gain_period ?? "");
  const [isGainVerified, setIsGainVerified] = useState(existing?.is_gain_verified ?? false);
  const [verifiedByDepartment, setVerifiedByDepartment] = useState<VerifyingDepartment | "">(existing?.verified_by_department ?? "");
  const [verifiedByDepartmentOtherNote, setVerifiedByDepartmentOtherNote] = useState(existing?.verified_by_department_other_note ?? "");
  const [verificationDate, setVerificationDate] = useState(existing?.verification_date ?? "");
  const [verificationNote, setVerificationNote] = useState(existing?.verification_note ?? "");

  const [previousDuration, setPreviousDuration] = useState(existing?.previous_duration?.toString() ?? "");
  const [newDuration, setNewDuration] = useState(existing?.new_duration?.toString() ?? "");
  const [durationUnit, setDurationUnit] = useState<ContributionTimeUnit>(existing?.duration_unit ?? "minute");
  const [repeatPeriod, setRepeatPeriod] = useState<RepeatPeriod | "">(existing?.repeat_period ?? "");

  const [gains, setGains] = useState<ContributionGainInput[]>(
    existing?.gains.map((g) => ({
      gain_type: g.gain_type, gain_type_other_note: g.gain_type_other_note ?? undefined,
      previous_value: g.previous_value ?? undefined, next_value: g.next_value ?? undefined,
      unit: g.unit ?? undefined, measurement_period: g.measurement_period ?? undefined, description: g.description ?? undefined,
    })) ?? []
  );

  const [isStandardized, setIsStandardized] = useState(existing?.is_standardized ?? false);
  const [isApplicableOtherPlants, setIsApplicableOtherPlants] = useState(existing?.is_applicable_other_plants ?? false);
  const [isPermanentSolution, setIsPermanentSolution] = useState(existing?.is_permanent_solution ?? false);
  const [workInstructionUpdated, setWorkInstructionUpdated] = useState(existing?.work_instruction_updated ?? false);

  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [dirty, setDirty] = useState(false);

  useEffect(() => {
    const handler = (e: BeforeUnloadEvent) => {
      if (!dirty) return;
      e.preventDefault();
    };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [dirty]);

  const markDirty = <T,>(setter: (v: T) => void) => (v: T) => {
    setDirty(true);
    setter(v);
  };

  const plantsForFactory = useMemo(
    () => (filterOptions.data?.plants ?? []).filter((p) => !factoryId || p.factory_id === factoryId),
    [filterOptions.data, factoryId]
  );

  const prevDurationNum = previousDuration === "" ? null : Number(previousDuration);
  const newDurationNum = newDuration === "" ? null : Number(newDuration);
  const perOccurrenceSaving = computeTimeSaving(prevDurationNum, newDurationNum);
  const newDurationInvalid = prevDurationNum != null && newDurationNum != null && newDurationNum >= prevDurationNum;
  const perOccurrenceMinutes = durationToMinutes(perOccurrenceSaving, durationUnit);
  const monthlyTotal = computeMonthlyTotal(perOccurrenceMinutes, repeatPeriod || null, repeatPeriod ? 1 : null);

  const handleClose = () => {
    if (dirty && !window.confirm("Kaydedilmemiş değişiklikleriniz var. Çıkmak istediğinize emin misiniz?")) return;
    onClose();
  };

  function addGain() {
    setDirty(true);
    setGains((g) => [...g, { gain_type: "other" }]);
  }
  function updateGain(index: number, patch: Partial<ContributionGainInput>) {
    setDirty(true);
    setGains((g) => g.map((item, i) => (i === index ? { ...item, ...patch } : item)));
  }
  function removeGain(index: number) {
    setDirty(true);
    setGains((g) => g.filter((_, i) => i !== index));
  }

  function buildPayload(status: "draft" | "published"): ContributionWorkCreatePayload {
    return {
      title, status,
      work_type: workType || undefined,
      work_type_other_note: workTypeOtherNote || undefined,
      summary: summary || undefined,
      detailed_description: detailedDescription || undefined,
      problem_description: problemDescription || undefined,
      solution_description: solutionDescription || undefined,
      result_description: resultDescription || undefined,
      foreman_ids: foremen.map((f) => f.id),
      plant_id: plantId || undefined,
      work_date: workDate || undefined,
      work_date_end: dateMode === "range" ? workDateEnd || undefined : undefined,
      impact_level: impactLevel || undefined,
      is_standardized: isStandardized,
      is_applicable_other_plants: isApplicableOtherPlants,
      is_permanent_solution: isPermanentSolution,
      work_instruction_updated: workInstructionUpdated,
      financial_gain_status: financialGainStatus,
      estimated_amount: estimatedAmount === "" ? undefined : Number(estimatedAmount),
      verified_amount: verifiedAmount === "" ? undefined : Number(verifiedAmount),
      currency: financialGainStatus === "yes" ? currency : undefined,
      gain_period: gainPeriod || undefined,
      is_gain_verified: isGainVerified,
      verified_by_department: verifiedByDepartment || undefined,
      verified_by_department_other_note: verifiedByDepartmentOtherNote || undefined,
      verification_date: verificationDate || undefined,
      verification_note: verificationNote || undefined,
      previous_duration: prevDurationNum ?? undefined,
      new_duration: newDurationNum ?? undefined,
      duration_unit: previousDuration || newDuration ? durationUnit : undefined,
      repeat_period: repeatPeriod || undefined,
      gains,
    };
  }

  async function handleSubmit(status: "draft" | "published") {
    setError(null);
    setFieldErrors({});

    if (dateMode === "range" && workDate && workDateEnd && workDateEnd < workDate) {
      setError("Bitiş tarihi başlangıç tarihinden önce olamaz.");
      return;
    }

    const payload = buildPayload(status);
    try {
      let saved: ContributionWorkItem;
      if (isEdit) {
        saved = await updateMutation.mutateAsync({ id: existing.id, payload });
      } else {
        saved = await createMutation.mutateAsync(payload);
      }
      setDirty(false);
      onClose();
      if (status === "published") {
        navigate(`/improvement-works/${saved.id}`, { state: { justPublished: true } });
      }
    } catch (err: unknown) {
      const axiosErr = err as { response?: { status?: number; data?: { detail?: { message?: string; errors?: Record<string, string> } } } };
      const detail = axiosErr.response?.data?.detail;
      if (axiosErr.response?.status === 422 && detail?.errors) {
        setFieldErrors(detail.errors);
        setError(detail.message ?? "Yayımlamak için zorunlu alanlar eksik.");
      } else {
        setError("Kaydedilemedi. Lütfen tekrar deneyin.");
      }
    }
  }

  const isPending = createMutation.isPending || updateMutation.isPending;
  const basicsHasError = !!(fieldErrors.title || fieldErrors.work_type || fieldErrors.work_type_other_note || fieldErrors.summary);
  const peopleHasError = !!(fieldErrors.foreman_ids || fieldErrors.plant_id || fieldErrors.work_date || fieldErrors.work_date_end);
  const flowHasError = !!(fieldErrors.problem_description || fieldErrors.solution_description);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={handleClose}>
      <div
        className="flex max-h-[92vh] w-full max-w-3xl flex-col overflow-hidden rounded-lg shadow-xl"
        style={{ background: "var(--surface)" }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b px-5 py-4" style={{ borderColor: "var(--border)" }}>
          <h3 className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
            {isEdit ? "Çalışmayı Düzenle" : "Yeni Katkı / İyileştirme Çalışması"}
          </h3>
          <button type="button" onClick={handleClose} style={{ color: "var(--text-muted)" }}>
            <X size={18} strokeWidth={2} />
          </button>
        </div>

        <div className="flex flex-col gap-3 overflow-y-auto px-5 py-4">
          <Section title="1. Kişiler ve Konum" subtitle="İlgili formenler, fabrika/tesis ve çalışma tarihi" hasError={peopleHasError}>
            <div>
              <label className={labelClass} style={labelStyle}>İlgili Formen(ler)</label>
              <ForemanMultiSelect selected={foremen} onChange={markDirty(setForemen)} />
              <FieldError message={fieldErrors.foreman_ids} />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className={labelClass} style={labelStyle}>Fabrika</label>
                <select
                  value={factoryId}
                  onChange={(e) => { markDirty(setFactoryId)(e.target.value); setPlantId(""); }}
                  className={fieldClass} style={fieldStyle}
                >
                  <option value="">Seçiniz</option>
                  {filterOptions.data?.factories.map((f) => <option key={f.id} value={f.id}>{f.code} — {f.name}</option>)}
                </select>
              </div>
              <div>
                <label className={labelClass} style={labelStyle}>Tesis</label>
                <select
                  value={plantId}
                  onChange={(e) => markDirty(setPlantId)(e.target.value)}
                  disabled={!factoryId}
                  className={`${fieldClass} disabled:opacity-50`} style={fieldStyle}
                >
                  <option value="">Seçiniz</option>
                  {plantsForFactory.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
                </select>
                <FieldError message={fieldErrors.plant_id} />
              </div>
            </div>

            <div>
              <label className={labelClass} style={labelStyle}>Kaydı Oluşturan Yönetici</label>
              <input disabled value={user?.full_name ?? ""} className={`${fieldClass} disabled:opacity-70`} style={fieldStyle} />
            </div>

            <div>
              <label className={labelClass} style={labelStyle}>Çalışma Tarihi</label>
              <div className="mb-2 flex gap-3 text-xs" style={{ color: "var(--text-secondary)" }}>
                <label className="flex items-center gap-1.5">
                  <input type="radio" checked={dateMode === "single"} onChange={() => markDirty(setDateMode)("single")} />
                  Tek tarih
                </label>
                <label className="flex items-center gap-1.5">
                  <input type="radio" checked={dateMode === "range"} onChange={() => markDirty(setDateMode)("range")} />
                  Tarih aralığı
                </label>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <input type="date" value={workDate} onChange={(e) => markDirty(setWorkDate)(e.target.value)} className={fieldClass} style={fieldStyle} />
                {dateMode === "range" && (
                  <input type="date" value={workDateEnd} min={workDate || undefined} onChange={(e) => markDirty(setWorkDateEnd)(e.target.value)} className={fieldClass} style={fieldStyle} />
                )}
              </div>
              <FieldError message={fieldErrors.work_date || fieldErrors.work_date_end} />
            </div>
          </Section>

          <Section title="2. Temel Bilgiler" subtitle="Başlık, tür ve açıklamalar" hasError={basicsHasError}>
            <div>
              <label className={labelClass} style={labelStyle}>Çalışma Başlığı</label>
              <input value={title} onChange={(e) => markDirty(setTitle)(e.target.value)} className={fieldClass} style={fieldStyle} />
              <FieldError message={fieldErrors.title} />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className={labelClass} style={labelStyle}>Çalışma Türü</label>
                <select value={workType} onChange={(e) => markDirty(setWorkType)(e.target.value as ContributionWorkType)} className={fieldClass} style={fieldStyle}>
                  <option value="">Seçiniz</option>
                  {WORK_TYPE_OPTIONS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                </select>
                <FieldError message={fieldErrors.work_type} />
              </div>
              <div>
                <label className={labelClass} style={labelStyle}>Etki Seviyesi</label>
                <select value={impactLevel} onChange={(e) => markDirty(setImpactLevel)(e.target.value as ImpactLevel)} className={fieldClass} style={fieldStyle}>
                  {IMPACT_OPTIONS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                </select>
              </div>
            </div>
            {workType === "other" && (
              <div>
                <label className={labelClass} style={labelStyle}>Çalışma Türünü Açıklayın</label>
                <input value={workTypeOtherNote} onChange={(e) => markDirty(setWorkTypeOtherNote)(e.target.value)} className={fieldClass} style={fieldStyle} />
                <FieldError message={fieldErrors.work_type_other_note} />
              </div>
            )}

            <div>
              <label className={labelClass} style={labelStyle}>Kısa Özet</label>
              <textarea value={summary} onChange={(e) => markDirty(setSummary)(e.target.value)} rows={2} maxLength={500} className={fieldClass} style={fieldStyle} />
              <FieldError message={fieldErrors.summary} />
            </div>
            <div>
              <label className={labelClass} style={labelStyle}>Detaylı Açıklama</label>
              <textarea value={detailedDescription} onChange={(e) => markDirty(setDetailedDescription)(e.target.value)} rows={3} className={fieldClass} style={fieldStyle} />
            </div>
          </Section>

          <Section title="3. Problem, Çözüm ve Sonuç" hasError={flowHasError}>
            <div>
              <label className={labelClass} style={labelStyle}>Tespit Edilen Problem</label>
              <textarea value={problemDescription} onChange={(e) => markDirty(setProblemDescription)(e.target.value)} rows={2} className={fieldClass} style={fieldStyle} />
              <FieldError message={fieldErrors.problem_description} />
            </div>
            <div>
              <label className={labelClass} style={labelStyle}>Uygulanan Çözüm</label>
              <textarea value={solutionDescription} onChange={(e) => markDirty(setSolutionDescription)(e.target.value)} rows={2} className={fieldClass} style={fieldStyle} />
              <FieldError message={fieldErrors.solution_description} />
            </div>
            <div>
              <label className={labelClass} style={labelStyle}>Elde Edilen Sonuç</label>
              <textarea value={resultDescription} onChange={(e) => markDirty(setResultDescription)(e.target.value)} rows={2} className={fieldClass} style={fieldStyle} />
            </div>
          </Section>

          <Section title="4. Maddi Kazanç" defaultOpen={false}>
            <div>
              <label className={labelClass} style={labelStyle}>Maddi Kazanç Var mı?</label>
              <select value={financialGainStatus} onChange={(e) => markDirty(setFinancialGainStatus)(e.target.value as FinancialGainStatus)} className={fieldClass} style={fieldStyle}>
                {(Object.entries(FINANCIAL_STATUS_LABELS) as [FinancialGainStatus, string][]).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </select>
            </div>

            {financialGainStatus === "yes" && (
              <>
                <div className="grid grid-cols-3 gap-3">
                  <div>
                    <label className={labelClass} style={labelStyle}>Tahmini Kazanç Tutarı</label>
                    <input type="number" value={estimatedAmount} onChange={(e) => markDirty(setEstimatedAmount)(e.target.value)} className={fieldClass} style={fieldStyle} />
                  </div>
                  <div>
                    <label className={labelClass} style={labelStyle}>Doğrulanmış Kazanç Tutarı</label>
                    <input type="number" value={verifiedAmount} onChange={(e) => markDirty(setVerifiedAmount)(e.target.value)} className={fieldClass} style={fieldStyle} />
                  </div>
                  <div>
                    <label className={labelClass} style={labelStyle}>Para Birimi</label>
                    <select value={currency} onChange={(e) => markDirty(setCurrency)(e.target.value as ContributionCurrency)} className={fieldClass} style={fieldStyle}>
                      <option value="TRY">TRY</option>
                      <option value="USD">USD</option>
                      <option value="EUR">EUR</option>
                    </select>
                  </div>
                </div>
                <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                  Tahmini ve doğrulanmış kazanç ayrı alanlar olarak saklanır; doğrulanmış tutar girilmeden tahmini tutar doğrulanmış gibi gösterilmez.
                </p>

                <div>
                  <label className={labelClass} style={labelStyle}>Kazanç Periyodu</label>
                  <select value={gainPeriod} onChange={(e) => markDirty(setGainPeriod)(e.target.value as GainPeriod)} className={fieldClass} style={fieldStyle}>
                    <option value="">Seçiniz</option>
                    {(Object.entries(GAIN_PERIOD_LABELS) as [GainPeriod, string][]).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                  </select>
                </div>

                <label className="flex items-center gap-2 text-[13px]" style={{ color: "var(--text-primary)" }}>
                  <input type="checkbox" checked={isGainVerified} onChange={(e) => markDirty(setIsGainVerified)(e.target.checked)} />
                  Kazanç doğrulandı mı?
                </label>

                {isGainVerified && (
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className={labelClass} style={labelStyle}>Doğrulayan Birim</label>
                      <select value={verifiedByDepartment} onChange={(e) => markDirty(setVerifiedByDepartment)(e.target.value as VerifyingDepartment)} className={fieldClass} style={fieldStyle}>
                        <option value="">Seçiniz</option>
                        {(Object.entries(DEPARTMENT_LABELS) as [VerifyingDepartment, string][]).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                      </select>
                    </div>
                    <div>
                      <label className={labelClass} style={labelStyle}>Doğrulama Tarihi</label>
                      <input type="date" value={verificationDate} onChange={(e) => markDirty(setVerificationDate)(e.target.value)} className={fieldClass} style={fieldStyle} />
                    </div>
                    {verifiedByDepartment === "other" && (
                      <div className="col-span-2">
                        <label className={labelClass} style={labelStyle}>Birimi Açıklayın</label>
                        <input value={verifiedByDepartmentOtherNote} onChange={(e) => markDirty(setVerifiedByDepartmentOtherNote)(e.target.value)} className={fieldClass} style={fieldStyle} />
                      </div>
                    )}
                    <div className="col-span-2">
                      <label className={labelClass} style={labelStyle}>Doğrulama Notu</label>
                      <textarea value={verificationNote} onChange={(e) => markDirty(setVerificationNote)(e.target.value)} rows={2} className={fieldClass} style={fieldStyle} />
                    </div>
                  </div>
                )}
              </>
            )}
          </Section>

          <Section title="5. Zamandan Kazanç" defaultOpen={false}>
            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className={labelClass} style={labelStyle}>Önceki İşlem Süresi</label>
                <input type="number" value={previousDuration} onChange={(e) => markDirty(setPreviousDuration)(e.target.value)} className={fieldClass} style={fieldStyle} />
              </div>
              <div>
                <label className={labelClass} style={labelStyle}>Yeni İşlem Süresi</label>
                <input type="number" value={newDuration} onChange={(e) => markDirty(setNewDuration)(e.target.value)} className={fieldClass} style={fieldStyle} />
              </div>
              <div>
                <label className={labelClass} style={labelStyle}>Süre Birimi</label>
                <select value={durationUnit} onChange={(e) => markDirty(setDurationUnit)(e.target.value as ContributionTimeUnit)} className={fieldClass} style={fieldStyle}>
                  {(Object.entries(TIME_UNIT_LABELS) as [ContributionTimeUnit, string][]).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                </select>
              </div>
            </div>

            {newDurationInvalid && (
              <p className="flex items-center gap-1.5 text-xs font-medium" style={{ color: "#b45309" }}>
                <TriangleAlert size={13} strokeWidth={2.5} />
                Yeni işlem süresi öncekinden büyük veya eşit olduğu için kazanç hesaplanamıyor.
              </p>
            )}

            <div>
              <label className={labelClass} style={labelStyle}>Tekrar Periyodu</label>
              <select value={repeatPeriod} onChange={(e) => markDirty(setRepeatPeriod)(e.target.value as RepeatPeriod)} className={fieldClass} style={fieldStyle}>
                <option value="">Seçiniz</option>
                {(Object.entries(REPEAT_PERIOD_LABELS) as [RepeatPeriod, string][]).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </select>
            </div>

            {(perOccurrenceSaving != null || monthlyTotal != null) && (
              <div className="rounded-md p-3 text-[13px]" style={{ background: "var(--page-bg)" }}>
                {perOccurrenceSaving != null && <p>İşlem başına kazanç: <strong>{perOccurrenceSaving} {TIME_UNIT_LABELS[durationUnit].toLowerCase()}</strong></p>}
                {monthlyTotal != null && <p>Tahmini aylık toplam zaman kazancı: <strong>{formatMinutes(monthlyTotal)}</strong></p>}
              </div>
            )}
          </Section>

          <Section title="6. Diğer Kazanımlar" defaultOpen={false}>
            {gains.map((gain, i) => {
              const { amount, percent } = computeChange(gain.previous_value ?? null, gain.next_value ?? null);
              return (
                <div key={i} className="rounded-md p-3" style={{ border: "1px solid var(--border)" }}>
                  <div className="mb-2 flex items-center justify-between">
                    <span className="text-xs font-semibold" style={{ color: "var(--text-secondary)" }}>Kazanım {i + 1}</span>
                    <button type="button" onClick={() => removeGain(i)} style={{ color: "var(--text-muted)" }}>
                      <Trash2 size={14} strokeWidth={2} />
                    </button>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className={labelClass} style={labelStyle}>Kazanım Türü</label>
                      <select value={gain.gain_type} onChange={(e) => updateGain(i, { gain_type: e.target.value as OtherGainType })} className={fieldClass} style={fieldStyle}>
                        {(Object.entries(GAIN_TYPE_LABELS) as [OtherGainType, string][]).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                      </select>
                    </div>
                    <div>
                      <label className={labelClass} style={labelStyle}>Ölçüm Birimi</label>
                      <input value={gain.unit ?? ""} onChange={(e) => updateGain(i, { unit: e.target.value })} className={fieldClass} style={fieldStyle} />
                    </div>
                    {gain.gain_type === "other" && (
                      <div className="col-span-2">
                        <label className={labelClass} style={labelStyle}>Türü Açıklayın</label>
                        <input value={gain.gain_type_other_note ?? ""} onChange={(e) => updateGain(i, { gain_type_other_note: e.target.value })} className={fieldClass} style={fieldStyle} />
                      </div>
                    )}
                    <div>
                      <label className={labelClass} style={labelStyle}>Önceki Değer</label>
                      <input type="number" value={gain.previous_value ?? ""} onChange={(e) => updateGain(i, { previous_value: e.target.value === "" ? undefined : Number(e.target.value) })} className={fieldClass} style={fieldStyle} />
                    </div>
                    <div>
                      <label className={labelClass} style={labelStyle}>Sonraki Değer</label>
                      <input type="number" value={gain.next_value ?? ""} onChange={(e) => updateGain(i, { next_value: e.target.value === "" ? undefined : Number(e.target.value) })} className={fieldClass} style={fieldStyle} />
                    </div>
                    <div>
                      <label className={labelClass} style={labelStyle}>Ölçüm Dönemi</label>
                      <input value={gain.measurement_period ?? ""} onChange={(e) => updateGain(i, { measurement_period: e.target.value })} className={fieldClass} style={fieldStyle} />
                    </div>
                    <div className="col-span-2">
                      <label className={labelClass} style={labelStyle}>Açıklama</label>
                      <input value={gain.description ?? ""} onChange={(e) => updateGain(i, { description: e.target.value })} className={fieldClass} style={fieldStyle} />
                    </div>
                  </div>
                  {(amount != null || percent != null) && (
                    <p className="mt-2 text-xs" style={{ color: "var(--text-muted)" }}>
                      Değişim: {amount} {percent != null && `(%${percent})`}
                    </p>
                  )}
                </div>
              );
            })}
            <button
              type="button"
              onClick={addGain}
              className="flex items-center justify-center gap-1.5 rounded-md py-2 text-xs font-medium"
              style={{ border: "1px dashed var(--border-strong)", color: "var(--accent)" }}
            >
              <Plus size={13} strokeWidth={2.5} />
              Kazanım Ekle
            </button>
          </Section>

          <Section title="7. Sınıflandırma" defaultOpen={false}>
            <label className="flex items-center gap-2 text-[13px]" style={{ color: "var(--text-primary)" }}>
              <input type="checkbox" checked={isStandardized} onChange={(e) => markDirty(setIsStandardized)(e.target.checked)} />
              Standartlaştırıldı mı?
            </label>
            <label className="flex items-center gap-2 text-[13px]" style={{ color: "var(--text-primary)" }}>
              <input type="checkbox" checked={isApplicableOtherPlants} onChange={(e) => markDirty(setIsApplicableOtherPlants)(e.target.checked)} />
              Başka tesislerde uygulanabilir mi?
            </label>
            <label className="flex items-center gap-2 text-[13px]" style={{ color: "var(--text-primary)" }}>
              <input type="checkbox" checked={isPermanentSolution} onChange={(e) => markDirty(setIsPermanentSolution)(e.target.checked)} />
              Kalıcı çözüm mü?
            </label>
            <label className="flex items-center gap-2 text-[13px]" style={{ color: "var(--text-primary)" }}>
              <input type="checkbox" checked={workInstructionUpdated} onChange={(e) => markDirty(setWorkInstructionUpdated)(e.target.checked)} />
              İş talimatı güncellendi mi?
            </label>
          </Section>

          {error && <p className="text-xs font-medium" style={{ color: "#b91c1c" }}>{error}</p>}
        </div>

        <div className="flex items-center justify-end gap-2 border-t px-5 py-3" style={{ borderColor: "var(--border)" }}>
          <button
            type="button"
            disabled={isPending || !title}
            onClick={() => handleSubmit("draft")}
            className="rounded-md px-4 py-2 text-[13px] font-medium disabled:opacity-50"
            style={{ border: "1px solid var(--border-strong)", color: "var(--text-secondary)" }}
          >
            {isPending ? "Kaydediliyor..." : "Taslak Olarak Kaydet"}
          </button>
          <button
            type="button"
            disabled={isPending}
            onClick={() => handleSubmit("published")}
            className="rounded-md px-4 py-2 text-[13px] font-medium text-white disabled:opacity-50"
            style={{ background: "var(--accent)" }}
          >
            {isPending ? "Kaydediliyor..." : "Kaydet ve Yayımla"}
          </button>
        </div>
      </div>
    </div>
  );
}
