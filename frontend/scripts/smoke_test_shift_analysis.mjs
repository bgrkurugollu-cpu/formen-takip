import { chromium } from "playwright";

const shotDir = "C:/Users/yucel/AppData/Local/Temp/claude/c--Users-yucel-Desktop-formen-takip/2441f3b5-2e99-4c98-845a-ab99cf4ac2df/scratchpad";
const BASE = "http://localhost:8080";

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1600, height: 1200 } });
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

  await page.goto(`${BASE}/shift-analysis`, { waitUntil: "networkidle" });
  await page.waitForSelector("text=Vardiya Analizi", { timeout: 15000 });
  await page.waitForTimeout(1500);
  await page.screenshot({ path: `${shotDir}/shift-analysis-${theme}.png`, fullPage: true });
  console.log("saved page", theme);

  const detailBtn = page.locator("button", { hasText: "Detayı Gör" }).first();
  if (await detailBtn.count()) {
    await detailBtn.click();
    try {
      await page.waitForSelector("text=Sistem Yorumu", { timeout: 15000 });
      await page.waitForTimeout(600);
    } catch (e) {
      console.log("MODAL WAIT FAILED:", String(e));
      console.log("MODAL TEXT:", await page.locator(".fixed.inset-0").innerText().catch(() => "<none>"));
    }
    await page.screenshot({ path: `${shotDir}/shift-analysis-detail-${theme}.png`, fullPage: true });
    console.log("saved detail modal", theme);
    await page.keyboard.press("Escape");
  } else {
    console.log("NO CARDS FOUND for", theme);
  }

  await page.evaluate(() => localStorage.clear());
}

console.log("CONSOLE ERRORS:", JSON.stringify(errors, null, 2));
await browser.close();
