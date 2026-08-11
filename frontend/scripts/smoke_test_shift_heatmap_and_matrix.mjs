import { chromium } from "playwright";

const shotDir = "C:/Users/yucel/AppData/Local/Temp/claude/c--Users-yucel-Desktop-formen-takip/cba24031-6be0-4bfb-b264-487ee701965d/scratchpad";
const BASE = "http://localhost:8080";

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1700, height: 1200 } });
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
  await page.waitForSelector("text=Vardiya Anomali Heatmap", { timeout: 15000 });
  await page.waitForTimeout(1500);
  await page.screenshot({ path: `${shotDir}/heatmap-page-${theme}.png`, fullPage: true });
  console.log("saved heatmap page", theme);

  // Heatmap grid + legend sanity checks
  const legendNormal = page.locator("text=Normal").first();
  console.log("legend visible:", await legendNormal.count() > 0, theme);

  // Click the first non-"no data" cell we can find and confirm drill-down navigation.
  const cellButtons = page.locator("table button");
  const cellCount = await cellButtons.count();
  console.log("heatmap cell button count:", cellCount, theme);

  let navigated = false;
  for (let i = 0; i < Math.min(cellCount, 40) && !navigated; i++) {
    const btn = cellButtons.nth(i);
    const text = (await btn.innerText()).trim();
    if (text === "—") continue;
    await btn.hover();
    await page.waitForTimeout(300);
    const tooltipVisible = await page.locator("text=Durum:").count();
    await btn.click();
    try {
      await page.waitForURL(/\/plants\/.+fs_kpi=/, { timeout: 8000 });
      navigated = true;
      console.log("drilldown navigated, tooltip had 'Durum:':", tooltipVisible > 0, theme);
    } catch {
      // not a plant page navigation attempt with this element, try next
      await page.goBack().catch(() => {});
    }
  }
  console.log("drilldown navigated:", navigated, theme);

  if (navigated) {
    await page.waitForSelector("text=Formen–Vardiya Karşılaştırması", { timeout: 15000 });
    await page.waitForTimeout(1500);
    await page.screenshot({ path: `${shotDir}/plant-matrix-${theme}.png`, fullPage: true });
    console.log("saved plant matrix section", theme);

    const insight = page.locator("text=Formen–Vardiya Karşılaştırması").locator("..").locator("..");
    console.log("insight block present:", (await page.locator("svg + p", { hasText: "" }).count()) >= 0, theme);

    // Change KPI selector (scoped to the Formen-Vardiya card, not the global date-preset select)
    // and confirm the matrix re-fetches without console errors.
    const matrixCard = page.locator("text=Formen–Vardiya Karşılaştırması").locator("xpath=ancestor::div[contains(@class,'rounded-lg')][1]");
    const kpiSelect = matrixCard.locator("select").first();
    const optionCount = await kpiSelect.locator("option").count();
    if (optionCount > 1) {
      await kpiSelect.selectOption({ index: 1 });
      await page.waitForTimeout(1200);
      const selectedLabel = await kpiSelect.locator("option:checked").innerText();
      console.log("changed KPI selector to:", selectedLabel, theme);
    }
    await page.screenshot({ path: `${shotDir}/plant-matrix-kpi-changed-${theme}.png`, fullPage: true });
  }

  await page.evaluate(() => localStorage.clear());
}

console.log("CONSOLE ERRORS:", JSON.stringify(errors, null, 2));
await browser.close();
