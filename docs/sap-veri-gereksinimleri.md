# Formen Performans Takip Sistemi — SAP Veri Gereksinimleri Dokümanı

| | |
|---|---|
| **Doküman türü** | Veri gereksinimleri talebi |
| **Gönderen** | Formen Performans Takip Sistemi proje ekibi |
| **Alıcı** | SAP Birimi |
| **Konu** | Formen Performans Takip Sistemi'nin gerçek üretim verisiyle çalışabilmesi için SAP'ten sağlanması gereken veri alanlarının tanımlanması |
| **Kapsam** | Bu doküman yalnızca **hangi verinin** SAP tarafından sağlanması gerektiğini konu edinir; sistemin yazılım mimarisi, veritabanı tasarımı veya entegrasyon teknolojisi bu dokümanın kapsamı dışındadır |

---

## 1. Çalışmanın Amacı

Karaman'daki üretim tesislerinde görev yapan formenlerin (vardiya amirlerinin) performansı, üst yönetime sunulmak üzere KPI bazlı bir sistemle ölçülmektedir. Sistemin ön çalışma (pilot) aşamasında; üretim, fire, duruş, kalite ve iş güvenliği alanlarını temsil eden genel KPI'lar kullanılmıştır.

Sistemin gerçek kullanıma geçmesiyle birlikte, işletmenin kendi üretim sürecine özgü **beş KPI** esas alınacaktır (Bölüm 2). Bu KPI'ların formen bazında doğru, güvenilir ve karşılaştırılabilir şekilde hesaplanabilmesi; günlük, haftalık, aylık, yıllık ve özel tarih aralıklarında analiz edilebilmesi için gerekli ham verinin kaynağı SAP'tir.

Bu dokümanın amacı, sistemin ihtiyaç duyduğu veri alanlarını SAP birimine **eksiksiz ve net** biçimde iletmek; hangi verilerin hangi modülde/tablo veya işlem türünde tutulduğunun SAP tarafından teyit edilmesini sağlamak ve gerektiğinde SAP birimiyle birlikte netleştirilmesi gereken açık noktaları belirlemektir. Dokümanda yer alan bazı KPI tanımları ve hesaplama mantıkları, iş birimiyle yapılan ön görüşmelere dayanan **çalışma varsayımlarıdır**; bunlar Bölüm 9'da ayrıca işaretlenmiştir ve SAP birimi ile üretim/kalite süreç sahiplerinin ortak doğrulamasına açıktır.

---

## 2. Sistemin Kullanacağı KPI'lar

Gerçek kullanımda formen performansı aşağıdaki beş KPI üzerinden değerlendirilecektir:

| # | KPI Adı | Kısa Tanım |
|---|---|---|
| 1 | **Ağır Gitme** | Bir ürünün, tanımlı standart/nominal gramajının üzerinde üretilmesi (ör. 40 gr yerine 42 gr üretilmesi). Fazladan verilen malzeme (giveaway) kaybını ifade eder. |
| 2 | **GSF** | Tekrar üretimde kullanılamayan, geri kazanılamayan ve çöp veya hayvan yemi olarak değerlendirilen nihai fire. |
| 3 | **Iskarta** | Şekil veya yapı bozukluğu nedeniyle paketlenemeyen ancak ürün hamurlarına katılarak yeniden üretimde (rework) kullanılabilen geri dönüştürülebilir ürün. |
| 4 | **İnkita** (Duruş) | Hattın/makinenin durma süresi. **Planlı İnkita** (temizlik, format değişimi, planlı bakım vb.) ve **Plansız İnkita** (ani arıza, malzeme yokluğu, elektrik kesintisi vb.) olarak iki ayrı bileşende izlenecektir. |
| 5 | **Plana Uyum** | Formenin sorumlu olduğu üretimin, **güncel (revize edilmiş) üretim planına** — miktar ve zamanlama açısından — ne ölçüde uyduğu. |

**Not:** Ön çalışmada kullanılan Üretim Hedef Gerçekleşme Oranı, Fire Oranı, Plansız Duruş Süresi, Kalite Uygunluk Oranı ve İş Güvenliği/Süreç Uyum Puanı KPI'ları gerçek kullanımda **yukarıdaki beş KPI ile değiştirilecektir**. Bu doküman yalnızca yeni KPI seti için gerekli veriyi kapsar.

Her KPI için formen, şef, tesis, hat, vardiya ve şirket seviyesinde toplam skor; gerçekleşen/hedef karşılaştırmasına dayalı **ağırlıklı bir puanlama** ile hesaplanacaktır. KPI ağırlıkları ve hesaplama toleransları iş birimi tarafından ayrıca belirlenecek olup, bu doküman ağırlık/skor mantığını değil, hesaplama için **girdi olacak ham veriyi** konu almaktadır.

---

## 3. Tüm KPI'lar İçin Gerekli Ortak Veriler

