import { chromium } from "playwright";

const shotDir = "C:/Users/yucel/AppData/Local/Temp/claude/c--Users-yucel-Desktop-formen-takip/95a5840b-e51a-49ba-9936-b4f984185bca/scratchpad";
const BASE = "http://localhost:8080";

const browser = await chromium.launch();
const errors = [];
const page = await browser.newPage({ viewport: { width: 375, height: 800 } });
page.on("pageerror", (e) => errors.push(String(e)));
page.on("console", (msg) => { if (msg.type() === "error") errors.push(msg.text()); });

await page.goto(`${BASE}/login`, { waitUntil: "networkidle" });
await page.fill('input[type="email"]', "genel.mudur@formen-demo.com");
await page.fill('input[type="password"]', "Demo!2026");
await page.click('button[type="submit"]');
await page.waitForSelector("text=Aktif Formen", { timeout: 15000 });
await page.waitForTimeout(500);

// 1. Closed state — no sidebar, hamburger visible
await page.screenshot({ path: `${shotDir}/mobilenav-1-closed.png` });
const hamburger = page.getByLabel("Menüyü aç");
console.log("hamburger visible:", await hamburger.isVisible());
console.log("sidebar nav link visible before open:", await page.getByRole("link", { name: "Tesisler" }).isVisible());

// 2. Open drawer
await hamburger.click();
await page.waitForSelector('[aria-label="Menüyü kapat"]', { timeout: 5000 });
await page.waitForTimeout(300);
await page.screenshot({ path: `${shotDir}/mobilenav-2-open.png` });
console.log("nav link visible after open:", await page.getByRole("link", { name: "Tesisler" }).last().isVisible());

// 3. Click a nav link — should navigate AND close the drawer
await page.getByRole("link", { name: "Tesisler" }).last().click();
await page.waitForURL("**/plants", { timeout: 5000 });
await page.waitForTimeout(300);
await page.screenshot({ path: `${shotDir}/mobilenav-3-after-navigate.png` });
console.log("drawer closed after navigate:", !(await page.getByLabel("Menüyü kapat").isVisible().catch(() => false)));

// 4. Reopen, then close via backdrop click
await hamburger.click();
await page.waitForSelector('[aria-label="Menüyü kapat"]', { timeout: 5000 });
await page.mouse.click(340, 400); // backdrop area, right of the 256px-wide drawer
await page.waitForTimeout(300);
await page.screenshot({ path: `${shotDir}/mobilenav-4-after-backdrop-close.png` });
console.log("drawer closed after backdrop click:", !(await page.getByLabel("Menüyü kapat").isVisible().catch(() => false)));

// 5. Desktop viewport — drawer/hamburger should be absent, real sidebar shown
await page.setViewportSize({ width: 1600, height: 900 });
await page.waitForTimeout(300);
await page.screenshot({ path: `${shotDir}/mobilenav-5-desktop.png` });
console.log("hamburger visible at desktop width:", await hamburger.isVisible().catch(() => false));
console.log("real sidebar nav visible at desktop width:", await page.getByRole("link", { name: "Tesisler" }).isVisible());

console.log("CONSOLE ERRORS:", JSON.stringify(errors, null, 2));
await browser.close();
