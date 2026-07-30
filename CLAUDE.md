# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

Everything runs through Docker Compose from the repo root:

```bash
docker compose up --build -d          # build + start (postgres, backend, frontend)
docker compose up --build -d backend  # rebuild just one service
docker compose logs backend --tail 50 # inspect errors
```

**Docker images bake the source at build time — there are no bind mounts.** Editing a file has no effect on a running container until you rebuild that service. Almost every "my fix didn't work" symptom in this repo traces back to a stale image.

Database seeding (containers must be up; migrations run automatically on backend start):

```bash
docker compose exec backend python -m app.cli seed --seed 42
docker compose exec backend python -m app.cli create-admin \
  --email genel.mudur@formen-demo.com --password "Demo!2026" --full-name "Demo Genel Müdür"
docker compose exec backend python -m app.cli backfill-data-quality-issues
docker compose exec backend python -m app.cli regenerate-personnel-identities
```

`regenerate-personnel-identities` rewrites chief/foreman names and employee numbers **in place**, leaving the ~1.3M performance rows untouched (they reference personnel by UUID). Use it to retrofit existing data after changing the name pools instead of paying for a full reseed.

`seed` refuses to run when reference data already exists (use `--force`), and it does **not** truncate. To regenerate from scratch you must clear the tables first, including the reference tables the seeder recreates with fixed codes:

```bash
docker compose exec -T postgres psql -U formen -d formen_takip -c \
  "TRUNCATE plants, foremen, kpi_targets, integration_runs, shifts, kpis, performance_level_rules CASCADE;"
```

Seeding produces ~1.3M performance records and takes several minutes — run it in the background.

Backend tests (run from `backend/`, against the **live Dockerized Postgres**):

```bash
.venv/Scripts/python.exe -m pytest -q                      # full suite
.venv/Scripts/python.exe -m pytest tests/unit -q           # unit only (no DB)
.venv/Scripts/python.exe -m pytest tests/integration/test_reports.py -q
.venv/Scripts/python.exe -m pytest tests/unit/test_kpi_engine.py::TestX::test_y -q
```

Integration tests expect a migrated, seeded database — they hit the real DB via `SessionLocal()`, there is no schema fixture. `backend/.env` sets `DATABASE_URL` to port **5433** (the host port Compose maps Postgres to); the default in `app/core/config.py` is 5432 and will not work from the host.

Frontend (from `frontend/`):

```bash
npx tsc --noEmit    # typecheck
npm run build       # tsc -b && vite build
npm run lint        # oxlint
npm run dev         # Vite on :5173, proxies /api to 127.0.0.1:8000
```

