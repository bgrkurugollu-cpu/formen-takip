import { useEffect, useState, type ReactNode } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import {
  LayoutGrid, Factory, Users, HardHat, Target, FileText,
  LogOut, Moon, Sun, Sparkles, SearchCheck, Repeat2,
  Menu, X,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { useTheme } from "../context/ThemeContext";

const NAV_ITEMS = [
  { to: "/", label: "Genel Bakış", icon: LayoutGrid },
  { to: "/plants", label: "Tesisler", icon: Factory },
  { to: "/groups", label: "Gruplar", icon: Users },
  { to: "/foremen", label: "Formenler", icon: HardHat },
  { to: "/kpis", label: "KPI Analizi", icon: Target },
  { to: "/improvement-works", label: "Katkılar", icon: Sparkles },
  { to: "/anomalies", label: "Tespitler", icon: SearchCheck },
  { to: "/shift-analysis", label: "Vardiya Analizi", icon: Repeat2 },
  { to: "/reports", label: "Raporlar", icon: FileText },
];

function NavLinks({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <nav className="flex flex-1 flex-col gap-0.5 overflow-y-auto p-3">
      {NAV_ITEMS.map((item) => {
        const Icon = item.icon;
        return (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === "/"}
            onClick={onNavigate}
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
  );
}

export function Layout({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  useEffect(() => {
    if (!mobileNavOpen) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") setMobileNavOpen(false);
    };
    document.addEventListener("keydown", onKeyDown);
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = previousOverflow;
    };
  }, [mobileNavOpen]);

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
        <NavLinks />
      </aside>

      {mobileNavOpen && (
        <div className="fixed inset-0 z-40 md:hidden">
          <div
            className="absolute inset-0 bg-black/50"
            onClick={() => setMobileNavOpen(false)}
            aria-hidden="true"
          />
          <aside
            className="absolute inset-y-0 left-0 flex w-64 flex-col shadow-xl"
            style={{ background: "var(--sidebar-bg)", borderRight: "1px solid var(--sidebar-border)" }}
          >
            <div
              className="flex items-center justify-between px-5 py-4"
              style={{ borderBottom: "1px solid var(--sidebar-border)" }}
            >
              <img src="/logo.png" alt="Formen Takip" className="h-auto w-[150px]" />
              <button
                onClick={() => setMobileNavOpen(false)}
                aria-label="Menüyü kapat"
                className="flex items-center justify-center rounded-md p-1.5 transition-colors hover:bg-[var(--sidebar-active-bg)]"
                style={{ color: "var(--sidebar-text)" }}
              >
                <X size={18} strokeWidth={1.75} />
              </button>
            </div>
            <NavLinks onNavigate={() => setMobileNavOpen(false)} />
          </aside>
        </div>
      )}

      <div className="flex min-h-screen flex-1 flex-col">
        <header
          className="flex items-center justify-between bg-[var(--surface)] px-6 py-3"
          style={{ borderBottom: "1px solid var(--border)" }}
        >
          <div className="flex items-center gap-3">
            <button
              onClick={() => setMobileNavOpen(true)}
              aria-label="Menüyü aç"
              className="flex items-center justify-center rounded-md border p-1.5 transition-colors hover:bg-[var(--page-bg)] md:hidden"
              style={{ borderColor: "var(--border-strong)", color: "var(--text-secondary)" }}
            >
              <Menu size={18} strokeWidth={1.75} />
            </button>
            <div className="flex items-center gap-2 text-xs" style={{ color: "var(--text-muted)" }}>
              <span
                className="inline-flex items-center rounded border px-2 py-0.5 font-medium uppercase tracking-wide"
                style={{ borderColor: "var(--border-strong)", color: "var(--text-secondary)" }}
              >
                Sentetik Veri Kaynağı — Demo
              </span>
              <span>SAP entegrasyonu bu ortamda aktif değildir.</span>
            </div>
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
