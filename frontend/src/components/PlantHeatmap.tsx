import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { usePlants } from "../api/hooks";
import { Card, ErrorState, LoadingState } from "./StateViews";
import type { DistributionItem, PlantListItem } from "../api/types";

const NO_DATA_COLOR = "#94a3b8";

function HeatmapCell({ plant, onNavigate }: { plant: PlantListItem; onNavigate: (id: string) => void }) {
  const [hover, setHover] = useState(false);
  const hasData = plant.record_count > 0;
  const color = hasData ? plant.level.color : NO_DATA_COLOR;

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => onNavigate(plant.id)}
        onMouseEnter={() => setHover(true)}
        onMouseLeave={() => setHover(false)}
        onFocus={() => setHover(true)}
        onBlur={() => setHover(false)}
        className="flex h-10 w-full items-center justify-center rounded text-[11px] font-semibold tabular-nums transition-transform duration-100 hover:z-10 hover:scale-105"
        style={{ background: `${color}26`, color, border: `1px solid ${color}66` }}
      >
        {String(plant.sequence_number).padStart(2, "0")}
      </button>
      {hover && (
        <div
          className="pointer-events-none absolute bottom-full left-1/2 z-30 mb-1.5 w-48 -translate-x-1/2 rounded-md p-2.5 text-xs shadow-lg"
          style={{ background: "var(--surface)", border: "1px solid var(--border)", color: "var(--text-primary)" }}
        >
          <p className="font-semibold">{plant.name}</p>
          <p style={{ color: "var(--text-muted)" }}>{plant.factory?.name ?? "-"}</p>
          {hasData ? (
            <>
              <p className="mt-1">
                Puan: <span className="font-medium tabular-nums">{plant.total_score.toFixed(1)}</span> — {plant.level.name}
              </p>
              <p style={{ color: "var(--text-muted)" }}>{plant.active_foreman_count} aktif formen</p>
            </>
          ) : (
            <p className="mt-1" style={{ color: "var(--text-muted)" }}>Bu dönem için veri yok</p>
          )}
        </div>
      )}
    </div>
  );
}

function FactoryGroup({ code, plants, onNavigate }: { code: string; plants: PlantListItem[]; onNavigate: (id: string) => void }) {
  return (
    <div>
      <p className="mb-2 text-[11px] font-semibold uppercase tracking-wide" style={{ color: "var(--text-muted)" }}>
        {code} <span className="normal-case" style={{ color: "var(--text-muted)" }}>({plants.length} tesis)</span>
      </p>
      <div className="grid grid-cols-6 gap-1.5 sm:grid-cols-9 md:grid-cols-12">
        {plants.map((p) => (
          <HeatmapCell key={p.id} plant={p} onNavigate={onNavigate} />
        ))}
      </div>
    </div>
  );
}

export function PlantHeatmap({
  filters,
  levels,
}: {
  filters: Record<string, string | number | undefined>;
  levels: DistributionItem[] | undefined;
}) {
  const navigate = useNavigate();
  const plants = usePlants({ ...filters, sort_by: "sequence", sort_dir: "asc", page_size: 50 });

  const groups = useMemo(() => {
    const items = plants.data?.items ?? [];
    const byFactory = new Map<string, PlantListItem[]>();
    for (const p of items) {
      const key = p.factory?.code ?? "?";
      if (!byFactory.has(key)) byFactory.set(key, []);
      byFactory.get(key)!.push(p);
    }
    return [...byFactory.entries()].sort(([a], [b]) => a.localeCompare(b));
  }, [plants.data]);

  return (
    <Card title="Tesis Performans Haritası (50 Tesis)">
      {plants.isLoading && <LoadingState />}
      {plants.isError && <ErrorState />}
      {plants.data && (
        <div className="flex flex-col gap-5">
          {groups.map(([code, factoryPlants]) => (
            <FactoryGroup key={code} code={code} plants={factoryPlants} onNavigate={(id) => navigate(`/plants/${id}`)} />
          ))}

          <div
            className="flex flex-wrap items-center gap-x-4 gap-y-2 pt-3 text-xs"
            style={{ borderTop: "1px solid var(--border)", color: "var(--text-secondary)" }}
          >
            {(levels ?? []).map((lv) => (
              <span key={lv.name} className="flex items-center gap-1.5">
                <span className="h-2.5 w-2.5 rounded-full" style={{ background: lv.color }} />
                {lv.name}
              </span>
            ))}
            <span className="flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-full" style={{ background: NO_DATA_COLOR }} />
              Veri Yok
            </span>
          </div>
        </div>
      )}
    </Card>
  );
}