Aşağıdaki veri grupları, beş KPI'nın tamamının doğru şekilde hesaplanabilmesi, doğru formene/tesise/vardiyaya bağlanabilmesi ve tarih aralığı bazlı analiz edilebilmesi için **her KPI kaydında ortak olarak** gereklidir.

| # | Veri Alanı | Açıklama | Zorunlu/İsteğe Bağlı | Beklenen Veri Türü | Örnek Değer | Kayıt Seviyesi | Güncelleme Sıklığı |
|---|---|---|---|---|---|---|---|
| 3.1 | Fabrika kodu | Üretimin yapıldığı fabrika (K1/K2) kodu | Zorunlu | Metin (kod) | `K1` | Fabrika | Değişiklikte |
| 3.2 | Tesis kodu | SAP'teki tesis/plant kodu | Zorunlu | Metin (kod) | `SAP-0029` | Tesis | Değişiklikte |
| 3.3 | Üretim hattı / iş merkezi kodu | Tesis içindeki hat veya iş merkezi tanımı | Zorunlu | Metin (kod) | `HAT-03` | Hat/İş merkezi | Değişiklikte |
| 3.4 | Makine/ekipman kodu | Hat içindeki ana makine/ekipman tanımı (varsa) | İsteğe bağlı | Metin (kod) | `MK-1204` | Makine | Değişiklikte |
| 3.5 | Şef sicil numarası | Formenin bağlı olduğu şefin SAP personel numarası | Zorunlu | Metin (kod) | `SAP-S-2901` | Şef | Değişiklikte |
| 3.6 | Formen sicil numarası | SAP personel numarası | Zorunlu | Metin (kod) | `SAP-P-29004` | Formen | Değişiklikte |
| 3.7 | Vardiya kodu | Vardiya tanımı ve saat aralığı | Zorunlu | Metin (kod) + saat | `V1` (08:00–16:00) | Vardiya | Değişiklikte |
| 3.8 | Üretim tarihi | Kaydın ait olduğu takvim günü | Zorunlu | Tarih (YYYY-AA-GG) | `2026-03-05` | Gün | Her kayıt |
| 3.9 | Üretim emri numarası | Kaydın bağlı olduğu SAP üretim emri | Zorunlu | Metin (kod) | `4500123456` | Üretim emri | Her kayıt |
| 3.10 | Ürün/malzeme kodu | SAP malzeme numarası | Zorunlu | Metin (kod) | `MLZ-100234` | Ürün | Değişiklikte |
| 3.11 | Ürün/malzeme açıklaması | Malzemenin okunabilir adı | Zorunlu | Metin | `Yem Tipi A – 40gr Paket` | Ürün | Değişiklikte |
| 3.12 | Parti/lot numarası | Üretilen partinin izlenebilirlik numarası | Zorunlu | Metin (kod) | `LOT-260305-07` | Parti | Her kayıt |
| 3.13 | Ölçü birimi | Miktar alanlarının birimi | Zorunlu | Metin (kod) | `KG`, `AD`, `GR` | Alan bazlı | Değişiklikte |
| 3.14 | Birim dönüşüm katsayısı | Farklı ölçü birimleri arası dönüşüm oranı (gr↔kg↔adet) | Zorunlu | Ondalık sayı | `1000` (gr→kg) | Malzeme | Değişiklikte |
| 3.15 | Kayıt/hareket benzersiz kimliği | SAP tarafındaki hareket/belge numarası (tekrar yükleme kontrolü için) | Zorunlu | Metin (kod) | `0004920381` | Her kayıt | Her kayıt |
| 3.16 | Kayıt oluşturma/güncelleme zaman damgası | Verinin SAP'te son değiştiği an | Zorunlu | Tarih-saat | `2026-03-05T14:32:10` | Her kayıt | Her kayıt |
| 3.17 | İptal/düzeltme/ters kayıt bilgisi | Kaydın iptal edildiğini veya bir ters kayıtla (storno) düzeltildiğini gösteren alan ve ilişkili orijinal belge numarası | Zorunlu | Boole + metin (kod) | `İptal: Evet, Orijinal: 0004920210` | Her kayıt | Her kayıt |

---

## 4. Formen, Vardiya, Tesis, Hat, Ürün ve Üretim Emri Eşleştirmeleri

KPI'ların formen bazında doğru hesaplanabilmesi için, bir performans olayının (üretim, duruş, fire vb.) **hangi formene ait olduğunun** tartışmasız biçimde belirlenebilmesi gerekir. Bunun için aşağıdaki eşleştirme (master data) verileri şarttır:

