import { useNavigate } from "react-router-dom";
import { ArrowDown, ArrowUp, ArrowUpDown, Trash2 } from "lucide-react";
import type { ContributionWorkItem } from "../api/types";
import { useDeleteContributionWork } from "../api/hooks";
import { STATUS_LABELS, workTypeLabel } from "../lib/contributionTheme";
import { rowHoverClass, rowStyle, tdClass, thClass, theadRowStyle, thStyle } from "../lib/tableStyles";

export type ContributionSortField = "title" | "type" | "foreman" | "plant" | "date" | "gain" | "status";

const COLUMNS: { field: ContributionSortField; label: string }[] = [
  { field: "title", label: "Başlık" },
  { field: "type", label: "Tür" },
  { field: "foreman", label: "Formenler" },
  { field: "plant", label: "Fabrika / Tesis" },
  { field: "date", label: "Tarih" },
  { field: "gain", label: "Öne Çıkan Kazanım" },
  { field: "status", label: "Durum" },
];

interface Props {
  items: ContributionWorkItem[];
  sortBy: ContributionSortField;
  sortDir: "asc" | "desc";
  onSort: (field: ContributionSortField) => void;
}

export function ContributionWorkTable({ items, sortBy, sortDir, onSort }: Props) {
  const navigate = useNavigate();
  const deleteWork = useDeleteContributionWork();

  const handleDelete = (work: ContributionWorkItem) => {
    if (!window.confirm(`"${work.title}" çalışmasını kaldırmak istediğinize emin misiniz?`)) return;
    deleteWork.mutate(work.id);
  };

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-[13px]">
        <thead>
          <tr style={theadRowStyle}>
            {COLUMNS.map((col) => {
              const active = sortBy === col.field;
              const Icon = active ? (sortDir === "asc" ? ArrowUp : ArrowDown) : ArrowUpDown;
              return (
                <th key={col.field} className={thClass} style={thStyle}>
                  <button
                    type="button"
                    onClick={() => onSort(col.field)}
                    className="flex items-center gap-1 uppercase tracking-wide hover:text-[var(--text-primary)]"
                    style={{ color: active ? "var(--accent)" : "inherit" }}
                  >
                    {col.label}
                    <Icon size={12} strokeWidth={2} className={active ? "" : "opacity-40"} />
                  </button>
                </th>
              );
            })}
            <th className={thClass} style={thStyle}></th>
          </tr>
        </thead>
        <tbody>
          {items.map((w) => (
            <tr
              key={w.id}
              onClick={() => navigate(`/improvement-works/${w.id}`)}
              className={`cursor-pointer ${rowHoverClass}`}
              style={rowStyle}
            >
              <td className={`${tdClass} font-medium`} style={{ color: "var(--text-primary)" }}>{w.title}</td>
              <td className={tdClass} style={{ color: "var(--text-secondary)" }}>{workTypeLabel(w.work_type)}</td>
              <td className={tdClass} style={{ color: "var(--text-secondary)" }}>
                {w.foremen.map((f) => f.name).join(", ") || "-"}
              </td>
              <td className={tdClass} style={{ color: "var(--text-secondary)" }}>
                {w.plant ? `${w.plant.factory_code} · ${w.plant.name}` : "-"}
              </td>
              <td className={tdClass} style={{ color: "var(--text-muted)" }}>{w.work_date ?? "-"}</td>
              <td className={tdClass} style={{ color: "var(--text-secondary)" }}>
                {w.highlighted_gain
                  ? `${new Intl.NumberFormat("tr-TR", { maximumFractionDigits: 2 }).format(w.highlighted_gain.value)}${w.highlighted_gain.unit ? " " + w.highlighted_gain.unit : ""}`
                  : "-"}
              </td>
              <td className={tdClass}>
                <span
                  className="rounded px-2 py-0.5 text-xs font-medium"
                  style={
                    w.status === "published"
                      ? { background: "rgba(21,128,61,0.1)", color: "#15803d" }
                      : { background: "var(--page-bg)", color: "var(--text-muted)", border: "1px solid var(--border-strong)" }
                  }
                >
                  {STATUS_LABELS[w.status]}
                </span>
              </td>
              <td className={tdClass}>
                <button
                  type="button"
                  onClick={(e) => { e.stopPropagation(); handleDelete(w); }}
                  disabled={deleteWork.isPending}
                  className="flex items-center gap-1 text-xs font-medium disabled:opacity-50"
                  style={{ color: "var(--text-muted)" }}
                >
                  <Trash2 size={12} strokeWidth={2.25} />
                  Kaldır
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
