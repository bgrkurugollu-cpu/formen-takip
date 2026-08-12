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
await page.waitForTimeout(1500);
await page.screenshot({ path: `${shotDir}/names-foremen.png`, fullPage: true });

await page.click('button:has-text("Sicil No")');
await page.waitForTimeout(1200);
await page.screenshot({ path: `${shotDir}/names-foremen-by-sicil.png`, fullPage: true });

console.log("CONSOLE ERRORS:", JSON.stringify(errors, null, 2));
await browser.close();
