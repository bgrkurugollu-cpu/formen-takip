import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { AlertTriangle, ArrowDown, ArrowUp, ArrowUpDown } from "lucide-react";
import { FilterBar } from "../components/FilterBar";
import { Card, EmptyState, ErrorState, LoadingState } from "../components/StateViews";
import { PerformanceLevelBadge } from "../components/PerformanceLevelBadge";
import { Pagination } from "../components/Pagination";
import { useForemen } from "../api/hooks";
import { useFilters } from "../hooks/useFilters";
import { rowHoverClass, rowStyle, searchInputClass, searchInputStyle, tdClass, thClass, theadRowStyle, thStyle } from "../lib/tableStyles";

type SortField = "name" | "employee_number" | "plant" | "chief" | "shift" | "score" | "level" | "reliability";

const DESC_FIRST: ReadonlySet<SortField> = new Set(["score", "level", "reliability"]);

const COLUMNS: { field: SortField; label: string }[] = [
  { field: "name", label: "Formen" },
  { field: "employee_number", label: "Sicil No" },
  { field: "plant", label: "Tesis" },
  { field: "chief", label: "Şef" },
  { field: "shift", label: "Vardiya" },
  { field: "score", label: "Toplam Puan" },
  { field: "level", label: "Seviye" },
  { field: "reliability", label: "Veri Güvenilirliği" },
];

export function ForemenPage() {
  const { filters, setFilters, clearFilters, asQueryParams } = useFilters();
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [sortBy, setSortBy] = useState<SortField>("name");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");
  const pageSize = 20;
  const navigate = useNavigate();

  function handleSort(field: SortField) {
    if (sortBy === field) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortBy(field);
      setSortDir(DESC_FIRST.has(field) ? "desc" : "asc");
    }
    setPage(1);
  }

  const params = {
    ...asQueryParams,
    search: search || undefined,
    plant_id: filters.plantIds[0],
    chief_id: filters.chiefIds[0],
    shift_id: filters.shiftIds[0],
    sort_by: sortBy,
    sort_dir: sortDir,
    page,
    page_size: pageSize,
  };
  const foremen = useForemen(params);

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-lg font-semibold" style={{ color: "var(--text-primary)" }}>Formenler</h1>
        <p className="text-[13px]" style={{ color: "var(--text-muted)" }}>Şirket genelindeki tüm formenlerin performans listesi.</p>
      </div>

      <FilterBar filters={filters} setFilters={setFilters} clearFilters={clearFilters} />

      <input
        type="search"
        placeholder="Ad, soyad veya sicil no ara..."
        value={search}
        onChange={(e) => {
          setSearch(e.target.value);
          setPage(1);
        }}
        className={searchInputClass}
        style={searchInputStyle}
      />

      <Card>
        {foremen.isLoading && <LoadingState />}
        {foremen.isError && <ErrorState />}
        {foremen.data && foremen.data.items.length === 0 && <EmptyState />}
        {foremen.data && foremen.data.items.length > 0 && (
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
                          onClick={() => handleSort(col.field)}
                          className="flex items-center gap-1 uppercase tracking-wide hover:text-[var(--text-primary)]"
                          style={{ color: active ? "var(--accent)" : "inherit" }}
                        >
                          {col.label}
                          <Icon size={12} strokeWidth={2} className={active ? "" : "opacity-40"} />
                        </button>
                      </th>
                    );
                  })}
                </tr>
              </thead>
              <tbody>
                {foremen.data.items.map((f) => (
                  <tr
                    key={f.id}
                    onClick={() => navigate(`/foremen/${f.id}`)}
                    className={`cursor-pointer ${rowHoverClass}`}
                    style={rowStyle}
                  >
                    <td className={`${tdClass} font-medium`} style={{ color: "var(--text-primary)" }}>{f.full_name}</td>
                    <td className={tdClass} style={{ color: "var(--text-muted)" }}>{f.employee_number}</td>
                    <td className={tdClass} style={{ color: "var(--text-secondary)" }}>{f.plant?.name ?? "-"}</td>
                    <td className={tdClass} style={{ color: "var(--text-secondary)" }}>{f.chief?.name ?? "-"}</td>
                    <td className={tdClass} style={{ color: "var(--text-secondary)" }}>{f.shift?.name ?? "-"}</td>
                    <td className={`${tdClass} font-medium tabular-nums`} style={{ color: "var(--text-primary)" }}>{f.total_score.toFixed(1)}</td>
                    <td className={tdClass}>
                      <PerformanceLevelBadge level={f.level} />
                    </td>
                    <td className={tdClass}>
                      {f.is_reliable ? (
                        <span className="text-xs" style={{ color: "var(--text-muted)" }}>Tam</span>
                      ) : (
                        <span className="flex items-center gap-1 text-xs font-medium text-amber-600">
                          <AlertTriangle size={12} strokeWidth={2} />
                          Eksik veri
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            <Pagination page={page} pageSize={pageSize} total={foremen.data.total} onPageChange={setPage} itemLabel="formen" />
          </div>
        )}
      </Card>
    </div>
  );
}
