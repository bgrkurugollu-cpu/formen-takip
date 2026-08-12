import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowDown, ArrowUp, ArrowUpDown } from "lucide-react";
import { FilterBar } from "../components/FilterBar";
import { Card, EmptyState, ErrorState, LoadingState } from "../components/StateViews";
import { PerformanceLevelBadge } from "../components/PerformanceLevelBadge";
import { Pagination } from "../components/Pagination";
import { usePlants } from "../api/hooks";
import { useFilters } from "../hooks/useFilters";
import { rowHoverClass, rowStyle, searchInputClass, searchInputStyle, tdClass, thClass, theadRowStyle, thStyle } from "../lib/tableStyles";

type SortField = "sequence" | "name" | "factory" | "active_foreman_count" | "score" | "level";

const DESC_FIRST: ReadonlySet<SortField> = new Set(["active_foreman_count", "score", "level"]);

const COLUMNS: { field: SortField; label: string }[] = [
  { field: "name", label: "Tesis" },
  { field: "factory", label: "Fabrika" },
  { field: "active_foreman_count", label: "Aktif Formen" },
  { field: "score", label: "Toplam Puan" },
  { field: "level", label: "Seviye" },
];

export function PlantsPage() {
  const { filters, setFilters, clearFilters, asQueryParams } = useFilters();
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [sortBy, setSortBy] = useState<SortField>("sequence");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");
  const pageSize = 15;
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

  const plants = usePlants({
    ...asQueryParams,
    search: search || undefined,
    sort_by: sortBy,
    sort_dir: sortDir,
    page,
    page_size: pageSize,
  });

  return (
    <div className="flex flex-col gap-4">
      <FilterBar filters={filters} setFilters={setFilters} clearFilters={clearFilters} />

      <input
        type="search"
        placeholder="Tesis adı veya kodu ara..."
        value={search}
        onChange={(e) => {
          setSearch(e.target.value);
          setPage(1);
        }}
        className={searchInputClass}
        style={searchInputStyle}
      />

      <Card>
        {plants.isLoading && <LoadingState />}
        {plants.isError && <ErrorState />}
        {plants.data && plants.data.items.length === 0 && <EmptyState />}
        {plants.data && plants.data.items.length > 0 && (
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
                {plants.data.items.map((p) => (
                  <tr
                    key={p.id}
                    onClick={() => navigate(`/plants/${p.id}`)}
                    className={`cursor-pointer ${rowHoverClass}`}
                    style={rowStyle}
                  >
                    <td className={tdClass}>
                      <div className="font-medium" style={{ color: "var(--text-primary)" }}>{p.name}</div>
                      <div className="text-xs" style={{ color: "var(--text-muted)" }}>{p.code}</div>
                    </td>
                    <td className={tdClass} style={{ color: "var(--text-secondary)" }}>{p.factory?.name ?? "-"}</td>
                    <td className={tdClass} style={{ color: "var(--text-secondary)" }}>{p.active_foreman_count}</td>
                    <td className={`${tdClass} font-medium tabular-nums`} style={{ color: "var(--text-primary)" }}>{p.total_score.toFixed(1)}</td>
                    <td className={tdClass}>
                      <PerformanceLevelBadge level={p.level} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            <Pagination page={page} pageSize={pageSize} total={plants.data.total} onPageChange={setPage} itemLabel="tesis" />
          </div>
        )}
      </Card>
    </div>
  );
}
