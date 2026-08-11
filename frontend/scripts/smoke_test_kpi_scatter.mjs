import { chromium } from "playwright";

const shotDir = "C:/Users/yucel/AppData/Local/Temp/claude/c--Users-yucel-Desktop-formen-takip/9a2de671-c61c-408a-9c99-62dcc3c18378/scratchpad";
const BASE = "http://localhost:8080";

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1600, height: 1100 } });
const errors = [];
page.on("pageerror", (e) => errors.push(String(e)));
page.on("console", (msg) => { if (msg.type() === "error") errors.push(msg.text()); });

for (const theme of ["light", "dark"]) {
  await page.addInitScript((t) => localStorage.setItem("formen_theme", t), theme);
  await page.goto(`${BASE}/login`, { waitUntil: "networkidle" });
  await page.fill('input[type="email"]', "genel.mudur@formen-demo.com");
  await page.fill('input[type="password"]', "Demo!2026");
  await page.click('button[type="submit"]');
  await page.waitForSelector("text=Genel Bakış", { timeout: 15000 });

  await page.goto(`${BASE}/kpis`, { waitUntil: "networkidle" });
  await page.waitForSelector("text=Formen Performans / Fabrika Hedefi Karşılaştırması", { timeout: 15000 });
  await page.waitForTimeout(1000);
  await page.screenshot({ path: `${shotDir}/kpi-scatter-${theme}.png`, fullPage: true });
  console.log("saved full page", theme);

  const iskartaBtn = page.locator("button", { hasText: "Iskarta" });
  if (await iskartaBtn.count()) {
    await iskartaBtn.first().click();
    await page.waitForTimeout(1000);
  }
  await page.screenshot({ path: `${shotDir}/kpi-scatter-iskarta-${theme}.png`, fullPage: true });
  console.log("saved iskarta", theme);

  const dot = page.locator("svg circle[r='7']").first();
  if (await dot.count()) {
    await dot.hover();
    await page.waitForTimeout(400);
    await page.screenshot({ path: `${shotDir}/kpi-scatter-tooltip-${theme}.png`, fullPage: false });
    console.log("saved tooltip", theme);
  } else {
    console.log("NO DOTS FOUND for", theme);
  }

  await page.evaluate(() => localStorage.clear());
}

console.log("CONSOLE ERRORS:", JSON.stringify(errors, null, 2));
await browser.close();
