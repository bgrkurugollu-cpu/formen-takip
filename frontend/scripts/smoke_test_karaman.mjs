import { chromium } from "playwright";

const shotDir = "C:/Users/yucel/AppData/Local/Temp/claude/c--Users-yucel-Desktop-formen-takip/0e4c88e4-79d1-40c8-8a63-b565af53ce69/scratchpad";
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
await page.waitForTimeout(1000);
await page.screenshot({ path: `${shotDir}/karaman-dashboard.png` });

// Dashboard
await page.goto(`${BASE}/plants`, { waitUntil: "networkidle" });
await page.waitForTimeout(1200);
await page.screenshot({ path: `${shotDir}/karaman-plants.png`, fullPage: true });

// Open FilterBar Fabrika dropdown, select K1
await page.click('button:has-text("Fabrika")');
await page.waitForTimeout(400);
await page.screenshot({ path: `${shotDir}/karaman-factory-dropdown.png` });
const k1Option = page.locator('label:has-text("K1 Fabrikası")');
if (await k1Option.count() > 0) {
  await k1Option.click();
}
await page.keyboard.press("Escape");
await page.mouse.click(10, 10);
await page.waitForTimeout(1000);
await page.screenshot({ path: `${shotDir}/karaman-plants-k1-filtered.png`, fullPage: true });

// Plant detail
await page.goto(`${BASE}/plants`, { waitUntil: "networkidle" });
await page.waitForTimeout(800);
const firstRow = page.locator("table tbody tr").first();
await firstRow.click();
await page.waitForTimeout(1500);
await page.screenshot({ path: `${shotDir}/karaman-plant-detail.png`, fullPage: true });

// Foremen page
await page.goto(`${BASE}/foremen`, { waitUntil: "networkidle" });
await page.waitForTimeout(1200);
await page.screenshot({ path: `${shotDir}/karaman-foremen.png`, fullPage: true });

// Foreman detail
const firstForemanRow = page.locator("table tbody tr").first();
await firstForemanRow.click();
await page.waitForTimeout(1500);
await page.screenshot({ path: `${shotDir}/karaman-foreman-detail.png`, fullPage: true });

console.log("CONSOLE ERRORS:", JSON.stringify(errors, null, 2));
await browser.close();
