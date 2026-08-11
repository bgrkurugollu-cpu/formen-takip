import { chromium } from "playwright";

const shotDir = "C:/Users/yucel/AppData/Local/Temp/claude/c--Users-yucel-Desktop-formen-takip/31b57c51-60e2-4db0-97e2-ae757b0d1730/scratchpad";
const BASE = "http://localhost:8080";

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
const errors = [];
page.on("pageerror", (e) => errors.push(String(e)));
page.on("console", (msg) => { if (msg.type() === "error") errors.push(msg.text()); });

await page.addInitScript(() => localStorage.setItem("formen_theme", "light"));
await page.goto(`${BASE}/login`, { waitUntil: "networkidle" });
await page.fill('input[type="email"]', "genel.mudur@formen-demo.com");
await page.fill('input[type="password"]', "Demo!2026");
await page.click('button[type="submit"]');
await page.waitForSelector("text=Genel Bakış", { timeout: 15000 });
await page.waitForTimeout(1500);
await page.screenshot({ path: `${shotDir}/dashboard-redesign-light.png`, fullPage: true });

console.log("CONSOLE ERRORS:", JSON.stringify(errors, null, 2));
await browser.close();
