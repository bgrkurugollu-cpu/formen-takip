export function formatDateTR(iso: string): string {
  return new Date(iso).toLocaleDateString("tr-TR", { day: "numeric", month: "long", year: "numeric" });
}

export function formatDateRangeTR(startIso: string, endIso: string): string {
  const from = new Date(startIso);
  const to = new Date(endIso);
  const sameMonth = from.getFullYear() === to.getFullYear() && from.getMonth() === to.getMonth();
  const fmtShort = (d: Date) => d.toLocaleDateString("tr-TR", { day: "numeric", month: "short", year: "numeric" });
  if (sameMonth) {
    return `${from.getDate()}–${to.toLocaleDateString("tr-TR", { day: "numeric", month: "long", year: "numeric" })}`;
  }
  return `${fmtShort(from)} – ${fmtShort(to)}`;
}
