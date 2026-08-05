import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { categoricalColor, resolveChartInk } from "../../lib/chartColors";
import { useTheme } from "../../context/ThemeContext";
import { EmptyState } from "../StateViews";

export interface ComparisonBar {
  name: string;
  value: number;
  highlight?: boolean;
}

export function AnomalyComparisonChart({ items }: { items: ComparisonBar[] }) {
  const { theme } = useTheme();
  const isDark = theme === "dark";
  const ink = resolveChartInk(isDark);

  if (items.length === 0) return <EmptyState message="Karşılaştırma verisi bulunamadı." />;

  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={items} margin={{ top: 8, right: 16, left: -8, bottom: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={ink.grid} vertical={false} />
        <XAxis dataKey="name" tick={{ fontSize: 11, fill: ink.muted }} tickLine={false} axisLine={{ stroke: ink.axis }} />
        <YAxis tick={{ fontSize: 11, fill: ink.muted }} tickLine={false} axisLine={false} width={40} />
        <Tooltip
          formatter={(value) => [`%${Number(value).toFixed(2)}`, "Değer"]}
          contentStyle={{
            fontSize: 12, borderRadius: 8, border: `1px solid ${ink.grid}`,
            background: isDark ? "#1a2333" : "#ffffff", color: ink.primary,
          }}
          labelStyle={{ color: ink.primary }}
          itemStyle={{ color: ink.primary }}
        />
        <Bar dataKey="value" radius={[4, 4, 0, 0]} barSize={40}>
          {items.map((item, i) => (
            <Cell key={item.name} fill={item.highlight ? "#b91c1c" : categoricalColor(i, isDark)} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
