import type { AnomalyDetail } from "../../api/types";
import { AnomalyComparisonChart, type ComparisonBar } from "../charts/AnomalyComparisonChart";
import { formatSignedPct, formatSignedPoints } from "../../lib/kpiDirection";

function comparisonLabel(key: string): string {
  if (key === "plant_average") return "Tesis Ortalaması";
  if (key === "factory_average") return "Fabrika Ortalaması";
  const m = key.match(/^v(\d+)_average$/);
  return m ? `${m[1]}. Vardiya` : key;
}

interface DeltaRow {
  label: string;
  absDiff: number;
  pctDiff: number | null;
}

export function BenchmarkComparison({ anomaly }: { anomaly: AnomalyDetail }) {
  const a = anomaly;

  const comparisonBars: ComparisonBar[] = Object.entries(a.comparison || {}).map(([key, value]) => ({
    name: comparisonLabel(key),
    value: Number(value),
    highlight: comparisonLabel(key) === a.shift_name,
  }));

  const deltaRows: DeltaRow[] = [{ label: "Beklenen Farkı", absDiff: a.observed_value - a.expected_value, pctDiff: a.deviation_percent }];
  for (const [key, rawValue] of Object.entries(a.comparison || {})) {
    const value = Number(rawValue);
    const label = comparisonLabel(key);
    if (label === a.shift_name) continue;
    const absDiff = a.observed_value - value;
    const pctDiff = value !== 0 ? (absDiff / Math.abs(value)) * 100 : null;
    deltaRows.push({ label: `${label} Farkı`, absDiff, pctDiff });
  }

  const plantAvg = a.comparison?.plant_average;
  let summary: string | null = null;
  if (plantAvg != null && a.shift_name) {
    const relDiffFromPlant = plantAvg !== 0 ? ((a.observed_value - plantAvg) / Math.abs(plantAvg)) * 100 : 0;
    if (Math.abs(relDiffFromPlant) >= 15) {
      const magnitude = a.observed_value > plantAvg ? "Yüksek" : "Düşük";
      summary = `${magnitude} ${a.kpi_name} seviyesi tesis genelinden ziyade ${a.shift_name}'da yoğunlaşıyor.`;
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <AnomalyComparisonChart items={comparisonBars} />
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
        {deltaRows.map((row) => (
          <div key={row.label} className="flex items-center justify-between rounded-md p-2.5 text-[13px]" style={{ border: "1px solid var(--border)" }}>
            <span style={{ color: "var(--text-secondary)" }}>{row.label}</span>
            <span className="font-medium tabular-nums" style={{ color: "var(--text-primary)" }}>
              {formatSignedPoints(row.absDiff)}
              {row.pctDiff != null && <span style={{ color: "var(--text-muted)" }}> / {formatSignedPct(row.pctDiff)}</span>}
            </span>
          </div>
        ))}
      </div>
      {summary && (
        <p className="rounded-md p-2.5 text-[13px]" style={{ background: "var(--page-bg)", color: "var(--text-primary)" }}>{summary}</p>
      )}
    </div>
  );
}
