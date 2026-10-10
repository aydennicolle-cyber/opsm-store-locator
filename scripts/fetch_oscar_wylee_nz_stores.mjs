#!/usr/bin/env node
/** Collect Oscar Wylee New Zealand stores through its rendered public pages. */

import { mkdir, writeFile, readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { resolveBusinessPoint, branchStatus, validateLocator } from "./operator_business_map.mjs";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const RETAILER_DIR = path.join(ROOT, "retailers", "oscar-wylee-nz");
const LIST_URL = "https://www.oscarwylee.co.nz/locations/";
const CHROME_PATH = process.env.CHROME_PATH || (process.platform === "darwin" ? "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" : "");
const BROWSER_OPTIONS = CHROME_PATH ? { executablePath: CHROME_PATH } : { channel: "chrome" };
const LOCALITIES = {
  "optometrist-auckland-cbd.html": "Auckland CBD",
  "optometrist-new-lynn.html": "New Lynn",
  "optometrist-manukau.html": "Manukau",
  "optometrist-northlands.html": "Papanui",
  "optometrist-queensgate.html": "Lower Hutt",
  "optometrist-palmerston-north.html": "Palmerston North",
  "optometrist-wellington-central.html": "Wellington",
  "optometrist-albany.html": "Albany",
  "stlukes.html": "Mount Albert",
  "optometrist-riccarton.html": "Riccarton",
};
const REGIONS = {
  "optometrist-auckland-cbd.html": "Auckland",
  "optometrist-new-lynn.html": "Auckland",
  "optometrist-manukau.html": "Auckland",
  "optometrist-northlands.html": "Canterbury",
  "optometrist-queensgate.html": "Wellington",
  "optometrist-palmerston-north.html": "Manawatu-Whanganui",
  "optometrist-wellington-central.html": "Wellington",
  "optometrist-albany.html": "Auckland",
  "stlukes.html": "Auckland",
  "optometrist-riccarton.html": "Canterbury",
};
const FIELDS = [
  "name",
  "id",
  "country",
  "state",
  "city",
  "postal_code",
  "full_address",
  "phone",
  "latitude",
  "longitude",
  "official_url",
  "services",
  "audiology",
  "status",
];

function csvCell(value) {
  const text = String(value ?? "");
  return /[",\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
}

export async function collectStore(page, link) {
  await page.goto(link.official_url, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.locator("h1").first().waitFor({ state: "attached", timeout: 20000 });
  const details = await page.evaluate(() => {
    const heading = document.querySelector("h1.static-location-header") || document.querySelector("h1");
    const address = document.querySelector(".left-container .short-content, p.short-content");
    const phone = document.querySelector('a[href^="tel:"]');
    const map = document.querySelector('iframe[src*="google.com/maps"]');
    return {
      heading: (heading?.textContent || "").trim(),
      status_headings: [...document.querySelectorAll("h1,h2")].map(el => el.textContent).join(" "),
      main_text: (document.querySelector("main")?.innerText || ""),
      address: (address?.innerText || address?.textContent || "").trim(),
      phone: (phone?.getAttribute("href") || "").replace(/^tel:/, ""),
      map_url: map?.getAttribute("src") || "",
    };
  });
  const filename = new URL(link.official_url).pathname.split("/").pop();
  const address = (details.address || "")
    .replace(/\s*\n\s*/g, ", ")
    .replace(/\s+/g, " ")
    .trim();
  const postcode = address.match(/\b(\d{4})\b(?!.*\b\d{4}\b)/)?.[1] || "";
  const status = branchStatus(details);
  const point = await resolveBusinessPoint(details.map_url, async url => {
    const response = await page.request.get(url, { timeout: 30000 });
    if (!response.ok()) throw new Error(`Business map request failed: ${response.status()}`);
    return response.text();
  }, { allowClosed: status === 'Closed' });
  return {
    store: {
      name: `Oscar Wylee ${link.list_name}`,
      id: filename.replace(/\.html$/, ""),
      country: "New Zealand",
      state: REGIONS[filename],
      city: LOCALITIES[filename],
      postal_code: postcode,
      full_address: address,
      phone: details.phone || "",
      latitude: point.latitude,
      longitude: point.longitude,
      official_url: link.official_url,
      services: "Comprehensive eye tests, Prescription glasses, Sunglasses",
      audiology: "false",
      status,
    },
    source: { ...link, ...details, coordinate_evidence: point },
  };
}

async function main() {
  const { chromium } = await import("playwright");
  const browser = await chromium.launch({
    ...BROWSER_OPTIONS,
    headless: process.env.HEADLESS === "1",
  });
  try {
    const context = await browser.newContext({ locale: "en-NZ" });
    const listPage = await context.newPage();
    await listPage.goto(LIST_URL, { waitUntil: "domcontentloaded", timeout: 60000 });
    await listPage.locator('a[href*="/locations/"]').first().waitFor({ state: "attached", timeout: 20000 });
    const links = await listPage.locator('a[href*="/locations/"]').evaluateAll((anchors) =>
      Array.from(
        new Map(
          anchors
            .map((anchor) => ({
              list_name: (anchor.textContent || "").trim(),
              official_url: anchor.href,
            }))
            .filter(
              (item) =>
                /\/locations\/(?:optometrist-|stlukes)/.test(item.official_url) && item.list_name
            )
            .map((item) => [item.official_url, item])
        ).values()
      )
    );
    let priorUrls = [];
    try {
      const prior = JSON.parse(await readFile(path.join(RETAILER_DIR, 'source_snapshot.json'), 'utf8'));
      priorUrls = (prior.stores || []).map(store => store.official_url);
    } catch (error) {
      if (error.code !== 'ENOENT') throw error;
    }
    validateLocator(links, priorUrls);
    const page = await context.newPage();
    const collected = [];
    for (const link of links) collected.push(await collectStore(page, link));
    const stores = collected.map((item) => item.store);
    const ids = new Set(stores.map((store) => store.id));
    const invalid = stores.filter(
      (store) =>
        !store.state ||
        !store.city ||
        !store.postal_code ||
        !store.full_address ||
        !Number.isFinite(store.latitude) ||
        !Number.isFinite(store.longitude) ||
        store.latitude < -48 ||
        store.latitude > -33.5 ||
        store.longitude < 165 ||
        store.longitude > 179.5
    );
    if (ids.size !== stores.length || invalid.length) {
      throw new Error(
        `Oscar Wylee New Zealand validation failed; existing data was not replaced\n${JSON.stringify(
          invalid,
          null,
          2
        )}`
      );
    }
    stores.sort(
      (a, b) => a.state.localeCompare(b.state) || a.city.localeCompare(b.city) || a.name.localeCompare(b.name)
    );
    const fetchedAt = new Date().toISOString();
    const csv = [
      FIELDS.join(","),
      ...stores.map((store) => FIELDS.map((field) => csvCell(store[field])).join(",")),
    ].join("\n");
    const features = stores.map((store) => ({
      type: "Feature",
      geometry: { type: "Point", coordinates: [store.longitude, store.latitude] },
      properties: Object.fromEntries(
        FIELDS.filter((field) => !["latitude", "longitude"].includes(field)).map((field) => [
          field,
          store[field],
        ])
      ),
    }));
    await mkdir(RETAILER_DIR, { recursive: true });
    await writeFile(path.join(RETAILER_DIR, "stores.csv"), `${csv}\n`, "utf8");
    await writeFile(
      path.join(RETAILER_DIR, "stores.geojson"),
      `${JSON.stringify(
        {
          type: "FeatureCollection",
          metadata: {
            retailer: "Oscar Wylee",
            countries: ["New Zealand"],
            source_url: LIST_URL,
            fetched_at: fetchedAt,
            store_count: stores.length,
          },
          features,
        },
        null,
        2
      )}\n`,
      "utf8"
    );
    await writeFile(
      path.join(RETAILER_DIR, "source_snapshot.json"),
      `${JSON.stringify(
        {
          source_url: LIST_URL,
          fetched_at: fetchedAt,
          list_count: links.length,
          store_count: stores.length,
          collection_method: "Rendered official store list and store pages",
          stores: collected.map((item) => item.source),
        },
        null,
        2
      )}\n`,
      "utf8"
    );
    process.stdout.write(`Wrote ${stores.length} validated Oscar Wylee New Zealand stores\n`);
  } finally {
    await browser.close();
  }
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) main().catch((error) => {
  process.stderr.write(`${error.stack || error}\n`);
  process.exitCode = 1;
});
