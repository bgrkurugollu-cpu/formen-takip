import { ArrowRight, Trophy, TrendingDown } from "lucide-react";
import type { ForemanRankingItem } from "../api/types";
import type { FilterState } from "../hooks/useFilters";
import { LoadingState, EmptyState } from "./StateViews";

const RANK_TINTS = [
  { background: "rgba(202,138,4,0.16)", color: "#ca8a04", border: "rgba(202,138,4,0.4)" },
  { background: "rgba(100,116,139,0.16)", color: "#64748b", border: "rgba(100,116,139,0.4)" },
  { background: "rgba(180,83,9,0.16)", color: "#b45309", border: "rgba(180,83,9,0.4)" },
];

function periodLabel(filters: FilterState): string {
  const from = new Date(filters.dateFrom);
  const to = new Date(filters.dateTo);
  const sameMonth = from.getFullYear() === to.getFullYear() && from.getMonth() === to.getMonth();
  if (sameMonth) return to.toLocaleDateString("tr-TR", { month: "long", year: "numeric" });
  const fmt = (d: Date) => d.toLocaleDateString("tr-TR", { day: "numeric", month: "short" });
  return `${fmt(from)} – ${fmt(to)} ${to.getFullYear()}`;
}

function scopeLabel(filters: FilterState): string {
  if (filters.plantIds.length === 1) return "1 Tesis";
  if (filters.plantIds.length > 1) return `${filters.plantIds.length} Tesis`;
  if (filters.factoryIds.length === 1) return "1 Fabrika";
  if (filters.factoryIds.length > 1) return `${filters.factoryIds.length} Fabrika`;
  return "Tüm Tesisler";
}

export function ForemanScoreRow({
  id,
  name,
  score,
  rank,
  color,
  showRankTint,
  onNavigate,
}: {
  id: string;
  name: string;
  score: number;
  rank: number;
  color: string;
  showRankTint: boolean;
  onNavigate: (id: string) => void;
}) {
  const barPct = Math.max(4, Math.min(100, score));
  const tint = showRankTint ? RANK_TINTS[rank - 1] : null;

  return (
    <button
      onClick={() => onNavigate(id)}
      className="group flex w-full items-center gap-2.5 rounded-md px-2 py-1.5 text-left transition-all duration-150 hover:-translate-y-0.5 hover:bg-[var(--page-bg)] hover:shadow-sm"
      style={{ border: "1px solid transparent" }}
    >
      <span
        className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[10px] font-semibold tabular-nums"
        style={
          tint
            ? { background: tint.background, color: tint.color, border: `1px solid ${tint.border}` }
            : { background: "var(--page-bg)", color: "var(--text-muted)", border: "1px solid var(--border)" }
        }
      >
        {rank}
      </span>

      <span className="min-w-0 flex-1">
        <span
          className="block truncate text-[13px] font-medium group-hover:underline"
          style={{ color: "var(--text-primary)" }}
        >
          {name}
        </span>
        <span className="mt-1 block h-1 w-full overflow-hidden rounded-full" style={{ background: "var(--border)" }}>
          <span className="block h-full rounded-full" style={{ width: `${barPct}%`, background: color }} />
        </span>
      </span>

      <span
        className="shrink-0 rounded-full px-2 py-0.5 text-[11px] font-semibold tabular-nums"
        style={{ background: `${color}1a`, color, border: `1px solid ${color}40` }}
      >
        {score.toFixed(1)}
      </span>
    </button>
  );
}

function RankingSection({
  title,
  accent,
  icon: Icon,
  items,
  isLoading,
  highlightRanks,
  onNavigate,
}: {
  title: string;
  accent: string;
  icon: typeof Trophy;
  items: ForemanRankingItem[] | undefined;
  isLoading: boolean;
  highlightRanks: boolean;
  onNavigate: (id: string) => void;
}) {
  return (
    <div className="rounded-lg p-2.5" style={{ background: `${accent}0d`, border: `1px solid ${accent}26` }}>
      <div className="mb-2 flex items-center gap-1.5 px-1">
        <Icon size={13} strokeWidth={2.25} style={{ color: accent }} />
        <p className="text-[11px] font-semibold uppercase tracking-wide" style={{ color: accent }}>
          {title}
        </p>
      </div>
      <div className="flex flex-col gap-0.5">
        {isLoading && <LoadingState />}
        {!isLoading && (!items || items.length === 0) && <EmptyState message="Veri yok" />}
        {items?.map((item, i) => (
          <ForemanScoreRow
            key={item.foreman_id}
            id={item.foreman_id}
            name={item.full_name}
            score={item.total_score}
            rank={i + 1}
            color={item.level.color}
            showRankTint={highlightRanks}
            onNavigate={onNavigate}
          />
        ))}
      </div>
    </div>
  );
}

export function ForemanRankingCard({
  filters,
  topItems,
  topLoading,
  bottomItems,
  bottomLoading,
  onNavigateForeman,
  onViewAll,
}: {
  filters: FilterState;
  topItems: ForemanRankingItem[] | undefined;
  topLoading: boolean;
  bottomItems: ForemanRankingItem[] | undefined;
  bottomLoading: boolean;
  onNavigateForeman: (id: string) => void;
  onViewAll: () => void;
}) {
  return (
    <div className="rounded-lg p-5" style={{ background: "var(--surface)", border: "1px solid var(--border)" }}>
      <div className="mb-4 flex flex-wrap items-start justify-between gap-2">
        <div>
          <h3 className="text-[14px] font-semibold" style={{ color: "var(--text-primary)" }}>
            Formen Performans Sıralaması
          </h3>
          <p className="mt-0.5 text-xs" style={{ color: "var(--text-muted)" }}>
            Seçili dönemin genel KPI puanlarına göre sıralama
          </p>
        </div>
        <span
          className="shrink-0 rounded-full px-2.5 py-1 text-[11px] font-medium"
          style={{ background: "var(--page-bg)", color: "var(--text-secondary)", border: "1px solid var(--border)" }}
        >
          {periodLabel(filters)} • {scopeLabel(filters)}
        </span>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <RankingSection
          title="En Yüksek Performans"
          accent="#16a34a"
          icon={Trophy}
          items={topItems}
          isLoading={topLoading}
          highlightRanks
          onNavigate={onNavigateForeman}
        />
        <RankingSection
          title="Gelişim Alanı"
          accent="#ea580c"
          icon={TrendingDown}
          items={bottomItems}
          isLoading={bottomLoading}
          highlightRanks={false}
          onNavigate={onNavigateForeman}
        />
      </div>

      <button
        onClick={onViewAll}
        className="group mt-4 inline-flex w-full items-center justify-center gap-1.5 rounded-md py-2 text-[13px] font-medium transition-colors hover:bg-[var(--page-bg)]"
        style={{ border: "1px solid var(--border)", color: "var(--accent)" }}
      >
        Tüm formen sıralamasını görüntüle
        <ArrowRight size={14} strokeWidth={2} className="transition-transform duration-150 group-hover:translate-x-0.5" />
      </button>
    </div>
  );
}
