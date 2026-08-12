import { chromium } from "playwright";

const shotDir = "C:/Users/yucel/AppData/Local/Temp/claude/c--Users-yucel-Desktop-formen-takip/0e4c88e4-79d1-40c8-8a63-b565af53ce69/scratchpad";
const BASE = "http://localhost:8080";

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1600, height: 1100 } });
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

await page.click('a[href="/groups"]');
await page.waitForTimeout(2500);
const total = (await page.locator("text=/Toplam \\d+ grup/").first().textContent())?.trim();
console.log("Gruplar listesi:", total);
await page.screenshot({ path: `${shotDir}/groups-list.png`, fullPage: true });

await page.locator('thead button:has-text("Grup Puanı")').click();
await page.waitForTimeout(2000);
const scores = (await page.locator("tbody tr td:nth-child(6)").allTextContents()).map((t) => parseFloat(t));
console.log("Puana göre azalan ilk 5:", scores.slice(0, 5).join(", "),
  "| monoton azalan mı:", scores.every((n, i) => i === 0 || n <= scores[i - 1]));

await page.locator('thead button:has-text("Şef")').click();
await page.waitForTimeout(2000);
const names = (await page.locator("tbody tr td:nth-child(1)").allTextContents()).slice(0, 4);
console.log("Ada göre artan ilk 4:", names.join(" | "));

await page.fill('input[type="search"]', "SEF-05");
await page.waitForTimeout(2000);
const searchRows = await page.locator("tbody tr").count();
const searchNos = (await page.locator("tbody tr td:nth-child(2)").allTextContents()).slice(0, 3);
console.log("'SEF-05' aramasi:", searchRows, "satir |", searchNos.join(", "));
await page.fill('input[type="search"]', "");
await page.waitForTimeout(1800);

const filterBar = page.locator("div.flex.flex-wrap.items-center.gap-2.rounded-lg.p-3").first();
await filterBar.locator('button:has-text("Fabrika")').click();
await page.waitForTimeout(300);
await page.locator('div.absolute label:has-text("K2 Fabrikası")').click();
await page.waitForTimeout(300);
await page.mouse.click(10, 700);
await page.waitForTimeout(2500);
const k2Total = (await page.locator("text=/Toplam \\d+ grup/").first().textContent())?.trim();
const k2Factories = new Set((await page.locator("tbody tr td:nth-child(3)").allTextContents()).map((t) => t.trim()));
console.log("K2 filtresi:", k2Total, "| gorunen fabrikalar:", [...k2Factories].join(", "));
await page.screenshot({ path: `${shotDir}/groups-k2.png`, fullPage: true });

await page.locator("tbody tr").first().click();
await page.waitForTimeout(3000);
await page.screenshot({ path: `${shotDir}/group-detail.png`, fullPage: true });
const heading = await page.locator("h1").first().textContent();
const headScore = await page.locator("h1").locator("xpath=../../div[2]/div[1]").textContent().catch(() => null);
const teamScores = (await page.locator("table").last().locator("tbody tr td:nth-child(4)").allTextContents()).map((t) => parseFloat(t));
const mean = teamScores.reduce((a, b) => a + b, 0) / teamScores.length;
console.log("Detay:", heading?.trim(), "| basliktaki puan:", headScore?.trim(),
  "| ekip:", teamScores.length, "formen | ekip ortalamasi:", mean.toFixed(1));

console.log("CONSOLE ERRORS:", JSON.stringify(errors, null, 2));
await browser.close();
