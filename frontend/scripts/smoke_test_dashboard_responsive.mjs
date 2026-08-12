import { chromium } from "playwright";

const shotDir = "C:/Users/yucel/AppData/Local/Temp/claude/c--Users-yucel-Desktop-formen-takip/95a5840b-e51a-49ba-9936-b4f984185bca/scratchpad";
const BASE = "http://localhost:8080";

const browser = await chromium.launch();
const errors = [];

async function loginAndScreenshot(viewport, label) {
  const page = await browser.newPage({ viewport });
  page.on("pageerror", (e) => errors.push(`[${label}] ${String(e)}`));
  page.on("console", (msg) => { if (msg.type() === "error") errors.push(`[${label}] ${msg.text()}`); });

  await page.goto(`${BASE}/login`, { waitUntil: "networkidle" });
  await page.fill('input[type="email"]', "genel.mudur@formen-demo.com");
  await page.fill('input[type="password"]', "Demo!2026");
  await page.click('button[type="submit"]');
  await page.waitForSelector("text=Aktif Formen", { timeout: 15000 });
  await page.waitForTimeout(1000);
  await page.screenshot({ path: `${shotDir}/dashboard-${label}.png`, fullPage: true });
  console.log("saved", label, viewport);
  await page.close();
}

await loginAndScreenshot({ width: 375, height: 800 }, "mobile-375");
await loginAndScreenshot({ width: 768, height: 1000 }, "tablet-768");
await loginAndScreenshot({ width: 1600, height: 900 }, "desktop-1600");

console.log("CONSOLE ERRORS:", JSON.stringify(errors, null, 2));
await browser.close();
