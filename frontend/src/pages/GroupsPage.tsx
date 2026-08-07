import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { AlertTriangle, ArrowDown, ArrowUp, ArrowUpDown } from "lucide-react";
import { FilterBar } from "../components/FilterBar";
import { Card, EmptyState, ErrorState, LoadingState } from "../components/StateViews";
import { PerformanceLevelBadge } from "../components/PerformanceLevelBadge";
import { Pagination } from "../components/Pagination";
import { useChiefs } from "../api/hooks";
import { useFilters } from "../hooks/useFilters";
import { rowHoverClass, rowStyle, searchInputClass, searchInputStyle, tdClass, thClass, theadRowStyle, thStyle } from "../lib/tableStyles";

type SortField = "name" | "employee_number" | "plant" | "factory" | "foreman_count" | "score" | "level" | "reliability";

const DESC_FIRST: ReadonlySet<SortField> = new Set(["foreman_count", "score", "level", "reliability"]);

const COLUMNS: { field: SortField; label: string }[] = [
  { field: "name", label: "Şef" },
  { field: "employee_number", label: "Sicil No" },
  { field: "factory", label: "Fabrika" },
  { field: "plant", label: "Tesis" },
  { field: "foreman_count", label: "Formen Sayısı" },
  { field: "score", label: "Grup Puanı" },
  { field: "level", label: "Seviye" },
  { field: "reliability", label: "Veri Güvenilirliği" },
];

export function GroupsPage() {
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
    sort_by: sortBy,
    sort_dir: sortDir,
    page,
    page_size: pageSize,
  };
  const chiefs = useChiefs(params);

  return (
    <div className="flex flex-col gap-4">
      <FilterBar filters={filters} setFilters={setFilters} clearFilters={clearFilters} />

      <input
        type="search"
        placeholder="Şef adı, soyadı veya sicil no ara..."
        value={search}
        onChange={(e) => {
          setSearch(e.target.value);
          setPage(1);
        }}
        className={searchInputClass}
        style={searchInputStyle}
      />

      <Card>
        {chiefs.isLoading && <LoadingState />}
        {chiefs.isError && <ErrorState />}
        {chiefs.data && chiefs.data.items.length === 0 && <EmptyState />}
        {chiefs.data && chiefs.data.items.length > 0 && (
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
                {chiefs.data.items.map((c) => (
                  <tr
                    key={c.id}
                    onClick={() => navigate(`/groups/${c.id}`)}
                    className={`cursor-pointer ${rowHoverClass}`}
                    style={rowStyle}
                  >
                    <td className={`${tdClass} font-medium`} style={{ color: "var(--text-primary)" }}>{c.full_name}</td>
                    <td className={tdClass} style={{ color: "var(--text-muted)" }}>{c.employee_number}</td>
                    <td className={tdClass} style={{ color: "var(--text-secondary)" }}>{c.factory?.name ?? "-"}</td>
                    <td className={tdClass} style={{ color: "var(--text-secondary)" }}>
                      {c.plants.length > 0 ? c.plants.map((p) => p.name).join(", ") : "-"}
                    </td>
                    <td className={`${tdClass} tabular-nums`} style={{ color: "var(--text-secondary)" }}>{c.foreman_count}</td>
                    <td className={`${tdClass} font-medium tabular-nums`} style={{ color: "var(--text-primary)" }}>{c.total_score.toFixed(1)}</td>
                    <td className={tdClass}>
                      <PerformanceLevelBadge level={c.level} />
                    </td>
                    <td className={tdClass}>
                      {c.is_reliable ? (
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

            <Pagination page={page} pageSize={pageSize} total={chiefs.data.total} onPageChange={setPage} itemLabel="grup" />
          </div>
        )}
      </Card>
    </div>
  );
}
