import { chromium } from "playwright";

const shotDir = "C:/Users/yucel/AppData/Local/Temp/claude/c--Users-yucel-Desktop-formen-takip/68674d04-3f5b-43c2-a4ca-f40f0fce04fa/scratchpad";

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const errors = [];
page.on("pageerror", (e) => errors.push(String(e)));
page.on("console", (msg) => {
  if (msg.type() === "error") errors.push(msg.text());
});

async function shot(name) {
  await page.screenshot({ path: `${shotDir}/${name}.png`, fullPage: true });
  console.log("saved", name);
}

console.log("nav to login");
await page.goto("http://localhost:8080/login", { waitUntil: "networkidle" });

await page.fill('input[type="email"]', "genel.mudur@formen-demo.com");
await page.fill('input[type="password"]', "Demo!2026");
await page.click('button[type="submit"]');

console.log("waiting for dashboard");
await page.waitForSelector("text=Genel Bakış", { timeout: 15000 });

console.log("nav to foremen");
await page.click('text=Formenler');
await page.waitForTimeout(1200);

console.log("click first foreman row");
const firstForemanRow = page.locator("table tbody tr").first();
await firstForemanRow.click();
await page.waitForTimeout(1500);

console.log("scroll to monthly reports card");
await page.locator("text=Aylık Değerlendirme Raporları").scrollIntoViewIfNeeded();
await page.waitForTimeout(1500);
await shot("01-foreman-detail-with-monthly-card");

console.log("click Raporu Görüntüle");
const viewButton = page.locator('button:has-text("Raporu Görüntüle")').first();
await viewButton.click();
await page.waitForTimeout(2000);
await shot("02-monthly-report-page");

console.log("checking key sections present");
const bodyText = await page.textContent("body");
const sections = ["Aylık Performans Özeti", "KPI Detayları", "Aylık Değerlendirme"];
for (const s of sections) {
  console.log(`  section "${s}" present:`, bodyText.includes(s));
}

console.log("attempting PDF download");
const [download] = await Promise.all([
  page.waitForEvent("download", { timeout: 15000 }),
  page.click('button:has-text("PDF İndir")'),
]);
const path = await download.path();
console.log("download saved to (temp):", path, "suggested filename:", download.suggestedFilename());

console.log("toggle theme (if available) and re-screenshot");
const themeToggle = page.locator('button[aria-label*="tema" i], button[title*="tema" i]').first();
if (await themeToggle.count()) {
  await themeToggle.click();
  await page.waitForTimeout(800);
  await shot("03-monthly-report-page-theme-toggled");
}

console.log("CONSOLE ERRORS:", JSON.stringify(errors, null, 2));

await browser.close();
