import { useState } from "react";
import { AlertTriangle, Circle, Star, ThumbsUp, TrendingDown, Trophy, X } from "lucide-react";
import type { DistributionItem } from "../api/types";
import { useForemen } from "../api/hooks";
import { LoadingState, ErrorState, EmptyState } from "./StateViews";
import { Pagination } from "./Pagination";
import { thClass, thStyle, theadRowStyle, tdClass, rowStyle, rowHoverClass } from "../lib/tableStyles";

const ICONS: Record<string, typeof Trophy> = {
  trophy: Trophy,
  star: Star,
  "thumbs-up": ThumbsUp,
  "trending-down": TrendingDown,
  "alert-triangle": AlertTriangle,
};

type Params = Record<string, string | number | undefined>;

export function PerformanceLevelDetailModal({
  level,
  filterParams,
  onClose,
  onNavigateForeman,
}: {
  level: DistributionItem;
  filterParams: Params;
  onClose: () => void;
  onNavigateForeman: (id: string) => void;
}) {
  const [page, setPage] = useState(1);
  const pageSize = 20;
  const Icon = ICONS[level.icon] ?? Circle;

  const foremen = useForemen({
    ...filterParams,
    level: level.name,
    sort_by: "score",
    sort_dir: "desc",
    page,
    page_size: pageSize,
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={onClose}>
      <div
        onClick={(e) => e.stopPropagation()}
        className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-lg p-5 shadow-xl"
        style={{ background: "var(--surface)" }}
      >
        <div className="mb-4 flex items-start justify-between gap-3">
          <div className="flex items-center gap-2">
            <span
              className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full"
              style={{ backgroundColor: `${level.color}14`, color: level.color, border: `1px solid ${level.color}33` }}
            >
              <Icon size={15} strokeWidth={2} />
            </span>
            <div>
              <h3 className="text-[15px] font-semibold leading-snug" style={{ color: "var(--text-primary)" }}>
                {level.name} Seviyesindeki Formenler
              </h3>
              <p className="text-xs" style={{ color: "var(--text-muted)" }}>{level.description}</p>
            </div>
          </div>
          <button type="button" onClick={onClose} style={{ color: "var(--text-muted)" }}>
            <X size={18} strokeWidth={2} />
          </button>
        </div>

        {foremen.isLoading && <LoadingState />}
        {foremen.isError && <ErrorState />}
        {foremen.data && foremen.data.items.length === 0 && <EmptyState />}
        {foremen.data && foremen.data.items.length > 0 && (
          <div className="overflow-x-auto rounded-md" style={{ border: "1px solid var(--border)" }}>
            <table className="w-full text-left text-[13px]">
              <thead>
                <tr style={theadRowStyle}>
                  <th className={thClass} style={thStyle}>Formen</th>
                  <th className={thClass} style={thStyle}>Sicil No</th>
                  <th className={thClass} style={thStyle}>Tesis</th>
                  <th className={thClass} style={thStyle}>Puan</th>
                </tr>
              </thead>
              <tbody>
                {foremen.data.items.map((f) => (
                  <tr
                    key={f.id}
                    onClick={() => onNavigateForeman(f.id)}
                    className={`cursor-pointer ${rowHoverClass}`}
                    style={rowStyle}
                  >
                    <td className={`${tdClass} font-medium`} style={{ color: "var(--text-primary)" }}>{f.full_name}</td>
                    <td className={tdClass} style={{ color: "var(--text-muted)" }}>{f.employee_number}</td>
                    <td className={tdClass} style={{ color: "var(--text-secondary)" }}>
                      {f.assignments.length ? f.assignments.map((a) => a.plant.name).join(", ") : "-"}
                    </td>
                    <td className={`${tdClass} font-medium tabular-nums`} style={{ color: level.color }}>
                      {f.total_score.toFixed(1)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            <div className="px-1 pb-1">
              <Pagination page={page} pageSize={pageSize} total={foremen.data.total} onPageChange={setPage} itemLabel="formen" />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
