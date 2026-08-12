import { Bar, BarChart, Cell, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { ShiftAnomalyForemanStat } from "../../api/types";
import { resolveChartInk } from "../../lib/chartColors";
import { useTheme } from "../../context/ThemeContext";

const BETTER_COLOR = "#16a34a";
const WORSE_COLOR = "#dc2626";

export function ShiftComparisonMiniChart({
  better, worse, unit, decimalPlaces = 1,
}: {
  better: ShiftAnomalyForemanStat;
  worse: ShiftAnomalyForemanStat;
  unit: string;
  decimalPlaces?: number;
}) {
  const { theme } = useTheme();
  const isDark = theme === "dark";
  const ink = resolveChartInk(isDark);

  const data = [
    { name: worse.name, value: worse.avg_actual, isBetter: false },
    { name: better.name, value: better.avg_actual, isBetter: true },
  ];

  return (
    <ResponsiveContainer width="100%" height={140}>
      <BarChart data={data} margin={{ top: 16, right: 12, left: -8, bottom: 4 }}>
        <XAxis dataKey="name" tick={{ fontSize: 11, fill: ink.secondary }} tickLine={false} axisLine={{ stroke: ink.axis }} />
        <YAxis tick={{ fontSize: 11, fill: ink.muted }} tickLine={false} axisLine={false} width={36} />
        <Tooltip
          formatter={(value) => [`${Number(value).toFixed(decimalPlaces)} ${unit}`, "Dönem Ortalaması"]}
          contentStyle={{
            fontSize: 12, borderRadius: 8, border: `1px solid ${ink.grid}`,
            background: isDark ? "#1a2333" : "#ffffff", color: ink.primary,
          }}
          labelStyle={{ color: ink.primary }}
          itemStyle={{ color: ink.primary }}
          cursor={{ fill: isDark ? "#ffffff0d" : "#0000000a" }}
        />
        <Bar dataKey="value" radius={[4, 4, 0, 0]} barSize={48} isAnimationActive={false}>
          {data.map((d) => (
            <Cell key={d.name} fill={d.isBetter ? BETTER_COLOR : WORSE_COLOR} />
          ))}
          <LabelList dataKey="value" position="top" fontSize={11} fill={ink.primary} formatter={(v) => Number(v).toFixed(decimalPlaces)} />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
