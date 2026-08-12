import { chromium } from "playwright";
const shotDir = "C:/Users/yucel/AppData/Local/Temp/claude/c--Users-yucel-Desktop-formen-takip/cba24031-6be0-4bfb-b264-487ee701965d/scratchpad";
const BASE = "http://localhost:8080";
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
const errors = [];
page.on("pageerror", (e) => errors.push(String(e)));
page.on("console", (msg) => { if (msg.type() === "error") errors.push(msg.text()); });

await page.goto(`${BASE}/login`, { waitUntil: "networkidle" });
await page.fill('input[type="email"]', "genel.mudur@formen-demo.com");
await page.fill('input[type="password"]', "Demo!2026");
await page.click('button[type="submit"]');
await page.waitForSelector("text=Aktif Formen", { timeout: 15000 });

await page.goto(`${BASE}/shift-analysis`, { waitUntil: "networkidle" });
await page.waitForSelector("text=Vardiya Anomali Heatmap", { timeout: 15000 });
await page.waitForTimeout(1200);
await page.screenshot({ path: `${shotDir}/heatmap-mobile.png`, fullPage: false });
console.log("saved mobile heatmap screenshot");

await page.goto(`${BASE}/plants`, { waitUntil: "networkidle" });
await page.waitForTimeout(800);
const firstPlantLink = page.locator("a[href^='/plants/']").first();
if (await firstPlantLink.count()) {
  await firstPlantLink.click();
} else {
  await page.locator("tbody tr").first().click();
}
await page.waitForSelector("text=Formen–Vardiya Karşılaştırması", { timeout: 15000 });
await page.waitForTimeout(1200);
await page.screenshot({ path: `${shotDir}/plant-matrix-mobile.png`, fullPage: true });
console.log("saved mobile plant matrix screenshot");

console.log("CONSOLE ERRORS:", JSON.stringify(errors, null, 2));
await browser.close();