| # | Veri Alanı | Açıklama | Zorunlu/İsteğe Bağlı | Beklenen Veri Türü | Örnek Değer | Kayıt Seviyesi | Güncelleme Sıklığı |
|---|---|---|---|---|---|---|---|
| 4.1 | Formen–tesis–hat görevlendirmesi | Formenin hangi tesis ve hatta görevli olduğu | Zorunlu | İlişki tablosu | Formen `SAP-P-29004` → Tesis `SAP-0029`, Hat `HAT-03` | Görevlendirme | Değişiklikte |
| 4.2 | Formen–şef ilişkisi | Formenin bağlı olduğu şef | Zorunlu | İlişki tablosu | Formen `SAP-P-29004` → Şef `SAP-S-2901` | Görevlendirme | Değişiklikte |
| 4.3 | Görevlendirme geçerlilik tarih aralığı | Formenin bu tesis/hat/şef ilişkisinin **başlangıç ve bitiş tarihi** — formen tesis/hat/şef değiştirdiğinde yeni bir aralık açılır | Zorunlu | Tarih–tarih aralığı | `2025-01-01 – (açık)` | Görevlendirme | Değişiklikte |
| 4.4 | Formen–vardiya–tarih ilişkisi | Formenin **hangi tarihte hangi vardiyada** çalıştığı (vardiya, görev süresi içinde dönemsel değişebilir) | Zorunlu | Tarih bazlı çizelge | `2026-03-05 → V2` | Gün | Günlük/vardiyalık |
| 4.5 | Üretim emri–hat–tesis ilişkisi | Bir üretim emrinin hangi tesis/hatta açıldığı | Zorunlu | İlişki tablosu | `4500123456` → `HAT-03` | Üretim emri | Her emir |
| 4.6 | Üretim emri–ürün ilişkisi | Üretim emrinin hangi malzeme için açıldığı | Zorunlu | İlişki tablosu | `4500123456` → `MLZ-100234` | Üretim emri | Her emir |
| 4.7 | Üretim emri–vardiya/formen ilişkisi | Bir üretim emri kapsamındaki üretimin hangi vardiya(lar) ve formen(ler) tarafından gerçekleştirildiği | Zorunlu | İlişki tablosu | `4500123456` → `V2`, `SAP-P-29004` | Üretim emri / vardiya kırılımı | Her kayıt |

**Kritik nokta:** Bir formenin sorumluluk alanı bugünkü sistemde yalnızca *tesis* seviyesinde tutulmaktadır; yeni KPI seti (özellikle Ağır Gitme ve İnkita) **hat/iş merkezi seviyesinde** veri gerektirdiğinden, formen–hat eşleştirmesinin de en az formen–tesis eşleştirmesi kadar güvenilir ve tarih aralıklı (4.3) olması gerekmektedir. Bu eşleştirmenin SAP'te mi (ör. PP/HR modülü) yoksa üretim planlama/vardiya çizelgeleme sisteminde mi tutulduğunun SAP birimi tarafından teyit edilmesi gerekmektedir (bkz. Bölüm 9).

---

## 5. Her KPI İçin Ayrı Ayrı Gerekli SAP Verileri

### 5.1 Ağır Gitme

**Tanım:** Üretilen ürünün, malzeme ana verisinde tanımlı standart/nominal gramajının üzerinde üretilmesi (ör. 40 gr hedef yerine 42 gr üretilmesi). İşletmeye maliyeti, standardın üzerinde verilen fazladan malzeme miktarıdır.

