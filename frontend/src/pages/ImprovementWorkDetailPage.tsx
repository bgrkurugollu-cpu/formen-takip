import { useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import { CalendarDays, CheckCircle2, ChevronLeft, Download, Factory, Pencil, Trash2 } from "lucide-react";
import { apiClient } from "../api/client";
import { useContributionWork, useDeleteContributionWork } from "../api/hooks";
import { Card, ErrorState, LoadingState } from "../components/StateViews";
import { BeforeAfterComparison } from "../components/BeforeAfterComparison";
import { ProblemSolutionResultFlow } from "../components/ProblemSolutionResultFlow";
import { ContributionWorkForm } from "../components/ContributionWorkForm";
import { useTheme } from "../context/ThemeContext";
import { STATUS_LABELS, workTypeColor, workTypeIcon, workTypeLabel } from "../lib/contributionTheme";
import { formatMoney } from "../lib/contributionCalc";

function initials(name: string): string {
  return name.split(" ").filter(Boolean).slice(0, 2).map((p) => p[0]?.toUpperCase()).join("");
}

function GainCard({ label, value, sub, verified }: { label: string; value: string; sub?: string; verified?: "verified" | "estimated" }) {
  return (
    <div className="rounded-lg p-4" style={{ background: "var(--surface)", border: "1px solid var(--border)" }}>
      <div className="flex items-center justify-between">
        <span className="text-[11px] font-semibold uppercase tracking-wide" style={{ color: "var(--text-muted)" }}>{label}</span>
        {verified === "verified" && (
          <span className="rounded-full px-1.5 py-0.5 text-[10px] font-medium" style={{ background: "rgba(21,128,61,0.1)", color: "#15803d" }}>Doğrulanmış</span>
        )}
        {verified === "estimated" && (
          <span className="rounded-full px-1.5 py-0.5 text-[10px] font-medium" style={{ background: "var(--page-bg)", color: "var(--text-muted)" }}>Tahmini</span>
        )}
      </div>
      <div className="mt-1.5 text-xl font-semibold" style={{ color: "var(--text-primary)" }}>{value}</div>
      {sub && <div className="mt-1 text-xs" style={{ color: "var(--text-muted)" }}>{sub}</div>}
    </div>
  );
}

export function ImprovementWorkDetailPage() {
  const { workId } = useParams<{ workId: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const { theme } = useTheme();
  const isDark = theme === "dark";
  const [editing, setEditing] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const justPublished = (location.state as { justPublished?: boolean } | null)?.justPublished;

  const work = useContributionWork(workId);
  const deleteWork = useDeleteContributionWork();

  if (work.isLoading) return <LoadingState />;
  if (work.isError || !work.data) return <ErrorState message="Çalışma bulunamadı." />;

  const w = work.data;
  const Icon = workTypeIcon(w.work_type);
  const accent = workTypeColor(w.work_type, isDark);

  const handleDelete = () => {
    if (!window.confirm(`"${w.title}" çalışmasını kaldırmak istediğinize emin misiniz?`)) return;
    deleteWork.mutate(w.id, { onSuccess: () => navigate("/improvement-works") });
  };

  const handleDownloadPdf = async () => {
    setDownloading(true);
    try {
      const resp = await apiClient.get(`/contribution-works/${w.id}/pdf`, { responseType: "blob" });
      const url = window.URL.createObjectURL(new Blob([resp.data], { type: "application/pdf" }));
      const a = document.createElement("a");
      a.href = url;
      a.download = `${w.title}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="flex flex-col gap-4">
      <button
        onClick={() => navigate("/improvement-works")}
        className="flex w-fit items-center gap-1 text-xs font-medium hover:underline"
        style={{ color: "var(--accent)" }}
      >
        <ChevronLeft size={13} strokeWidth={2} />
        Katkı ve İyileştirme Çalışmaları
      </button>

      {justPublished && (
        <div className="flex items-center gap-2 rounded-lg p-3 text-[13px] font-medium" style={{ background: "rgba(21,128,61,0.1)", color: "#15803d" }}>
          <CheckCircle2 size={16} strokeWidth={2} />
          Çalışma başarıyla yayımlandı.
        </div>
      )}

      <div className="rounded-lg p-6" style={{ background: "var(--surface)", border: "1px solid var(--border)", borderTop: `3px solid ${accent}` }}>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 rounded px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide" style={{ backgroundColor: `${accent}14`, color: accent, border: `1px solid ${accent}33` }}>
              <Icon size={12} strokeWidth={2.25} />
              {workTypeLabel(w.work_type)}
            </span>
            <span
              className="rounded px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide"
              style={w.status === "published" ? { background: "rgba(21,128,61,0.1)", color: "#15803d" } : { background: "var(--page-bg)", color: "var(--text-muted)", border: "1px solid var(--border-strong)" }}
            >
              {STATUS_LABELS[w.status]}
            </span>
          </div>
          <div className="flex gap-2">
            <button
              onClick={handleDownloadPdf}
              disabled={downloading}
              className="flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium disabled:opacity-50"
              style={{ border: "1px solid var(--border-strong)", color: "var(--text-secondary)" }}
            >
              <Download size={13} strokeWidth={2} />
              {downloading ? "İndiriliyor..." : "PDF olarak indir"}
            </button>
            <button
              onClick={() => setEditing(true)}
              className="flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium text-white"
              style={{ background: "var(--accent)" }}
            >
              <Pencil size={13} strokeWidth={2} />
              Düzenle
            </button>
            <button
              onClick={handleDelete}
              disabled={deleteWork.isPending}
              className="flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium disabled:opacity-50"
              style={{ border: "1px solid var(--border-strong)", color: "var(--text-secondary)" }}
            >
              <Trash2 size={13} strokeWidth={2} />
              Kaldır
            </button>
          </div>
        </div>

        <h1 className="mt-3 text-2xl font-bold leading-tight" style={{ color: "var(--text-primary)" }}>{w.title}</h1>
        {w.summary && <p className="mt-2 max-w-3xl text-[14px]" style={{ color: "var(--text-secondary)" }}>{w.summary}</p>}

        <div className="mt-4 flex flex-wrap items-center gap-x-5 gap-y-2 text-[13px]" style={{ color: "var(--text-muted)" }}>
          {w.plant && (
            <span className="flex items-center gap-1.5">
              <Factory size={14} strokeWidth={2} />
              {w.plant.factory_code} · {w.plant.name}
            </span>
          )}
          {w.work_date && (
            <span className="flex items-center gap-1.5">
              <CalendarDays size={14} strokeWidth={2} />
              {w.work_date}{w.work_date_end ? ` — ${w.work_date_end}` : ""}
            </span>
          )}
          <span>Kaydeden: {w.created_by ?? "-"}</span>
        </div>

        {w.foremen.length > 0 && (
          <div className="mt-4 flex flex-wrap items-center gap-2">
            {w.foremen.map((f) => (
              <span key={f.id} className="flex items-center gap-1.5 rounded-full py-1 pl-1 pr-3 text-xs font-medium" style={{ background: "var(--page-bg)", border: "1px solid var(--border)", color: "var(--text-primary)" }}>
                <span className="flex h-5 w-5 items-center justify-center rounded-full text-[9px] font-semibold" style={{ background: "var(--accent-subtle)", color: "var(--accent)" }}>
                  {initials(f.name)}
                </span>
                {f.name}
              </span>
            ))}
          </div>
        )}

        {w.badges.length > 0 && (
          <div className="mt-4 flex flex-wrap gap-1.5">
            {w.badges.map((b) => (
              <span key={b} className="rounded-full px-2.5 py-1 text-xs font-medium" style={{ background: "var(--page-bg)", color: "var(--text-secondary)", border: "1px solid var(--border)" }}>{b}</span>
            ))}
          </div>
        )}

        {(w.highlighted_gain || w.before_after) && (
          <div className="mt-5 grid grid-cols-1 gap-4 md:grid-cols-2">
            {w.highlighted_gain && (
              <div className="rounded-lg p-4" style={{ background: `${accent}0d`, border: `1px solid ${accent}33` }}>
                <div className="text-xs font-semibold uppercase tracking-wide" style={{ color: "var(--text-muted)" }}>Öne Çıkan Kazanım</div>
                <div className="mt-1 text-3xl font-bold" style={{ color: accent }}>
                  {new Intl.NumberFormat("tr-TR", { maximumFractionDigits: 2 }).format(w.highlighted_gain.value)}
                  {w.highlighted_gain.unit && <span className="ml-1.5 text-lg font-medium">{w.highlighted_gain.unit}</span>}
                </div>
                <div className="mt-0.5 text-[13px]" style={{ color: "var(--text-secondary)" }}>{w.highlighted_gain.label}</div>
              </div>
            )}
            {w.before_after && (
              <div className="rounded-lg p-4" style={{ border: "1px solid var(--border)" }}>
                <BeforeAfterComparison data={w.before_after} />
              </div>
            )}
          </div>
        )}
      </div>

      <ProblemSolutionResultFlow problem={w.problem_description} solution={w.solution_description} result={w.result_description} />

      {w.detailed_description && (
        <Card title="Detaylı Açıklama">
          <p className="text-[13px] leading-relaxed" style={{ color: "var(--text-secondary)" }}>{w.detailed_description}</p>
        </Card>
      )}

      {(w.financial_gain_status === "yes" || w.monthly_total_saving_minutes != null || w.gains.length > 0) && (
        <div>
          <h2 className="mb-2 text-sm font-semibold" style={{ color: "var(--text-primary)" }}>Ölçülebilir Kazanımlar</h2>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {w.estimated_amount != null && (
              <GainCard label="Tahmini Maddi Kazanç" value={formatMoney(w.estimated_amount, w.currency)} sub={w.gain_period ?? undefined} verified="estimated" />
            )}
            {w.verified_amount != null && (
              <GainCard label="Doğrulanmış Maddi Kazanç" value={formatMoney(w.verified_amount, w.currency)} sub={w.verified_by_department ?? undefined} verified="verified" />
            )}
            {w.per_occurrence_saving != null && (
              <GainCard label="İşlem Başına Zaman Kazancı" value={`${w.per_occurrence_saving} ${w.duration_unit === "hour" ? "saat" : w.duration_unit === "second" ? "saniye" : "dakika"}`} />
            )}
            {w.monthly_total_saving_minutes != null && (
              <GainCard label="Aylık Toplam Zaman Kazancı" value={`${w.monthly_total_saving_minutes} dakika`} />
            )}
            {w.gains.map((g) => (
              <GainCard
                key={g.id}
                label={g.gain_type_label}
                value={g.change_percent != null ? `%${Math.abs(g.change_percent)}` : g.change_amount != null ? `${g.change_amount}` : "-"}
                sub={g.previous_value != null && g.next_value != null ? `${g.previous_value} → ${g.next_value} ${g.unit ?? ""}` : undefined}
              />
            ))}
          </div>
        </div>
      )}

      {editing && <ContributionWorkForm existing={w} onClose={() => setEditing(false)} />}
    </div>
  );
}
