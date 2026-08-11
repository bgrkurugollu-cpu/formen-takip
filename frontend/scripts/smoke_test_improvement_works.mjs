import { chromium } from "playwright";

const shotDir = "C:/Users/yucel/AppData/Local/Temp/claude/c--Users-yucel-Desktop-formen-takip/23f79635-4ddc-4250-8cf8-00dfd457c2b9/scratchpad";
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
await page.waitForTimeout(1000);

await page.waitForSelector("text=Katkı ve İyileştirme Çalışmaları Özeti", { timeout: 10000 });
await page.screenshot({ path: `${shotDir}/dashboard-with-contrib.png` });
console.log("dashboard summary section visible");

await page.click('text=Katkı ve İyileştirme Çalışmaları');
await page.waitForSelector("text=Yeni Çalışma Ekle", { timeout: 10000 });
await page.waitForTimeout(1000);
await page.screenshot({ path: `${shotDir}/improvement-works-list-card.png`, fullPage: true });
console.log("list page (card view) loaded");

await page.click('button:has-text("Tablo")');
await page.waitForTimeout(500);
await page.screenshot({ path: `${shotDir}/improvement-works-list-table.png`, fullPage: true });
console.log("list page (table view) loaded");
await page.click('button:has-text("Kart")');
await page.waitForTimeout(500);

const firstCard = page.locator('a[href^="/improvement-works/"]').first();
await firstCard.click();
await page.waitForSelector("text=PDF olarak indir", { timeout: 10000 });
await page.waitForTimeout(500);
await page.screenshot({ path: `${shotDir}/improvement-work-detail.png`, fullPage: true });
console.log("detail page loaded");

await page.goBack();
await page.waitForTimeout(500);

await page.click('text=Yeni Çalışma Ekle');
await page.waitForSelector('text=Yeni Katkı / İyileştirme Çalışması', { timeout: 10000 });
const titleInput = page.locator('label:has-text("Çalışma Başlığı")').locator('xpath=following-sibling::input[1]');
await titleInput.fill("Playwright Smoke Test Taslağı");
await page.screenshot({ path: `${shotDir}/improvement-work-form.png` });
const draftButton = page.locator('button:has-text("Taslak Olarak Kaydet")');
await draftButton.click();
await page.waitForTimeout(1500);
console.log("draft save attempted");

await page.fill('input[placeholder*="Başlık"]', "Playwright Smoke Test");
await page.waitForTimeout(1000);
await page.screenshot({ path: `${shotDir}/improvement-works-search-result.png`, fullPage: true });
console.log("search result screenshot saved");

console.log("CONSOLE ERRORS:", JSON.stringify(errors, null, 2));
await browser.close();
