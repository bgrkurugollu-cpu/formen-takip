import { chromium } from "playwright";

const shotDir = "C:/Users/yucel/AppData/Local/Temp/claude/c--Users-yucel-Desktop-formen-takip/0e4c88e4-79d1-40c8-8a63-b565af53ce69/scratchpad";
const BASE = "http://localhost:8080";

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
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
  await page.waitForTimeout(1000);
  await page.screenshot({ path: `${shotDir}/logo-${theme}-full.png` });
  const sidebar = page.locator("aside");
  await sidebar.screenshot({ path: `${shotDir}/logo-${theme}-sidebar.png` });
  console.log("saved", theme);
  await page.evaluate(() => localStorage.clear());
}

console.log("CONSOLE ERRORS:", JSON.stringify(errors, null, 2));
await browser.close();
