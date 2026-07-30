# Frontend

React + TypeScript + Vite tabanlı istemci uygulaması. Mimari, dizin yapısı,
tema/renk kuralları ve dağıtım detayları için depo kökündeki
[README.md](../README.md#frontend) dosyasına bakın.

## Komutlar

```bash
npm install
npm run dev         # Vite dev sunucusu, :5173 — /api isteklerini :8000'e proxy'ler
npm run build       # tsc -b && vite build
npx tsc --noEmit    # yalnızca tip kontrolü
npm run lint        # oxlint
```

Playwright smoke test betikleri `scripts/` altındadır ve bu dizinden
(`frontend/`) çalıştırılmalıdır.
