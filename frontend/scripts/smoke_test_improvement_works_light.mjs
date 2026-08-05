import { chromium } from "playwright";

const shotDir = "C:/Users/yucel/AppData/Local/Temp/claude/c--Users-yucel-Desktop-formen-takip/23f79635-4ddc-4250-8cf8-00dfd457c2b9/scratchpad";
const BASE = "http://localhost:8080";

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
const errors = [];
page.on("pageerror", (e) => errors.push(String(e)));
page.on("console", (msg) => { if (msg.type() === "error") errors.push(msg.text()); });

await page.addInitScript((t) => localStorage.setItem("formen_theme", t), "light");
await page.goto(`${BASE}/login`, { waitUntil: "networkidle" });
await page.fill('input[type="email"]', "genel.mudur@formen-demo.com");
await page.fill('input[type="password"]', "Demo!2026");
await page.click('button[type="submit"]');
await page.waitForSelector("text=Genel Bakış", { timeout: 15000 });

await page.click('text=Katkı ve İyileştirme Çalışmaları');
await page.waitForSelector("text=Yeni Çalışma Ekle", { timeout: 10000 });
await page.waitForTimeout(1000);
await page.screenshot({ path: `${shotDir}/improvement-works-list-light.png`, fullPage: true });
console.log("list page (light) loaded");

const firstCard = page.locator('a[href^="/improvement-works/"]').first();
await firstCard.click();
await page.waitForSelector("text=PDF olarak indir", { timeout: 10000 });
await page.waitForTimeout(500);
await page.screenshot({ path: `${shotDir}/improvement-work-detail-light.png`, fullPage: true });
console.log("detail page (light) loaded");

console.log("CONSOLE ERRORS:", JSON.stringify(errors, null, 2));
await browser.close();
