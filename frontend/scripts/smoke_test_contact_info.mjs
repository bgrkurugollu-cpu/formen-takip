import { chromium } from "playwright";

const shotDir = "C:/Users/yucel/AppData/Local/Temp/claude/c--Users-yucel-Desktop-formen-takip/67bbb470-43d6-4b94-a33a-d29bcadbf9b0/scratchpad";
const BASE = "http://localhost:8080";

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1500, height: 900 } });
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
await page.waitForSelector("tbody tr");
await page.click("tbody tr");
await page.waitForSelector('a[href^="tel:"]', { timeout: 15000 });
await page.waitForTimeout(500);
await page.screenshot({ path: `${shotDir}/foreman-detail-contact-info.png`, fullPage: true });

const phoneHref = await page.locator('a[href^="tel:"]').first().getAttribute("href");
const emailHref = await page.locator('a[href^="mailto:"]').first().getAttribute("href");
console.log("FOREMAN phone href:", phoneHref);
console.log("FOREMAN email href:", emailHref);

await page.goto(`${BASE}/groups`, { waitUntil: "networkidle" });
await page.waitForSelector("tbody tr");
await page.click("tbody tr");
await page.waitForSelector("text=Telefon", { timeout: 15000 });
await page.waitForTimeout(500);
await page.screenshot({ path: `${shotDir}/chief-detail-contact-info.png`, fullPage: true });

const chiefPhoneHref = await page.locator('a[href^="tel:"]').first().getAttribute("href");
const chiefEmailHref = await page.locator('a[href^="mailto:"]').first().getAttribute("href");
console.log("CHIEF phone href:", chiefPhoneHref);
console.log("CHIEF email href:", chiefEmailHref);

console.log("CONSOLE ERRORS:", JSON.stringify(errors, null, 2));
await browser.close();
