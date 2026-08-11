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

const filterBar = () => page.locator("div.flex.flex-wrap.items-center.gap-2.rounded-lg.p-3").first();

async function pickFactory(label) {
  await filterBar().locator('button:has-text("Fabrika")').click();
  await page.waitForTimeout(300);
  await page.locator(`div.absolute label:has-text("${label}")`).click();
  await page.waitForTimeout(300);
  await page.mouse.click(10, 500);
  await page.waitForTimeout(2000);
}

await page.goto(`${BASE}/foremen`, { waitUntil: "networkidle" });
await page.waitForTimeout(1500);
const beforeTotal = (await page.locator("text=/Toplam \\d+ formen/").first().textContent())?.trim();
console.log("Filtresiz:", beforeTotal);

await pickFactory("K2 Fabrikası");
await page.screenshot({ path: `${shotDir}/factory-k2-foremen.png`, fullPage: true });
const afterTotal = (await page.locator("text=/Toplam \\d+ formen/").first().textContent())?.trim();
console.log("K2 seçili:", afterTotal);

const plantCells = await page.locator("tbody tr td:nth-child(3)").allTextContents();
const seqs = plantCells.map((t) => parseInt(t.trim(), 10)).filter((n) => !Number.isNaN(n));
console.log("Sayfadaki tesis no aralığı:", Math.min(...seqs), "-", Math.max(...seqs), "| örnek:", plantCells.slice(0, 5).map(s => s.trim()));
console.log("K1'e ait (28'den küçük) satır sayısı:", seqs.filter((n) => n < 28).length);

const zeroScores = (await page.locator("tbody tr").allTextContents()).filter((t) => /\b0[.,]00\b/.test(t)).length;
console.log("Puanı 0,00 görünen satır sayısı:", zeroScores);

const params = new URL(page.url()).search;
await page.goto(`${BASE}/plants${params}`, { waitUntil: "networkidle" });
await page.waitForTimeout(2000);
await page.screenshot({ path: `${shotDir}/factory-k2-plants.png`, fullPage: true });
const plantsTotal = (await page.locator("text=/Toplam \\d+ tesis/").first().textContent())?.trim();
console.log("Tesisler (K2 seçili):", plantsTotal);

console.log("CONSOLE ERRORS:", JSON.stringify(errors, null, 2));
await browser.close();
