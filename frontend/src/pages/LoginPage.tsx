import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { AlertCircle, Moon, Sun } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { useTheme } from "../context/ThemeContext";

export function LoginPage() {
  const { login } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();
  const [email, setEmail] = useState("genel.mudur@formen-demo.com");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login(email, password);
      navigate("/", { replace: true });
    } catch (err: any) {
      if (err?.response?.status === 423) {
        setError("Hesap çok sayıda başarısız denemeden dolayı geçici olarak kilitlendi.");
      } else if (err?.response?.status === 401) {
        setError("E-posta veya parola hatalı.");
      } else {
        setError("Giriş yapılamadı. Lütfen tekrar deneyin.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen" style={{ background: "var(--page-bg)" }}>
      <button
        onClick={toggleTheme}
        title={theme === "dark" ? "Açık temaya geç" : "Koyu temaya geç"}
        aria-label={theme === "dark" ? "Açık temaya geç" : "Koyu temaya geç"}
        className="fixed right-6 top-6 z-10 flex items-center justify-center rounded-md border p-2 transition-colors hover:bg-[var(--surface-raised)]"
        style={{ borderColor: "var(--border-strong)", color: "var(--text-secondary)", background: "var(--surface)" }}
      >
        {theme === "dark" ? <Sun size={16} strokeWidth={1.75} /> : <Moon size={16} strokeWidth={1.75} />}
      </button>

      <div
        className="hidden w-[46%] flex-col justify-between p-12 lg:flex"
        style={{ background: "var(--sidebar-bg)", borderRight: "1px solid var(--sidebar-border)" }}
      >
        <div />
        <div className="flex flex-col items-center text-center">
          <img src="/logo.png" alt="Formen Takip" className="w-full max-w-md" />
          <h1 className="mt-6 max-w-md text-2xl font-semibold leading-snug" style={{ color: "var(--sidebar-heading)" }}>
            Üretim Performans Yönetim Sistemi
          </h1>
          <p className="mt-3 max-w-sm text-sm" style={{ color: "var(--sidebar-text)" }}>
            50 tesis, 2 vardiya ve 5 temel performans göstergesi üzerinden formen
            performansını tek merkezden izleyin.
          </p>
        </div>
        <p className="text-xs" style={{ color: "var(--sidebar-muted)" }}>Yalnızca yetkilendirilmiş üst yönetim erişimine açıktır.</p>
      </div>

      <div className="flex flex-1 items-center justify-center px-6">
        <div className="w-full max-w-sm">
          <div className="mb-8 flex justify-center lg:hidden">
            <img src="/logo.png" alt="Formen Takip" className="h-auto w-40" />
          </div>

          <div className="rounded-lg p-6" style={{ background: "var(--surface)", border: "1px solid var(--border)" }}>
            <h2 className="text-lg font-semibold" style={{ color: "var(--text-primary)" }}>Sisteme Giriş</h2>
            <p className="mt-1 text-[13px]" style={{ color: "var(--text-muted)" }}>Üst yönetim hesabınızla oturum açın.</p>

            <form onSubmit={handleSubmit} className="mt-6 flex flex-col gap-4">
              <div>
                <label className="mb-1.5 block text-xs font-medium" style={{ color: "var(--text-secondary)" }}>Kurumsal E-posta</label>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--accent)]/30"
                  style={{ border: "1px solid var(--border-strong)", background: "var(--surface-raised)", color: "var(--text-primary)" }}
                />
              </div>
              <div>
                <label className="mb-1.5 block text-xs font-medium" style={{ color: "var(--text-secondary)" }}>Parola</label>
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--accent)]/30"
                  style={{ border: "1px solid var(--border-strong)", background: "var(--surface-raised)", color: "var(--text-primary)" }}
                />
              </div>

              {error && (
                <p className="flex items-center gap-1.5 text-xs font-medium" style={{ color: "var(--accent)" }}>
                  <AlertCircle size={13} strokeWidth={2} />
                  {error}
                </p>
              )}

              <button
                type="submit"
                disabled={loading}
                className="mt-1 rounded-md py-2 text-sm font-medium text-white transition-colors disabled:opacity-60"
                style={{ background: "var(--accent)" }}
                onMouseEnter={(e) => (e.currentTarget.style.background = "var(--accent-hover)")}
                onMouseLeave={(e) => (e.currentTarget.style.background = "var(--accent)")}
              >
                {loading ? "Giriş yapılıyor..." : "Giriş Yap"}
              </button>
            </form>
          </div>

          <div className="mt-4 rounded-md p-3 text-xs" style={{ background: "var(--surface-raised)", border: "1px solid var(--border)", color: "var(--text-muted)" }}>
            Demo hesabı: <strong style={{ color: "var(--text-secondary)" }}>genel.mudur@formen-demo.com</strong> / <strong style={{ color: "var(--text-secondary)" }}>Demo!2026</strong>
          </div>
        </div>
      </div>
    </div>
  );
}
