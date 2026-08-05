import { chromium } from "playwright";

const shotDir = "C:/Users/yucel/AppData/Local/Temp/claude/c--Users-yucel-Desktop-formen-takip/206fba74-9200-4b9c-83be-9aeb712d967a/scratchpad";
const BASE = "http://localhost:8080";

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1600, height: 1100 } });
const errors = [];
page.on("pageerror", (e) => errors.push(String(e)));
page.on("console", (msg) => { if (msg.type() === "error") errors.push(msg.text()); });

await page.goto(`${BASE}/login`, { waitUntil: "networkidle" });
await page.fill('input[type="email"]', "genel.mudur@formen-demo.com");
await page.fill('input[type="password"]', "Demo!2026");
await page.click('button[type="submit"]');
await page.waitForSelector("text=Genel Bakış", { timeout: 15000 });
await page.waitForTimeout(500);

// Nav to Tespitler list page
await page.click('text=Tespitler');
await page.waitForSelector("text=Toplam Aktif Tespit", { timeout: 10000 });
await page.waitForTimeout(800);
await page.screenshot({ path: `${shotDir}/anomalies-list.png`, fullPage: true });
console.log("anomalies list page loaded, summary cards visible");

// Filter by severity=critical
await page.selectOption('select:near(:text("Önem Seviyesi"))', "critical").catch(() => {});
const severitySelects = await page.locator("select").all();
// fallback: pick the select whose options include 'Kritik'
for (const sel of severitySelects) {
  const options = await sel.locator("option").allTextContents();
  if (options.includes("Kritik")) {
    await sel.selectOption("critical");
    break;
  }
}
await page.waitForTimeout(800);
await page.screenshot({ path: `${shotDir}/anomalies-list-filtered-critical.png`, fullPage: true });
console.log("severity filter applied");

// clear filters
const clearBtn = page.locator('button:has-text("Filtreleri temizle")');
if (await clearBtn.count()) {
  await clearBtn.click();
  await page.waitForTimeout(500);
}

// Open first row's detail page
await page.locator("table tbody tr").first().click();
await page.waitForSelector("text=Sayısal Veriler", { timeout: 10000 });
await page.waitForTimeout(800);
await page.screenshot({ path: `${shotDir}/anomaly-detail.png`, fullPage: true });
console.log("detail page loaded");

// Trigger AI analysis
const analyzeBtn = page.locator('button:has-text("Yapay Zeka ile Analiz Et")');
if (await analyzeBtn.count()) {
  await analyzeBtn.click();
  await page.waitForSelector("text=analiz ediliyor", { timeout: 5000 }).catch(() => {});
  await page.screenshot({ path: `${shotDir}/anomaly-detail-analyzing.png`, fullPage: true });
  await page.waitForSelector("text=Yönetici Özeti", { timeout: 15000 });
  await page.waitForTimeout(500);
  await page.screenshot({ path: `${shotDir}/anomaly-detail-analyzed.png`, fullPage: true });
  console.log("AI analysis triggered and rendered");
} else {
  console.log("analysis already existed for first row, skipping analyze click");
}

console.log("console/page errors:", errors.length ? errors : "none");
await browser.close();
