import { Legend, PolarAngleAxis, PolarGrid, Radar, RadarChart, ResponsiveContainer, Tooltip } from "recharts";
import type { ForemanKpiItem } from "../../api/types";
import { accentLineColor, categoricalColor, resolveChartInk } from "../../lib/chartColors";
import { useTheme } from "../../context/ThemeContext";
import { EmptyState } from "../StateViews";

interface CompareSeriesItem {
  code: string;
  avg_score: number;
}

export function KpiRadarChart({
  items,
  compareItems,
  compareLabel,
  seriesLabel = "Formen",
}: {
  items: ForemanKpiItem[];
  compareItems?: CompareSeriesItem[];
  compareLabel?: string;
  seriesLabel?: string;
}) {
  const { theme } = useTheme();
  const isDark = theme === "dark";
  const ink = resolveChartInk(isDark);
  const lineColor = accentLineColor(isDark);
  const compareColor = categoricalColor(1, isDark);

  if (items.length === 0) return <EmptyState />;
  const compareByCode = new Map((compareItems ?? []).map((c) => [c.code, c.avg_score]));
  const showCompare = !!compareItems;
  const data = items.map((i) => ({
    subject: i.code,
    score: Math.min(i.avg_capped_score, 120),
    compare: showCompare ? Math.min(compareByCode.get(i.code) ?? 0, 120) : undefined,
  }));

  return (
    <ResponsiveContainer width="100%" height={showCompare ? 300 : 260}>
      <RadarChart data={data} outerRadius="75%">
        <PolarGrid stroke={ink.grid} />
        <PolarAngleAxis dataKey="subject" tick={{ fontSize: 11, fill: ink.secondary }} />
        <Radar name={seriesLabel} dataKey="score" stroke={lineColor} fill={lineColor} fillOpacity={0.25} strokeWidth={2} />
        {showCompare && (
          <Radar
            name={compareLabel ?? "Karşılaştırma"}
            dataKey="compare"
            stroke={compareColor}
            fill={compareColor}
            fillOpacity={0.12}
            strokeWidth={2}
            strokeDasharray="4 3"
          />
        )}
        {showCompare && (
          <Legend wrapperStyle={{ fontSize: 12, color: ink.secondary }} />
        )}
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