Playwright smoke scripts live in `frontend/scripts/*.mjs` and must be run from `frontend/` (that's where `playwright` resolves). They log in against the running stack and capture screenshots plus console errors.

Access: frontend http://localhost:8080, API docs http://localhost:8000/docs, login `genel.mudur@formen-demo.com` / `Demo!2026`.

## Architecture

FastAPI + SQLAlchemy 2.0 + Alembic + PostgreSQL 16 backend; React + TypeScript + Vite + TanStack Query + Tailwind v4 + Recharts frontend. Senior-management-only decision support tool — foremen and plant managers are never users.

### Organizational hierarchy

**Karaman (single location) → Factory (K1 = plants 1–27, K2 = plants 28–50) → Plant → Chief (Şef) → Foreman.**

This shape is a fixed business rule encoded in `app/services/synthetic/reference_data.py` (`FACTORY_SEED`), not a configurable parameter. Plants are named `"{n}. Tesis"` and carry a unique `sequence_number` 1–50 — **always order plants by `sequence_number`, never by `name`**, or "10. Tesis" sorts before "2. Tesis".

`Foreman` carries no org FKs. All placement lives in `ForemanAssignment` (SCD2-style `start_date`/`end_date` ranges): a foreman's chief and plant are fixed for their whole tenure; only shift changes mid-period. A composite FK `(chief_id, plant_id) → chiefs(id, plant_id)` makes chief/plant mismatch a DB-level impossibility.

Personnel identities must stay unique and self-describing. Names are drawn **without replacement** from the shuffled cartesian product of `FIRST_NAMES` × `LAST_NAMES` (80 × 70 = 5600 combinations for ~1000 people), so no two chiefs or foremen ever share a full name — `rng.choice()` per field would guarantee collisions by the pigeonhole principle. Employee numbers encode the plant (`SCL-29-004`, `SEF-29-01`) and are zero-padded so lexicographic sort matches numeric order.

`README.md` still describes the pre-restructuring model (Turkish regions/cities, Department, ProductionLine, `--plants` flag). Those concepts were removed entirely — trust the code, not the README.

### Data flow: provider → ingestion → scores

Performance data is **read-only to the whole API surface**. Nothing outside the ingestion pipeline may create, update, or delete `performance_records` / `performance_scores`.

`PerformanceDataProvider.fetch()` (`app/services/providers/base.py`) yields `RawPerformanceRecord`s keyed by *codes* (`plant_code`, `chief_employee_number`, `shift_code`, `foreman_employee_number`, `kpi_code`) — never internal UUIDs. `run_ingestion()` resolves those codes to FKs via `_Lookups`, computes scores, and batch-inserts. Swapping `SyntheticDataProvider` for a future `SAPDataProvider` requires no changes anywhere else.

Ingestion is idempotent by two unique constraints: `uq_perf_record_source` (source_system, source_record_id) and `uq_perf_record_natural_key` (foreman, kpi, chief, shift, date). Conflicts are silently skipped via `ON CONFLICT DO NOTHING ... RETURNING`, and skipped rows are recorded as DUPLICATE data-quality issues.

`BATCH_SIZE = 1000` in `ingestion.py` is not arbitrary — psycopg caps a statement at 65535 bound parameters, and these rows have ~20 columns.

### KPI scoring

`app/services/kpi_engine.py` implements 5 calculation types (higher/lower-is-better, range target, direct score, proportional penalty), clamps to per-KPI min/max, and weights each contribution.

Aggregate score everywhere is `SUM(weighted_contribution) / SUM(kpi_weight) * 100` (`app/services/analytics.py`), which auto-renormalizes when KPIs are missing; `is_reliable` flags rows whose covered weight falls short of the active total.

Target resolution (`app/services/target_resolver.py`) is a pure function with precedence **FOREMAN > CHIEF > PLANT > COMPANY**. In practice the seeder only ever creates COMPANY-scoped targets, so every resolution today falls through to that tier — the narrower tiers are live capability, not live data.

### Filters

One `Filters` dataclass (`app/schemas/common.py`: dates, `plant_ids`, `factory_ids`, `chief_ids`, `shift_ids`, `kpi_ids`) threads through every analytics query via `_apply_filters`. `factory_ids` resolves through a `Plant.factory_id` subquery because `PerformanceRecord` deliberately stores no `factory_id`.

The frontend mirrors this exactly: `useFilters` keeps state in URL search params → `asQueryParams` → `common_filters`. Filter bar order is **Lokasyon (static "Karaman") → Fabrika → Tesis → Şef → Vardiya → KPI**, cascading via `/meta/filters` (picking a factory clears plants and chiefs; picking a plant clears chiefs). Foreman-level filtering is intentionally *not* a global filter chip — it happens by drilling into the Formenler list.

`analytics._grouped_scores(db, filters, group_col, total_weight)` is the shared aggregation helper; `plant_scores` / `foreman_scores` / `chief_scores` / `shift_scores` are one-liners over it. Add new rollups the same way rather than writing bespoke queries.

### Frontend conventions

UI language is Turkish. The design is deliberately corporate: **no emoji anywhere** — icons come from `lucide-react`.

Theming is entirely CSS custom properties defined per `:root[data-theme="dark"|"light"]` in `index.css`, toggled by `ThemeContext` (default dark, persisted to localStorage). Component styles reference `var(--accent)`, `var(--surface)`, etc. — this is why theme changes are token edits, not component sweeps. Light theme's accent is `#e90128`, applied in a controlled way (active nav item, buttons, KPI card top rules, chart primary series, highlights) over white/light-gray surfaces.

Recharts needs special handling:
- SVG color props must be literal JS values, not `var(...)`. Use the theme-aware helpers in `lib/chartColors.ts` (`resolveChartInk(isDark)`, `accentLineColor(isDark)`, `categoricalColor(i, isDark)`) — always pass the `isDark` argument.
- `<Tooltip contentStyle>` does **not** cascade to its label/item text. Every tooltip needs explicit `labelStyle` and `itemStyle` or the text renders black on a dark background.

Shared style constants live in `lib/tableStyles.ts` and `lib/formStyles.ts`; reuse them instead of re-deriving table/form styling.

### Migrations

`alembic upgrade head` runs automatically at backend container start. The Karaman restructuring migration (`6ad63dbc115b`) is intentionally destructive — it truncates org and performance data and raises `NotImplementedError` on downgrade. Postgres enums cannot drop values, so changing one requires the rename → create → `ALTER COLUMN ... USING` → drop-old sequence used there.
