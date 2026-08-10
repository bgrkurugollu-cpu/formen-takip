/**
 * Genel Bakış grafiklerinden detay sayfalarına giderken aktif filtreleri (tarih, fabrika,
 * tesis, şef, vardiya, KPI) taşımak için kullanılır — mevcut filtre yönetimi tamamen URL
 * search params üzerinden çalıştığından (bkz. useFilters), hedef sayfaya aynı search string'i
 * aktarmak yeterlidir.
 */
export function withSearchParam(search: string, key: string, value: string): string {
  const params = new URLSearchParams(search);
  params.set(key, value);
  return params.toString();
}
