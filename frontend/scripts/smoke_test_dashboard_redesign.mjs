import { chromium } from "playwright";

const shotDir = "C:/Users/yucel/AppData/Local/Temp/claude/c--Users-yucel-Desktop-formen-takip/31b57c51-60e2-4db0-97e2-ae757b0d1730/scratchpad";
const BASE = "http://localhost:8080";

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
const errors = [];
page.on("pageerror", (e) => errors.push(String(e)));
page.on("console", (msg) => { if (msg.type() === "error") errors.push(msg.text()); });

await page.goto(`${BASE}/login`, { waitUntil: "networkidle" });
await page.fill('input[type="email"]', "genel.mudur@formen-demo.com");
await page.fill('input[type="password"]', "Demo!2026");
await page.click('button[type="submit"]');
await page.waitForSelector("text=Genel Bakış", { timeout: 15000 });
await page.waitForTimeout(2000);

console.log("HAS Tesis Performans Haritası:", await page.isVisible("text=Tesis Performans Haritası"));
console.log("HAS Gelişim Gösteren Formenler:", await page.isVisible("text=Gelişim Gösteren Formenler"));
console.log("HAS En Fazla Performans Kaybı:", await page.isVisible("text=En Fazla Performans Kaybı"));
console.log("HAS Formen filter chip:", await page.isVisible("button:has-text('Formen')"));
console.log("HAS Veri Yok legend:", await page.isVisible("text=Veri Yok"));

await page.screenshot({ path: `${shotDir}/dashboard-redesign-top.png`, fullPage: false });

// scroll down to trigger sticky filter bar and check heatmap render
await page.evaluate(() => window.scrollTo(0, 900));
await page.waitForTimeout(500);
await page.screenshot({ path: `${shotDir}/dashboard-redesign-scrolled.png`, fullPage: false });

await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
await page.waitForTimeout(500);
await page.screenshot({ path: `${shotDir}/dashboard-redesign-heatmap.png`, fullPage: false });

// Open the Formen filter facet and select one
await page.evaluate(() => window.scrollTo(0, 0));
await page.waitForTimeout(300);
const formenButton = page.locator("button", { hasText: "Formen" }).first();
await formenButton.click();
await page.waitForTimeout(500);
await page.fill('input[placeholder*="sicil"]', "a");
await page.waitForTimeout(800);
const firstOption = page.locator("label", { hasText: "—" }).first();
if (await firstOption.count() > 0) {
  await firstOption.click();
  await page.waitForTimeout(500);
}
await page.keyboard.press("Escape");
await page.waitForTimeout(300);
console.log("HAS active filter chip strip:", await page.isVisible("text=Aktif filtreler:"));
await page.screenshot({ path: `${shotDir}/dashboard-redesign-foreman-filter.png`, fullPage: false });

// Navigate to a foreman detail page (profile)
await page.goto(`${BASE}/foremen`, { waitUntil: "networkidle" });
await page.waitForTimeout(1500);
await page.click("table tbody tr:first-child");
await page.waitForTimeout(1500);
console.log("HAS Bu Dönem Performansı:", await page.isVisible("text=Bu Dönem Performansı"));
console.log("HAS Güçlü Alanlar:", await page.isVisible("text=Güçlü Alanlar"));
console.log("HAS Geliştirilmesi Gereken Alanlar:", await page.isVisible("text=Geliştirilmesi Gereken Alanlar"));
console.log("HAS KPI Karşılaştırması:", await page.isVisible("text=KPI Karşılaştırması"));
console.log("HAS Sorumlu Tesisler:", await page.isVisible("text=Sorumlu Tesisler:"));
await page.screenshot({ path: `${shotDir}/foreman-profile.png`, fullPage: true });

console.log("CONSOLE ERRORS:", JSON.stringify(errors, null, 2));
await browser.close();
