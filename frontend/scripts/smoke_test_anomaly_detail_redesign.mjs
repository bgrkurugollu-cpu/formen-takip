import { chromium } from "playwright";

const shotDir = "C:/Users/yucel/AppData/Local/Temp/claude/c--Users-yucel-Desktop-formen-takip/ebd5c088-c4c2-4f43-923d-ff14bfbaf1c5/scratchpad";
const BASE = "http://localhost:8080";

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1600, height: 1400 } });
const errors = [];
page.on("pageerror", (e) => errors.push(String(e)));
page.on("console", (msg) => { if (msg.type() === "error") errors.push(msg.text()); });

await page.goto(`${BASE}/login`, { waitUntil: "networkidle" });
await page.fill('input[type="email"]', "genel.mudur@formen-demo.com");
await page.fill('input[type="password"]', "Demo!2026");
await page.click('button[type="submit"]');
await page.waitForSelector("text=Genel Bakış", { timeout: 15000 });

await page.click("text=Tespitler");
await page.waitForSelector("text=Toplam Aktif Tespit", { timeout: 10000 });
await page.waitForTimeout(600);

await page.locator("table tbody tr").first().click();
await page.waitForSelector("text=Neden Bu Tespit Oluştu?", { timeout: 10000 });
await page.waitForTimeout(1200);

const sectionsToCheck = [
  "Neden Bu Tespit Oluştu?",
  "KPI Trendi",
  "Neye Göre Anormal?",
  "Sorunun Kapsamı",
  "Sorumlu Formen",
  "Öncesi / Anomali Dönemi Karşılaştırması",
  "Aynı Dönemde Değişen KPI'lar",
  "Operasyonel Etki",
  "Benzer Geçmiş Tespitler",
  "Kök Neden ve Aksiyon Analizi",
];
for (const text of sectionsToCheck) {
  const found = await page.locator(`text=${text}`).first().count();
  console.log(`${found > 0 ? "OK " : "MISSING "} section: ${text}`);
}

await page.screenshot({ path: `${shotDir}/anomaly-detail-redesign-top.png`, fullPage: false });
await page.screenshot({ path: `${shotDir}/anomaly-detail-redesign-full.png`, fullPage: true });
console.log("screenshots captured for first anomaly");

const analyzeBtn = page.locator('button:has-text("Yapay Zeka ile Analiz Et")');
if (await analyzeBtn.count()) {
  await analyzeBtn.click();
  await page.waitForSelector("text=Yönetici Özeti", { timeout: 20000 });
  await page.waitForTimeout(500);
  const hypothesisTag = await page.locator("text=AI Hipotezi").first().count();
  console.log(`${hypothesisTag > 0 ? "OK " : "MISSING "} AI hypothesis card rendered`);
  await page.screenshot({ path: `${shotDir}/anomaly-detail-redesign-ai.png`, fullPage: true });
} else {
  console.log("analysis already existed, checking hypothesis cards directly");
  const hypothesisTag = await page.locator("text=AI Hipotezi").first().count();
  console.log(`${hypothesisTag > 0 ? "OK " : "MISSING "} AI hypothesis card rendered`);
}

console.log("console/page errors:", errors.length ? errors : "none");
await browser.close();
