import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { FilterBar } from "../components/FilterBar";
import { Card, EmptyState, ErrorState, LoadingState } from "../components/StateViews";
import { PerformanceLevelBadge } from "../components/PerformanceLevelBadge";
import { Pagination } from "../components/Pagination";
import { usePlants } from "../api/hooks";
import { useFilters } from "../hooks/useFilters";
import { rowHoverClass, rowStyle, searchInputClass, searchInputStyle, tdClass, thClass, theadRowStyle, thStyle } from "../lib/tableStyles";

export function PlantsPage() {
  const { filters, setFilters, clearFilters, asQueryParams } = useFilters();
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const pageSize = 15;
  const navigate = useNavigate();

  const plants = usePlants({ ...asQueryParams, search: search || undefined, page, page_size: pageSize });

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-lg font-semibold" style={{ color: "var(--text-primary)" }}>Tesisler</h1>
        <p className="text-[13px]" style={{ color: "var(--text-muted)" }}>Şirket genelindeki 50 tesisin performans karşılaştırması.</p>
      </div>

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
                  <th className={thClass} style={thStyle}>Tesis</th>
                  <th className={thClass} style={thStyle}>Fabrika</th>
                  <th className={thClass} style={thStyle}>Aktif Formen</th>
                  <th className={thClass} style={thStyle}>Toplam Puan</th>
                  <th className={thClass} style={thStyle}>Seviye</th>
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
