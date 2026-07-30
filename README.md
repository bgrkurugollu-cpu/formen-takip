# Formen Performans Takip Sistemi

Karaman'daki üretim tesislerinde formen (vardiya amiri) performansını KPI bazlı
izleyen, **üst yönetime yönelik salt-okunur karar destek** uygulaması. Foremen
ve tesis şefleri sistemin kullanıcısı değildir; veri girişi yalnızca ingestion
pipeline'ı (bugün sentetik veri üreticisi, ileride SAP) üzerinden gerçekleşir.

## İçindekiler

- [Mimari](#mimari)
- [Organizasyon Hiyerarşisi](#organizasyon-hiyerarşisi)
- [Veri Akışı: Sağlayıcı → Ingestion → Skor](#veri-akışı-sağlayıcı--ingestion--skor)
- [KPI Hesaplama Motoru](#kpi-hesaplama-motoru)
- [Backend API](#backend-api)
- [Frontend](#frontend)
- [Veritabanı Şeması](#veritabanı-şeması)
- [Kurulum (Docker)](#kurulum-docker)
- [Yerel Geliştirme (Docker'sız)](#yerel-geliştirme-dockersız)
- [Testler](#testler)
- [Depoyu Klonladıktan Sonra](#depoyu-klonladıktan-sonra)
- [Ortam Değişkenleri](#ortam-değişkenleri)
- [Bilinen Sınırlamalar / Kapsam Dışı](#bilinen-sınırlamalar--kapsam-dışı)

## Mimari

| Katman | Teknoloji |
|---|---|
| Backend | FastAPI (0.115) · SQLAlchemy 2.0 (`Mapped`/`mapped_column`) · Alembic · Pydantic v2 · Python 3.11 |
| Veritabanı | PostgreSQL 16 |
| Kimlik doğrulama | JWT (access + refresh, `python-jose`), bcrypt parola hash'i |
| Raporlama | `openpyxl` (XLSX), `reportlab` (PDF), `csv` (stdlib) |
| Frontend | React 19 · TypeScript · Vite 8 · TanStack Query v5 · React Router v7 · Tailwind CSS v4 · Recharts 3 |
| Dağıtım | Docker Compose: `postgres` + `backend` (Uvicorn) + `frontend` (statik build, Nginx) |

Servisler arasında bind mount **yoktur** — imajlar build anında kaynağı içine
gömer. Bir dosyayı değiştirmek, ilgili servisi yeniden build etmeden
konteynerde hiçbir etki yaratmaz (bkz. [CLAUDE.md](CLAUDE.md)).

```
frontend (Nginx :80, host :8080)
   │  /api/* → proxy
   ▼
backend (Uvicorn :8000)
   │  SQLAlchemy
   ▼
postgres:16 (host :5433 → container :5432)
```

## Organizasyon Hiyerarşisi

**Karaman (tek lokasyon) → Fabrika (K1 = 1–27. tesisler, K2 = 28–50. tesisler) → Tesis → Şef → Formen.**

Bu yapı `backend/app/services/synthetic/reference_data.py` içindeki
`FACTORY_SEED` sabitiyle kodlanmış sabit bir iş kuralıdır, yapılandırılabilir
bir parametre değildir. Tesisler `"{n}. Tesis"` biçiminde adlandırılır ve
1–50 arasında benzersiz bir `sequence_number` taşır — **tesisler her zaman
`sequence_number`'a göre sıralanmalı, `name`'e göre değil** ("10. Tesis"
alfabetik olarak "2. Tesis"ten önce gelir).

- `Foreman` modeli organizasyon FK'sı taşımaz. Tüm yerleşim `ForemanAssignment`
  tablosunda SCD2 tarzı `start_date`/`end_date` aralıklarıyla tutulur: bir
  formenin şefi ve tesisi görev süresi boyunca sabittir, yalnızca vardiyası
  ara dönemlerde değişebilir.
- `(chief_id, plant_id) → chiefs(id, plant_id)` bileşik yabancı anahtarı,
  şef/tesis uyuşmazlığını veritabanı seviyesinde imkânsız kılar.
- Kimlikler benzersiz ve kendini açıklayan biçimde üretilir: ad/soyad çiftleri
  `FIRST_NAMES × LAST_NAMES` (80 × 70 = 5600 kombinasyon) kartezyen çarpımından
  **yerine koymadan** (without replacement) örneklenir, böylece ~1000 kişilik
  havuzda hiçbir şef veya formen aynı tam adı taşımaz. Sicil numaraları
  tesisi kodlar (`SCL-29-004`, `SEF-29-01`) ve sözlüksel sıralama sayısal
  sıralamayla eşleşsin diye sıfırla doldurulur.

`docker compose exec backend python -m app.cli regenerate-personnel-identities`
komutu, mevcut şef/formen ad-soyad ve sicil numaralarını performans verisine
dokunmadan (~1,3M satır UUID ile referans verir) yeniden üretir — isim
havuzlarını değiştirdikten sonra tam yeniden seed yerine kullanılır.

## Veri Akışı: Sağlayıcı → Ingestion → Skor

Performans verisi **API yüzeyinin tamamına salt okunurdur**. Ingestion
pipeline'ı dışında hiçbir yer `performance_records` / `performance_scores`
tablolarını oluşturamaz, güncelleyemez veya silemez.

1. `PerformanceDataProvider.fetch()` (`app/services/providers/base.py`),
   dahili UUID'ler yerine **kodlarla** (`plant_code`, `chief_employee_number`,
   `shift_code`, `foreman_employee_number`, `kpi_code`) `RawPerformanceRecord`
   üretir. Bugün tek implementasyon `SyntheticDataProvider`; `SAPDataProvider`
   iskeleti (`app/services/providers/sap_provider.py`) `SAP_BASE_URL` ayarlı
   değilse `SAPNotConfiguredError`, ayarlıysa `NotImplementedError` fırlatır.
2. `run_ingestion()` (`app/services/ingestion.py`) kodları FK'lere çözer
   (`_Lookups`), hedef değeri `target_resolver` ile bulur, `kpi_engine` ile
   skoru hesaplar ve `BATCH_SIZE = 1000` satırlık gruplar halinde toplu insert
   eder — psycopg'nin bir statement başına 65535 bound parametre limiti ve
   ~20 kolonluk satır boyutu bu sabiti belirler.
3. Idempotency iki benzersiz kısıtla sağlanır: `uq_perf_record_source`
   (source_system, source_record_id) ve `uq_perf_record_natural_key`
   (foreman, kpi, chief, shift, date). Çakışan satırlar
   `ON CONFLICT DO NOTHING ... RETURNING` ile sessizce atlanır ve
   `data_quality_issues` tablosuna `DUPLICATE` olarak kaydedilir.

Veri kalitesi durumları (`DataQualityStatus`): `complete`, `missing`,
`invalid`, `suspicious`, `duplicate`, `needs_source_correction`,
`pending_resync`, `reprocessed`.

### Manuel yeniden senkronizasyon

`POST /api/v1/integration/resync` (Entegrasyon Durumu ekranından tetiklenir),
mevcut sağlayıcıyı (bu ortamda sentetik) belirtilen tarih aralığı için
yeniden çalıştırır — kullanıcının performans verisi girmesi anlamına GELMEZ.
Aralık en fazla **31 gün** (`MAX_RESYNC_DAYS`) ile sınırlıdır. Zaten yüklenmiş
bir dönemi yeniden senkronize etmek, tüm satırların doğal anahtar
çakışmasıyla atlanması nedeniyle idempotent biçimde no-op'tur.

## KPI Hesaplama Motoru

`app/services/kpi_engine.py`, `KPI.calculation_type` alanına göre 5 hesaplama
türü uygular (`custom_formula` kod çalıştırma riski nedeniyle bilinçli olarak
desteklenmez):

| Tür | Mantık |
|---|---|
| `higher_is_better` | `(gerçekleşen / hedef) × 100`, min/max skora clip |
| `lower_is_better` | `(hedef / gerçekleşen) × 100`, min/max skora clip |
| `range_target` | Aralık içindeyse taban skor; dışındaysa tolerans düşülmüş mesafe × ceza oranı kadar düşüş |
| `direct_score` | Gerçekleşen değer doğrudan skor (clip'lenir) |
| `proportional_penalty` | Hedefi aşan miktar başına birim ceza uygulanır |

Toplam skor **her yerde** aynı formülle hesaplanır
(`app/services/analytics.py`):

```
SUM(weighted_contribution) / SUM(kpi_weight) × 100
```

Bu formül eksik KPI'larda otomatik yeniden normalize eder;
`is_reliable` alanı, kapsanan ağırlığın aktif toplam ağırlığın altında
kaldığı satırları işaretler (`WEIGHT_TOLERANCE = 0.5`).

Varsayılan 5 KPI (`DEFAULT_KPI_SEED`, ağırlıkları toplamda 100):

| Kod | Ad | Tür | Ağırlık |
|---|---|---|---|
| `URETIM_GERCEKLESME` | Üretim Hedef Gerçekleşme Oranı | higher_is_better | 30 |
| `FIRE_ORANI` | Fire Oranı | lower_is_better | 20 |
| `PLANSIZ_DURUS` | Plansız Duruş Süresi | proportional_penalty | 20 |
| `KALITE_UYGUNLUK` | Kalite Uygunluk Oranı | range_target | 20 |
| `IS_GUVENLIGI` | İş Güvenliği ve Süreç Uyum Puanı | direct_score | 10 |

Performans seviyeleri (`performance_level_rules`, seed'de sabit): Kritik
(0–69.99), Geliştirilmeli (70–79.99), İyi (80–89.99), Çok İyi (90–99.99),
Mükemmel (100–120).

### Hedef çözümleme

`app/services/target_resolver.py` — saf fonksiyon, öncelik sırası
**FOREMAN > CHIEF > PLANT > COMPANY**. Seeder bugün yalnızca COMPANY
kapsamlı hedefler üretir, dolayısıyla tüm çözümlemeler pratikte bu katmana
düşer; daha dar katmanlar canlı bir yetenektir, canlı veri değil.

## Backend API

Tüm uçlar `/api/v1` altında, JWT bearer token ile korunur (`/auth/*` hariç).
OpenAPI dokümantasyonu: `http://localhost:8000/docs`.

| Router | Öne çıkan uçlar |
|---|---|
| `auth` | `POST /login`, `POST /refresh`, `POST /logout`, `GET /me` |
| `meta` | `GET /filters` — filtre barının kademeli (cascading) seçenekleri |
| `dashboard` | `GET /summary`, `/trend`, `/kpi-summary`, `/plant-ranking`, `/shift-comparison`, `/foreman-ranking`, `/performance-distribution` |
| `plants` | `GET /plants`, `/{id}`, `/{id}/summary`, `/{id}/kpis`, `/{id}/shifts`, `/{id}/chiefs`, `/{id}/foremen` |
| `chiefs` | `GET /chiefs`, `/{id}`, `/{id}/foremen`, `/{id}/kpis`, `/{id}/trend` |
| `foremen` | `GET /foremen`, `/{id}`, `/{id}/kpis`, `/{id}/kpis/{kpi_id}/calculation-detail`, `/{id}/trend`, `/{id}/assignment-history` |
| `kpis` | `GET /kpis`, `/{id}`, `/{id}/analysis` |
| `data_quality` | `GET /issues`, `/summary` |
| `integration` | `GET /runs`, `/runs/{id}`, `POST /resync` |
| `action_plans` | `GET /`, `POST /`, `GET /{id}`, `PATCH /{id}` |
| `reports` | `POST /generate`, `GET /`, `GET /{id}/download` |
| `audit_logs` | `GET /` |

Ortak filtreleme: `common_filters` bağımlılığı (`app/schemas/common.py`)
`date_from`, `date_to`, virgülle ayrılmış `plant_ids` / `factory_ids` /
`chief_ids` / `shift_ids` / `kpi_ids` parametrelerini tek bir `Filters`
nesnesine çözer ve `analytics._apply_filters` üzerinden tüm sorgulara
uygulanır. `factory_ids`, `PerformanceRecord`'ın `factory_id` taşımaması
nedeniyle bir `Plant.factory_id` alt sorgusu üzerinden çözülür.

Aksiyon planları performans kaydını hiçbir şekilde değiştirmez — tamamen
bağımsız bir takip tablosudur. Raporlama modülü de mevcut
`analytics.py` sorgularını yeniden kullanır; üretilen dosya içeriği demo
ölçeğinde ayrı bir obje deposu gerektirmediği için `report_exports`
tablosunda (`LargeBinary`) saklanır.

Denetlenebilir eylemler (giriş/çıkış, aksiyon planı CRUD, rapor
oluşturma/indirme, resync tetikleme) `app/services/audit.py::record_audit()`
üzerinden tek noktadan `audit_logs` tablosuna yazılır.

## Frontend

`frontend/src/App.tsx` React Router v7 ile sayfaları tanımlar; kimlik
doğrulaması olmayan istekler `/login`'e yönlendirilir (`ProtectedRoute`).

| Sayfa | Yol |
|---|---|
| Dashboard | `/` |
| Tesisler / Tesis Detayı | `/plants`, `/plants/:plantId` |
| Şef Grupları / Grup Detayı | `/groups`, `/groups/:chiefId` |
| Formenler / Formen Detayı | `/foremen`, `/foremen/:foremanId` |
| KPI Analizi | `/kpis` |
| Aksiyon Planları | `/action-plans` |
| Raporlar | `/reports` |
| Veri Kalitesi | `/data-quality` |
| Entegrasyon Durumu | `/integration-status` |
| Denetim Kayıtları | `/audit-log` |

Dizin yapısı: `api/` (axios client + TanStack Query hook'ları + tip
tanımları), `components/` (paylaşılan bileşenler ve `charts/` altında
Recharts sarmalayıcıları), `context/` (`AuthContext`, `ThemeContext`),
`hooks/useFilters.ts` (filtre durumunu URL query param'larında tutar),
`lib/` (`chartColors.ts`, `tableStyles.ts`, `formStyles.ts`), `pages/`.

Arayüz dili Türkçedir; tasarımda emoji kullanılmaz, ikonlar
`lucide-react`'ten gelir. Tema tamamen CSS custom property'leri üzerinden
çalışır (`index.css`, `:root[data-theme="dark"|"light"]`), `ThemeContext`
tarafından yönetilir ve varsayılan olarak koyu temadır (localStorage'da
kalıcı). Recharts renk/tooltip prop'ları CSS değişkeni kabul etmediği için
`lib/chartColors.ts` içindeki tema-duyarlı yardımcılar (`resolveChartInk`,
`accentLineColor`, `categoricalColor`) kullanılır.

Vite dev sunucusu (`vite.config.ts`) `:5173` portunda çalışır ve `/api`
isteklerini `http://127.0.0.1:8000`'e proxy'ler. Prod build'de statik
dosyalar Nginx ile sunulur ve `/api/` istekleri `nginx.conf` üzerinden
`http://backend:8000/api/`'ye proxy'lenir.

`frontend/scripts/*.mjs` altında Playwright ile yazılmış smoke test
betikleri bulunur (login, filtreleme, sıralama, PDF render, logo gibi
senaryolar); `frontend/` dizininden çalıştırılmalıdır (playwright oradan
çözülür).

## Veritabanı Şeması

Ana tablo grupları (SQLAlchemy 2.0 `Mapped`/`mapped_column`, `app/models/`):

- **Organizasyon:** `factories`, `plants`, `shifts`
- **Personel:** `chiefs`, `foremen`, `foreman_assignments` (SCD2)
- **KPI:** `kpis`, `kpi_calculation_rules` (versiyonlu), `kpi_targets`
  (kapsam bazlı), `performance_level_rules`
- **Performans (salt okunur):** `performance_records`, `performance_scores`
- **Entegrasyon:** `integration_runs`, `data_quality_issues`
- **Aksiyon/rapor:** `action_plans`, `report_exports`
- **Kimlik/denetim:** `users`, `audit_logs`

Alembic migration geçmişi (`backend/alembic/versions/`):

1. `afa71ec04497` — ilk şema
2. `ef3f90d743f8` — aksiyon planları ve rapor export tabloları
3. `6ad63dbc115b` — **Karaman fabrika/şef hiyerarşisi restrukturasyonu.**
   Bilinçli olarak yıkıcıdır: organizasyon ve performans verisini
   `TRUNCATE` eder, `downgrade()` çağrısı `NotImplementedError` fırlatır.
   Postgres enum'ları değer silemediği için bu migration'da
   rename → yeni enum oluştur → `ALTER COLUMN ... USING` → eski enum'u
   sil sırası izlenmiştir.
4. `55082513f1be` — audit log `ip_address` alanını string'e çevirir

`alembic upgrade head`, backend konteyneri her başladığında otomatik
çalışır (`backend/Dockerfile` CMD'si).

> `README.md`'nin önceki sürümü Türkçe bölge/il, `Department`,
> `ProductionLine` ve `--plants` bayrağına dayanan eski bir modeli
> tanımlıyordu. Bu kavramlar Karaman restrukturasyonuyla tamamen
> kaldırıldı; bu belge yalnızca mevcut kodu yansıtır.

## Kurulum (Docker)

Gereksinim: Docker + Docker Compose.

```bash
cp .env.example .env
docker compose up --build -d
```

- Frontend: http://localhost:8080
- Backend / OpenAPI: http://localhost:8000/docs
- PostgreSQL (host'tan erişim): `localhost:5433`

Şema `alembic upgrade head` ile otomatik oluşur ancak **sentetik veri ve
demo kullanıcı otomatik seed edilmez** (kasıtlı tasarım: üst yönetim
kullanıcıları arayüzden veri giremediği gibi, demo verisi de yalnızca
geliştirici tarafından kontrollü parametrelerle üretilir). Konteynerler
ayaktayken:

```bash
docker compose exec backend python -m app.cli seed --seed 42
docker compose exec backend python -m app.cli create-admin \
  --email genel.mudur@formen-demo.com --password "Demo!2026" --full-name "Demo Genel Müdür"
```

`seed`, varsayılan olarak son 12 ay için ~1,3 milyon performans kaydı
üretir — birkaç dakika sürebilir, arka planda çalıştırın. Yalnızca boş bir
veritabanında (veya `--force` ile) çalışır ve mevcut referans veriyi
üzerine yazmaz. Sıfırdan yeniden üretmek için önce ilgili tabloları
temizleyin:

```bash
docker compose exec -T postgres psql -U formen -d formen_takip -c \
  "TRUNCATE plants, foremen, kpi_targets, integration_runs, shifts, kpis, performance_level_rules CASCADE;"
```

Sentetik veri üretici parametreleri (`app/cli.py`):

```bash
docker compose exec backend python -m app.cli seed \
  --seed 42 \
  --min-foremen 8 --max-foremen 25 \
  --start-date 2025-07-27 --end-date 2026-07-27 \
  --missing-rate 0.02 --error-rate 0.01 --anomaly-rate 0.015 --duplicate-rate 0.005 \
  --force
```

Aynı `--seed` ile tekrar çalıştırma aynı veri setini üretir
(deterministik). Fabrika/tesis sayısı `--plants` gibi bir bayrakla
**değiştirilemez** — 50 tesislik K1/K2 yapısı `FACTORY_SEED`'de sabittir.

Diğer CLI komutları:

```bash
docker compose exec backend python -m app.cli backfill-data-quality-issues
docker compose exec backend python -m app.cli regenerate-personnel-identities
```

Servis bazlı yeniden build ve log inceleme:

```bash
docker compose up --build -d backend
docker compose logs backend --tail 50
```

> **Önemli:** İmajlar kaynağı build anında gömer, bind mount yoktur. Bir
> dosyayı düzenlemek, ilgili servisi `--build` ile yeniden oluşturmadan
> çalışan konteynerde hiçbir etki yaratmaz.

## Yerel Geliştirme (Docker'sız)

### Backend

```bash
cd backend
python -m venv .venv && .venv/Scripts/activate   # Windows
pip install -r requirements.txt
cp .env.example .env   # DATABASE_URL Compose'un host portu 5433'ü hedefler;
                       # farklı bir yerel Postgres kullanıyorsanız düzenleyin
alembic upgrade head
python -m app.cli seed --seed 42
python -m app.cli create-admin --email genel.mudur@formen-demo.com --password "Demo!2026" --full-name "Demo Genel Müdür"
uvicorn app.main:app --reload
```

`backend/.env.example`'daki `DATABASE_URL`, Compose'un Postgres'i host'a
map'lediği **5433** portunu kullanır; `app/core/config.py`'deki varsayılan
5432, host'tan doğrudan çalıştırıldığında işe yaramaz. `backend/.env`
`.gitignore` ile hariç tutulur — her geliştirici kendi kopyasını
`.env.example`'dan türetir.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Vite dev sunucusu `/api` isteklerini `http://127.0.0.1:8000`'e proxy'ler,
bu yüzden backend'in ayrıca (Docker'da ya da yerelde) çalışıyor olması
gerekir.

Diğer frontend komutları:

```bash
npx tsc --noEmit    # tip kontrolü
npm run build       # tsc -b && vite build
npm run lint        # oxlint
```

## Testler

```bash
cd backend
.venv/Scripts/python.exe -m pytest -q                      # tüm paket (142 test fonksiyonu)
.venv/Scripts/python.exe -m pytest tests/unit -q            # yalnızca unit (DB gerekmez)
.venv/Scripts/python.exe -m pytest tests/integration/test_reports.py -q
.venv/Scripts/python.exe -m pytest tests/unit/test_kpi_engine.py::TestX::test_y -q
```

- **Unit testler** (`tests/unit/`) DB gerektirmez: `test_kpi_engine.py`,
  `test_target_resolver.py`, `test_shift_utils.py`, `test_turkish_sort.py`,
  `test_reporting_pdf.py`.
- **Integration testler** (`tests/integration/`) **çalışan, migrasyonu
  yapılmış ve seed edilmiş** bir Postgres bekler — gerçek DB'ye
  `SessionLocal()` üzerinden bağlanır, ayrı bir şema fixture'ı yoktur:
  `test_auth_flow.py`, `test_dashboard.py`, `test_plants_foremen.py`,
  `test_chiefs.py`, `test_data_quality.py`, `test_integration_status.py`,
  `test_ingestion_idempotency.py`, `test_action_plans.py`,
  `test_audit_logs.py`, `test_reports.py`.

`pytest.ini`, `testpaths = tests` ve `pythonpath = .` tanımlar; ek yapılandırma
gerekmez. Otomatik CI pipeline'ı (GitHub Actions vb.) bu depoda **tanımlı
değildir** — testler manuel çalıştırılır.

## Depoyu Klonladıktan Sonra

Aşağıdakiler kasıtlı olarak `.gitignore` ile depo dışında tutulur — çünkü
tamamen tekrar üretilebilirler ve kaynak koduna bağlı değildirler:

- `backend/.venv/` — `pip install -r requirements.txt` ile yeniden kurulur
- `frontend/node_modules/` — `npm install` ile yeniden kurulur
- `frontend/dist/` — `npm run build` ile yeniden üretilir
- `backend/.env`, `.env` (kök) — ilgili `.env.example` şablonlarından
  kopyalanır (bkz. [Ortam Değişkenleri](#ortam-değişkenleri))
- Python/Node önbellekleri (`__pycache__/`, `*.pyc`, `.pytest_cache/`,
  `.coverage`, `htmlcov/`) ve editör/IDE'ye özel dosyalar (`.vscode/*`,
  `.idea/`)
- `.claude/settings.local.json` — bu makineye özel Claude Code izin ayarları

Bir klondan sonra sistemi çalışır hale getirmek için gereken adımlar
[Kurulum (Docker)](#kurulum-docker) veya [Yerel Geliştirme](#yerel-geliştirme-dockersız)
bölümlerinde eksiksiz olarak yer alır; ek bir adım gerekmez.

## Ortam Değişkenleri

Kök dizindeki `.env.example`, Docker Compose için referans şablondur
(`cp .env.example .env`). `backend/.env.example` ise yerelden (Docker'sız)
çalıştırma için şablondur (`cp backend/.env.example backend/.env`) —
`DATABASE_URL` doğrudan Compose'un host'a map'lediği `5433` portunu hedefler.
Her iki gerçek `.env` dosyası da `.gitignore` ile hariç tutulur; yalnızca
`.example` şablonları repoya dahildir.

| Değişken | Varsayılan | Açıklama |
|---|---|---|
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | `formen` / `formen` / `formen_takip` | Compose Postgres servisi |
| `DATABASE_URL` | `postgresql+psycopg://formen:formen@localhost:5432/formen_takip` | Backend DB bağlantısı — Compose bunu `postgres:5432` olarak override eder |
| `JWT_SECRET_KEY` | `change-me-in-production` | **Production'da mutlaka değiştirilmeli** |
| `JWT_ALGORITHM` | `HS256` | pydantic-settings alanı, env ile override edilebilir |
| `ACCESS_TOKEN_EXPIRE_MINUTES` / `REFRESH_TOKEN_EXPIRE_DAYS` | 30 / 7 | JWT ömürleri |
| `MAX_FAILED_LOGIN_ATTEMPTS` / `ACCOUNT_LOCKOUT_MINUTES` | 5 / 15 | Hesap kilitleme eşiği ve süresi |
| `TIMEZONE` | `Europe/Istanbul` | Zaman dilimi |
| `CORS_ORIGINS` | `["http://localhost:5173"]` | Compose'da `["http://localhost:5173","http://localhost:8080"]` olarak set edilir |
| `SAP_BASE_URL` / `SAP_CLIENT_ID` / `SAP_CLIENT_SECRET` | boş | `SAPDataProvider` için yer tutucu — bugün kullanılmıyor |

Ayarların tam listesi ve varsayılanlar için `backend/app/core/config.py`
(pydantic-settings `Settings` sınıfı) doğrudan referans alınmalıdır.

## Demo Girişi

- E-posta: `genel.mudur@formen-demo.com`
- Parola: `Demo!2026`

(Yalnızca `create-admin` komutu çalıştırıldıktan sonra geçerlidir; veritabanında
otomatik oluşturulmaz.)

## Bilinen Sınırlamalar / Kapsam Dışı

- **Gerçek SAP entegrasyonu** yapılmamıştır. `SAPDataProvider`
  (`app/services/providers/sap_provider.py`) yapılandırılmadığında
  `SAPNotConfiguredError`, yapılandırılsa bile `NotImplementedError`
  fırlatan bir iskelettir.
- `custom_formula` KPI hesaplama türü, keyfi kod çalıştırma riski nedeniyle
  bilinçli olarak desteklenmez (`kpi_engine.py` bu durumda hata fırlatır).
- `alembic downgrade` desteği `6ad63dbc115b` migration'ında bilinçli olarak
  kırıktır (`NotImplementedError`) — bu migration geri alınamaz.
- Bildirim/uyarı sistemi ve ayrı bir "Dönem Karşılaştırma" rapor türü
  uygulanmamıştır; ilgili karşılaştırmaların büyük kısmı zaten
  dashboard, tesis/formen/KPI detay ekranları ve Raporlar'daki "Vardiya
  Karşılaştırma" raporunda mevcuttur.
- Otomatik CI/CD pipeline'ı tanımlı değildir — **Doğrulanmalı**: dağıtım
  öncesi test/build adımlarının hangi süreçle (manuel, harici CI) icra
  edileceği bu depo dışında netleştirilmelidir.
