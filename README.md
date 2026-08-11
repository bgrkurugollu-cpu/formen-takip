# Formen Performans Takip Sistemi

Karaman'daki üretim tesislerinde formen (vardiya amiri) performansını KPI bazlı
izleyen, **üst yönetime yönelik salt-okunur karar destek** uygulaması. Foremen
ve tesis şefleri sistemin kullanıcısı değildir; veri girişi yalnızca ingestion
pipeline'ı (bugün sentetik veri üreticisi, ileride SAP) üzerinden gerçekleşir.

## İçindekiler

- [Mimari](#mimari)
- [Organizasyon Hiyerarşisi](#organizasyon-hiyerarşisi)
- [Veri Akışı: Sağlayıcı → Ingestion → Skor](#veri-akışı-sağlayıcı--ingestion--skor)
- [Üretim Verisi Katmanı](#üretim-verisi-katmanı)
- [KPI Hesaplama Motoru](#kpi-hesaplama-motoru)
- [Backend API](#backend-api)
- [Tespitler Modülü (Anomali Tespiti + Yapay Zekâ Analizi)](#tespitler-modülü-anomali-tespiti--yapay-zekâ-analizi)
  - [Aşama 2 — Tool Calling Destekli Analiz Ajanı](#aşama-2--tool-calling-destekli-analiz-ajanı)
- [Katkılar](#katkılar)
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
konteynerde hiçbir etki yaratmaz.

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
1–50 arasında benzersiz bir `sequence_number` taşır — tesisler her zaman
`sequence_number`'a göre sıralanmalı, `name`'e göre değil.

- Her tesisin tam olarak bir şefi vardır (`Plant.chief_id`), ama bir şef
  tek bir tesise değil, aynı fabrika içindeki tesislerden oluşan sabit bir
  bölgeden ("zone") sorumludur (`app/services/synthetic/reference_data.py::seed_reference_data`,
  her fabrikanın tesisleri `min_plants_per_foreman`–`max_plants_per_foreman`
  büyüklüğünde bölgelere ayrılır). Bu bölgedeki her formen (her vardiyada bir
  tane, yani bir şefin 2 formeni olur) bölgenin
  tüm tesislerinden sorumludur, bu yüzden bir formen hiçbir zaman birden
  fazla şefe bağlı olamaz.
- `Foreman` modeli organizasyon FK'sı taşımaz. Tüm yerleşim `ForemanAssignment`
  tablosunda SCD2 tarzı `start_date`/`end_date` aralıklarıyla tutulur: bir
  formenin şefi ve vardiyası görev süresi boyunca sabittir, yalnızca bölgesi
  ara dönemlerde değişebilir.
- `(plant_id, chief_id) → plants(id, chief_id)` bileşik yabancı anahtarı
  (`foreman_assignments`, `foreman_work_calendar` ve `production_records`
  üzerinde tekrarlanır), tesis/şef uyuşmazlığını veritabanı seviyesinde
  imkânsız kılar.
- Kimlikler benzersiz ve kendini açıklayan biçimde üretilir: ad/soyad çiftleri
  `FIRST_NAMES × LAST_NAMES` (80 × 70 = 5600 kombinasyon) kartezyen çarpımından
  yerine koymadan örneklenir, böylece ~1000 kişilik
  havuzda hiçbir şef veya formen aynı tam adı taşımaz. Şef sicil numaraları
  tek bir tesisi değil bölgeyi kodlar (`SEF-003`); formen sicil
  numaraları vardiyayı kodlar (`SCL-V1-014`) — ikisi de sözlüksel sıralama
  sayısal sıralamayla eşleşsin diye sıfırla doldurulur.

`docker compose exec backend python -m app.cli regenerate-personnel-identities`
komutu, mevcut şef/formen ad-soyad ve sicil numaralarını performans verisine
dokunmadan (satırlar UUID ile referans verir) yeniden üretir — isim
havuzlarını değiştirdikten sonra tam yeniden seed yerine kullanılır.

## Veri Akışı: Sağlayıcı → Ingestion → Skor

Performans verisi API yüzeyinin tamamına salt okunurdur. Ingestion
pipeline'ı dışında hiçbir yer `performance_records` / `performance_scores`
tablolarını oluşturamaz, güncelleyemez veya silemez.

1. `PerformanceDataProvider.fetch()` (`app/services/providers/base.py`),
   dahili UUID'ler yerine **kodlarla** (`plant_code`, `chief_employee_number`,
   `shift_code`, `foreman_employee_number`, `kpi_code`) `RawPerformanceRecord`
   üretir. Bugün tek implementasyon `SyntheticDataProvider` — bu sınıf
   **rastgele KPI değeri üretmez**: `app/services/production_kpi_derivation.py`
   üzerinden yalnızca önceden seed edilmiş `production_records` tablosunu okur
   ve ham üretim/kayıp verisinden KPI değerlerini türetir (bkz.
   [Üretim Verisi Katmanı](#üretim-verisi-katmanı)). `SAPDataProvider`
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
`pending_resync`, `reprocessed`. Bu durumlar `data_quality_issues`
tablosuna yazılır.

## Üretim Verisi Katmanı

`performance_records`'ın altında, SAP'in üretim emri/konfirmasyonu ile
göndereceği ham veriyi taklit eden salt okunur bir "ham veri" katmanı bulunur
(`app/models/production.py`):

- `products` — ürün master verisi. `standard_gram`/`lower_gram_limit`/
  `upper_gram_limit` bilinçli olarak nullable — tanımsızsa o ürün için
  Ağır Gitme KPI'sı hiç hesaplanmaz (değer uydurulmaz).
- `production_lines` — tesis içi üretim hattı / iş merkezi.
- `company_calendar` — şirket geneli tatil takvimi.
- `foreman_work_calendar` — formenin hangi tarihte fiilen hangi tesis/şef/
  vardiya/hatta çalıştığı; `ForemanAssignment`'ın (yapısal, nadiren değişen
  atama) gün bazlı somutlaşmış hali. Bir üretim kaydı yalnızca burada
  `is_working=true` bir satır varsa formene bağlanabilir.
- `production_records` — ham üretim/kayıp kaydı: planlanan/gerçekleşen
  miktar, ölçülen ortalama gramaj, GSF/Iskarta miktarı, Teknik/İmalat/Diğer
  duruş dakikaları, plan revizyon no'su. `performance_records`'la aynı
  idempotency deseni uygulanır (`uq_production_record_source`,
  `uq_production_record_natural_key`). Hiçbir KPI yüzdesi burada
  tutulmaz — yalnızca ham ölçüm.

`app/services/production_kpi_derivation.py::derive_raw_performance_records()`
bu tabloları okuyup her üretim kaydından sıfır veya daha fazla
`(kpi_code, actual, numerator, denominator)` bileşeni türetir:

| KPI | Türetildiği ham veri |
|---|---|
| `AGIR_GITME` | `measured_avg_gram`'ın ürünün `lower_gram_limit`/`upper_gram_limit` aralığı dışına taşan işaretli sapması |
| `GSF` | `gsf_qty / actual_qty` |
| `ISKARTA` | `iskarta_qty / actual_qty` |
| `PLANA_UYUM` | `actual_qty / planned_qty` |
| `INKITA` | `(technical_downtime_minutes + manufacturing_downtime_minutes) / planlanan vardiya süresi` — `other_downtime_minutes` puanlamaya hiç dahil edilmez |

`target_value` bu katmandan bilinçli olarak `None` gelir; `ingestion.py`
her zaman olduğu gibi hedefi `target_resolver.resolve_target()` ile
`kpi_targets`'tan çözer. Bu ayrım kaynak-agnostiktir: `production_records`
tablosunu sentetik üretici (`app/services/synthetic/production_generator.py`)
yerine gerçek bir SAP sağlayıcısı doldursa bile `ingestion.py` /
`kpi_engine.py` / `analytics.py` hiçbir değişiklik gerektirmez — yalnızca
`production_records`'ı dolduran katman değişir.

`performance_records.production_record_id` (nullable), her KPI sonucunu
kaynak üretim kaydına geri izlenebilir kılar.

## KPI Hesaplama Motoru

`app/services/kpi_engine.py` iki katmanlı bir modeldir:

- **Jenerik motor** (`calculate_score` / `calculate_raw_score`), `KPI.calculation_type`
  alanına göre 4 klasik hesaplama türü uygular ve gelecekteki veri odaklı
  KPI'lar için kullanılabilir kalır: `higher_is_better`, `lower_is_better`,
  `range_target`, `direct_score`, `proportional_penalty`. Bu türlerin
  dışındaki (tanınmayan) bir `calculation_type` için hâlâ hata fırlatır —
  keyfi kod veya string formül çalıştırma yoktur.
- **Bugün seed edilen 5 KPI'nın tamamı** `calculation_type=CUSTOM_FORMULA`'dır
  ve sabit bir `formula_type` dispatch tablosuna (`_CUSTOM_FORMULA_DISPATCH`)
  yönlendirilerek KPI'a özel, elle yazılmış formüllerle puanlanır — yalnızca
  burada tanımlı 4 formül türünden birine yönlenebilir, keyfi kod
  çalıştırılamaz.

Varsayılan 5 KPI (`DEFAULT_KPI_SEED`, ağırlıkları toplamda 100):

| Kod | Ad | Ağırlık | `formula_type` | Mantık |
|---|---|---|---|---|
| `AGIR_GITME` | Ağır Gitme Oranı | 20 | `SIGNED_ABSOLUTE_PIECEWISE` | Kabul aralığı dışına taşan işaretli sapmanın mutlak büyüklüğü; hedefi tutturursa 100, sapma arttıkça `good_coefficient`/`bad_coefficient` (log2) ile ceza |
| `GSF` | GSF Oranı | 25 | `HYBRID_BASE_PIECEWISE_LOG` | Geri kazanılamayan nihai kayıp oranı; Iskarta'dan daha sert (log tabanlı) cezalandırılır |
| `ISKARTA` | Iskarta Oranı | 15 | `TARGET_RATIO_PIECEWISE` | Geri dönüştürülebilir kayıp oranı; GSF'ye göre daha yumuşak cezalandırılır |
| `INKITA` | İnkita Oranı | 20 | `HYBRID_BASE_PIECEWISE_LOG` | Yalnızca Teknik + İmalat duruş süresi / planlanan süre — Diğer duruşlar hariç |
| `PLANA_UYUM` | Plana Uyum Oranı | 20 | `PIECEWISE_LINEAR_LOGARITHMIC` | `\|gerçekleşen − planlanan\| / planlanan`; plan altı ve plan üstü sapma eşit ağırlıkta cezalandırılır |

Ortak mantık: hedef tam tutturulduğunda **100**, daha iyi performansta
doğrusal olarak **100'ün üzerine** çıkar, daha kötüde logaritmik olarak
**100'ün altına** düşer — `min_score=0` dışında **manuel bir üst sınır
(tavan) uygulanmaz** (`kpis.max_score` sütunundaki `999999.99`, yalnızca
NOT NULL kısıtı içindir; CUSTOM_FORMULA bu değeri hiç okumaz). Bu model
`9f3a2c7b1e44` (skor kolonlarının hassasiyetini genişletme) ve `b6d4f8a2c1e7`
(KPI'a özel formüller) migration'larıyla geldi; eski 5 KPI'lık jenerik model
(`URETIM_GERCEKLESME`, `FIRE_ORANI`, `PLANSIZ_DURUS`, `KALITE_UYGUNLUK`,
`IS_GUVENLIGI`) tamamen kaldırıldı. Var olan performans verisini yeni
formüllerle yeniden hesaplamak için:
`docker compose exec backend python -m app.cli apply-scoring-model-v2`.

Toplam skor **ağırlıklı geometrik ortalamayla** hesaplanır
(`app/services/analytics.py::_grouped_scores` →
`kpi_engine.py::weighted_geometric_score`):

```
100 × Π (score_i / 100) ^ (weight_i / Σ weight)
```

Geometrik ortalama, tek bir KPI'daki aşırı yüksek puanın diğer kötü
sonuçları gizlemesini engeller (aritmetik ortalamanın aksine). Kapsanan
ağırlık, aktif toplam ağırlığın `MIN_COVERED_WEIGHT_RATIO = 0.5` katından
azsa genel puan üretilmez, doğrudan 0 döner.

Skor tabanlı KPI'lar önce **dönem boyunca pay/payda toplanır**, tek bir
orandan tek bir puan üretilir — günlük puanların ortalaması alınmaz.

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
| `foremen` | `GET /foremen`, `/{id}`, `/{id}/kpis`, `/{id}/kpis/{kpi_id}/calculation-detail`, `/{id}/trend`, `/{id}/assignment-history`, `/{id}/contribution-summary` |
| `kpis` | `GET /kpis`, `/{id}`, `/{id}/analysis` |
| `contributions` | `GET /contribution-works`, `/summary`, `/{id}`, `/{id}/pdf`, `POST /`, `PATCH /{id}`, `DELETE /{id}` — bkz. [Katkılar](#katkılar) |
| `anomalies` | `GET /anomalies`, `/summary`, `/{id}`, `POST /{id}/analyze`, `/{id}/reanalyze`, `GET /{id}/analysis`, `PATCH /{id}/status` — bkz. [Tespitler Modülü](#tespitler-modülü-anomali-tespiti--yapay-zekâ-analizi) |
| `analyses` | `GET /analyses/{id}`, `GET /analyses/{id}/tool-calls` — Aşama 2 tool calling geçmişi |
| `shift_analysis` | `GET /shift-analysis/cards`, `/detail` — aynı tesis/KPI'da bir ayın vardiya rotasyonuna göre iki formen arasındaki belirgin performans farklarını yüzeye çıkarır |
| `reports` | `POST /generate`, `GET /`, `GET /{id}/download` |

Ortak filtreleme: `common_filters` bağımlılığı (`app/schemas/common.py`)
`date_from`, `date_to`, virgülle ayrılmış `plant_ids` / `factory_ids` /
`chief_ids` / `shift_ids` / `kpi_ids` parametrelerini tek bir `Filters`
nesnesine çözer ve `analytics._apply_filters` üzerinden tüm sorgulara
uygulanır. `factory_ids`, `PerformanceRecord`'ın `factory_id` taşımaması
nedeniyle bir `Plant.factory_id` alt sorgusu üzerinden çözülür.

Raporlama modülü mevcut `analytics.py` sorgularını yeniden kullanır;
üretilen dosya içeriği demo ölçeğinde ayrı bir obje deposu gerektirmediği
için `report_exports` tablosunda (`LargeBinary`) saklanır.

Denetlenebilir eylemler (giriş/çıkış, katkı çalışması CRUD, tespit durumu/
analiz güncelleme, rapor oluşturma/indirme) `app/services/audit.py::record_audit()`
üzerinden tek noktadan `audit_logs` tablosuna yazılır — bu tabloyu
görüntüleyen ayrı bir API/ekran bulunmaz, yalnızca dahili iz kaydı olarak
tutulur.

## Tespitler Modülü (Anomali Tespiti + Yapay Zekâ Analizi)

**Amaç:** Üretim verilerindeki olağan dışı durumları ("Ağır Gitme", "GSF",
"Iskarta", "İnkita", "Plana Uyum" KPI'larında) yöneticilere göstermek, önem
derecesi ve durumlarını takip etmek ve her tespit için isteğe bağlı bir yapay
zekâ analizi üretmek. Modül iki kademede geliştirilmiştir:

- **Aşama 1 — Sentetik Veriyle Prototip**: tüm bağlam LLM'e tek pakette
  gönderilir (`single_context` modu, aşağıda anlatılıyor).
- **Aşama 2 — Tool Calling Destekli Analiz Ajanı**: LLM, ihtiyaç duyduğu ek
  veriyi salt-okunur backend araçlarını çağırarak kendisi toplar
  (`tool_calling` modu, [ayrı bölümde](#aşama-2--tool-calling-destekli-analiz-ajanı) anlatılıyor).

İkisinde de gerçek bir ML modeli, SAP/Ocean entegrasyonu, RAG veya vektör veri
tabanı kullanılmaz — tüm operasyonel veri sentetiktir.

### Sentetik tespit verisi

`app/services/synthetic/anomaly_generator.py`, gerçek makine öğrenmesi
tespitiymiş gibi davranan **24 sabit senaryodan** (13 farklı tespit türünü en
az bir kez kapsayan: vardiya bazlı sürekli düşük performans, yükselen trend,
formen bazlı sapma, ürün grubu sapması, duruş yoğunlaşması, art arda plan
altı kalma, tesis geçmişinden sapma, tesisler arası fark, eş zamanlı çoklu
KPI bozulması, tek günlük sıçrama, kronik anormallik, kritik üretim kaybı,
veri kalitesi şüphesi), K1/K2 fabrikaları arasında dengeli biçimde,
gerçek (seed edilmiş) tesis/vardiya/KPI referans verisine bağlı, birbiriyle
tutarlı sayısal veriler (gözlenen/beklenen değer, sapma oranı, vardiya
karşılaştırması, ilişkili KPI sinyalleri, ML güven skoru) üretir. Aynı
`--seed` ile her çalıştırma aynı sonucu verir (tekrar üretilebilirlik);
zaten var olan tespit kodları (`ANM-YYYY-NNNN`) atlanır, bu yüzden komutu
tekrar çalıştırmak güvenlidir:

```bash
docker compose exec backend python -m app.cli seed-anomalies --seed 42
```

(`seed` komutu bu adımı otomatik olarak son adım — `[5/5]` — olarak da çalıştırır.)

Şema (`app/models/anomaly.py`, `Anomaly` ve `AnomalyAnalysis` tabloları),
gelecekte gerçek bir ML tespit servisinin üreteceği çıktıyla aynı alanları
taşır — sentetik üretici ileride bu şemaya yazan gerçek bir servisle
değiştirilebilir, API ve frontend değişmeden kalır.

### Yapay zekâ analizi nasıl çalışır

1. Kullanıcı arayüzden "Yapay Zeka ile Analiz Et" butonuna basar →
   `POST /api/v1/anomalies/{id}/analyze`.
2. `app/services/anomaly_context.py::build_analysis_package()`, tespitin
   tüm sayısal verisini, KPI tanımını, vardiya/tesis/fabrika
   karşılaştırmalarını, ilişkili KPI sinyallerini ve sentetik bağlam
   öğelerini (günlük geçmiş, duruş özeti, bakım sinyalleri, ürün dağılımı,
   vardiya notları, benzer geçmiş olaylar) tek bir JSON paketinde
   toplar, LLM'nin ihtiyaç duyacağı her şey
   bu tek pakette gönderilir. Formen bilgisi isim değil sicil kodu
   (`employee_number`) ile temsil edilir.
3. `app/services/llm_service.py`, `LLM_ENABLED=true` ve `LLM_API_KEY` tanımlıysa
   OpenAI uyumlu bir `chat/completions` uç noktasına (`LLM_BASE_URL`,
   `LLM_MODEL`, `LLM_TIMEOUT_SECONDS`) sistem promptu + JSON paketiyle istek
   atar; sağlayıcı bağımsız tek bir servis katmanıdır (ileride farklı bir
   sağlayıcıya geçmek yalnızca bu dosyanın içini değiştirmeyi gerektirir).
4. LLM cevabı (veya demo fallback çıktısı) `app/schemas/anomaly_analysis.py`
   içindeki `AnalysisResult` Pydantic şemasına karşı doğrulanır. Geçersiz
   JSON, eksik alan veya zaman aşımı durumunda en fazla bir kez otomatik
   yeniden denenir; iki deneme de başarısız olursa analiz `failed` durumuna
   geçer ve kullanıcıya jenerik bir hata mesajı gösterilir (teknik ayrıntılar
   yalnızca backend loglarında tutulur).
5. Sonuç `anomaly_analyses` tablosuna yeni bir satır olarak yazılır —
   önceki analizler silinmez, arayüzde varsayılan olarak en güncel analiz
   gösterilir (`GET /{id}/analysis` ve tespit detayındaki `latest_analysis`).

### Demo modu (LLM olmadan)

`LLM_ENABLED=false` veya `LLM_API_KEY` boşsa (varsayılan durum),
`app/services/anomaly_demo_fallback.py` gerçek çıktı şemasıyla birebir aynı
şekilde, tespitin gerçek sayısal verilerine dayanan deterministik bir analiz
üretir. Uygulama asla bozulmaz. Arayüzde bu durum küçük bir
**"Demo Yapay Zekâ Analizi"** etiketiyle; gerçek LLM kullanıldığında ise
**"Yapay Zekâ Analizi"** etiketiyle belirtilir.

### Yapılandırılmış çıktı şeması

LLM'den (veya demo üreticiden) beklenen JSON şekli (`AnalysisResult`):
`executive_summary`, `verified_findings[]` (finding/evidence), `possible_causes[]`
(cause/confidence/supporting_evidence/contradicting_evidence/verification_required),
`recommended_investigations[]`, `immediate_actions[]`, `medium_term_actions[]`,
`missing_information[]`, `risk_level`, `analysis_confidence` (0–1),
`requires_human_review` (her zaman `true`), `disclaimer`. Sistem promptu
(`anomaly_context.py::SYSTEM_PROMPT`), formenleri doğrudan suçlamamayı,
doğrulanmış bulgularla varsayımları ayırmayı, her önerinin bir sorumlu birim/
öncelik taşımasını ve tüm aksiyonların yönetici onayı gerektirdiğini açıkça
şart koşar; tespit açıklaması içine sızabilecek "talimatları yok say" türü
metinlerin komut olarak yorumlanmaması için ayrı bir güvenlik notu içerir.

### Güvenlik

`LLM_API_KEY` yalnızca backend ortam değişkeni olarak okunur, frontend'e asla
gönderilmez ve repository'ye yazılmaz (`.env` `.gitignore` ile hariç tutulur).
Tüm LLM çağrıları backend üzerinden yapılır. LLM'nin veritabanına yazma,
SAP/Ocean'a işlem gönderme veya aksiyon uygulama yetkisi yoktur — yalnızca
salt-okunur bir analiz metni üretir, kullanıcı arayüzde bunu yapılandırılmış
kartlar halinde görür (ham HTML render edilmez).

### Aşama 2 — Tool Calling Destekli Analiz Ajanı

`LLM_ANALYSIS_MODE` ayarı veya her analiz isteğinde gönderilebilen `mode` alanı 
(`single_context`, `tool_calling`) ile hangi yöntemin kullanılacağı seçilir. 
Frontend'de tespit detay ekranındaki **Hızlı Analiz / Derinlemesine Analiz** seçici 
bu iki moda karşılık gelir.

**Mimari akış** (`app/services/anomaly_orchestrator.py::AnomalyAnalysisOrchestrator`):

1. LLM'e başlangıçta yalnızca tespitin özeti (başlık, tesis, vardiya, KPI,
   sapma, ML güven skoru, kullanılabilir araçların açıklamaları) verilir —
   Aşama 1'deki gibi tüm bağlam paketi baştan gönderilmez.
2. Model önce kısa bir **iç araştırma planı** üretir (`investigation_plan`,
   kullanıcıya gösterilmez, `anomaly_analyses.investigation_plan` alanında saklanır).
3. Model, ihtiyaç duydukça `app/services/tools/definitions.py`'deki **11
   salt-okunur araçtan** (allowlist) birini çağırır; her çağrı Pydantic ile
   doğrulanır (geçersiz fabrika/tesis/vardiya/KPI/tarih aralığı → kontrollü
   hata), gerçek sentetik sağlayıcı katmanı çalıştırılır ve sonuç modele
   `tool_call_reference` koduyla geri gönderilir. Her çağrı bir
   `anomaly_tool_calls` satırı olarak kaydedilir (adım no, argümanlar, süre,
   dönen kayıt sayısı, hata kodu).
4. Döngü; `LLM_MAX_TOOL_CALLS`, `LLM_MAX_ANALYSIS_STEPS` veya
   `LLM_ANALYSIS_TIMEOUT_SECONDS` sınırlarından biri aşılınca ya da model
   kendiliğinden yeterli veri topladığına karar verince durur.
5. Modelden, topladığı bulgulara dayanan **nihai yapılandırılmış analiz**
   ayrıca istenir; `verified_findings`/`possible_causes` içindeki
   `source_refs`, gerçekten yapılmış `tool_call_reference` kodlarına karşı
   doğrulanır — LLM'nin uydurduğu bir referans varsa sessizce ayıklanır ve
   `analysis_limitations`'a not düşülür (bkz.
   `anomaly_orchestrator.py::_sanitize_source_refs`).

**Sentetik veri tutarlılığı** (`app/services/synthetic/world.py`): Aşama 2'nin
11 aracının hepsi, aynı birkaç temel fonksiyona (özellikle `_value_for_date`)
dayanır — hiçbir araç bağımsız/rastgele veri üretmez. "Zemin gerçeği", Aşama
1'de üretilip `anomalies` tablosuna yazılmış olan tespitlerdir: bir
(tesis, KPI) çifti için bir tespit varsa, o tespitin `observed_value`/
`expected_value`/`comparison` alanları tüm günlük seri, duruş, bakım ve
vardiya karşılaştırması detaylarının çıkış noktasıdır (`get_kpi_history` ile
`compare_shifts`'in aynı vardiya için ürettiği sayı **bit bit aynıdır**).
Tespit olmayan tesis/KPI kombinasyonları için "sağlıklı" (KPI hedefine yakın,
düşük varyanslı) bir seri üretilir. `find_similar_anomalies` gerçek seed
edilmiş `Anomaly` kayıtlarını sorgular.

**Veri sağlayıcı katmanı** (`app/services/data_providers/`): `base.py`'deki 7
soyut arayüz (`AnomalyDataProvider`, `KPIDataProvider`, `DowntimeDataProvider`,
`MaintenanceDataProvider`, `ProductDataProvider`, `ShiftDataProvider`,
`HistoricalCaseDataProvider`) bugün yalnızca `synthetic.py`'deki
`Synthetic*Provider` sınıflarıyla implemente edilir. Araçlar
(`tools/definitions.py`) bu arayüzlere karşı yazılmıştır ve verinin sentetik
mi Ocean mı olduğunu bilmez — `app/services/providers/base.py`'deki
`PerformanceDataProvider` deseniyle aynı mimari. `app/services/data_providers/__init__.py::get_data_providers()`
tek fabrika noktasıdır; gelecekte `OceanKPIDataProvider`/`MLAnomalyDataProvider`
gibi gerçek implementasyonlar eklendiğinde yalnızca bu fonksiyonun içi
değişir — araç adları, LLM şemaları ve frontend etkilenmez.

**Demo tool calling** (`app/services/anomaly_demo_tool_calling.py`):
`LLM_ENABLED=false` veya API anahtarı yokken (`LLM_DEMO_TOOL_CALLING_ENABLED=true`,
varsayılan), `tool_calling` modu tamamen devre dışı kalmaz — sabit bir araç
sırası (`compare_shifts → get_kpi_history → get_downtime_breakdown →
get_maintenance_signals → get_product_mix → find_similar_anomalies`)
**gerçekten çalıştırılır** (gerçek sentetik sağlayıcılara karşı), yalnızca
LLM'nin hangi aracı çağıracağına karar verme adımı atlanır. Nihai analiz metni
Aşama 1'in demo üreticisiyle üretilir ve gerçek tool-call kodlarıyla
ilişkilendirilir; arayüzde **"Demo Yapay Zekâ Analizi"** etiketiyle gösterilir.
Tool calling desteklemeyen bir model 400 hatası döndürürse
(`LLMToolCallingUnsupportedError`), sistem otomatik olarak `single_context`
moduna düşer ve bunu `analysis_limitations`'da belirtir.

**Genişletilmiş çıktı şeması**: Aşama 1'in `AnalysisResult` şeması korunur,
üstüne `tools_used[]` (tool_name/tool_call_id/purpose),
`data_scope` (start_date/end_date/record_count/data_quality_status) ve
`analysis_limitations[]` eklenir; `verified_findings`/`possible_causes`
öğeleri `source_refs[]` taşır. `single_context` modunda bu alanlar boş/`null`
bırakılabilir.

**Genişletilmiş analiz durum modeli** (`AnomalyAnalysisStatus`): Aşama 1'in
`not_analyzed`/`analyzing`/`completed`/`failed` değerlerine ek olarak
`queued`, `planning`, `collecting_data`, `generating_analysis`,
`completed_with_warnings` (sınırlara ulaşıldığında veya `tool_calling`→
`single_context` düşüşünde), `timed_out`, `cancelled` eklenmiştir. Orkestratör
bu durumları analiz sırasında ilerledikçe commit eder — aynı tespidi başka bir
sekmeden görüntüleyen bir kullanıcı kaba taneli ilerlemeyi görebilir.

**Araç çağrı sınırları ve önbellek**: `LLM_MAX_TOOL_CALLS` (varsayılan 10),
`LLM_MAX_ANALYSIS_STEPS` (12), `LLM_TOOL_TIMEOUT_SECONDS` (10),
`LLM_ANALYSIS_TIMEOUT_SECONDS` (60), `LLM_MAX_DATE_RANGE_DAYS` (365) — bir
araç bu tarih aralığını aşan bir istek alırsa `TOOL_VALIDATION_ERROR`
döndürür. Aynı analiz içinde aynı araç aynı parametrelerle tekrar çağrılırsa
bellek-içi önbellekten döner (yeni bir `anomaly_tool_calls` satırı oluşmaz,
tool-call sayacı artmaz). Hata kodları
(`TOOL_VALIDATION_ERROR`, `TOOL_NOT_FOUND`, `TOOL_TIMEOUT`,
`TOOL_DATA_NOT_FOUND`, `LLM_TOOL_LOOP_LIMIT`, `LLM_INVALID_STRUCTURED_OUTPUT`,
`LLM_TIMEOUT`, `LLM_PROVIDER_ERROR`) hem `anomaly_tool_calls.error_code`
hem de `anomaly_analyses.error_code` alanında saklanır; teknik ayrıntılar
kullanıcıya gösterilmez, yalnızca backend loglarında tutulur.

**Frontend**: Tespit detay ekranında "Derinlemesine Analiz" sonuçları için
ek bölümler gösterilir — **Analizde Kullanılan Veriler** (kaç araç
kullanıldığı, incelenen tarih aralığı/kayıt sayısı, veri kalitesi) ve
**Analiz Adımları** (her tool-call için sıra no, araç adı, durum, süre, dönen
kayıt sayısı; `GET /analyses/{id}/tool-calls`'tan gelir). Doğrulanmış
bulgu/neden kartlarında "Kaynak: <araç adı>" etiketiyle hangi araçtan
geldiği görülebilir. Analiz sürerken gerçek iç düşünce zinciri değil, sabit
bir aşama listesi gösterilir.

### Testler

```bash
cd backend
.venv/Scripts/python.exe -m pytest tests/unit/test_anomaly_demo_fallback.py tests/unit/test_anomaly_analysis_schema.py tests/unit/test_anomaly_orchestrator_helpers.py -q
.venv/Scripts/python.exe -m pytest tests/integration/test_anomalies.py tests/integration/test_anomaly_analysis_service.py tests/integration/test_anomaly_generator.py tests/integration/test_world.py tests/integration/test_tools.py tests/integration/test_anomaly_orchestrator.py -q
```

Aşama 1 kapsanan senaryolar: sentetik tespitlerin şemaya uygunluğu (≥20 tespit, 13
tür de temsil ediliyor, benzersiz kod, tutarlı sapma hesabı), liste/detay/
filtreleme/sayfalama uçları, başarılı LLM analizi, geçersiz JSON / eksik alan
/ zaman aşımı durumlarında yeniden deneme ve `failed` düşüşü, API anahtarı
olmadan demo fallback, çift tıklama koruması (`409`), analiz geçmişinin
korunması ve tespit durumu güncelleme.

Aşama 2 kapsanan senaryolar: sentetik veri sağlayıcılarının tutarlılığı
(`get_kpi_history`/`compare_shifts` aynı sayıyı üretir, anchor'sız
kombinasyonlar "sağlıklı" seri üretir, determinizm), her aracın başarılı
çağrı/eksik parametre/geçersiz parametre/tarih sınırı doğrulaması, orkestrasyon
(tek/çoklu tool çağrısı, maksimum araç sınırı, önbellekten dönme, bilinmeyen
araç adı, hatalı argüman, zaman aşımı, bir araç başarısız olsa bile analizin
tamamlanması, uydurma kaynak referanslarının ayıklanması, tool calling
desteklenmeyen modelde `single_context`'e düşüş), demo tool calling akışının
gerçek araçları çalıştırması ve `single_context` modunun bozulmadan çalışmaya
devam etmesi. Frontend tarafında
`frontend/scripts/smoke_test_anomalies.mjs` ve
`frontend/scripts/smoke_test_tool_calling.mjs` (Playwright) liste sayfası,
filtreleme, detay sayfası ve analiz akışını uçtan uca doğrular.

## Katkılar

Formenlerin/şeflerin ürettiği iyileştirme çalışmalarını (SMED, Kaizen, sorun
çözme vb.) kaydeden, mali kazanç doğrulaması ve PDF raporu üreten bağımsız
bir modül (`app/models/contribution.py`, `app/api/v1/contributions.py`).
Performans skorlamasıyla hiçbir bağlantısı yoktur — tamamen ayrı bir takip
tablosudur.

- `contribution_works` — başlık, tür (`ContributionWorkType`: SMED, KAIZEN,
  PROBLEM_SOLVING, ...), problem/çözüm/sonuç açıklaması, `status`
  (`ContributionStatus`: DRAFT/PUBLISHED), standardizasyon bayrakları
  (`is_standardized`, `is_applicable_other_plants`, `is_permanent_solution`,
  `work_instruction_updated`) ve mali kazanç alanları
  (`financial_gain_status`, `estimated_amount`/`verified_amount`, `currency`,
  doğrulayan departman, doğrulama tarihi/notu).
- `contribution_work_foremen` — bir çalışmaya katkı veren formenleri
  `ContributionRole` (`LEAD` / `CONTRIBUTOR`) ile ilişkilendiren çoka-çok
  tablo; tek formenli çalışmalar migration `f2a4b8e6c9d1` ile otomatik
  `LEAD` olarak işaretlenmiştir.
- `contribution_gains` — süre/verim kazancı dışındaki diğer kazanım türlerini
  (`OtherGainType`) önceki/sonraki değer ve değişim yüzdesiyle kaydeder.

`app/services/contribution_calc.py`, süre tasarrufu gibi tekrar eden
kazançları (`previous_duration`/`new_duration`, `repeat_period`,
`repeat_count`) aylık toplam tasarruf dakikasına (`monthly_total_saving_minutes`)
çevirir. `GET /{id}/pdf`, `reportlab` ile tek bir çalışmanın özet raporunu
üretir. Sentetik örnek veri `app/services/synthetic/contribution_generator.py`
ile üretilir — `seed` komutunun katkı çalışması adımı (yalnızca en az bir
kullanıcı varsa çalışır, bkz. [Kurulum](#kurulum-docker)) veya bağımsız
olarak `docker compose exec backend python -m app.cli seed-contributions`.

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
| Katkılar / Detay | `/improvement-works`, `/improvement-works/:workId` |
| Tespitler / Tespit Detayı | `/anomalies`, `/anomalies/:anomalyId` |
| Vardiya Analizi / Detay | `/shift-analysis`, `/shifts/:shiftId` |
| Raporlar | `/reports` |

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
- **Üretim (ham veri katmanı):** `products`, `production_lines`,
  `company_calendar`, `foreman_work_calendar`, `production_records` —
  bkz. [Üretim Verisi Katmanı](#üretim-verisi-katmanı)
- **KPI:** `kpis`, `kpi_calculation_rules` (versiyonlu), `kpi_targets`
  (kapsam bazlı), `performance_level_rules`
- **Performans (salt okunur, üretim verisinden türetilir):**
  `performance_records`, `performance_scores`
- **Entegrasyon:** `integration_runs`, `data_quality_issues` — dahili
  kullanımdadır; bunları görüntüleyen ayrı bir API/ekran bulunmaz
- **Rapor:** `report_exports`
- **Katkı ve iyileştirme çalışmaları:** `contribution_works`,
  `contribution_work_foremen`, `contribution_gains`
- **Tespitler:** `anomalies`, `anomaly_analyses`, `anomaly_tool_calls` (Aşama 2
  tool calling geçmişi)
- **Kimlik/denetim:** `users`, `audit_logs`

Alembic migration geçmişi (`backend/alembic/versions/`, `down_revision`
zincirine göre sıralı):

1. `afa71ec04497` — ilk şema
2. `55082513f1be` — audit log `ip_address` alanını string'e çevirir
3. `ef3f90d743f8` — aksiyon planları ve rapor export tabloları
4. `6ad63dbc115b` — **Karaman fabrika/şef hiyerarşisi restrukturasyonu.**
   Bilinçli olarak yıkıcıdır: organizasyon ve performans verisini
   `TRUNCATE` eder, `downgrade()` çağrısı `NotImplementedError` fırlatır.
   Postgres enum'ları değer silemediği için bu migration'da
   rename → yeni enum oluştur → `ALTER COLUMN ... USING` → eski enum'u
   sil sırası izlenmiştir.
5. `9f3a2c7b1e44` — tavansız (uncapped) KPI'lar için skor kolonlarının
   hassasiyetini genişletir
6. `c7a1f9d0b2e3` — üretim verisi katmanını ekler (`products`,
   `production_lines`, `company_calendar`, `foreman_work_calendar`,
   `production_records`) ve `performance_records.production_record_id`'yi
   tanıtır
7. `b6d4f8a2c1e7` — KPI'a özel puanlama formülleri (`custom_formula`
   dispatch tablosu) — bkz. [KPI Hesaplama Motoru](#kpi-hesaplama-motoru)
8. `d3e5a7c9f102` — katkı ve iyileştirme çalışmaları tabloları
9. `e1b2c4d6f8a0` — tespitler (anomali) tabloları
10. `f2a4b8e6c9d1` — katkı çalışmalarına formen rolü (`LEAD`/`CONTRIBUTOR`)
    ekler
11. `a4c8e0b2d6f1` — tool calling destekli analiz ajanı: `anomaly_tool_calls`
    tablosu, `anomaly_analyses.mode`/`investigation_plan`/`error_code`
    kolonları, genişletilmiş analiz durumları — bkz.
    [Aşama 2 — Tool Calling Destekli Analiz Ajanı](#aşama-2--tool-calling-destekli-analiz-ajanı)
12. `b7c9e1a3d5f2` — `foreman_assignments(plant_id, shift_id) WHERE is_active`
    üzerinde kısmi benzersiz indeks: bir tesisin bir vardiyasından aynı anda
    yalnızca bir formen sorumlu olabilir
13. `c3e5f7a9b1d4` — `foreman_work_calendar`/`production_records` doğal
    anahtarlarına `plant_id` ekler (formen 2-4 eşzamanlı tesise bağlı
    olabildiğinden gerekli)
14. `a1b3c5d7e9f2` — **şef artık tek tesise değil bölgeye (zone) sorumlu.**
    `chiefs.plant_id` kaldırılır, `plants.chief_id` eklenir (yön tersine
    döner); `(plant_id, chief_id) → plants(id, chief_id)` kompozit FK'si
    `foreman_assignments`/`foreman_work_calendar`/`production_records`'a
    eklenir. Karaman migration'ıyla aynı gerekçeyle yıkıcıdır (organizasyon
    kimlikleri kökten değiştiği için `TRUNCATE` eder, `downgrade()`
    `NotImplementedError` fırlatır)
15. `d4f6a8b1c3e5` — Plana Uyum v3: asimetrik puanlama. Plan üstü üretim
    artık cezalandırılmaz, ödüllendirilir (logaritmik olarak +%5'ten sonra
    yavaşlar); plan altı öncekinden daha güçlü cezalandırılır. Yalnızca yeni
    bir `kpi_calculation_rules` versiyonu ekler — var olan
    `performance_scores`'u yeniden hesaplamaz (bkz. `apply-scoring-model-v2`)
16. `f8a1c3e5b7d9` — `performance_records`'ın doğal anahtarına `plant_id`
    ekler — bir formenin 2-4 eşzamanlı tesisinden yalnızca ilkinin KPI
    kayıtları `ON CONFLICT DO NOTHING` ile hayatta kalıyordu, geri kalanı
    `DUPLICATE` olarak atlanıyordu (bkz. [Veri Akışı](#veri-akışı-sağlayıcı--ingestion--skor))
17. `a2c4e6f8b0d3` — `performance_records`'a da `(plant_id, chief_id) →
    plants(id, chief_id)` kompozit FK'sini ekler (`production_records`/
    `foreman_work_calendar`'da zaten vardı) — `ingestion.py`'nin
    `assignment_resolver.py` üzerinden yaptığı doğrulamaya DB seviyesinde
    bir yedek katman
18. `b3d5f7a9c1e2` — `foreman_assignments` tarih aralığı bütünlüğü: `CHECK`
    kısıtları (`start_date <= end_date`, pasif atamanın `end_date`'i
    olmalı), aynı tesis+vardiya için tarih aralığı çakışmasını engelleyen
    `EXCLUDE` kısıtı (`btree_gist`) ve bir formenin aynı anda yalnızca tek
    bir şefe bağlı olabilmesini DB seviyesinde zorunlu kılan trigger
19. `c9e2a4f6b8d0` — **Aksiyon Planları özelliği tamamen kaldırılır.**
    `action_plans` tablosu ve ilgili enum'lar (`action_plan_status`,
    `action_plan_priority`) drop edilir. Bilinçli olarak geri alınamaz
    (`downgrade()` `NotImplementedError` fırlatır) (HEAD)

`alembic upgrade head`, backend konteyneri her başladığında otomatik
çalışır (`backend/Dockerfile` CMD'si).


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
docker compose exec backend python -m app.cli create-admin \
  --email genel.mudur@formen-demo.com --password "Demo!2026" --full-name "Demo Genel Müdür"
docker compose exec backend python -m app.cli seed --seed 42
```

> **Sıra önemli:** `seed`'in katkı/iyileştirme çalışması örnek verisi
> üretme adımı (`[4/5]`), çalıştığı anda **en az bir kullanıcı** olmasını
> gerektirir — yoksa bu adımı sessizce atlar (hata vermez). `create-admin`'i
> `seed`'den önce çalıştırmazsanız, örnek katkı verisini daha sonra ayrıca
> `docker compose exec backend python -m app.cli seed-contributions`
> ile üretebilirsiniz.

`seed` sırasıyla şunları yapar: `[1/3]` referans veri (organizasyon +
KPI hedefleri), `[2/3]` sentetik üretim verisi
(`production_records` — bkz. [Üretim Verisi Katmanı](#üretim-verisi-katmanı)),
`[3/3]` bu üretim verisinden KPI türetme + ingestion, ardından (admin
varsa) katkı çalışması örnekleri ve son olarak Tespitler modülü için
sentetik ML tespitleri (`seed-anomalies`). Varsayılan olarak son 12 ay için
~50–75K performans kaydı üretir (`docker compose exec backend python -m app.cli seed`
çıktısındaki `[3/3]` satırı `başarılı` sayısı) — birkaç dakika sürebilir,
arka planda çalıştırın. Bu, ham üretim kaydı sayısından belirgin düşüktür:
`performance_records`'ın doğal anahtarı (`foreman_id`, `kpi_id`, `chief_id`,
`shift_id`, `performance_date`) `plant_id` içermez, bu yüzden bir formenin
aynı gün sorumlu olduğu 2-4 tesisin ürettiği KPI kayıtlarından yalnızca
ilki eklenir, geri kalanı `DUPLICATE` olarak atlanır (bkz.
[Veri Akışı](#veri-akışı-sağlayıcı--ingestion--skor)). Yalnızca boş bir
veritabanında (veya `--force` ile) çalışır ve mevcut referans veriyi
üzerine yazmaz. Sıfırdan yeniden üretmek için önce ilgili tabloları
temizleyin:

```bash
docker compose exec -T postgres psql -U formen -d formen_takip -c \
  "TRUNCATE factories, plants, chiefs, foremen, kpi_targets, integration_runs, shifts, kpis, performance_level_rules, products, company_calendar CASCADE;"
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
docker compose exec backend python -m app.cli seed-anomalies --seed 42
docker compose exec backend python -m app.cli seed-contributions --seed 42 --count 40
docker compose exec backend python -m app.cli apply-scoring-model-v2
```

`apply-scoring-model-v2`, var olan performans verisini KPI'a özel yeni
puanlama formülleriyle yeniden hesaplar (AGIR_GITME'nin işaretli
türetimini düzeltir, İNKITA için geriye dönük ingestion çalıştırır ve
tüm `performance_scores`'u aktif kurallarla yeniden puanlar) — bkz.
[KPI Hesaplama Motoru](#kpi-hesaplama-motoru).

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
.venv/Scripts/python.exe -m pytest -q                      # tüm paket (431 test fonksiyonu)
.venv/Scripts/python.exe -m pytest tests/unit -q            # yalnızca unit (DB gerekmez)
.venv/Scripts/python.exe -m pytest tests/integration/test_reports.py -q
.venv/Scripts/python.exe -m pytest tests/unit/test_kpi_engine.py::TestX::test_y -q
```

- **Unit testler** (`tests/unit/`) DB gerektirmez: `test_kpi_engine.py`,
  `test_target_resolver.py`, `test_shift_utils.py`, `test_turkish_sort.py`,
  `test_reporting_pdf.py`, `test_production_kpi_derivation.py`,
  `test_contribution_calc.py`, `test_anomaly_demo_fallback.py`,
  `test_anomaly_analysis_schema.py`, `test_anomaly_orchestrator_helpers.py`,
  `test_assignment_resolver.py`, `test_shift_analysis.py`.
- **Integration testler** (`tests/integration/`) **çalışan, migrasyonu
  yapılmış ve seed edilmiş** bir Postgres bekler — gerçek DB'ye
  `SessionLocal()` üzerinden bağlanır, ayrı bir şema fixture'ı yoktur:
  `test_auth_flow.py`, `test_dashboard.py`, `test_plants_foremen.py`,
  `test_chiefs.py`, `test_data_quality.py`, `test_foreman_assignment_integrity.py`,
  `test_ingestion_idempotency.py`, `test_reports.py`, `test_contribution_works.py`,
  `test_anomalies.py`, `test_anomaly_analysis_service.py`,
  `test_anomaly_generator.py`, `test_world.py`, `test_tools.py`,
  `test_anomaly_orchestrator.py`, `test_shift_analysis.py`,
  `test_analytics_agir_gitme_display.py`,
  `test_production_kpi_derivation_plant_scoping.py`,
  `test_n_plus_one_regression.py` (Tespitler'e ait olanlar için önce
  `seed-anomalies` çalıştırılmış olmalıdır).

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
| `LLM_ENABLED` | `false` | `true` olmadıkça Tespitler modülü her zaman demo analiz döndürür |
| `LLM_API_KEY` | boş | LLM sağlayıcısı API anahtarı — yalnızca backend'de okunur, asla frontend'e gönderilmez |
| `LLM_MODEL` | `gpt-4o-mini` | Kullanılacak model adı |
| `LLM_BASE_URL` | `https://api.openai.com/v1` | OpenAI uyumlu `chat/completions` uç noktası |
| `LLM_TIMEOUT_SECONDS` | `30` | LLM isteği zaman aşımı süresi |
| `LLM_ANALYSIS_MODE` | `single_context` | Varsayılan analiz modu — `single_context` \| `tool_calling` |
| `LLM_TOOL_CALLING_ENABLED` | `true` | `false` ise `tool_calling` isteği bile `single_context`'e döner |
| `LLM_DEMO_TOOL_CALLING_ENABLED` | `true` | API anahtarı yokken `tool_calling` modunun demo akışının çalışıp çalışmayacağı |
| `LLM_MAX_TOOL_CALLS` | `10` | Bir analizde izin verilen azami araç çağrısı sayısı |
| `LLM_MAX_ANALYSIS_STEPS` | `12` | Azami LLM tur (round-trip) sayısı |
| `LLM_TOOL_TIMEOUT_SECONDS` | `10` | Tek bir araç çağrısı için azami süre |
| `LLM_ANALYSIS_TIMEOUT_SECONDS` | `60` | Tüm analiz için azami toplam süre |
| `LLM_MAX_DATE_RANGE_DAYS` | `365` | Araçlara verilebilecek azami tarih aralığı |

Ayarların tam listesi ve varsayılanlar için `backend/app/core/config.py`
(pydantic-settings `Settings` sınıfı) doğrudan referans alınmalıdır.

## Demo Girişi

- E-posta: `genel.mudur@formen-demo.com`
- Parola: `Demo!2026`

(Yalnızca `create-admin` komutu çalıştırıldıktan sonra geçerlidir; veritabanında
otomatik oluşturulmaz.)

## Bilinen Sınırlamalar / Kapsam Dışı

- Gerçek SAP entegrasyonu yapılmamıştır. `SAPDataProvider`
  (`app/services/providers/sap_provider.py`) yapılandırılmadığında
  `SAPNotConfiguredError`, yapılandırılsa bile `NotImplementedError`
  fırlatan bir iskelettir.
- `custom_formula` KPI hesaplama türü yalnızca sabit bir `formula_type`
  dispatch tablosu (`_CUSTOM_FORMULA_DISPATCH`) üzerinden desteklenir —
  keyfi kod veya kullanıcı tanımlı string formül çalıştırma riski
  bilinçli olarak dışarıda bırakılmıştır; jenerik motor (`calculate_raw_score`)
  tanımadığı bir hesaplama türü için hâlâ hata fırlatır (bkz.
  [KPI Hesaplama Motoru](#kpi-hesaplama-motoru)).
- `alembic downgrade` desteği `6ad63dbc115b` migration'ında bilinçli olarak
  kırıktır (`NotImplementedError`) — bu migration geri alınamaz.
- Bildirim/uyarı sistemi ve ayrı bir "Dönem Karşılaştırma" rapor türü
  uygulanmamıştır; ilgili karşılaştırmaların büyük kısmı zaten
  dashboard, tesis/formen/KPI detay ekranları ve Raporlar'daki "Vardiya
  Karşılaştırma" raporunda mevcuttur.
- Otomatik CI/CD pipeline'ı tanımlı değildir — **Doğrulanmalı**: dağıtım
  öncesi test/build adımlarının hangi süreçle (manuel, harici CI) icra
  edileceği bu depo dışında netleştirilmelidir.
- **Tespitler modülü** (bkz. [Tespitler Modülü](#tespitler-modülü-anomali-tespiti--yapay-zekâ-analizi))
  bilinçli olarak Aşama 1 + Aşama 2 kapsamındadır: tespitler sabit
  senaryolardan sentetik olarak üretilir (gerçek bir ML modeli
  eğitilmemiştir/kullanılmamıştır). Aşama 2'nin tool calling'i, LLM'nin
  backend'e **serbest/dinamik** bir sorgu atmasına izin vermez — yalnızca
  önceden tanımlanmış, salt-okunur, allowlist'teki 11 aracı çağırabilir; SQL
  üretemez, veritabanına yazamaz. Gelecekte sentetik veri sağlayıcılarının
  (`app/services/data_providers/synthetic.py`) gerçek Ocean/ML servisleriyle
  değiştirilmesi planlanmıştır — bkz. bir üstteki "Veri sağlayıcı katmanı"
  bölümü; araç adları, LLM şemaları ve frontend bileşenleri bu geçişten
  etkilenmeyecek şekilde tasarlanmıştır.
- Aşama 2'nin araç çağrı geçmişi (`anomaly_tool_calls`) prototip aşamasında
  hata ayıklama kolaylığı için her aracın **tam sonucunu** saklar (yalnızca
  sentetik operasyonel veri, gizli bilgi içermez). Gerçek bir üretime geçişte
  bu, veri minimizasyonu ilkesine uygun olarak özet/hash'e indirgenmelidir.
- Analiz durum modelindeki `cancelled` değeri şema/dokümantasyon
  tamlığı için tanımlıdır ancak arayüzde bir "analizi iptal et" eylemi
  henüz yoktur.
