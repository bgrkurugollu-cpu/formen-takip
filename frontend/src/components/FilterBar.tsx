import { useMemo, useState } from "react";
import { ChevronDown, X } from "lucide-react";
import { useFilterOptions } from "../api/hooks";
import { DATE_PRESETS, type FilterState } from "../hooks/useFilters";

interface Props {
  filters: FilterState;
  setFilters: (partial: Partial<FilterState>) => void;
  clearFilters: () => void;
}

const inputClass =
  "rounded-md border px-2.5 py-1.5 text-[13px] transition-colors focus:outline-none focus:ring-2 focus:ring-[var(--accent)]/30";
const inputStyle = { borderColor: "var(--border-strong)", background: "var(--surface)", color: "var(--text-primary)" };

interface Option {
  id: string;
  name: string;
  hint?: string;
}

const SEARCH_THRESHOLD = 10;

function MultiSelect({
  label,
  options,
  selected,
  onChange,
  disabled,
}: {
  label: string;
  options: Option[];
  selected: string[];
  onChange: (ids: string[]) => void;
  disabled?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");

  const toggle = (id: string) => {
    onChange(selected.includes(id) ? selected.filter((x) => x !== id) : [...selected, id]);
  };

  const close = () => {
    setOpen(false);
    setQuery("");
  };

  const showSearch = options.length > SEARCH_THRESHOLD;
  const visibleOptions = useMemo(() => {
    const q = query.trim().toLocaleLowerCase("tr");
    if (!q) return options;
    return options.filter(
      (o) =>
        o.name.toLocaleLowerCase("tr").includes(q) || (o.hint ?? "").toLocaleLowerCase("tr").includes(q)
    );
  }, [options, query]);

  return (
    <div className="relative">
      <button
        type="button"
        disabled={disabled}
        onClick={() => (open ? close() : setOpen(true))}
        className={`flex min-w-32 items-center justify-between gap-2 ${inputClass} disabled:opacity-40`}
        style={inputStyle}
      >
        <span>
          {label}
          {selected.length > 0 && <span className="ml-1 font-medium" style={{ color: "var(--accent)" }}>({selected.length})</span>}
        </span>
        <ChevronDown size={13} strokeWidth={2} style={{ color: "var(--text-muted)" }} />
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={close} />
          <div
            className="absolute z-20 mt-1 w-72 rounded-md shadow-lg"
            style={{ background: "var(--surface)", border: "1px solid var(--border)" }}
          >
            {showSearch && (
              <div className="p-1.5" style={{ borderBottom: "1px solid var(--border)" }}>
                <input
                  autoFocus
                  type="search"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Ara..."
                  className="w-full rounded border px-2 py-1 text-[13px] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]/30"
                  style={inputStyle}
                />
              </div>
            )}
            <div className="max-h-64 overflow-auto p-1">
              {visibleOptions.length === 0 && (
                <div className="p-2 text-xs" style={{ color: "var(--text-muted)" }}>
                  {options.length === 0 ? "Seçenek yok" : "Eşleşen sonuç yok"}
                </div>
              )}
              {visibleOptions.map((opt) => (
                <label
                  key={opt.id}
                  className="flex cursor-pointer items-start gap-2 rounded px-2 py-1.5 text-[13px] hover:bg-[var(--page-bg)]"
                  style={{ color: "var(--text-primary)" }}
                >
                  <input
                    type="checkbox"
                    className="mt-0.5 shrink-0"
                    checked={selected.includes(opt.id)}
                    onChange={() => toggle(opt.id)}
                  />
                  <span className="min-w-0">
                    <span className="block truncate">{opt.name}</span>
                    {opt.hint && (
                      <span className="block truncate text-xs" style={{ color: "var(--text-muted)" }}>
                        {opt.hint}
                      </span>
                    )}
                  </span>
                </label>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

export function FilterBar({ filters, setFilters, clearFilters }: Props) {
  const { data: options, isLoading } = useFilterOptions(
    filters.plantIds.join(",") || undefined,
    filters.factoryIds.join(",") || undefined
  );

  const activeCount =
    filters.plantIds.length + filters.factoryIds.length + filters.chiefIds.length + filters.shiftIds.length + filters.kpiIds.length;

  const plantNameById = useMemo(
    () => new Map((options?.plants ?? []).map((p) => [p.id, p.name])),
    [options]
  );
  const chiefOptions = useMemo(
    () => (options?.chiefs ?? []).map((c) => ({ id: c.id, name: c.name, hint: plantNameById.get(c.plant_id) })),
    [options, plantNameById]
  );

  const plantIdByChief = useMemo(
    () => new Map((options?.chiefs ?? []).map((c) => [c.id, c.plant_id])),
    [options]
  );
  const factoryIdByPlant = useMemo(
    () => new Map((options?.plants ?? []).map((p) => [p.id, p.factory_id])),
    [options]
  );

  const handleFactoryChange = (ids: string[]) => {
    const allowed = new Set(ids);
    const plantStillValid = (plantId: string) =>
      allowed.size === 0 || allowed.has(factoryIdByPlant.get(plantId) ?? "");
    setFilters({
      factoryIds: ids,
      plantIds: filters.plantIds.filter(plantStillValid),
      chiefIds: filters.chiefIds.filter((chiefId) => {
        const plantId = plantIdByChief.get(chiefId);
        return plantId ? plantStillValid(plantId) : false;
      }),
    });
  };

  const handlePlantChange = (ids: string[]) => {
    const allowed = new Set(ids);
    setFilters({
      plantIds: ids,
      chiefIds:
        allowed.size === 0
          ? filters.chiefIds
          : filters.chiefIds.filter((chiefId) => allowed.has(plantIdByChief.get(chiefId) ?? "")),
    });
  };

  return (
    <div
      className="flex flex-wrap items-center gap-2 rounded-lg p-3"
      style={{ background: "var(--surface)", border: "1px solid var(--border)" }}
    >
      <select
        className={inputClass}
        style={inputStyle}
        onChange={(e) => {
          const preset = DATE_PRESETS.find((p) => p.label === e.target.value);
          if (preset) {
            const [from, to] = preset.getRange();
            setFilters({ dateFrom: from, dateTo: to });
          }
        }}
        defaultValue=""
      >
        <option value="" disabled>
          Hazır tarih aralığı
        </option>
        {DATE_PRESETS.map((p) => (
          <option key={p.label} value={p.label}>
            {p.label}
          </option>
        ))}
      </select>

      <input
        type="date"
        value={filters.dateFrom}
        max={filters.dateTo}
        onChange={(e) => setFilters({ dateFrom: e.target.value })}
        className={inputClass}
        style={inputStyle}
      />
      <span style={{ color: "var(--text-muted)" }}>–</span>
      <input
        type="date"
        value={filters.dateTo}
        min={filters.dateFrom}
        max={new Date().toISOString().slice(0, 10)}
        onChange={(e) => setFilters({ dateTo: e.target.value })}
        className={inputClass}
        style={inputStyle}
      />

      <div className="mx-1 h-6 w-px" style={{ background: "var(--border)" }} />

      <button
        type="button"
        disabled
        title="Sistem şu an yalnızca Karaman lokasyonunu kapsıyor"
        className={`flex min-w-28 items-center justify-between gap-2 ${inputClass} disabled:opacity-70`}
        style={inputStyle}
      >
        <span>Lokasyon: Karaman</span>
      </button>

      <MultiSelect
        label="Fabrika"
        options={options?.factories ?? []}
        selected={filters.factoryIds}
        onChange={handleFactoryChange}
        disabled={isLoading}
      />
      <MultiSelect
        label="Tesis"
        options={options?.plants ?? []}
        selected={filters.plantIds}
        onChange={handlePlantChange}
        disabled={isLoading}
      />
      <MultiSelect
        label="Şef"
        options={chiefOptions}
        selected={filters.chiefIds}
        onChange={(ids) => setFilters({ chiefIds: ids })}
        disabled={isLoading}
      />
      <MultiSelect
        label="Vardiya"
        options={options?.shifts ?? []}
        selected={filters.shiftIds}
        onChange={(ids) => setFilters({ shiftIds: ids })}
        disabled={isLoading}
      />
      <MultiSelect
        label="KPI"
        options={options?.kpis ?? []}
        selected={filters.kpiIds}
        onChange={(ids) => setFilters({ kpiIds: ids })}
        disabled={isLoading}
      />

      {activeCount > 0 && (
        <button
          onClick={clearFilters}
          className="ml-auto flex items-center gap-1 rounded-md px-2.5 py-1.5 text-xs font-medium hover:bg-[var(--page-bg)]"
          style={{ color: "var(--accent)" }}
        >
          <X size={13} strokeWidth={2} />
          Filtreleri temizle ({activeCount})
        </button>
      )}
    </div>
  );
}
