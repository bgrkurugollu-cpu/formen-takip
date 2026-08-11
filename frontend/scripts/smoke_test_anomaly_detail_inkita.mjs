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

const kpiSelects = await page.locator("select").all();
for (const sel of kpiSelects) {
  const options = await sel.locator("option").allTextContents();
  const match = options.find((o) => o.includes("İnkita"));
  if (match) {
    await sel.selectOption({ label: match });
    break;
  }
}
await page.waitForTimeout(800);
await page.locator("table tbody tr").first().click();
await page.waitForSelector("text=Neden Bu Tespit Oluştu?", { timeout: 10000 });
await page.waitForTimeout(1200);

const breakdownCard = await page.locator("text=Dağılımı").first().count();
console.log(`${breakdownCard > 0 ? "OK " : "MISSING "} downtime breakdown card for İnkita anomaly`);

await page.screenshot({ path: `${shotDir}/anomaly-detail-inkita.png`, fullPage: true });

const themeBtn = page.locator('button[aria-label], header button').first();
await page.locator("header button").first().click().catch(() => {});
await page.waitForTimeout(500);
await page.screenshot({ path: `${shotDir}/anomaly-detail-light-theme.png`, fullPage: false });

console.log("console/page errors:", errors.length ? errors : "none");
await browser.close();
