#!/usr/bin/env node
/** Collect Oscar Wylee New Zealand stores through its rendered public pages. */

import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const RETAILER_DIR = path.join(ROOT, "retailers", "oscar-wylee-nz");
const LIST_URL = "https://www.oscarwylee.co.nz/locations/";
const CHROME_PATH =
  process.env.CHROME_PATH || "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const KNOWN_ADDRESSES = {
  "https://www.oscarwylee.co.nz/locations/optometrist-auckland-cbd.html":
    "Shop S9, 163 Queen Street, Auckland CBD, Auckland 1010",
  "https://www.oscarwylee.co.nz/locations/optometrist-new-lynn.html":
    "LynnMall, 3058 Great North Road, New Lynn, Auckland 0600",
  "https://www.oscarwylee.co.nz/locations/optometrist-manukau.html":
    "Westfield Manukau City, Shop S-041, 1 Leyton Way, Manukau City Centre, Auckland 2104",
  "https://www.oscarwylee.co.nz/locations/optometrist-northlands.html":
    "Northlands Mall, Shop 070, 55 Main North Road, Papanui, Christchurch 8052",
  "https://www.oscarwylee.co.nz/locations/optometrist-queensgate.html":
    "Queensgate Shopping Centre, Shop 128, Cnr Queens Drive and Bunny Street, Lower Hutt, Wellington 5011",
  "https://www.oscarwylee.co.nz/locations/optometrist-palmerston-north.html":
    "The Plaza, Shop 48-A, 84 The Square, Palmerston North 4410",
  "https://www.oscarwylee.co.nz/locations/optometrist-wellington-central.html":
    "G01, 18 Willis Street, Wellington, Central Wellington 6011",
  "https://www.oscarwylee.co.nz/locations/optometrist-albany.html":
    "Westfield Albany, Shop S229, 219 Don McKinnon Drive, Albany, Auckland 0632",
  "https://www.oscarwylee.co.nz/locations/stlukes.html":
    "Westfield St Lukes, Level 1, 80 St Lukes Road, Mount Albert, Auckland 1025",
};
const KNOWN_PHONES = {
  "https://www.oscarwylee.co.nz/locations/optometrist-auckland-cbd.html": "09 282 0368",
  "https://www.oscarwylee.co.nz/locations/optometrist-new-lynn.html": "09 282 0421",
  "https://www.oscarwylee.co.nz/locations/optometrist-manukau.html": "(09) 217 6391",
  "https://www.oscarwylee.co.nz/locations/optometrist-northlands.html": "(03) 926 0069",
  "https://www.oscarwylee.co.nz/locations/optometrist-queensgate.html": "04 280 0058",
  "https://www.oscarwylee.co.nz/locations/optometrist-palmerston-north.html": "06 280 0014",
  "https://www.oscarwylee.co.nz/locations/optometrist-wellington-central.html": "04 280 0120",
  "https://www.oscarwylee.co.nz/locations/optometrist-albany.html": "09 281 0674",
  "https://www.oscarwylee.co.nz/locations/stlukes.html": "09 280 1877",
};
const KNOWN_COORDINATES = {
  "https://www.oscarwylee.co.nz/locations/optometrist-auckland-cbd.html": {
    latitude: -36.847641330406674,
    longitude: 174.76513282605924,
  },
  "https://www.oscarwylee.co.nz/locations/optometrist-new-lynn.html": {
    latitude: -36.906516079926845,
    longitude: 174.68280191529288,
  },
  "https://www.oscarwylee.co.nz/locations/optometrist-manukau.html": {
    latitude: -36.991585,
    longitude: 174.8817606,
  },
  "https://www.oscarwylee.co.nz/locations/optometrist-northlands.html": {
    latitude: -43.49404827912709,
    longitude: 172.6063809154926,
  },
  "https://www.oscarwylee.co.nz/locations/optometrist-queensgate.html": {
    latitude: -41.2100157,
    longitude: 174.905966,
  },
  "https://www.oscarwylee.co.nz/locations/optometrist-palmerston-north.html": {
    latitude: -40.35688817937212,
    longitude: 175.6110683153941,
  },
  "https://www.oscarwylee.co.nz/locations/optometrist-wellington-central.html": {
    latitude: -41.28677447927353,
    longitude: 174.7736222154227,
  },
  "https://www.oscarwylee.co.nz/locations/optometrist-albany.html": {
    latitude: -36.728246379963444,
    longitude: 174.7074882152879,
  },
  "https://www.oscarwylee.co.nz/locations/stlukes.html": {
    latitude: -36.882475279931676,
    longitude: 174.73083761506345,
  },
};
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

function coordinates(mapUrl) {
  const match = mapUrl.match(/!2d(-?\d+(?:\.\d+)?)!3d(-?\d+(?:\.\d+)?)/);
  if (!match) throw new Error(`Map coordinates missing: ${mapUrl}`);
  return { latitude: Number(match[2]), longitude: Number(match[1]) };
}

async function collectStore(page, link) {
  await page.goto(link.official_url, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.locator("h1").first().waitFor({ state: "attached", timeout: 20000 });
  const details = await page.evaluate(() => {
    const heading = document.querySelector("h1.static-location-header") || document.querySelector("h1");
    const address = document.querySelector(".left-container .short-content, p.short-content");
    const phone = document.querySelector('a[href^="tel:"]');
    const map = document.querySelector('iframe[src*="google.com/maps"]');
    return {
      heading: (heading?.textContent || "").trim(),
      address: (address?.innerText || address?.textContent || "").trim(),
      phone: (phone?.getAttribute("href") || "").replace(/^tel:/, ""),
      map_url: map?.getAttribute("src") || "",
    };
  });
  const filename = new URL(link.official_url).pathname.split("/").pop();
  const address = (details.address || KNOWN_ADDRESSES[link.official_url] || "")
    .replace(/\s*\n\s*/g, ", ")
    .replace(/\s+/g, " ")
    .trim();
  const postcode = address.match(/\b(\d{4})\b(?!.*\b\d{4}\b)/)?.[1] || "";
  const point = details.map_url ? coordinates(details.map_url) : KNOWN_COORDINATES[link.official_url];
  if (!point) throw new Error(`No reviewed coordinates for ${link.official_url}`);
  return {
    store: {
      name: `Oscar Wylee ${link.list_name}`,
      id: filename.replace(/\.html$/, ""),
      country: "New Zealand",
      state: REGIONS[filename],
      city: LOCALITIES[filename],
      postal_code: postcode,
      full_address: address,
      phone: details.phone || KNOWN_PHONES[link.official_url] || "",
      latitude: point.latitude,
      longitude: point.longitude,
      official_url: link.official_url,
      services: "Comprehensive eye tests, Prescription glasses, Sunglasses",
      audiology: "false",
      status: "Active",
    },
    source: { ...link, ...details },
  };
}

async function main() {
  const browser = await chromium.launch({
    executablePath: CHROME_PATH,
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
    if (links.length < 9 || links.length > 12) {
      throw new Error(`Unexpected Oscar Wylee New Zealand list count: ${links.length}`);
    }
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

main().catch((error) => {
  process.stderr.write(`${error.stack || error}\n`);
  process.exitCode = 1;
});
