import { TrendingDown, TrendingUp } from "lucide-react";
import type { ContributionBeforeAfter } from "../api/types";

export function BeforeAfterComparison({ data, compact = false }: { data: ContributionBeforeAfter; compact?: boolean }) {
  const Icon = data.is_improvement ? TrendingDown : TrendingUp;

  return (
    <div>
      {!compact && (
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide" style={{ color: "var(--text-muted)" }}>
          {data.metric_label}
        </p>
      )}
      <div className="grid grid-cols-3 gap-2">
        <div className="rounded-md p-2.5 text-center" style={{ background: "var(--page-bg)", border: "1px solid var(--border)" }}>
          <div className="text-[10px] font-medium uppercase tracking-wide" style={{ color: "var(--text-muted)" }}>Önce</div>
          <div className={compact ? "mt-0.5 text-sm font-semibold" : "mt-1 text-base font-semibold"} style={{ color: "var(--text-secondary)" }}>
            {data.before}
          </div>
        </div>
        <div className="rounded-md p-2.5 text-center" style={{ background: "var(--page-bg)", border: "1px solid var(--border)" }}>
          <div className="text-[10px] font-medium uppercase tracking-wide" style={{ color: "var(--text-muted)" }}>Sonra</div>
          <div className={compact ? "mt-0.5 text-sm font-semibold" : "mt-1 text-base font-semibold"} style={{ color: "var(--text-primary)" }}>
            {data.after}
          </div>
        </div>
        <div
          className="rounded-md p-2.5 text-center"
          style={{ background: "var(--accent-subtle)", border: "1px solid var(--accent)" }}
        >
          <div className="text-[10px] font-medium uppercase tracking-wide" style={{ color: "var(--accent)" }}>İyileşme</div>
          <div
            className={`mt-0.5 flex items-center justify-center gap-1 font-semibold ${compact ? "text-sm" : "text-base"}`}
            style={{ color: "var(--accent)" }}
          >
            <Icon size={compact ? 12 : 14} strokeWidth={2.25} />
            {data.change}
          </div>
        </div>
      </div>
    </div>
  );
}
