import { useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useShiftHeatmap } from "../api/hooks";
import { Card, EmptyState, ErrorState, LoadingState } from "./StateViews";
import { withSearchParam } from "../lib/chartDrilldown";
import type { HeatmapCell, HeatmapLevel } from "../api/types";

const LEVEL_CONFIG: Record<HeatmapLevel, { label: string; color: string }> = {
  no_data: { label: "Veri Yok", color: "#94a3b8" },
  normal: { label: "Normal", color: "#16a34a" },
  attention: { label: "Dikkat", color: "#ca8a04" },
  significant: { label: "Önemli", color: "#ea580c" },
  critical: { label: "Kritik", color: "#b91c1c" },
};

const LEVEL_ORDER: HeatmapLevel[] = ["normal", "attention", "significant", "critical", "no_data"];

function decimalPlacesFor(unit: string): number {
  return unit === "%" ? 1 : 2;
}

function HeatmapCellButton({
  cell, plantLabel, kpiName, kpiUnit, shiftNames, onNavigate,
}: {
  cell: HeatmapCell;
  plantLabel: string;
  kpiName: string;
  kpiUnit: string;
  shiftNames: [string, string];
  onNavigate: (plantId: string, kpiId: string) => void;
}) {
  const [hover, setHover] = useState(false);
  const cfg = LEVEL_CONFIG[cell.level];
  const decimals = decimalPlacesFor(kpiUnit);
  const hasData = cell.level !== "no_data" && cell.v1 && cell.v2;

  return (
    <td className="p-0.5 text-center align-middle">
      <div className="relative">
        <button
          type="button"
          onClick={() => onNavigate(cell.plant_id, cell.kpi_id)}
          onMouseEnter={() => setHover(true)}
          onMouseLeave={() => setHover(false)}
          onFocus={() => setHover(true)}
          onBlur={() => setHover(false)}
          className="flex h-8 w-full min-w-16 items-center justify-center rounded text-[11px] font-semibold tabular-nums transition-transform duration-100 hover:z-20 hover:scale-105"
          style={{ background: `${cfg.color}22`, color: cfg.color, border: `1px solid ${cfg.color}55` }}
        >
          {hasData ? `%${cell.pct_diff!.toFixed(1)}` : "—"}
        </button>
        {hover && (
          <div
            className="pointer-events-none absolute bottom-full left-1/2 z-30 mb-1.5 w-56 -translate-x-1/2 rounded-md p-2.5 text-left text-xs shadow-lg"
            style={{ background: "var(--surface)", border: "1px solid var(--border)", color: "var(--text-primary)" }}
          >
            <p className="font-semibold">{plantLabel} — {kpiName}</p>
            {hasData ? (
              <>
                <p className="mt-1" style={{ color: "var(--text-secondary)" }}>
                  {shiftNames[0]}: <span className="font-medium tabular-nums" style={{ color: "var(--text-primary)" }}>{cell.v1!.avg_actual.toFixed(decimals)}</span>
                </p>
                <p style={{ color: "var(--text-secondary)" }}>
                  {shiftNames[1]}: <span className="font-medium tabular-nums" style={{ color: "var(--text-primary)" }}>{cell.v2!.avg_actual.toFixed(decimals)}</span>
                </p>
                <p className="mt-1 tabular-nums" style={{ color: "var(--text-secondary)" }}>
                  Fark: {(cell.v1!.avg_actual - cell.v2!.avg_actual >= 0 ? "+" : "")}
                  {(cell.v1!.avg_actual - cell.v2!.avg_actual).toFixed(decimals)} puan · Sapma: %{cell.pct_diff!.toFixed(1)}
                </p>
                <p className="mt-1 font-medium" style={{ color: cfg.color }}>Durum: {cfg.label}</p>
              </>
            ) : (
              <p className="mt-1" style={{ color: "var(--text-muted)" }}>Bu dönem için yeterli veri yok</p>
            )}
          </div>
        )}
      </div>
    </td>
  );
}

