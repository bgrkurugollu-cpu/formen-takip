import { CartesianGrid, Line, LineChart, ReferenceDot, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { AnomalyDailyPoint, KpiDirection } from "../../api/types";
import { accentLineColor, resolveChartInk } from "../../lib/chartColors";
import { useTheme } from "../../context/ThemeContext";
import { EmptyState } from "../StateViews";
import { formatSignedPct, isHigherBetter, performanceDirection, PERFORMANCE_COLORS, PERFORMANCE_LABELS } from "../../lib/kpiDirection";

export function KpiTrendInvestigationChart({
  points, expectedValue, desiredDirection, baselineAvg,
}: {
  points: AnomalyDailyPoint[];
  expectedValue: number;
  desiredDirection: KpiDirection;
  baselineAvg?: number | null;
}) {
  const { theme } = useTheme();
  const isDark = theme === "dark";
  const ink = resolveChartInk(isDark);

  if (points.length === 0) return <EmptyState message="Bu tespit için günlük geçmiş verisi bulunamadı." />;

  const higherIsBetter = isHigherBetter(desiredDirection);
  const worstPoint =
    higherIsBetter === null
      ? null
      : points.reduce((worst, p) => {
          const pIsWorse = higherIsBetter ? p.value < worst.value : p.value > worst.value;
          return pIsWorse ? p : worst;
        }, points[0]);

  const startValue = points[0].value;
  const endValue = points[points.length - 1].value;
  const change = endValue - startValue;
  const changePct = startValue !== 0 ? (change / Math.abs(startValue)) * 100 : null;
  const perfDir = performanceDirection(desiredDirection, change > 0);

  return (
    <div className="flex flex-col gap-3">
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={points} margin={{ top: 8, right: 16, left: -8, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={ink.grid} vertical={false} />
          <XAxis dataKey="date" tick={{ fontSize: 11, fill: ink.muted }} tickLine={false} axisLine={{ stroke: ink.axis }} />
          <YAxis tick={{ fontSize: 11, fill: ink.muted }} tickLine={false} axisLine={false} width={40} />
          <ReferenceLine
            y={expectedValue}
            stroke={ink.muted}
            strokeDasharray="4 4"
            label={{ value: "Beklenen", fontSize: 10, fill: ink.muted, position: "insideTopRight" }}
          />
          {baselineAvg != null && (
            <ReferenceLine
              y={baselineAvg}
              stroke={ink.axis}
              strokeDasharray="2 2"
              label={{ value: "Önceki Dönem", fontSize: 10, fill: ink.muted, position: "insideBottomLeft" }}
            />
          )}
          {worstPoint && (
            <ReferenceDot
              x={worstPoint.date}
              y={worstPoint.value}
              r={5}
              fill="#b91c1c"
              stroke={isDark ? "#1a2333" : "#ffffff"}
              strokeWidth={2}
              label={{ value: `Dönem zirvesi: %${worstPoint.value.toFixed(2)}`, fontSize: 10, fill: "#b91c1c", position: "top" }}
            />
          )}
          <Tooltip
            formatter={(value) => [`%${Number(value).toFixed(2)}`, "Gözlenen Değer"]}
            contentStyle={{
              fontSize: 12, borderRadius: 8, border: `1px solid ${ink.grid}`,
              background: isDark ? "#1a2333" : "#ffffff", color: ink.primary,
            }}
            labelStyle={{ color: ink.primary }}
            itemStyle={{ color: ink.primary }}
          />
          <Line type="monotone" dataKey="value" stroke={accentLineColor(isDark)} strokeWidth={2} dot={false} activeDot={{ r: 4 }} />
        </LineChart>
      </ResponsiveContainer>

      <div className="flex flex-wrap items-center gap-3 rounded-md p-3 text-[13px]" style={{ background: "var(--page-bg)" }}>
        <span style={{ color: "var(--text-muted)" }}>Dönem başlangıcı</span>
        <span className="font-semibold tabular-nums" style={{ color: "var(--text-primary)" }}>%{startValue.toFixed(2)}</span>
        <span style={{ color: "var(--text-muted)" }}>→</span>
        <span style={{ color: "var(--text-muted)" }}>Dönem sonu</span>
        <span className="font-semibold tabular-nums" style={{ color: "var(--text-primary)" }}>%{endValue.toFixed(2)}</span>
        <span style={{ color: "var(--text-muted)" }}>Değişim</span>
        <span className="font-semibold tabular-nums" style={{ color: PERFORMANCE_COLORS[perfDir] }}>
          {changePct != null ? formatSignedPct(changePct) : "-"} ({PERFORMANCE_LABELS[perfDir]})
        </span>
      </div>
    </div>
  );
}
