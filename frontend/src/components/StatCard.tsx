import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import type { LucideIcon } from "lucide-react";

export function StatCard({
  label,
  value,
  sub,
  to,
  icon: Icon,
}: {
  label: string;
  value: ReactNode;
  sub?: ReactNode;
  to?: string;
  icon?: LucideIcon;
}) {
  const content = (
    <div
      className="h-full rounded-lg p-4 transition-colors"
      style={{
        background: "var(--surface)",
        border: "1px solid var(--border)",
        borderTop: "2px solid var(--accent)",
      }}
    >
      <div className="flex items-center justify-between">
        <span className="text-[11px] font-semibold uppercase tracking-wide" style={{ color: "var(--text-muted)" }}>
          {label}
        </span>
        {Icon && <Icon size={15} strokeWidth={1.75} style={{ color: "var(--text-muted)" }} />}
      </div>
      <div className="mt-1.5 text-xl font-semibold leading-tight" style={{ color: "var(--text-primary)" }}>
        {value}
      </div>
      {sub && (
        <div className="mt-1 text-xs" style={{ color: "var(--text-muted)" }}>
          {sub}
        </div>
      )}
    </div>
  );
  return to ? (
    <Link to={to} className="block h-full hover:[&>div]:border-[var(--border-strong)]">
      {content}
    </Link>
  ) : (
    content
  );
}