export function ShiftAnomalyHeatmap({ params }: { params: Record<string, string | undefined> }) {
  const navigate = useNavigate();
  const location = useLocation();
  const heatmap = useShiftHeatmap(params);

  const cellByKey = useMemo(() => {
    const map = new Map<string, HeatmapCell>();
    for (const c of heatmap.data?.cells ?? []) map.set(`${c.plant_id}|${c.kpi_id}`, c);
    return map;
  }, [heatmap.data]);

  const handleNavigate = (plantId: string, kpiId: string) => {
    navigate({ pathname: `/plants/${plantId}`, search: withSearchParam(location.search, "fs_kpi", kpiId) });
  };

  return (
    <Card title="Vardiya Anomali Heatmap">
      <p className="-mt-2 mb-3 text-[13px]" style={{ color: "var(--text-muted)" }}>
        Her hücre, ilgili tesis/KPI için {heatmap.data ? `${heatmap.data.shifts[0]?.name} ile ${heatmap.data.shifts[1]?.name}` : "iki vardiya"} arasındaki
        normalize edilmiş performans farkını gösterir. Bir hücreye tıklayarak ilgili tesise, seçili KPI bağlamında gidebilirsiniz.
      </p>

      {heatmap.isLoading && <LoadingState label="Heatmap hesaplanıyor..." />}
      {heatmap.isError && <ErrorState />}
      {heatmap.data && heatmap.data.plants.length === 0 && (
        <EmptyState message="Seçilen filtrelerle eşleşen tesis bulunamadı." />
      )}
      {heatmap.data && heatmap.data.plants.length > 0 && heatmap.data.shifts.length === 2 && (
        <>
          <div className="max-h-[480px] overflow-auto rounded-md" style={{ border: "1px solid var(--border)" }}>
            <table className="w-full border-collapse text-[12px]">
              <thead>
                <tr>
                  <th
                    className="sticky left-0 top-0 z-30 whitespace-nowrap px-3 py-2 text-left text-[11px] font-semibold uppercase tracking-wide"
                    style={{ background: "var(--surface)", borderBottom: "1px solid var(--border)", borderRight: "1px solid var(--border)" }}
                  >
                    Tesis
                  </th>
                  {heatmap.data.kpis.map((k) => (
                    <th
                      key={k.id}
                      className="sticky top-0 z-20 whitespace-nowrap px-1.5 py-2 text-center text-[11px] font-semibold uppercase tracking-wide"
                      style={{ background: "var(--surface)", borderBottom: "1px solid var(--border)", color: "var(--text-muted)" }}
                    >
                      {k.name}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {heatmap.data.plants.map((p) => (
                  <tr key={p.id}>
                    <td
                      className="sticky left-0 z-10 whitespace-nowrap px-3 py-1 text-[12px] font-medium"
                      style={{ background: "var(--surface)", borderRight: "1px solid var(--border)", color: "var(--text-primary)" }}
                    >
                      <span className="tabular-nums" style={{ color: "var(--text-muted)" }}>{String(p.sequence_number).padStart(2, "0")}</span>{" "}
                      {p.name} <span style={{ color: "var(--text-muted)" }}>({p.factory_code})</span>
                    </td>
                    {heatmap.data!.kpis.map((k) => {
                      const cell = cellByKey.get(`${p.id}|${k.id}`);
                      if (!cell) return <td key={k.id} />;
                      return (
                        <HeatmapCellButton
                          key={k.id}
                          cell={cell}
                          plantLabel={`${p.name} (${p.factory_code})`}
                          kpiName={k.name}
                          kpiUnit={k.unit}
                          shiftNames={[heatmap.data!.shifts[0].name, heatmap.data!.shifts[1].name]}
                          onNavigate={handleNavigate}
                        />
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div
            className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-2 pt-3 text-xs"
            style={{ borderTop: "1px solid var(--border)", color: "var(--text-secondary)" }}
          >
            {LEVEL_ORDER.map((level) => (
              <span key={level} className="flex items-center gap-1.5">
                <span className="h-2.5 w-2.5 rounded-full" style={{ background: LEVEL_CONFIG[level].color }} />
                {LEVEL_CONFIG[level].label}
              </span>
            ))}
          </div>
        </>
      )}
    </Card>
  );
}
