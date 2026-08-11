import { useEffect, useState } from "react";
import { useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { ArrowRight, Info } from "lucide-react";
import { useKpis, usePlantForemanShiftMatrix } from "../api/hooks";
import { Card, EmptyState, ErrorState, LoadingState } from "./StateViews";
import { PerformanceLevelBadge } from "./PerformanceLevelBadge";
import { withSearchParam } from "../lib/chartDrilldown";
import { fieldClass, fieldStyle, labelClass, labelStyle } from "../lib/formStyles";
import { rowStyle, tdClass, thClass, theadRowStyle, thStyle } from "../lib/tableStyles";
import type { ForemanShiftMatrixCell } from "../api/types";

function decimalPlacesFor(unit: string): number {
  return unit === "%" ? 1 : 2;
}

function MatrixCell({ cell, unit }: { cell: ForemanShiftMatrixCell | null; unit: string }) {
  if (!cell) {
    return (
      <div
        className="rounded-md p-3 text-center text-xs"
        style={{ background: "var(--page-bg)", border: "1px dashed var(--border)", color: "var(--text-muted)" }}
      >
        Veri yok
      </div>
    );
  }
  const decimals = decimalPlacesFor(unit);
  return (
    <div
      className="rounded-md p-3"
      style={{ background: "var(--page-bg)", border: "1px solid var(--border)", borderTop: `2px solid ${cell.level.color}` }}
    >
      <p className="text-lg font-semibold tabular-nums" style={{ color: "var(--text-primary)" }}>
        {cell.avg_actual.toFixed(decimals)} <span className="text-xs font-normal" style={{ color: "var(--text-muted)" }}>{unit}</span>
      </p>
      {cell.deviation_pct !== null && (
        <p className="mt-0.5 text-[11px] tabular-nums" style={{ color: "var(--text-muted)" }}>
          Hedefe göre {cell.deviation_pct >= 0 ? "+" : ""}%{cell.deviation_pct.toFixed(1)}
        </p>
      )}
      <div className="mt-1.5"><PerformanceLevelBadge level={cell.level} /></div>
    </div>
  );
}

export function ForemanShiftComparisonMatrix({
  plantId, dateParams,
}: {
  plantId: string;
  dateParams: Record<string, string | undefined>;
}) {
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const kpis = useKpis();
  const focusKpiId = searchParams.get("fs_kpi");

  const [selectedKpiId, setSelectedKpiId] = useState<string>("");

  useEffect(() => {
    if (selectedKpiId) return;
    if (focusKpiId) {
      setSelectedKpiId(focusKpiId);
      return;
    }
    const first = kpis.data?.items[0];
    if (first) setSelectedKpiId(first.id);
  }, [focusKpiId, kpis.data, selectedKpiId]);

  const matrix = usePlantForemanShiftMatrix(plantId, selectedKpiId || undefined, dateParams);

  return (
    <Card title="Formen–Vardiya Karşılaştırması">
      <p className="-mt-2 mb-3 text-[13px]" style={{ color: "var(--text-muted)" }}>
        Bu tesis için formenlerin vardiya bazlı performans farklarını gösterir.
      </p>

      <div className="mb-4 flex flex-wrap items-end gap-2">
        <div>
          <label className={labelClass} style={labelStyle}>KPI</label>
          <select
            className={fieldClass}
            style={fieldStyle}
            value={selectedKpiId}
            onChange={(e) => setSelectedKpiId(e.target.value)}
            disabled={kpis.isLoading}
          >
            {(kpis.data?.items ?? []).map((k) => (
              <option key={k.id} value={k.id}>{k.name}</option>
            ))}
          </select>
        </div>
      </div>

      {matrix.isLoading && <LoadingState label="Karşılaştırma hesaplanıyor..." />}
      {matrix.isError && (
        <ErrorState message="Bu tesis/KPI için formen-vardiya karşılaştırması yapılacak yeterli veri bulunamadı." />
      )}
      {matrix.data && matrix.data.rows.length === 0 && <EmptyState message="Bu tesiste karşılaştırılacak formen bulunamadı." />}
      {matrix.data && matrix.data.rows.length > 0 && (
        <>
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-[13px]">
              <thead>
                <tr style={theadRowStyle}>
                  <th className={thClass} style={thStyle} />
                  {matrix.data.shifts.map((s) => (
                    <th key={s.id} className={`${thClass} text-center`} style={thStyle}>{s.name}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {matrix.data.rows.map((row) => (
                  <tr key={row.foreman_id} style={rowStyle}>
                    <td className={`${tdClass} align-top font-medium`} style={{ color: "var(--text-primary)" }}>
                      {row.full_name}
                      <span className="mt-0.5 block text-xs font-normal" style={{ color: "var(--text-muted)" }}>{row.employee_number}</span>
                    </td>
                    {matrix.data!.shifts.map((s) => (
                      <td key={s.id} className="py-2 pr-4 align-top">
                        <MatrixCell cell={row.cells[s.id] ?? null} unit={matrix.data!.kpi.unit} />
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div
            className="mt-3 flex items-start gap-2 rounded-md p-3 text-[13px]"
            style={{ background: "var(--accent-subtle)", border: "1px solid var(--border)" }}
          >
            <Info size={15} strokeWidth={2} className="mt-0.5 shrink-0" style={{ color: "var(--accent)" }} />
            <p style={{ color: "var(--text-secondary)" }}>{matrix.data.insight}</p>
          </div>

          <div className="mt-3 flex flex-wrap gap-2">
            {matrix.data.rows.map((row) => (
              <button
                key={row.foreman_id}
                type="button"
                onClick={() => navigate(`/foremen/${row.foreman_id}`)}
                className="inline-flex items-center gap-1 rounded-md px-2.5 py-1.5 text-xs font-medium hover:bg-[var(--page-bg)]"
                style={{ border: "1px solid var(--border)", color: "var(--accent)" }}
              >
                {row.full_name} Profiline Git
                <ArrowRight size={12} strokeWidth={2} />
              </button>
            ))}
            <button
              type="button"
              onClick={() => navigate({ pathname: "/kpis", search: withSearchParam(location.search, "kpi", matrix.data!.kpi.id) })}
              className="inline-flex items-center gap-1 rounded-md px-2.5 py-1.5 text-xs font-medium hover:bg-[var(--page-bg)]"
              style={{ border: "1px solid var(--border)", color: "var(--accent)" }}
            >
              KPI Analizini Gör
              <ArrowRight size={12} strokeWidth={2} />
            </button>
          </div>
        </>
      )}
    </Card>
  );
}
