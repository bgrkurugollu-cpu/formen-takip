import { ChevronLeft, ChevronRight } from "lucide-react";

interface Props {
  page: number;
  pageSize: number;
  total: number;
  onPageChange: (page: number) => void;
  itemLabel?: string;
}

export function Pagination({ page, pageSize, total, onPageChange, itemLabel = "kayıt" }: Props) {
  return (
    <div className="mt-3 flex items-center justify-between text-xs" style={{ color: "var(--text-muted)" }}>
      <span>Toplam {total} {itemLabel} — sayfa {page}</span>
      <div className="flex gap-2">
        <button
          disabled={page <= 1}
          onClick={() => onPageChange(page - 1)}
          className="flex items-center gap-1 rounded-md px-2 py-1 disabled:opacity-40"
          style={{ border: "1px solid var(--border-strong)" }}
        >
          <ChevronLeft size={13} strokeWidth={2} />
          Önceki
        </button>
        <button
          disabled={page * pageSize >= total}
          onClick={() => onPageChange(page + 1)}
          className="flex items-center gap-1 rounded-md px-2 py-1 disabled:opacity-40"
          style={{ border: "1px solid var(--border-strong)" }}
        >
          Sonraki
          <ChevronRight size={13} strokeWidth={2} />
        </button>
      </div>
    </div>
  );
}
