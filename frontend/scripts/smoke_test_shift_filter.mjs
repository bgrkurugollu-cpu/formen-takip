import { chromium } from "playwright";

const shotDir = "C:/Users/yucel/AppData/Local/Temp/claude/c--Users-yucel-Desktop-formen-takip/0e4c88e4-79d1-40c8-8a63-b565af53ce69/scratchpad";
const BASE = "http://localhost:8080";

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
const errors = [];
page.on("pageerror", (e) => errors.push(String(e)));
page.on("console", (msg) => { if (msg.type() === "error") errors.push(msg.text()); });
page.on("response", (r) => { if (r.status() >= 400) errors.push(`${r.status()} ${r.url()}`); });

await page.addInitScript((t) => localStorage.setItem("formen_theme", t), "light");
await page.goto(`${BASE}/login`, { waitUntil: "networkidle" });
await page.fill('input[type="email"]', "genel.mudur@formen-demo.com");
await page.fill('input[type="password"]', "Demo!2026");
await page.click('button[type="submit"]');
await page.waitForSelector("text=Genel Bakış", { timeout: 15000 });

await page.goto(`${BASE}/foremen`, { waitUntil: "networkidle" });
await page.waitForTimeout(1500);

const filterBar = page.locator("div.flex.flex-wrap.items-center.gap-2.rounded-lg.p-3").first();
await filterBar.locator('button:has-text("Vardiya")').click();
await page.waitForTimeout(300);
await page.locator('div.absolute label:has-text("2. Vardiya")').click();
await page.waitForTimeout(300);
await page.mouse.click(10, 600);
await page.waitForTimeout(2000);

const shiftHeader = page.locator('thead button:has-text("Vardiya")');

for (const dir of ["artan", "azalan"]) {
  await shiftHeader.click();
  await page.waitForTimeout(1500);
  const cells = (await page.locator("tbody tr td:nth-child(5)").allTextContents()).map((t) => t.trim());
  const wrong = cells.filter((c) => c !== "2. Vardiya");
  console.log(`Vardiya sıralı (${dir}): ${cells.length} satır, 2. Vardiya olmayan: ${wrong.length}`, wrong.slice(0, 5));
  await page.screenshot({ path: `${shotDir}/shift-sorted-${dir}.png`, fullPage: true });
}

const total = (await page.locator("text=/Toplam \\d+ formen/").first().textContent())?.trim();
console.log("Liste:", total);
console.log("CONSOLE ERRORS:", JSON.stringify(errors, null, 2));
await browser.close();
