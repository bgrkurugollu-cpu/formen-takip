import { AlertTriangle, Circle, Star, ThumbsUp, TrendingDown, Trophy } from "lucide-react";
import type { PerformanceLevel } from "../api/types";

const ICONS: Record<string, typeof Trophy> = {
  trophy: Trophy,
  star: Star,
  "thumbs-up": ThumbsUp,
  "trending-down": TrendingDown,
  "alert-triangle": AlertTriangle,
};

export function PerformanceLevelBadge({ level, showDescription = false }: { level: PerformanceLevel; showDescription?: boolean }) {
  const Icon = ICONS[level.icon] ?? Circle;
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded px-2 py-0.5 text-xs font-medium"
      style={{ backgroundColor: `${level.color}14`, color: level.color, border: `1px solid ${level.color}33` }}
      title={showDescription ? level.description : undefined}
    >
      <Icon size={12} strokeWidth={2} aria-hidden="true" />
      {level.name}
    </span>
  );
}
