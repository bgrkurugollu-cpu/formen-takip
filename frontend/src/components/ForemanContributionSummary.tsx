import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowRight, ChevronDown } from "lucide-react";
import { useForemanContributionSummary, useForemanRecentContributions } from "../api/hooks";
import { LoadingState } from "./StateViews";
import { STATUS_LABELS, workTypeLabel } from "../lib/contributionTheme";
import type { ContributionWorkItem } from "../api/types";

const dateFormatter = new Intl.DateTimeFormat("tr-TR", { day: "numeric", month: "long", year: "numeric" });
const shortDateFormatter = new Intl.DateTimeFormat("tr-TR", { day: "numeric", month: "short", year: "numeric" });
const numberFormatter = new Intl.NumberFormat("tr-TR", { maximumFractionDigits: 0 });

function formatMoneyShort(amount: number, currency: string): string {
  return `${numberFormatter.format(amount)} ${currency}`;
}

function formatHours(minutes: number): string {
  if (minutes <= 0) return "0 saat";
  const hours = minutes / 60;
  if (hours < 1) return `${numberFormatter.format(minutes)} dk`;
  return `${numberFormatter.format(Math.round(hours))} saat`;
}

function financialGainText(work: ContributionWorkItem): string | null {
  if (work.verified_amount != null) return `${formatMoneyShort(work.verified_amount, work.currency ?? "")} kazanç`;
  if (work.estimated_amount != null) return `${formatMoneyShort(work.estimated_amount, work.currency ?? "")} tahmini kazanç`;
  return null;
}

function timeSavingText(work: ContributionWorkItem): string | null {
  if (work.monthly_total_saving_minutes == null) return null;
  return `Aylık ${formatHours(work.monthly_total_saving_minutes)} tasarruf`;
}

function ContributionRow({ work, foremanId, onNavigate }: { work: ContributionWorkItem; foremanId: string; onNavigate: (id: string) => void }) {
  const me = work.foremen.find((f) => f.id === foremanId);
  const isShared = work.foremen.length > 1;
  const roleLabel = me?.role === "lead" ? "Çalışma Lideri" : "Katılımcı";
  const financialText = financialGainText(work);
  const timeText = timeSavingText(work);
  const shareAmount = work.verified_amount ?? work.estimated_amount;

  return (
    <div className="rounded-md p-3" style={{ border: "1px solid var(--border)" }}>
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="truncate text-[13px] font-semibold" style={{ color: "var(--text-primary)" }}>{work.title}</p>
          <p className="mt-0.5 text-xs" style={{ color: "var(--text-muted)" }}>
            {workTypeLabel(work.work_type)} · {roleLabel} · {work.work_date ? dateFormatter.format(new Date(work.work_date)) : "Tarih belirtilmedi"}
          </p>
        </div>
        <span
          className="shrink-0 rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide"
          style={
            work.status === "published"
              ? { background: "rgba(21,128,61,0.1)", color: "#15803d" }
              : { background: "var(--page-bg)", color: "var(--text-muted)", border: "1px solid var(--border-strong)" }
          }
        >
          {STATUS_LABELS[work.status]}
        </span>
      </div>

      {(financialText || timeText) && (
        <p className="mt-1.5 text-xs font-medium" style={{ color: "var(--text-secondary)" }}>
          {[financialText, timeText].filter(Boolean).join(" · ")}
        </p>
      )}
      {isShared && shareAmount != null && (
        <p className="mt-0.5 text-[11px]" style={{ color: "var(--text-muted)" }}>
          Dahil olduğu çalışmanın toplam etkisi — formene atfedilen katkı: {formatMoneyShort(shareAmount / work.foremen.length, work.currency ?? "")}
        </p>
      )}

      <button
        type="button"
        onClick={() => onNavigate(work.id)}
        className="mt-2 text-xs font-medium hover:underline"
        style={{ color: "var(--accent)" }}
      >
        Detayı Görüntüle
      </button>
    </div>
  );
}

