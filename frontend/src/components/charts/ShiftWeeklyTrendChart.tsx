import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { ShiftAnomalyCard, ShiftAnomalyWeeklyPoint } from "../../api/types";
import { resolveChartInk } from "../../lib/chartColors";
import { useTheme } from "../../context/ThemeContext";
import { EmptyState } from "../StateViews";

const BETTER_COLOR = "#16a34a";
const WORSE_COLOR = "#dc2626";

export function ShiftWeeklyTrendChart({
  points, better, worse, unit, decimalPlaces = 1,
}: {
  points: ShiftAnomalyWeeklyPoint[];
  better: ShiftAnomalyCard["better"];
  worse: ShiftAnomalyCard["worse"];
  unit: string;
  decimalPlaces?: number;
}) {
  const { theme } = useTheme();
  const isDark = theme === "dark";
  const ink = resolveChartInk(isDark);

  if (points.length === 0) return <EmptyState message="Haftalık kırılım verisi bulunamadı." />;

  const data = [...points]
    .sort((a, b) => a.week_index - b.week_index)
    .map((p) => {
      const isBetter = p.foreman_id === better.id;
      return {
        week_label: p.week_label,
        value: p.avg_actual,
        name: isBetter ? better.name : worse.name,
        isBetter,
      };
    });

  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data} margin={{ top: 8, right: 16, left: -8, bottom: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={ink.grid} vertical={false} />
        <XAxis dataKey="week_label" tick={{ fontSize: 11, fill: ink.muted }} tickLine={false} axisLine={{ stroke: ink.axis }} />
        <YAxis tick={{ fontSize: 11, fill: ink.muted }} tickLine={false} axisLine={false} width={44} />
        <Tooltip
          formatter={(value, _key, item) => [`${Number(value).toFixed(decimalPlaces)} ${unit}`, item.payload.name]}
          contentStyle={{
            fontSize: 12, borderRadius: 8, border: `1px solid ${ink.grid}`,
            background: isDark ? "#1a2333" : "#ffffff", color: ink.primary,
          }}
          labelStyle={{ color: ink.primary }}
          itemStyle={{ color: ink.primary }}
        />
        <Bar dataKey="value" radius={[4, 4, 0, 0]} barSize={40} isAnimationActive={false}>
          {data.map((d, i) => (
            <Cell key={i} fill={d.isBetter ? BETTER_COLOR : WORSE_COLOR} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
