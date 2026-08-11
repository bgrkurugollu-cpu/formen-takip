import { useMemo, useState } from "react";
import {
  CartesianGrid, ReferenceLine, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis,
} from "recharts";
import type { KpiForemanValueItem } from "../../api/types";
import { resolveChartInk } from "../../lib/chartColors";
import { useTheme } from "../../context/ThemeContext";
import { EmptyState } from "../StateViews";
import { PerformanceLevelBadge } from "../PerformanceLevelBadge";
import { fieldClass, fieldStyle } from "../../lib/formStyles";

const TIER_COLOR: Record<KpiForemanValueItem["tier"], string> = {
  better: "#16a34a",
  near: "#ca8a04",
  worse: "#dc2626",
};

const TIER_LABEL: Record<KpiForemanValueItem["tier"], string> = {
  better: "Hedefin Üzerinde Performans",
  near: "Hedefe Yakın Performans",
  worse: "Hedefin Altında Performans",
};

type SortMode = "name" | "best" | "worst" | "deviation";

const SORT_OPTIONS: { value: SortMode; label: string }[] = [
  { value: "name", label: "Formen Adına Göre" },
  { value: "best", label: "En İyi Performanstan En Kötüye" },
  { value: "worst", label: "En Kötü Performanstan En İyiye" },
  { value: "deviation", label: "Hedeften Sapmaya Göre" },
];

function formatValue(value: number, unit: string, decimalPlaces: number): string {
  return `${value.toFixed(decimalPlaces)} ${unit}`;
}

function pctDeviation(actual: number, target: number): number {
  return target !== 0 ? Math.abs((actual - target) / target) * 100 : 0;
}

const TIER_QUALIFIER: Record<KpiForemanValueItem["tier"], string> = {
  better: "daha iyi",
  near: "hedefe yakın",
  worse: "daha kötü",
};

function CustomTooltip({
  active, payload, unit, decimalPlaces, target,
}: {
  active?: boolean;
  payload?: { payload: KpiForemanValueItem }[];
  unit: string;
  decimalPlaces: number;
  target: number;
}) {
  const { theme } = useTheme();
  const isDark = theme === "dark";
  const ink = resolveChartInk(isDark);
  if (!active || !payload?.length) return null;
  const point = payload[0].payload;
  const raw = point.avg_actual - target;
  const pct = pctDeviation(point.avg_actual, target);

  return (
    <div
      className="rounded-lg px-3 py-2.5 text-xs"
      style={{
        border: `1px solid ${ink.grid}`,
        background: isDark ? "#1a2333" : "#ffffff",
        color: ink.primary,
        minWidth: 220,
      }}
    >
      <p className="mb-1.5 text-[13px] font-semibold">{point.full_name ?? "-"}</p>
      <div className="flex flex-col gap-1">
        <div className="flex items-center justify-between gap-4">
          <span style={{ color: ink.secondary }}>Gerçekleşen</span>
          <span className="font-medium tabular-nums">{formatValue(point.avg_actual, unit, decimalPlaces)}</span>
        </div>
        <div className="flex items-center justify-between gap-4">
          <span style={{ color: ink.secondary }}>Fabrika Hedefi</span>
          <span className="font-medium tabular-nums">{formatValue(target, unit, decimalPlaces)}</span>
        </div>
        <div className="flex items-center justify-between gap-4">
          <span style={{ color: ink.secondary }}>Hedeften Fark</span>
          <span className="font-medium tabular-nums">{raw >= 0 ? "+" : ""}{formatValue(raw, unit, decimalPlaces)}</span>
        </div>
        <div className="flex items-center justify-between gap-4">
          <span style={{ color: ink.secondary }}>Hedefe Göre Fark</span>
          <span className="font-medium tabular-nums" style={{ color: TIER_COLOR[point.tier] }}>
            %{pct.toFixed(1)} {TIER_QUALIFIER[point.tier]}
          </span>
        </div>
      </div>
      <div className="mt-2 flex items-center justify-between gap-2 border-t pt-2" style={{ borderColor: ink.grid }}>
        <span style={{ color: ink.secondary }}>{TIER_LABEL[point.tier]}</span>
        {point.level && <PerformanceLevelBadge level={point.level} />}
      </div>
    </div>
  );
}

