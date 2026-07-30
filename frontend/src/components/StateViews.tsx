import { AlertTriangle, Inbox, Loader2 } from "lucide-react";

export function LoadingState({ label = "Yükleniyor..." }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-2 py-12 text-[13px]" style={{ color: "var(--text-muted)" }}>
      <Loader2 size={15} strokeWidth={2} className="animate-spin" style={{ color: "var(--accent)" }} />
      {label}
    </div>
  );
}

export function ErrorState({ message = "Veri yüklenirken bir hata oluştu." }: { message?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-12 text-center text-[13px] text-red-600">
      <AlertTriangle size={20} strokeWidth={1.5} />
      {message}
    </div>
  );
}

export function EmptyState({ message = "Seçilen filtrelerle eşleşen veri bulunamadı." }: { message?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-12 text-center text-[13px]" style={{ color: "var(--text-muted)" }}>
      <Inbox size={20} strokeWidth={1.5} />
      {message}
    </div>
  );
}

export function Card({ title, children, action }: { title?: string; children: React.ReactNode; action?: React.ReactNode }) {
  return (
    <div className="rounded-lg p-5" style={{ background: "var(--surface)", border: "1px solid var(--border)" }}>
      {title && (
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-[13px] font-semibold uppercase tracking-wide" style={{ color: "var(--text-secondary)" }}>
            {title}
          </h3>
          {action}
        </div>
      )}
      {children}
    </div>
  );
}