export function ForemanContributionSummary({ foremanId }: { foremanId: string }) {
  const [expanded, setExpanded] = useState(false);
  const summary = useForemanContributionSummary(foremanId);
  const recent = useForemanRecentContributions(foremanId, expanded);
  const navigate = useNavigate();

  if (summary.isLoading) {
    return (
      <div className="rounded-lg px-4 py-3" style={{ background: "var(--surface)", border: "1px solid var(--border)" }}>
        <LoadingState label="Katkı özeti yükleniyor..." />
      </div>
    );
  }
  if (summary.isError || !summary.data) return null;

  const s = summary.data;

  if (s.total_contributions === 0) {
    return (
      <div className="rounded-lg px-4 py-3" style={{ background: "var(--surface)", border: "1px solid var(--border)" }}>
        <p className="text-[13px] font-semibold" style={{ color: "var(--text-primary)" }}>Katkı ve İyileştirme Çalışmaları</p>
        <p className="mt-0.5 text-xs" style={{ color: "var(--text-muted)" }}>
          Bu formen için henüz onaylanmış bir katkı çalışması bulunmuyor.
        </p>
      </div>
    );
  }

  const verifiedEntries = Object.entries(s.verified_financial_gain);
  const estimatedEntries = Object.entries(s.estimated_financial_gain);

  const chips: string[] = [`${s.total_contributions} çalışma`];
  if (s.smed_count > 0) chips.push(`${s.smed_count} SMED`);
  if (verifiedEntries.length > 0) {
    chips.push(`${verifiedEntries.map(([cur, amt]) => formatMoneyShort(amt, cur)).join(", ")} doğrulanmış kazanç`);
  } else if (estimatedEntries.length > 0) {
    chips.push(`${estimatedEntries.map(([cur, amt]) => formatMoneyShort(amt, cur)).join(", ")} tahmini kazanç`);
  }
  if (s.total_time_saving_minutes > 0) chips.push(`${formatHours(s.total_time_saving_minutes)} tasarruf`);
  if (s.last_contribution_date) chips.push(`Son: ${shortDateFormatter.format(new Date(s.last_contribution_date))}`);

  return (
    <div className="rounded-lg" style={{ background: "var(--surface)", border: "1px solid var(--border)" }}>
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left"
      >
        <div className="flex min-w-0 flex-wrap items-baseline gap-x-2 gap-y-1">
          <span className="text-[13px] font-semibold" style={{ color: "var(--text-primary)" }}>
            Katkı ve İyileştirme Çalışmaları
          </span>
          <span className="text-xs" style={{ color: "var(--text-muted)" }}>{chips.join(" · ")}</span>
        </div>
        <span className="flex shrink-0 items-center gap-1 text-xs font-medium" style={{ color: "var(--accent)" }}>
          Detayları Görüntüle
          <ChevronDown
            size={14}
            strokeWidth={2}
            style={{ transition: "transform 200ms ease", transform: expanded ? "rotate(180deg)" : "rotate(0deg)" }}
          />
        </span>
      </button>

      <div style={{ display: "grid", gridTemplateRows: expanded ? "1fr" : "0fr", transition: "grid-template-rows 200ms ease" }}>
        <div className="overflow-hidden">
          <div className="flex flex-col gap-3 px-4 pb-4 pt-1" style={{ borderTop: "1px solid var(--border)" }}>
            {(verifiedEntries.length > 0 || estimatedEntries.length > 0) && (
              <div className="mt-2 flex flex-wrap items-baseline gap-x-3 gap-y-0.5">
                {verifiedEntries.length > 0 && (
                  <span className="text-base font-semibold" style={{ color: "var(--text-primary)" }}>
                    {verifiedEntries.map(([cur, amt]) => formatMoneyShort(amt, cur)).join(", ")} doğrulanmış
                  </span>
                )}
                {estimatedEntries.length > 0 && (
                  <span className="text-xs font-medium" style={{ color: "var(--text-muted)" }}>
                    +{estimatedEntries.map(([cur, amt]) => formatMoneyShort(amt, cur)).join(", ")} tahmini
                  </span>
                )}
              </div>
            )}
            {s.led_contributions > 0 && (
              <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                {s.led_contributions} çalışmada liderlik rolü üstlendi.
              </p>
            )}

            {recent.isLoading && <LoadingState label="Son katkılar yükleniyor..." />}
            {recent.data && (
              <div className="flex flex-col gap-2">
                {recent.data.items.map((work) => (
                  <ContributionRow key={work.id} work={work} foremanId={foremanId} onNavigate={(id) => navigate(`/improvement-works/${id}`)} />
                ))}
              </div>
            )}

            {s.total_contributions > 3 && (
              <button
                type="button"
                onClick={() => navigate(`/improvement-works?foreman_ids=${foremanId}`)}
                className="inline-flex w-fit items-center gap-1 text-xs font-medium hover:underline"
                style={{ color: "var(--accent)" }}
              >
                Tüm Katkıları Görüntüle ({s.total_contributions})
                <ArrowRight size={13} strokeWidth={2} />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
