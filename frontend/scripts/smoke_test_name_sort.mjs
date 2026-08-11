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

await page.goto(`${BASE}/foremen?date_from=2025-08-01&date_to=2026-07-28`, { waitUntil: "networkidle" });
await page.waitForTimeout(1800);

const surnames = async () =>
  (await page.locator("tbody tr td:nth-child(1)").allTextContents()).map((t) => t.trim().split(" ").pop());

console.log("Varsayılan (artan) ilk 6 soyad:", (await surnames()).slice(0, 6).join(", "));
await page.screenshot({ path: `${shotDir}/name-sort-asc.png`, fullPage: true });

await page.locator('thead button:has-text("Formen")').click();
await page.waitForTimeout(1800);
console.log("Azalan ilk 6 soyad:", (await surnames()).slice(0, 6).join(", "));
await page.screenshot({ path: `${shotDir}/name-sort-desc.png`, fullPage: true });

await page.locator('thead button:has-text("Tesis")').click();
await page.waitForTimeout(1800);
const plants = (await page.locator("tbody tr td:nth-child(3)").allTextContents())
  .map((t) => parseInt(t.trim(), 10));
const monotonic = plants.every((n, i) => i === 0 || n >= plants[i - 1]);
console.log("Tesis sırası (ilk 10):", plants.slice(0, 10).join(", "), "| artan mı:", monotonic);

await page.locator('thead button:has-text("Şef")').click();
await page.waitForTimeout(1800);
const chiefs = (await page.locator("tbody tr td:nth-child(4)").allTextContents()).map((t) => t.trim());
console.log("Şef (artan) ilk 5:", chiefs.slice(0, 5).join(" | "));

console.log("CONSOLE ERRORS:", JSON.stringify(errors, null, 2));
await browser.close();
