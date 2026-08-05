import {
  Award, Cpu, Gauge, Lightbulb, Puzzle, Shield, Sparkles, Timer, TrendingDown, Wallet, Zap,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { ContributionStatus, ContributionWorkType, FinancialGainStatus, ImpactLevel } from "../api/types";
import { categoricalColor } from "./chartColors";

export const WORK_TYPE_LABELS: Record<ContributionWorkType, string> = {
  smed: "SMED",
  kaizen: "Kaizen",
  problem_solving: "Problem Çözme",
  cost_reduction: "Maliyet Azaltma",
  time_saving: "Zaman Kazancı",
  quality_improvement: "Kalite İyileştirme",
  safety_improvement: "İş Güvenliği İyileştirmesi",
  energy_resource_saving: "Enerji veya Kaynak Tasarrufu",
  production_efficiency: "Üretim Verimliliği",
  digitalization: "Dijitalleşme",
  other: "Diğer",
};

const WORK_TYPE_ICONS: Record<ContributionWorkType, LucideIcon> = {
  smed: Timer,
  kaizen: TrendingDown,
  problem_solving: Puzzle,
  cost_reduction: Wallet,
  time_saving: Timer,
  quality_improvement: Award,
  safety_improvement: Shield,
  energy_resource_saving: Zap,
  production_efficiency: Gauge,
  digitalization: Cpu,
  other: Lightbulb,
};

const WORK_TYPE_COLOR_INDEX: Record<ContributionWorkType, number> = {
  smed: 0,
  kaizen: 2,
  problem_solving: 6,
  cost_reduction: 3,
  time_saving: 0,
  quality_improvement: 5,
  safety_improvement: 7,
  energy_resource_saving: 3,
  production_efficiency: 1,
  digitalization: 4,
  other: 6,
};

export function workTypeIcon(type: ContributionWorkType | null): LucideIcon {
  return type ? WORK_TYPE_ICONS[type] : Sparkles;
}

export function workTypeLabel(type: ContributionWorkType | null): string {
  return type ? WORK_TYPE_LABELS[type] : "Belirtilmedi";
}

export function workTypeColor(type: ContributionWorkType | null, isDark: boolean): string {
  return categoricalColor(type ? WORK_TYPE_COLOR_INDEX[type] : 6, isDark);
}

export const STATUS_LABELS: Record<ContributionStatus, string> = {
  draft: "Taslak",
  published: "Yayımlandı",
};

export const IMPACT_LEVEL_LABELS: Record<ImpactLevel, string> = {
  low: "Düşük Etki",
  medium: "Orta Etki",
  high: "Yüksek Etki",
};

export const FINANCIAL_STATUS_FILTER_LABELS: Record<FinancialGainStatus, string> = {
  yes: "Maddi kazanç var",
  no: "Maddi kazanç yok",
  not_calculated: "Henüz hesaplanmadı",
};
