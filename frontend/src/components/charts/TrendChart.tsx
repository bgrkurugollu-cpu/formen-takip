import { AlertTriangle } from "lucide-react";
import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { TrendPoint } from "../../api/types";
import { accentLineColor, resolveChartInk } from "../../lib/chartColors";
import { useTheme } from "../../context/ThemeContext";
import { EmptyState } from "../StateViews";

export function TrendChart({ points }: { points: TrendPoint[] }) {
  const { theme } = useTheme();
  const isDark = theme === "dark";
  const ink = resolveChartInk(isDark);

  if (points.length === 0) return <EmptyState />;

  const hasUnreliable = points.some((p) => !p.is_reliable);

  return (
    <div>
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={points} margin={{ top: 8, right: 16, left: -8, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={ink.grid} vertical={false} />
          <XAxis dataKey="date" tick={{ fontSize: 11, fill: ink.muted }} tickLine={false} axisLine={{ stroke: ink.axis }} />
          <YAxis tick={{ fontSize: 11, fill: ink.muted }} tickLine={false} axisLine={false} width={36} />
          <ReferenceLine y={100} stroke={ink.muted} strokeDasharray="4 4" label={{ value: "Hedef (100)", fontSize: 10, fill: ink.muted, position: "insideTopRight" }} />
          <Tooltip
            formatter={(value) => [Number(value).toFixed(1), "Performans Puanı"]}
            contentStyle={{
              fontSize: 12, borderRadius: 8, border: `1px solid ${ink.grid}`,
              background: isDark ? "#1a2333" : "#ffffff", color: ink.primary,
            }}
            labelStyle={{ color: ink.primary }}
            itemStyle={{ color: ink.primary }}
          />
          <Line
            type="monotone"
            dataKey="total_score"
            stroke={accentLineColor(isDark)}
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4 }}
          />
        </LineChart>
      </ResponsiveContainer>
      {hasUnreliable && (
        <p className="mt-2 flex items-center gap-1.5 text-xs font-medium text-amber-600">
          <AlertTriangle size={12} strokeWidth={2} className="shrink-0" />
          Bazı dönemlerde eksik KPI verisi nedeniyle puan yeniden normalize edildi — güvenilirlik sınırlı olabilir.
        </p>
      )}
    </div>
  );
}