| Alan Adı | Açıklama | Kullanım | Zorunlu/İsteğe Bağlı | Veri Türü | Örnek Değer | Kayıt Seviyesi | Güncelleme Sıklığı |
|---|---|---|---|---|---|---|---|
| Standart/nominal gramaj | Malzeme ana verisinde tanımlı hedef birim ağırlık | Hedef değer | Zorunlu | Ondalık sayı (gr) | `40.00` | Ürün (malzeme master) | Değişiklikte |
| Alt–üst tolerans limiti | Standarttan sapmanın kabul edilebilir aralığı (varsa kalite/regülasyon kaynaklı) | Hesaplama toleransı | İsteğe bağlı | Ondalık sayı (gr) | `39.50 – 40.50` | Ürün (malzeme master) | Değişiklikte |
| Gerçekleşen ortalama gramaj | Üretim/paketleme hattında ölçülen (tartım sistemi veya kalite kontrol örneklemesi) fiili birim ağırlık | Gerçekleşen değer | Zorunlu | Ondalık sayı (gr) | `42.10` | Üretim emri / parti / vardiya | Vardiyalık veya parti bazlı |
| Ölçüm/örnekleme sayısı | Ortalamanın kaç örneğe dayandığı | Veri güvenilirliği | İsteğe bağlı | Tam sayı | `24` | Üretim emri / parti | Vardiyalık |
| Üretilen adet | Aynı dönemde üretilen toplam adet (fazladan malzeme maliyetinin toplam kg'a çevrilebilmesi için) | Toplam kayıp hesaplama | Zorunlu | Tam sayı | `18.400` | Üretim emri / vardiya | Vardiyalık |
| Sapma nedeni (varsa) | Kalibrasyon hatası, hammadde değişimi vb. neden kodu | Kök neden analizi | İsteğe bağlı | Metin (kod) | `KALIBRASYON` | Üretim emri / vardiya | Oluştuğunda |

### 5.2 Iskarta (Geri Dönüştürülebilir Ürün / Rework)

**Tanım:** Şekil veya yapı bozukluğu nedeniyle paketlenemeyen ancak ürün hamurlarına katılarak yeniden işlenerek (rework) tekrar üretimde kullanılabilen geri dönüştürülebilir ürün/malzeme miktarı.

| Alan Adı | Açıklama | Kullanım | Zorunlu/İsteğe Bağlı | Veri Türü | Örnek Değer | Kayıt Seviyesi | Güncelleme Sıklığı |
|---|---|---|---|---|---|---|---|
| Iskarta miktarı | Rework'e (ürün hamuruna geri katıma) ayrılan miktar | Gerçekleşen değer | Zorunlu | Ondalık sayı (kg) | `85.50` | Üretim emri / vardiya | Vardiyalık |
| Toplam üretim miktarı (aynı dönem) | Iskarta oranının hesaplanabilmesi için payda | Oran hesaplama | Zorunlu | Ondalık sayı (kg) | `4.200,00` | Üretim emri / vardiya | Vardiyalık |
| Iskarta oluşma nedeni | Ana/alt neden kodu (ör. şekil bozukluğu, yapı bozukluğu) | Kök neden analizi | Zorunlu | Metin (kod) | `SEKIL_BOZUKLUGU` | Kayıt bazlı | Oluştuğunda |
| Iskarta'nın SAP'teki hareket/malzeme türü | Iskarta'nın SAP'te ayrı bir malzeme numarası veya hareket türü ile mi izlendiği | Veri eşleştirme | Zorunlu (SAP tarafından teyit) | Metin (kod) | *(SAP tarafından belirlenecek)* | Malzeme master | Değişiklikte |
| Rework sonucu tekrar üretime giriş tarihi/miktarı | Iskarta'nın hangi tarihte/parti ile ürün hamuruna geri katıldığı | İzlenebilirlik (opsiyonel analiz) | İsteğe bağlı | Tarih + ondalık sayı | `2026-03-07 → 82.00 kg` | Parti | Oluştuğunda |

### 5.3 GSF (Geri Kazanılamayan Nihai Fire)

**Tanım:** Tekrar üretimde kullanılamayan, geri kazanılamayan ve çöp veya hayvan yemi olarak değerlendirilen nihai fire.

| Alan Adı | Açıklama | Kullanım | Zorunlu/İsteğe Bağlı | Veri Türü | Örnek Değer | Kayıt Seviyesi | Güncelleme Sıklığı |
|---|---|---|---|---|---|---|---|
| GSF miktarı | Nihai olarak elenen (geri kazanılamayan) miktar | Gerçekleşen değer | Zorunlu | Ondalık sayı (kg) | `132.00` | Üretim emri / vardiya | Vardiyalık |
| Toplam üretim/girdi miktarı (aynı dönem) | GSF oranının hesaplanabilmesi için payda | Oran hesaplama | Zorunlu | Ondalık sayı (kg) | `4.200,00` | Üretim emri / vardiya | Vardiyalık |
| GSF türü | Hammadde/yarı mamul/mamul kaynaklı ayrımı | Analiz kırılımı | Zorunlu | Metin (kod) | `MAMUL_KAYNAKLI` | Kayıt bazlı | Oluştuğunda |
| GSF ana/alt neden kodu | GSF'ye yol açan neden | Kök neden analizi | Zorunlu | Metin (kod) | `NEM_ORANI_YUKSEK` | Kayıt bazlı | Oluştuğunda |
| Yönlendirildiği yan ürün/malzeme kodu | GSF'nin hayvan yemi olarak değerlendirildiği SAP yan ürün (co-product/by-product) malzeme numarası | İzlenebilirlik ve değerleme | İsteğe bağlı | Metin (kod) | `YANURUN-YEM-01` | Kayıt bazlı | Oluştuğunda |

### 5.4 İnkita (Planlı / Plansız Duruş)

**Tanım:** Hattın/makinenin durma süresi. Planlı İnkita (temizlik, format değişimi, planlı bakım) ve Plansız İnkita (ani arıza, malzeme yokluğu, elektrik kesintisi vb.) olarak iki ayrı bileşende izlenir.

| Alan Adı | Açıklama | Kullanım | Zorunlu/İsteğe Bağlı | Veri Türü | Örnek Değer | Kayıt Seviyesi | Güncelleme Sıklığı |
|---|---|---|---|---|---|---|---|
| Duruş başlangıç tarih-saati | Duruşun başladığı an | Süre hesaplama | Zorunlu | Tarih-saat | `2026-03-05 10:15:00` | Duruş olayı | Oluştuğunda |
| Duruş bitiş tarih-saati | Duruşun sona erdiği an | Süre hesaplama | Zorunlu | Tarih-saat | `2026-03-05 10:47:00` | Duruş olayı | Oluştuğunda |
| Duruş süresi | Bitiş–başlangıç farkı (SAP tarafından hesaplanmış veya sistemin kendisinin hesaplaması) | Gerçekleşen değer | Zorunlu | Tam sayı (dakika) | `32` | Duruş olayı | Oluştuğunda |
| Planlı/Plansız bayrağı | Duruşun planlı mı plansız mı olduğu | KPI bileşen ayrımı | Zorunlu | Boole/kod | `PLANSIZ` | Duruş olayı | Oluştuğunda |
| Ana neden kodu | Duruşun üst kategori nedeni (Bakım/Elektrik/Malzeme/Temizlik/Format Değişimi vb.) | Kök neden analizi | Zorunlu | Metin (kod) | `MEKANIK_ARIZA` | Duruş olayı | Oluştuğunda |
| Alt neden kodu | Ana nedenin detayı | Kök neden analizi | İsteğe bağlı | Metin (kod) | `RULMAN_ARIZASI` | Duruş olayı | Oluştuğunda |
| Sorumlu birim | Duruşu gidermekle/onaylamakla sorumlu birim | Analiz kırılımı, süreç sahipliği | Zorunlu | Metin (kod) | `BAKIM` | Duruş olayı | Oluştuğunda |
| Formen kontrolünde olup olmadığı | Duruşun formenin karar/etki alanında olup olmadığı (adil skorlama için) | KPI adalet ayarı | Zorunlu (tanımı SAP+iş birimiyle netleştirilecek) | Boole | `Hayır (dış kaynaklı arıza)` | Duruş olayı | Oluştuğunda |
| İlgili hat/makine kodu | Duruşun gerçekleştiği hat/ekipman | Konum kırılımı | Zorunlu | Metin (kod) | `HAT-03` / `MK-1204` | Duruş olayı | Oluştuğunda |
| İlişkili üretim emri (varsa) | Duruşun hangi üretim emri sırasında gerçekleştiği | İzlenebilirlik | İsteğe bağlı | Metin (kod) | `4500123456` | Duruş olayı | Oluştuğunda |

### 5.5 Plana Uyum

**Tanım:** Formenin sorumlu olduğu üretimin, güncel (en son revize edilmiş) üretim planına — miktar ve zamanlama açısından — ne ölçüde uyduğu.

| Alan Adı | Açıklama | Kullanım | Zorunlu/İsteğe Bağlı | Veri Türü | Örnek Değer | Kayıt Seviyesi | Güncelleme Sıklığı |
|---|---|---|---|---|---|---|---|
| Planlanan üretim miktarı (güncel revizyon) | Üretim emrinin en son revize edilmiş plan miktarı | Hedef değer | Zorunlu | Ondalık sayı | `4.500,00 kg` | Üretim emri / vardiya | Revize edildikçe |
| Planlanan başlangıç tarih-saati (güncel revizyon) | Üretimin planlanan başlama anı | Hedef değer | Zorunlu | Tarih-saat | `2026-03-05 08:00:00` | Üretim emri / vardiya | Revize edildikçe |
| Planlanan bitiş tarih-saati (güncel revizyon) | Üretimin planlanan bitiş anı | Hedef değer | Zorunlu | Tarih-saat | `2026-03-05 16:00:00` | Üretim emri / vardiya | Revize edildikçe |
| Plan revizyon numarası/tarihi | Hangi revizyonun ilgili dönemde "güncel" sayıldığının belirlenebilmesi için revizyon kimliği ve geçerlilik anı | Doğru revizyonun seçilmesi | Zorunlu | Metin (kod) + tarih-saat | `Rev.3 – 2026-03-04 18:20` | Üretim emri | Revize edildikçe |
| İlk (dondurulmuş) plan miktarı/zamanlaması | Üretim emri ilk onaylandığındaki plan değerleri | İkincil analiz (plan kararlılığı) | İsteğe bağlı | Ondalık sayı + tarih-saat | `4.300,00 kg / 08:00–15:30` | Üretim emri | Bir kez (ilk onayda) |
| Gerçekleşen üretim miktarı | Fiilen üretilen miktar | Gerçekleşen değer | Zorunlu | Ondalık sayı | `4.410,00 kg` | Üretim emri / vardiya | Vardiyalık |
| Gerçekleşen başlangıç tarih-saati | Üretimin fiilen başladığı an | Gerçekleşen değer | Zorunlu | Tarih-saat | `2026-03-05 08:12:00` | Üretim emri / vardiya | Oluştuğunda |
| Gerçekleşen bitiş tarih-saati | Üretimin fiilen sona erdiği an | Gerçekleşen değer | Zorunlu | Tarih-saat | `2026-03-05 16:05:00` | Üretim emri / vardiya | Oluştuğunda |
| Standart üretim hızı | Hat/ürün için tanımlı nominal üretim hızı | Bağlamsal analiz (opsiyonel, OEE benzeri ek analizler için) | İsteğe bağlı | Ondalık sayı (adet veya kg / saat) | `560 kg/saat` | Ürün-Hat kombinasyonu | Değişiklikte |
| Gerçekleşen üretim hızı | Ölçülen fiili üretim hızı | Bağlamsal analiz (opsiyonel) | İsteğe bağlı | Ondalık sayı (adet veya kg / saat) | `540 kg/saat` | Üretim emri / vardiya | Vardiyalık |

---

## 6. KPI Hesaplamaları İçin Gerekli Hedef, Gerçekleşen, Süre, Miktar ve Neden Kodu Verileri

Beş KPI'nın tamamı, aynı temel veri iskeletine oturur. Aşağıdaki tablo bu iskeleti KPI bazında özetler; ayrıntılı alan tanımları Bölüm 5'tedir.

| KPI | Hedef Değer | Gerçekleşen Değer | Süre | Miktar | Neden Kodu |
|---|---|---|---|---|---|
| Ağır Gitme | Standart gramaj | Ölçülen ortalama gramaj | — | Üretilen adet (toplam kayıp hesaplama için) | Sapma nedeni (isteğe bağlı) |
| Iskarta | — (oran bazlı KPI, hedef iş birimince belirlenecek) | Iskarta miktarı | — | Toplam üretim miktarı (oran paydası) | Iskarta oluşma nedeni |
| GSF | — (oran bazlı KPI, hedef iş birimince belirlenecek) | GSF miktarı | — | Toplam üretim/girdi miktarı (oran paydası) | GSF ana/alt neden kodu |
| İnkita | — (oran/süre bazlı KPI, hedef iş birimince belirlenecek) | Duruş süresi | Duruş süresi (dakika) | — | Ana/alt neden kodu, sorumlu birim |
| Plana Uyum | Planlanan miktar ve zamanlama (güncel revizyon) | Gerçekleşen miktar ve zamanlama | Planlanan/gerçekleşen süre farkı | Planlanan/gerçekleşen miktar | — |

Tüm KPI'larda hedef değerlerin (varsa) SAP'te mi yoksa şirketin kendi hedef yönetim sürecinde mi tutulacağı ayrıca netleştirilmelidir (bkz. Bölüm 9).

---

## 7. Grafik ve Analizlerin Oluşturulabilmesi İçin Gerekli Detay Alanları

Yönetim panosu, tesis/şef/formen detay ekranları ve KPI analiz ekranlarında; trend grafikleri, tesis/vardiya karşılaştırmaları, en iyi/kötü formen sıralamaları ve dönemsel karşılaştırmalar üretilmektedir. Bu analizlerin doğru kırılımda çalışabilmesi için verinin şu boyutlarla birlikte gelmesi gerekir:

| Boyut | Neden Gerekli | İlgili Bölüm |
|---|---|---|
| Gün bazlı tarih damgası | Günlük/haftalık/aylık/yıllık ve özel tarih aralığı analizleri; trend grafikleri | 3.8 |
| Vardiya | Vardiyalar arası karşılaştırma grafiği | 3.7, 4.4 |
| Tesis / Fabrika / Hat | Tesis ve fabrika bazlı karşılaştırma, hat bazlı Ağır Gitme/İnkita analizi | 3.1–3.4 |
| Formen / Şef | Formen sıralaması, şef ekip skorları | 3.5, 3.6, 4.1, 4.2 |
| Neden kodu (ana/alt) | Kök neden dağılım grafikleri (ör. "en çok duruşa neden olan 5 sebep") | 5.2–5.4 |
| Ürün/malzeme | Ürün bazlı Ağır Gitme/Iskarta/GSF analizleri | 3.10, 3.11 |

**Önemli:** Grafiklerin ve trend analizlerinin anlamlı olabilmesi için veri **gün ve vardiya kırılımında** gelmelidir; yalnızca aylık toplam/ortalama şeklinde gelen veri, günlük/haftalık trend ve vardiya karşılaştırma grafiklerinin üretilmesine imkân tanımaz.

---

## 8. Beklenen Veri Ayrıntı Seviyesi ve Güncelleme Sıklığı

**Kayıt seviyesi (detay/grain):** Her performans olayı; **formen + KPI + tarih + vardiya + üretim emri** kombinasyonunda benzersiz olacak şekilde sağlanmalıdır. Duruş (İnkita) gibi olay bazlı veriler için ayrıca **olay (event) seviyesinde** kayıt (başlangıç-bitiş saatiyle) beklenmektedir; günlük toplamlaştırılmış (aggregate) duruş süresi tek başına yeterli değildir, çünkü neden kodu ve sorumlu birim bilgisi olay bazında değişebilir.

**Güncelleme sıklığı:** Vardiya kapanışını takiben, en geç **bir sonraki iş günü içinde** ilgili vardiyanın tüm KPI verilerinin sağlanması beklenmektedir (günlük toplu aktarım). Gerçek zamanlı veya gün içi kademeli aktarım mümkünse, veri kalitesi ve erken uyarı açısından tercih edilir; ancak asgari beklenti günlük toplu (batch) aktarımdır. Plan revizyonları (Bölüm 5.5) oluştukları anda veya en geç aynı gün içinde yansıtılmalıdır, aksi hâlde "Plana Uyum" hesaplaması yanlış revizyonla karşılaştırma yapabilir.

**Geçmişe dönük veri:** Sistemin devreye alınabilmesi için en az **son 12 aylık** geçmiş veri (varsa) talep edilmektedir; bu, dönemsel karşılaştırma ve trend analizlerinin devreye alım anından itibaren anlamlı olabilmesi içindir.

---

## 9. SAP Birimi Tarafından Açıklanması veya Doğrulanması Gereken Konular

1. **Iskarta'nın SAP'teki temsili:** Iskarta, SAP'te ayrı bir malzeme numarası, hareket türü veya parti statüsü ile mi izlenmektedir? Yoksa manuel/harici bir kayıt mı gerekecektir? (Bölüm 5.2)
2. **Formen–hat görevlendirmesinin kaynağı:** Formenin hangi tarih/saat aralığında hangi tesis/hattan sorumlu olduğu bilgisi SAP'in bir modülünde (ör. PP, HR) mi tutulmaktadır, yoksa ayrı bir vardiya çizelgeleme sisteminde mi? (Bölüm 4)
3. **Üretim planı revizyon geçmişi:** SAP üretim planlaması, her revizyonu (miktar/zamanlama) tarihçeli olarak saklıyor mu? "Güncel plan" ifadesinin, ilgili vardiya/tarih için **o an geçerli olan** revizyon anlamına geldiği doğrulanmalı; bu revizyonun geriye dönük olarak (ör. bir ay sonra) hâlâ sorgulanabilir olup olmadığı netleştirilmelidir. (Bölüm 5.5)
4. **Standart/nominal gramaj ve tolerans verisi:** Bu bilgi malzeme ana verisinde mi tutulmaktadır, yoksa kalite biriminin ayrı bir spesifikasyon kaynağında mı? (Bölüm 5.1)
5. **Tartım/ölçüm verisinin kaynağı:** Ağır Gitme KPI'sı için gerekli "gerçekleşen ortalama gramaj" verisi otomatik tartım sisteminden mi, yoksa kalite kontrol örneklemesinden mi gelecektir? Örnekleme sıklığı ve güvenilirliği ne olacaktır? (Bölüm 5.1)
6. **İnkita'da "formenin kontrolünde olup olmadığı" ayrımı:** Bu ayrımın SAP'te mevcut bir alan/neden kodu sınıflandırmasıyla mı yapılacağı, yoksa yeni bir sınıflandırma kuralı mı gerektireceği; bu konunun SAP birimi ile birlikte üretim/bakım süreç sahiplerince de doğrulanması gerekir. (Bölüm 5.4)
7. **Neden kodu (ana/alt) master listesi:** Ağır Gitme, GSF, Iskarta ve İnkita için kullanılacak ana/alt neden kodu listelerinin SAP'teki mevcut master data'dan mı geleceği, yoksa yeni bir kod listesi tanımlanmasının mı gerekeceği. (Bölüm 5.2–5.4)
8. **Ölçü birimi dönüşüm katsayılarının kaynağı:** Gram–kilogram–adet dönüşümlerinin malzeme bazında SAP'te tanımlı olup olmadığı. (Bölüm 3.14)
9. **GSF'nin yan ürün değerlemesi:** GSF'nin hayvan yemi olarak yönlendirildiği yan ürün/malzeme kodunun SAP'te co-product/by-product olarak tanımlı olup olmadığı. (Bölüm 5.3)
10. **KPI hedeflerinin kaynağı:** Iskarta, GSF ve İnkita için "hedef/tolerans/kritik eşik" değerlerinin SAP'te mi (ör. standart maliyet, kalite spesifikasyonu) yoksa şirketin kendi hedef belirleme sürecinde mi tanımlanacağı. (Bölüm 6)
11. **İptal/ters kayıt senaryoları:** Bir üretim emri veya duruş kaydı SAP'te iptal edildiğinde/düzeltildiğinde, bu değişikliğin daha önce aktarılmış veriye nasıl yansıtılacağı (yeni bir ters kayıt mı gönderilecek, yoksa orijinal kayıt mı güncellenecek). (Bölüm 3.17)
12. **Veri aktarım yöntemi ve zamanlaması:** Günlük toplu aktarımın hangi saatte, hangi yöntemle (dosya, servis vb.) yapılacağı — bu doküman kapsamında yalnızca *içerik/alan* talebi yer almaktadır; aktarım yöntemi SAP birimi ile ayrıca planlanmalıdır.

---

## 10. SAP'ten Talep Edilecek Alanları Özetleyen Veri Talep Tablosu

| Grup | Veri Alanı | Zorunlu/İsteğe Bağlı | Veri Türü | Kayıt Seviyesi | Güncelleme Sıklığı |
|---|---|---|---|---|---|
| Ortak | Fabrika kodu | Zorunlu | Metin | Fabrika | Değişiklikte |
| Ortak | Tesis kodu | Zorunlu | Metin | Tesis | Değişiklikte |
| Ortak | Üretim hattı / iş merkezi kodu | Zorunlu | Metin | Hat | Değişiklikte |
| Ortak | Makine/ekipman kodu | İsteğe bağlı | Metin | Makine | Değişiklikte |
| Ortak | Şef sicil numarası | Zorunlu | Metin | Şef | Değişiklikte |
| Ortak | Formen sicil numarası | Zorunlu | Metin | Formen | Değişiklikte |
| Ortak | Vardiya kodu ve saat aralığı | Zorunlu | Metin + saat | Vardiya | Değişiklikte |
| Ortak | Üretim tarihi | Zorunlu | Tarih | Gün | Her kayıt |
| Ortak | Üretim emri numarası | Zorunlu | Metin | Üretim emri | Her kayıt |
| Ortak | Ürün/malzeme kodu ve açıklaması | Zorunlu | Metin | Ürün | Değişiklikte |
| Ortak | Parti/lot numarası | Zorunlu | Metin | Parti | Her kayıt |
| Ortak | Ölçü birimi ve dönüşüm katsayısı | Zorunlu | Metin + sayı | Malzeme | Değişiklikte |
| Ortak | Kayıt benzersiz kimliği ve zaman damgası | Zorunlu | Metin + tarih-saat | Her kayıt | Her kayıt |
| Ortak | İptal/düzeltme/ters kayıt bilgisi | Zorunlu | Boole + metin | Her kayıt | Her kayıt |
| Eşleştirme | Formen–tesis–hat–şef görevlendirmesi ve geçerlilik tarih aralığı | Zorunlu | İlişki tablosu | Görevlendirme | Değişiklikte |
| Eşleştirme | Formen–vardiya–tarih ilişkisi | Zorunlu | Tarih bazlı çizelge | Gün | Günlük/vardiyalık |
| Eşleştirme | Üretim emri–hat–ürün–vardiya–formen ilişkisi | Zorunlu | İlişki tablosu | Üretim emri | Her emir |
| Ağır Gitme | Standart gramaj, tolerans, gerçekleşen ortalama gramaj, üretilen adet, sapma nedeni | Zorunlu (tolerans/neden isteğe bağlı) | Sayı + metin | Üretim emri / vardiya / parti | Vardiyalık |
| Iskarta | Iskarta miktarı, toplam üretim miktarı, oluşma nedeni, SAP hareket/malzeme türü, rework giriş bilgisi | Zorunlu (rework girişi isteğe bağlı) | Sayı + metin | Üretim emri / vardiya | Vardiyalık |
| GSF | GSF miktarı, toplam üretim/girdi miktarı, tür, ana/alt neden kodu, yan ürün kodu | Zorunlu (yan ürün kodu isteğe bağlı) | Sayı + metin | Üretim emri / vardiya | Vardiyalık |
| İnkita | Başlangıç/bitiş saati, süre, planlı/plansız bayrağı, ana/alt neden kodu, sorumlu birim, formen kontrolü ayrımı, hat/makine kodu, üretim emri | Zorunlu (alt neden, üretim emri isteğe bağlı) | Tarih-saat + sayı + metin + boole | Duruş olayı | Oluştuğunda |
| Plana Uyum | Planlanan miktar/başlangıç/bitiş (güncel revizyon), revizyon no/tarihi, ilk plan (opsiyonel), gerçekleşen miktar/başlangıç/bitiş, standart/gerçekleşen hız (opsiyonel) | Zorunlu (ilk plan ve hız alanları isteğe bağlı) | Sayı + tarih-saat + metin | Üretim emri / vardiya | Vardiyalık, revizyonlar oluştuğunda |

---

*Bu doküman, Formen Performans Takip Sistemi'nin gerçek üretim verisiyle çalışabilmesi için gerekli SAP veri alanlarını konu edinir. KPI tanımlarındaki bazı ayrıntılar (Bölüm 9) SAP birimi ve ilgili süreç sahipleriyle birlikte netleştirilmek üzere açık madde olarak işaretlenmiştir; bu maddelerin netleşmesiyle birlikte doküman güncellenecektir.*
