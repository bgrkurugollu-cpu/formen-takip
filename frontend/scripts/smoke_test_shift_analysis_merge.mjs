import { chromium } from "playwright";

const shotDir = "C:/Users/yucel/AppData/Local/Temp/claude/c--Users-yucel-Desktop-formen-takip/95a5840b-e51a-49ba-9936-b4f984185bca/scratchpad";
const BASE = "http://localhost:8080";

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1600, height: 900 } });
const errors = [];
const shiftAnalysisRequests = [];
page.on("pageerror", (e) => errors.push(String(e)));
page.on("console", (msg) => { if (msg.type() === "error") errors.push(msg.text()); });
page.on("request", (req) => {
  if (req.url().includes("/shift-analysis/")) shiftAnalysisRequests.push(req.url());
});

await page.goto(`${BASE}/login`, { waitUntil: "networkidle" });
await page.fill('input[type="email"]', "genel.mudur@formen-demo.com");
await page.fill('input[type="password"]', "Demo!2026");
await page.click('button[type="submit"]');
await page.waitForSelector("text=Aktif Formen", { timeout: 15000 });

shiftAnalysisRequests.length = 0; // reset after login-time noise
await page.click('a[href="/shift-analysis"]');
await page.waitForSelector("text=Vardiya Analizi", { timeout: 15000 });
await page.waitForSelector("text=İncelenen Dönem", { timeout: 15000 });
await page.waitForTimeout(1000);

await page.screenshot({ path: `${shotDir}/shiftanalysis-merged.png`, fullPage: true });
console.log("shift-analysis requests fired:", JSON.stringify(shiftAnalysisRequests, null, 2));
console.log("summary request count:", shiftAnalysisRequests.filter((u) => u.includes("/summary")).length);
console.log("cards request count:", shiftAnalysisRequests.filter((u) => u.includes("/cards")).length);
console.log("CONSOLE ERRORS:", JSON.stringify(errors, null, 2));
await browser.close();
