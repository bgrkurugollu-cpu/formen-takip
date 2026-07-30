import { Bar, BarChart, CartesianGrid, Cell, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { resolveChartInk } from "../../lib/chartColors";
import { useTheme } from "../../context/ThemeContext";
import { EmptyState } from "../StateViews";

interface Item {
  name: string;
  score: number;
  color: string;
}

export function RankingBarChart({ items }: { items: Item[] }) {
  const { theme } = useTheme();
  const isDark = theme === "dark";
  const ink = resolveChartInk(isDark);

  if (items.length === 0) return <EmptyState />;

  const height = Math.max(120, items.length * 32);

  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={items} layout="vertical" margin={{ top: 4, right: 24, left: 4, bottom: 4 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={ink.grid} horizontal={false} />
        <XAxis type="number" tick={{ fontSize: 11, fill: ink.muted }} tickLine={false} axisLine={{ stroke: ink.axis }} />
        <YAxis
          type="category"
          dataKey="name"
          width={140}
          tick={{ fontSize: 12, fill: ink.secondary }}
          tickLine={false}
          axisLine={false}
        />
        <ReferenceLine x={100} stroke={ink.muted} strokeDasharray="4 4" />
        <Tooltip
          formatter={(value) => [Number(value).toFixed(1), "Puan"]}
          contentStyle={{
            fontSize: 12, borderRadius: 8, border: `1px solid ${ink.grid}`,
            background: isDark ? "#1a2333" : "#ffffff", color: ink.primary,
          }}
          labelStyle={{ color: ink.primary }}
          itemStyle={{ color: ink.primary }}
        />
        <Bar dataKey="score" radius={[0, 4, 4, 0]} barSize={18}>
          {items.map((item, idx) => (
            <Cell key={idx} fill={item.color} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
