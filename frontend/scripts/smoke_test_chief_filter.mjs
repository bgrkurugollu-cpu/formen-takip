import { chromium } from "playwright";

const shotDir = "C:/Users/yucel/AppData/Local/Temp/claude/c--Users-yucel-Desktop-formen-takip/0e4c88e4-79d1-40c8-8a63-b565af53ce69/scratchpad";
const BASE = "http://localhost:8080";

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1600, height: 900 } });
const errors = [];
page.on("pageerror", (e) => errors.push(String(e)));
page.on("console", (msg) => { if (msg.type() === "error") errors.push(msg.text()); });

await page.addInitScript((t) => localStorage.setItem("formen_theme", t), "light");
await page.goto(`${BASE}/login`, { waitUntil: "networkidle" });
await page.fill('input[type="email"]', "genel.mudur@formen-demo.com");
await page.fill('input[type="password"]', "Demo!2026");
await page.click('button[type="submit"]');
await page.waitForSelector("text=Genel Bakış", { timeout: 15000 });

await page.goto(`${BASE}/foremen`, { waitUntil: "networkidle" });
await page.waitForTimeout(1200);

const filterBar = page.locator("div.flex.flex-wrap.items-center.gap-2.rounded-lg.p-3").first();
const chiefBtn = filterBar.locator('button:has-text("Şef")');
console.log("Şef butonu disabled mi (tesis seçilmemişken):", await chiefBtn.isDisabled());
await chiefBtn.click();
await page.waitForTimeout(500);
await page.screenshot({ path: `${shotDir}/chief-open-no-plant.png` });

const optionCount = await page.locator('div.absolute label').count();
console.log("Görünen şef seçeneği sayısı (arama yokken):", optionCount);

await page.fill('input[placeholder="Ara..."]', "12. Tesis");
await page.waitForTimeout(500);
const filtered = await page.locator('div.absolute label').count();
console.log("'12. Tesis' aramasindan sonra:", filtered);
await page.screenshot({ path: `${shotDir}/chief-search.png` });

await page.locator('div.absolute label').first().click();
await page.waitForTimeout(300);
await page.keyboard.press("Escape");
await page.mouse.click(10, 400);
await page.waitForTimeout(1500);
await page.screenshot({ path: `${shotDir}/chief-selected-result.png`, fullPage: true });

const total = await page.locator("text=/Toplam \\d+ formen/").first().textContent();
console.log("Filtre sonrasi liste:", total?.trim());

console.log("CONSOLE ERRORS:", JSON.stringify(errors, null, 2));
await browser.close();
