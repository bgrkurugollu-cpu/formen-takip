import { chromium } from "playwright";

const shotDir = "C:/Users/yucel/AppData/Local/Temp/claude/c--Users-yucel-Desktop-formen-takip/206fba74-9200-4b9c-83be-9aeb712d967a/scratchpad";
const BASE = "http://localhost:8080";

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1600, height: 1200 } });
const errors = [];
page.on("pageerror", (e) => errors.push(String(e)));
page.on("console", (msg) => { if (msg.type() === "error") errors.push(msg.text()); });

await page.goto(`${BASE}/login`, { waitUntil: "networkidle" });
await page.fill('input[type="email"]', "genel.mudur@formen-demo.com");
await page.fill('input[type="password"]', "Demo!2026");
await page.click('button[type="submit"]');
await page.waitForSelector("text=Genel Bakış", { timeout: 15000 });

await page.click('text=Tespitler');
await page.waitForSelector("text=Toplam Aktif Tespit", { timeout: 10000 });
await page.locator("table tbody tr").nth(2).click();
await page.waitForSelector("text=Sayısal Veriler", { timeout: 10000 });

// Switch to "Derinlemesine Analiz" mode
await page.click('button:has-text("Derinlemesine Analiz")');
await page.waitForTimeout(200);
await page.screenshot({ path: `${shotDir}/tool-calling-mode-selected.png`, fullPage: true });

// Trigger analysis (works whether this is first analyze or a re-run)
const analyzeBtn = page.locator('button:has-text("Yapay Zeka ile Analiz Et")');
const refreshBtn = page.locator('button:has-text("Analizi Yenile")');
if (await analyzeBtn.count()) {
  await analyzeBtn.click();
} else {
  await refreshBtn.click();
}

await page.waitForSelector("text=analiz ediliyor", { timeout: 5000 }).catch(() => {});
await page.screenshot({ path: `${shotDir}/tool-calling-analyzing.png`, fullPage: true });
console.log("analyzing state captured");

await page.waitForSelector("text=Yönetici Özeti", { timeout: 90000 });
await page.waitForTimeout(500);
await page.screenshot({ path: `${shotDir}/tool-calling-result.png`, fullPage: true });
console.log("tool_calling analysis result rendered");

// Expand Analiz Adımları
const stepsToggle = page.locator('button:has-text("adımı göster")');
if (await stepsToggle.count()) {
  await stepsToggle.click();
  await page.waitForTimeout(300);
  await page.screenshot({ path: `${shotDir}/tool-calling-steps.png`, fullPage: true });
  console.log("tool call steps expanded");
}

console.log("console/page errors:", errors.length ? errors : "none");
await browser.close();
