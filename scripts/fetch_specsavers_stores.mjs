#!/usr/bin/env node
/** Collect Specsavers structured store data through its rendered public pages. */

import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const COUNTRY = (process.env.SPECSAVERS_COUNTRY || "AU").toUpperCase();
const IS_NZ = COUNTRY === "NZ";
const RETAILER_DIR = path.join(ROOT, "retailers", IS_NZ ? "specsavers-nz" : "specsavers");
const SNAPSHOT_PATH = path.join(RETAILER_DIR, "source_snapshot.json");
const LIST_URL = IS_NZ
  ? "https://www.specsavers.co.nz/stores/full-store-list"
  : "https://www.specsavers.com.au/stores/full-store-list";
const CHROME_PATH = process.env.CHROME_PATH || "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const WORKERS = Math.max(1, Math.min(4, Number(process.env.SPECSAVERS_WORKERS || 4)));

async function collectStore(page, item) {
  let lastError = "";
  for (let attempt = 0; attempt < 3; attempt += 1) {
    try {
      await page.goto(item.official_url, { waitUntil: "domcontentloaded", timeout: 45000 });
      const locator = page.locator('script[type="application/ld+json"]');
      await locator.waitFor({ state: "attached", timeout: 15000 });
      const data = JSON.parse(await locator.textContent());
      if (!data.geo || !data.address || !data.name || !data["@id"]) {
        throw new Error("Structured store data is incomplete");
      }
      return { ok: true, list_name: item.list_name, official_url: item.official_url, data };
    } catch (error) {
      lastError = String(error);
    }
  }
  return { ok: false, ...item, error: lastError };
}

async function main() {
  const browser = await chromium.launch({
    executablePath: CHROME_PATH,
    headless: process.env.HEADLESS === "1",
  });
  try {
    const context = await browser.newContext({ locale: IS_NZ ? "en-NZ" : "en-AU" });
    const listPage = await context.newPage();
    await listPage.goto(LIST_URL, { waitUntil: "domcontentloaded", timeout: 60000 });
    const links = await listPage.locator('a[href*="/stores/"]').evaluateAll((anchors) =>
      Array.from(
        new Map(
          anchors
            .map((anchor) => ({
              list_name: (anchor.textContent || "").trim(),
              official_url: anchor.href,
            }))
            .filter((item) => item.official_url && !item.official_url.endsWith("/stores/full-store-list"))
            .map((item) => [item.official_url, item])
        ).values()
      )
    );
    const minimum = IS_NZ ? 45 : 350;
    const maximum = IS_NZ ? 75 : 450;
    if (links.length < minimum || links.length > maximum) {
      throw new Error(`Unexpected public store-list count: ${links.length}. Existing data was not replaced.`);
    }

    const pages = await Promise.all(Array.from({ length: WORKERS }, () => context.newPage()));
    const groups = await Promise.all(
      pages.map(async (page, workerIndex) => {
        const output = [];
        for (let index = workerIndex; index < links.length; index += pages.length) {
          output.push(await collectStore(page, links[index]));
          if (output.length % 20 === 0) {
            process.stdout.write(`Worker ${workerIndex + 1}: ${output.length} pages checked\n`);
          }
        }
        return output;
      })
    );
    const stores = groups.flat().sort((a, b) => a.official_url.localeCompare(b.official_url));
    const failed = stores.filter((store) => !store.ok);
    const uniqueIds = new Set(stores.filter((store) => store.ok).map((store) => store.data["@id"]));
    if (failed.length || stores.length !== links.length || uniqueIds.size !== links.length) {
      const failedUrls = failed.map((store) => store.official_url).join("\n");
      throw new Error(
        `Specsavers refresh incomplete (${stores.length - failed.length}/${links.length}). Existing data was not replaced.\n${failedUrls}`
      );
    }

    const snapshot = {
      source_url: LIST_URL,
      fetched_at: new Date().toISOString(),
      list_count: links.length,
      store_count: stores.length,
      collection_method: "Rendered official store pages; Schema.org structured data",
      country: IS_NZ ? "New Zealand" : "Australia",
      stores,
    };
    await mkdir(RETAILER_DIR, { recursive: true });
    await writeFile(SNAPSHOT_PATH, `${JSON.stringify(snapshot, null, 2)}\n`, "utf8");
    process.stdout.write(`Wrote ${stores.length} validated Specsavers stores to ${SNAPSHOT_PATH}\n`);
    process.stdout.write("Run python3 scripts/build_specsavers_stores.py, then python3 scripts/build_optical_network.py.\n");
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  process.stderr.write(`${error.stack || error}\n`);
  process.exitCode = 1;
});
