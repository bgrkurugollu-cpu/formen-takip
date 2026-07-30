import { chromium } from "playwright";

const shotDir = "C:/Users/yucel/AppData/Local/Temp/claude/c--Users-yucel-Desktop-formen-takip/0e4c88e4-79d1-40c8-8a63-b565af53ce69/scratchpad";

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const errors = [];
page.on("pageerror", (e) => errors.push(String(e)));
page.on("console", (msg) => {
  if (msg.type() === "error") errors.push(msg.text());
});

async function shot(name) {
  await page.screenshot({ path: `${shotDir}/${name}.png` });
  console.log("saved", name);
}

console.log("nav to login");
await page.goto("http://localhost:5173/login", { waitUntil: "networkidle" });
await shot("01-login");

await page.fill('input[type="email"]', "genel.mudur@formen-demo.com");
await page.fill('input[type="password"]', "Demo!2026");
await page.click('button[type="submit"]');

console.log("waiting for dashboard");
await page.waitForSelector("text=Genel Bakış", { timeout: 15000 });
await page.waitForTimeout(1500);
await shot("02-dashboard");

console.log("nav to plants");
await page.click('text=Tesisler');
await page.waitForTimeout(1200);
await shot("03-plants");

console.log("click first plant row");
const firstRow = page.locator("table tbody tr").first();
await firstRow.click();
await page.waitForTimeout(1200);
await shot("04-plant-detail");

console.log("nav to foremen");
await page.click('text=Formenler');
await page.waitForTimeout(1200);
await shot("05-foremen");

console.log("click first foreman row");
const firstForemanRow = page.locator("table tbody tr").first();
await firstForemanRow.click();
await page.waitForTimeout(1200);
await shot("06-foreman-detail");

console.log("click a KPI card to open calc detail modal");
const firstKpiCard = page.locator("button:has-text('Hedef:')").first();
await firstKpiCard.click();
await page.waitForTimeout(1000);
await shot("07-calc-detail-modal");

console.log("nav to kpi analysis");
await page.click('button:has-text("✕")');
await page.waitForTimeout(300);
await page.click('text=KPI Analizi');
await page.waitForTimeout(1500);
await shot("08-kpi-analysis");

console.log("CONSOLE ERRORS:", JSON.stringify(errors, null, 2));

await browser.close();
