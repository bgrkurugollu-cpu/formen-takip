import type { RelatedKpiChange } from "../../api/types";
import { EmptyState } from "../StateViews";
import { formatSignedPct, formatSignedPoints, PERFORMANCE_COLORS, PERFORMANCE_LABELS } from "../../lib/kpiDirection";
import { accentLineColor } from "../../lib/chartColors";
import { useTheme } from "../../context/ThemeContext";

function Sparkline({ values, color }: { values: number[]; color: string }) {
  if (values.length < 2) return null;
  const width = 72;
  const height = 24;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const points = values
    .map((v, i) => {
      const x = (i / (values.length - 1)) * width;
      const y = height - ((v - min) / span) * height;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} className="shrink-0">
      <polyline points={points} fill="none" stroke={color} strokeWidth={1.5} />
    </svg>
  );
}

export function RelatedKpiChanges({ items }: { items: RelatedKpiChange[] }) {
  const { theme } = useTheme();
  const isDark = theme === "dark";

  if (items.length === 0) return <EmptyState message="İlişkili KPI sinyali bulunamadı." />;

  return (
    <div className="flex flex-col gap-3">
      <ul className="flex flex-col gap-2">
        {items.map((item) => {
          const dir = item.performance_direction ?? "unknown";
          return (
            <li
              key={item.kpi_code}
              className="flex flex-wrap items-center justify-between gap-3 rounded-md p-3 text-[13px]"
              style={{ border: "1px solid var(--border)" }}
            >
              <div className="min-w-[140px]">
                <p className="font-medium" style={{ color: "var(--text-primary)" }}>{item.kpi}</p>
                <p className="tabular-nums" style={{ color: "var(--text-muted)" }}>
                  %{item.baseline_value.toFixed(2)} → %{item.current_value.toFixed(2)}
                </p>
              </div>
              <Sparkline values={item.sparkline} color={accentLineColor(isDark)} />
              <div className="text-right">
                <p className="font-semibold tabular-nums" style={{ color: PERFORMANCE_COLORS[dir] }}>
                  {formatSignedPoints(item.abs_change)}
                </p>
                <p className="text-xs tabular-nums" style={{ color: PERFORMANCE_COLORS[dir] }}>
                  {formatSignedPct(item.change_percent)} · {PERFORMANCE_LABELS[dir]}
                </p>
              </div>
            </li>
          );
        })}
      </ul>
      <p className="text-xs italic" style={{ color: "var(--text-muted)" }}>
        Bu değişimler tespit edilen KPI ile aynı dönemde gerçekleşmiştir; nedensellik ifade etmez.
      </p>
    </div>
  );
}
