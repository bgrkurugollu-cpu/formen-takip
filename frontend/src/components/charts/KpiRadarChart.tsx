import { PolarAngleAxis, PolarGrid, Radar, RadarChart, ResponsiveContainer, Tooltip } from "recharts";
import type { ForemanKpiItem } from "../../api/types";
import { accentLineColor, resolveChartInk } from "../../lib/chartColors";
import { useTheme } from "../../context/ThemeContext";
import { EmptyState } from "../StateViews";

export function KpiRadarChart({ items }: { items: ForemanKpiItem[] }) {
  const { theme } = useTheme();
  const isDark = theme === "dark";
  const ink = resolveChartInk(isDark);
  const lineColor = accentLineColor(isDark);

  if (items.length === 0) return <EmptyState />;
  const data = items.map((i) => ({ subject: i.code, score: Math.min(i.avg_capped_score, 120) }));

  return (
    <ResponsiveContainer width="100%" height={260}>
      <RadarChart data={data} outerRadius="75%">
        <PolarGrid stroke={ink.grid} />
        <PolarAngleAxis dataKey="subject" tick={{ fontSize: 11, fill: ink.secondary }} />
        <Radar dataKey="score" stroke={lineColor} fill={lineColor} fillOpacity={0.25} strokeWidth={2} />
        <Tooltip
          formatter={(value) => [Number(value).toFixed(1), "Puan"]}
          contentStyle={{ fontSize: 12, borderRadius: 8, background: isDark ? "#1a2333" : "#ffffff", color: ink.primary, border: `1px solid ${ink.grid}` }}
          labelStyle={{ color: ink.primary }}
          itemStyle={{ color: ink.primary }}
        />
      </RadarChart>
    </ResponsiveContainer>
  );
}
