import { chromium } from "playwright";

const shotDir = "C:/Users/yucel/AppData/Local/Temp/claude/c--Users-yucel-Desktop-formen-takip/4df33485-5907-43a5-bf7e-750700c20b8b/scratchpad";
const BASE = "http://localhost:8080";

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1500, height: 800 } });
const errors = [];
page.on("pageerror", (e) => errors.push(String(e)));
page.on("console", (msg) => { if (msg.type() === "error") errors.push(msg.text()); });

await page.addInitScript((t) => localStorage.setItem("formen_theme", t), "light");
await page.goto(`${BASE}/login`, { waitUntil: "networkidle" });
await page.fill('input[type="email"]', "genel.mudur@formen-demo.com");
await page.fill('input[type="password"]', "Demo!2026");
await page.click('button[type="submit"]');
await page.waitForSelector("text=Genel Bakış", { timeout: 15000 });

await page.goto(`${BASE}/plants`, { waitUntil: "networkidle" });
await page.waitForTimeout(1000);
await page.screenshot({ path: `${shotDir}/plants-default.png` });

async function firstRowText() {
  return page.locator("tbody tr").first().innerText();
}

const before = await firstRowText();

await page.click('button:has-text("Toplam Puan")');
await page.waitForTimeout(800);
await page.screenshot({ path: `${shotDir}/plants-sorted-score-desc.png` });
const afterDesc = await firstRowText();

await page.click('button:has-text("Toplam Puan")');
await page.waitForTimeout(800);
await page.screenshot({ path: `${shotDir}/plants-sorted-score-asc.png` });
const afterAsc = await firstRowText();

await page.click('button:has-text("Aktif Formen")');
await page.waitForTimeout(800);
await page.screenshot({ path: `${shotDir}/plants-sorted-active-foreman.png` });

console.log("BEFORE FIRST ROW:", before.replace(/\n/g, " | "));
console.log("AFTER SCORE DESC FIRST ROW:", afterDesc.replace(/\n/g, " | "));
console.log("AFTER SCORE ASC FIRST ROW:", afterAsc.replace(/\n/g, " | "));
console.log("CONSOLE ERRORS:", JSON.stringify(errors, null, 2));
await browser.close();
