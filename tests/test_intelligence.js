const assert = require("node:assert/strict");
const fs = require("node:fs");
const Intel = require("../assets/intelligence.js");

assert.equal(Intel.haversine({latitude: 0, longitude: 0}, {latitude: 0, longitude: 0}), 0);
assert.equal(Intel.formatFitScore(120, 100, 140), 100);
assert.equal(Intel.formatFitScore(null, 100, 140), null);
assert.equal(Intel.geometryIntersectsRadius(
  {latitude: 0, longitude: 0},
  {type: "Polygon", coordinates: [[[0.05, -0.01], [0.05, 0.01], [0.1, 0.01], [0.1, -0.01], [0.05, -0.01]]]},
  6
), true);
assert.equal(Intel.geometryIntersectsRadius(
  {latitude: 0, longitude: 0},
  {type: "Polygon", coordinates: [[[1, 1], [1, 1.1], [1.1, 1.1], [1.1, 1], [1, 1]]]},
  10
), false);

const markets = [
  {properties: {population_2025: 1000, population_growth_2021_2025_pct: 2, age_45_plus_pct_2021: 40, median_household_income_weekly_2021: 1500}},
  {properties: {population_2025: 2000, population_growth_2021_2025_pct: 4, age_45_plus_pct_2021: 50, median_household_income_weekly_2021: 2000}},
];
const profile = {retailer: "OPSM", weights: {market_demand: 25, competitive_white_space: 25, centre_strength: 20, accessibility: 10, network_fit: 10, format_fit: 10}};
const base = Intel.candidateScore({
  point: {latitude: -33.87, longitude: 151.2},
  stores: [
    {retailer: "OPSM", latitude: -33.9, longitude: 151.2},
    {retailer: "Specsavers", latitude: -33.88, longitude: 151.2},
  ],
  markets,
  market: markets[1],
  centres: [],
  profile,
  areaSqm: null,
  targetAreaMin: null,
  targetAreaMax: null,
  amenitySummary: null,
});
assert.equal(base.coverage, 60);
assert.equal(base.reliable, false);
assert.equal(base.components.format_fit, null);

const covered = Intel.candidateScore({
  point: {latitude: -33.87, longitude: 151.2},
  stores: [{retailer: "Specsavers", latitude: -33.88, longitude: 151.2}],
  markets,
  market: markets[1],
  centres: [{latitude: -33.87, longitude: 151.2, annual_visits: 12000000, gla_sqm: 100000, trade_area_population: 500000, optical_store_count: 2}],
  profile,
  areaSqm: 120,
  targetAreaMin: 100,
  targetAreaMax: 140,
  amenitySummary: {transport: 4, parking: 2, health: 5},
});
assert.equal(covered.coverage, 100);
assert.equal(covered.reliable, true);
assert.ok(covered.score >= 0 && covered.score <= 100);

const shared = Intel.sanitiseShareState({
  view: "opportunity",
  filters: {retailers: new Set(["OPSM"]), country: "Australia", state: "NSW"},
  map: {latitude: -33.87, longitude: 151.2, zoom: 12},
  candidates: [{id: "one", name: "Public candidate", latitude: -33.8, longitude: 151.1, area_sqm: 120, profile_id: "opsm", asking_rent: 900000, notes: "private"}],
  lease_expiry: "2030-01-01",
});
assert.equal(shared.candidates[0].asking_rent, undefined);
assert.equal(shared.candidates[0].notes, undefined);
assert.equal(shared.lease_expiry, undefined);
assert.equal(shared.filters.country, "Australia");

const appSource = fs.readFileSync(require.resolve("../assets/app.js"), "utf8");
const indexSource = fs.readFileSync(require.resolve("../index.html"), "utf8");
assert.ok(appSource.includes("const CENTRE_BAG_SVG"));
assert.ok(appSource.match(/CENTRE_BAG_SVG/g).length >= 4);
assert.ok(indexSource.includes("centre-bag-icon centre-layer-icon"));
console.log("Intelligence tests passed");
