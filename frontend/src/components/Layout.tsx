import type { ReactNode } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import {
  LayoutGrid, Factory, Users, HardHat, Target, ClipboardList, FileText,
  FlaskConical, RefreshCw, ShieldCheck, LogOut, Moon, Sun, Sparkles, SearchCheck,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { useTheme } from "../context/ThemeContext";

const NAV_ITEMS = [
  { to: "/", label: "Genel Bakış", icon: LayoutGrid },
  { to: "/plants", label: "Tesisler", icon: Factory },
  { to: "/groups", label: "Gruplar", icon: Users },
  { to: "/foremen", label: "Formenler", icon: HardHat },
  { to: "/kpis", label: "KPI Analizi", icon: Target },
  { to: "/action-plans", label: "Aksiyon Planları", icon: ClipboardList },
  { to: "/improvement-works", label: "Katkılar", icon: Sparkles },
  { to: "/anomalies", label: "Tespitler", icon: SearchCheck },
  { to: "/reports", label: "Raporlar", icon: FileText },
  { to: "/data-quality", label: "Veri Kalitesi", icon: FlaskConical },
  { to: "/integration-status", label: "Entegrasyon Durumu", icon: RefreshCw },
  { to: "/audit-log", label: "Denetim Kayıtları", icon: ShieldCheck },
];

export function Layout({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();

  return (
    <div className="flex min-h-screen bg-[var(--page-bg)]">
      <aside
        className="hidden w-60 shrink-0 flex-col md:flex"
        style={{ background: "var(--sidebar-bg)", borderRight: "1px solid var(--sidebar-border)" }}
      >
        <div className="px-5 py-4" style={{ borderBottom: "1px solid var(--sidebar-border)" }}>
          <img src="/logo.png" alt="Formen Takip" className="h-auto w-[150px]" />
          <p className="mt-1 text-xs" style={{ color: "var(--sidebar-subtext)" }}>Üst Yönetim Paneli</p>
        </div>
        <nav className="flex flex-1 flex-col gap-0.5 overflow-y-auto p-3">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === "/"}
                className={({ isActive }) =>
                  `flex items-center gap-2.5 rounded-md px-3 py-2 text-[13px] font-medium transition-colors ${
                    isActive ? "" : "text-[var(--sidebar-text)] hover:text-[var(--sidebar-text-hover)]"
                  }`
                }
                style={({ isActive }) =>
                  isActive ? { background: "var(--sidebar-active-bg)", color: "var(--sidebar-text-active)" } : undefined
                }
              >
                <Icon size={16} strokeWidth={1.75} className="shrink-0" />
                {item.label}
              </NavLink>
            );
          })}
        </nav>
      </aside>

      <div className="flex min-h-screen flex-1 flex-col">
        <header
          className="flex items-center justify-between bg-[var(--surface)] px-6 py-3"
          style={{ borderBottom: "1px solid var(--border)" }}
        >
          <div className="flex items-center gap-2 text-xs" style={{ color: "var(--text-muted)" }}>
            <span
              className="inline-flex items-center rounded border px-2 py-0.5 font-medium uppercase tracking-wide"
              style={{ borderColor: "var(--border-strong)", color: "var(--text-secondary)" }}
            >
              Sentetik Veri Kaynağı — Demo
            </span>
            <span>SAP entegrasyonu bu ortamda aktif değildir.</span>
          </div>
          <div className="flex items-center gap-4">
            <button
              onClick={toggleTheme}
              title={theme === "dark" ? "Açık temaya geç" : "Koyu temaya geç"}
              aria-label={theme === "dark" ? "Açık temaya geç" : "Koyu temaya geç"}
              className="flex items-center justify-center rounded-md border p-1.5 transition-colors hover:bg-[var(--page-bg)]"
              style={{ borderColor: "var(--border-strong)", color: "var(--text-secondary)" }}
            >
              {theme === "dark" ? <Sun size={15} strokeWidth={1.75} /> : <Moon size={15} strokeWidth={1.75} />}
            </button>
            <div className="text-right text-xs leading-tight">
              <div className="font-medium" style={{ color: "var(--text-primary)" }}>{user?.full_name}</div>
              <div style={{ color: "var(--text-muted)" }}>{user?.title}</div>
            </div>
            <button
              onClick={() => {
                logout();
                navigate("/login");
              }}
              className="flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-xs font-medium transition-colors hover:bg-[var(--page-bg)]"
              style={{ borderColor: "var(--border-strong)", color: "var(--text-secondary)" }}
            >
              <LogOut size={14} strokeWidth={1.75} />
              Çıkış Yap
            </button>
          </div>
        </header>
        <main className="flex-1 overflow-x-hidden p-6">{children}</main>
      </div>
    </div>
  );
}