export function ForemanKpiTargetChart({
  points, target, unit, kpiName, decimalPlaces, subtitle,
}: {
  points: KpiForemanValueItem[];
  target: number | null;
  unit: string;
  kpiName: string;
  decimalPlaces: number;
  subtitle: string;
}) {
  const { theme } = useTheme();
  const isDark = theme === "dark";
  const ink = resolveChartInk(isDark);
  const [sortMode, setSortMode] = useState<SortMode>("name");

  const sorted = useMemo(() => {
    const items = [...points];
    switch (sortMode) {
      case "best":
        return items.sort((a, b) => b.avg_score - a.avg_score);
      case "worst":
        return items.sort((a, b) => a.avg_score - b.avg_score);
      case "deviation": {
        const dev = (p: KpiForemanValueItem) => (target !== null ? pctDeviation(p.avg_actual, target) : 0);
        return items.sort((a, b) => dev(b) - dev(a));
      }
      default:
        return items.sort((a, b) => (a.full_name ?? "").localeCompare(b.full_name ?? "", "tr"));
    }
  }, [points, sortMode, target]);

  if (points.length === 0 || target === null) {
    return <EmptyState message="Seçilen filtrelerle bu KPI için formen verisi bulunamadı." />;
  }

  const metCount = points.filter((p) => p.tier === "better").length;
  const bestPoint = points.reduce((best, p) => (p.avg_score > best.avg_score ? p : best), points[0]);
  const avgForemanActual = points.reduce((sum, p) => sum + p.avg_actual, 0) / points.length;

  const values = points.map((p) => p.avg_actual).concat(target);
  const dataMin = Math.min(...values);
  const dataMax = Math.max(...values);
  const pad = (dataMax - dataMin) * 0.2 || Math.abs(target) * 0.1 || 1;
  const yDomain: [number, number] = [dataMin - pad, dataMax + pad];

  const height = 340;

  return (
    <div>
      <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-[14px] font-semibold" style={{ color: "var(--text-primary)" }}>
            {kpiName} — Formen Performans / Fabrika Hedefi Karşılaştırması
          </h3>
          <p className="mt-0.5 text-xs" style={{ color: "var(--text-muted)" }}>{subtitle}</p>
        </div>
        <select
          value={sortMode}
          onChange={(e) => setSortMode(e.target.value as SortMode)}
          className={fieldClass}
          style={{ ...fieldStyle, width: "auto" }}
        >
          {SORT_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
      </div>

      <div className="mb-4 grid grid-cols-2 gap-3 md:grid-cols-4">
        <div className="rounded-md p-2.5" style={{ background: "var(--page-bg)", border: "1px solid var(--border)" }}>
          <p className="text-[10px] font-medium uppercase tracking-wide" style={{ color: "var(--text-muted)" }}>Fabrika Ort. Hedefi</p>
          <p className="mt-0.5 text-sm font-semibold tabular-nums" style={{ color: "var(--text-primary)" }}>{formatValue(target, unit, decimalPlaces)}</p>
        </div>
        <div className="rounded-md p-2.5" style={{ background: "var(--page-bg)", border: "1px solid var(--border)" }}>
          <p className="text-[10px] font-medium uppercase tracking-wide" style={{ color: "var(--text-muted)" }}>Hedefi Karşılayan Formen</p>
          <p className="mt-0.5 text-sm font-semibold tabular-nums" style={{ color: "var(--text-primary)" }}>{metCount} / {points.length}</p>
        </div>
        <div className="rounded-md p-2.5" style={{ background: "var(--page-bg)", border: "1px solid var(--border)" }}>
          <p className="text-[10px] font-medium uppercase tracking-wide" style={{ color: "var(--text-muted)" }}>En İyi Sonuç</p>
          <p className="mt-0.5 text-sm font-semibold tabular-nums" style={{ color: "var(--text-primary)" }}>{formatValue(bestPoint.avg_actual, unit, decimalPlaces)}</p>
        </div>
        <div className="rounded-md p-2.5" style={{ background: "var(--page-bg)", border: "1px solid var(--border)" }}>
          <p className="text-[10px] font-medium uppercase tracking-wide" style={{ color: "var(--text-muted)" }}>Ort. Formen Gerçekleşeni</p>
          <p className="mt-0.5 text-sm font-semibold tabular-nums" style={{ color: "var(--text-primary)" }}>{formatValue(avgForemanActual, unit, decimalPlaces)}</p>
        </div>
      </div>

      <div>
        <ResponsiveContainer width="100%" height={height}>
          <ScatterChart data={sorted} margin={{ top: 12, right: 24, left: 4, bottom: 64 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={ink.grid} vertical={false} />
            <XAxis
              dataKey="full_name"
              type="category"
              allowDuplicatedCategory={false}
              interval={0}
              angle={-60}
              textAnchor="end"
              height={90}
              tick={{ fontSize: 10, fill: ink.muted }}
              tickLine={false}
              axisLine={{ stroke: ink.axis }}
            />
            <YAxis
              dataKey="avg_actual"
              type="number"
              domain={yDomain}
              tick={{ fontSize: 11, fill: ink.muted }}
              tickLine={false}
              axisLine={false}
              width={48}
              tickFormatter={(v) => Number(v).toFixed(decimalPlaces)}
            />
            <ReferenceLine
              y={target}
              stroke={ink.primary}
              strokeWidth={2}
              strokeDasharray="6 4"
              label={{
                value: `Ortalama Fabrika Hedefi: ${formatValue(target, unit, decimalPlaces)}`,
                position: "insideTopRight",
                fontSize: 11,
                fontWeight: 600,
                fill: ink.primary,
              }}
            />
            <Tooltip
              content={<CustomTooltip unit={unit} decimalPlaces={decimalPlaces} target={target} />}
              cursor={{ stroke: ink.axis, strokeDasharray: "3 3" }}
            />
            <Scatter
              shape={(shapeProps: { cx?: number; cy?: number; payload?: KpiForemanValueItem }) => {
                const { cx, cy, payload } = shapeProps;
                if (cx === undefined || cy === undefined || !payload) return <g />;
                return (
                  <circle cx={cx} cy={cy} r={7} fill={TIER_COLOR[payload.tier]} stroke="var(--surface)" strokeWidth={2} />
                );
              }}
            />
          </ScatterChart>
        </ResponsiveContainer>
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-4 text-[11px]" style={{ color: "var(--text-muted)" }}>
        <span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-full" style={{ background: TIER_COLOR.better }} />Hedefin Üzerinde</span>
        <span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-full" style={{ background: TIER_COLOR.near }} />Hedefe Yakın</span>
        <span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-full" style={{ background: TIER_COLOR.worse }} />Hedefin Altında</span>
        <span className="flex items-center gap-1.5"><span className="inline-block h-0.5 w-4" style={{ background: ink.primary }} />Ortalama Fabrika Hedefi</span>
      </div>
    </div>
  );
}
