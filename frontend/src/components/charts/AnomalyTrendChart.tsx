import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { AnomalyDailyPoint } from "../../api/types";
import { accentLineColor, resolveChartInk } from "../../lib/chartColors";
import { useTheme } from "../../context/ThemeContext";
import { EmptyState } from "../StateViews";

export function AnomalyTrendChart({ points, expectedValue }: { points: AnomalyDailyPoint[]; expectedValue: number }) {
  const { theme } = useTheme();
  const isDark = theme === "dark";
  const ink = resolveChartInk(isDark);

  if (points.length === 0) return <EmptyState message="Bu tespit için günlük geçmiş verisi bulunamadı." />;

  return (
    <ResponsiveContainer width="100%" height={260}>
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
  );
}
