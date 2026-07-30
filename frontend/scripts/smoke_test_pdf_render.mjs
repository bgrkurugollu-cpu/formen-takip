import { chromium } from "playwright";

const shotDir = "C:/Users/yucel/AppData/Local/Temp/claude/c--Users-yucel-Desktop-formen-takip/0e4c88e4-79d1-40c8-8a63-b565af53ce69/scratchpad";
const pdfPath = process.argv[2] ?? `${shotDir}/rapor.pdf`;
const outName = process.argv[3] ?? "pdf-render.png";

const browser = await chromium.launch({ args: ["--enable-features=PdfOopif"] });
const page = await browser.newPage({ viewport: { width: 1500, height: 1000 } });
await page.goto(`file:///${pdfPath.replace(/\\/g, "/")}`, { waitUntil: "load" });
await page.waitForTimeout(4000);
await page.screenshot({ path: `${shotDir}/${outName}` });
console.log("kaydedildi:", `${shotDir}/${outName}`);
await browser.close();
