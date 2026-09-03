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
const partialGeometry = {type: "Polygon", coordinates: [[[-0.01, -0.01], [-0.01, 0.01], [0.01, 0.01], [0.01, -0.01], [-0.01, -0.01]]]};
const partialFraction = Intel.geometryOverlapFraction({latitude: 0, longitude: 0}, partialGeometry, 0.8);
assert.ok(partialFraction > 0 && partialFraction < 1);
const apportioned = Intel.catchmentSummary(
  {latitude: 0, longitude: 0}, 0.8,
  [{geometry: partialGeometry, properties: {population_2025: 1000, age_45_plus_pct_2021: 40, median_household_income_weekly_2021: 1500}}]
);
assert.ok(apportioned.population > 0 && apportioned.population < 1000);
assert.equal(apportioned.apportionmentMethod, "SA2 area-overlap apportionment");

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
  centres: [{centre_id: "place-au-test", latitude: -33.87, longitude: 151.2, annual_visits: 12000000, gla_sqm: 100000, trade_area_population: 500000, optical_store_count: 2}],
  placeId: "place-au-test",
  profile,
  areaSqm: 120,
  targetAreaMin: 100,
  targetAreaMax: 140,
  amenitySummary: {transport: 4, parking: 2, health: 5},
});
assert.equal(covered.coverage, 100);
assert.equal(covered.reliable, true);
assert.ok(covered.score >= 0 && covered.score <= 100);

const proximityOnly = Intel.candidateScore({
  point: {latitude: -33.87, longitude: 151.2},
  stores: [{retailer: "Specsavers", latitude: -33.88, longitude: 151.2}],
  markets,
  market: markets[1],
  centres: [{centre_id: "place-au-test", latitude: -33.87, longitude: 151.2, annual_visits: 12000000}],
  profile,
  areaSqm: null,
  targetAreaMin: null,
  targetAreaMax: null,
  amenitySummary: null,
});
assert.equal(proximityOnly.components.centre_strength, null);
assert.equal(proximityOnly.nearestCentre, null);
assert.equal(proximityOnly.nearbyCentreLead.centre.centre_id, "place-au-test");

const noCertifiedNetwork = Intel.candidateScore({
  point: {latitude: -33.87, longitude: 151.2}, stores: [], markets, market: markets[1], centres: [], profile,
  areaSqm: null, targetAreaMin: null, targetAreaMax: null, amenitySummary: null,
});
assert.equal(noCertifiedNetwork.components.competitive_white_space, null);
assert.equal(noCertifiedNetwork.components.network_fit, null);
assert.equal(noCertifiedNetwork.coverage, 25);

const shared = Intel.sanitiseShareState({
  view: "opportunity",
  filters: {retailers: new Set(["OPSM"]), country: "Australia", state: "NSW", affiliation: "provision"},
  map: {latitude: -33.87, longitude: 151.2, zoom: 12},
  candidates: [{id: "one", name: "Public candidate", latitude: -33.8, longitude: 151.1, area_sqm: 120, profile_id: "opsm", asking_rent: 900000, notes: "private"}],
  lease_expiry: "2030-01-01",
});
assert.equal(shared.candidates[0].asking_rent, undefined);
assert.equal(shared.candidates[0].notes, undefined);
assert.equal(shared.lease_expiry, undefined);
assert.equal(shared.filters.country, "Australia");
assert.equal(shared.filters.affiliation, "provision");

assert.equal(Intel.deriveLeasingArrangement([
  {status: "ACTIVE", role: "OWNER", group_id: "one"},
  {status: "ACTIVE", role: "LEASING_CONTROLLER", group_id: "one"},
], [{group_id: "one", group_type: "PROPERTY_COMPANY"}]), "In-house");
assert.equal(Intel.deriveLeasingArrangement([
  {status: "ACTIVE", role: "EXTERNAL_LEASING_AGENT", group_id: "agency"},
], []), "External agency");
assert.equal(Intel.deriveLeasingArrangement([
  {status: "ACTIVE", role: "OWNER", group_id: "private"},
  {status: "ACTIVE", role: "LEASING_CONTROLLER", group_id: "private"},
], [{group_id: "private", group_type: "PRIVATE_LANDLORD"}]), "Private landlord");
assert.equal(Intel.portfolioOverlapStatus({
  hasBailey: false,
  relationships: [{status: "ACTIVE", role: "MANAGER", group_id: "one"}],
  groupPortfolio: {one: {bailey_property_count: 2}},
  researchStatus: "Partial",
}), "PROPERTY_GROUP_OVERLAP");
const effectiveRelationships = Intel.effectivePropertyRelationships(
  [{relationship_id: "old", place_id: "p", group_id: "g", role: "OWNER", status: "ACTIVE"}],
  [{correction_type: "ASSET_RELATIONSHIP", action: "REMOVE", record_id: "old"},
   {correction_type: "ASSET_RELATIONSHIP", action: "UPSERT", record_id: "new", place_id: "p", group_id: "g", role: "MANAGER"}]
);
assert.deepEqual(effectiveRelationships.map((item) => item.relationship_id), ["new"]);
const propertyContext = Intel.competitorPropertyContext(
  {place_id: "centre", latitude: 0, longitude: 0},
  [
    {store_id: "inside", name: "Inside", retailer: "OPSM", place_id: "centre", latitude: 0.01, longitude: 0.01},
    {store_id: "near", name: "Near", retailer: "OPSM", place_id: "", latitude: 0, longitude: 0.001},
  ]
);
assert.equal(propertyContext.by_retailer.OPSM.in_centre.length, 1);
assert.equal(propertyContext.by_retailer.OPSM.nearby_unverified.length, 1);
assert.equal(Intel.placeMatchesRetailerFilters(
  {retailers: ["OPSM", "Specsavers"]},
  new Set(["OPSM", "Specsavers"]),
  new Set(["Oscar Wylee"])
), true);
assert.equal(Intel.placeMatchesRetailerFilters(
  {retailers: ["OPSM", "Specsavers", "Oscar Wylee"]},
  ["OPSM", "Specsavers"],
  ["Oscar Wylee"]
), false);
assert.equal(Intel.placeMatchesRetailerFilters({retailers: []}, [], []), true);
assert.equal(Intel.placeMatchesRetailerFilters({retailers: []}, [], [], true), false);
assert.equal(Intel.placeMatchesRetailerFilters({retailers: ["OPSM"]}, [], [], true), true);
const propertyShare = Intel.sanitiseShareState({
  view: "centres", filters: {}, placeFilters: {group_id: "group-qic", retailers: new Set(["OPSM", "Specsavers"]), min_income: "1500"},
  propertyCorrections: [{private_contact: "person"}], map: {}, candidates: [],
});
assert.equal(propertyShare.place_filters.group_id, "group-qic");
assert.deepEqual(propertyShare.place_filters.retailers, ["OPSM", "Specsavers"]);
assert.equal(propertyShare.propertyCorrections, undefined);
const opportunityShare = Intel.sanitiseShareState({
  view: "opportunity", filters: {}, placeFilters: {},
  opportunityFilters: {country: "Australia", setting: "", require_any_retailer: true, must_have_retailers: new Set(["OPSM", "Specsavers"]), must_not_have_retailers: new Set(["Oscar Wylee"])},
  map: {}, candidates: [],
});
assert.equal(opportunityShare.opportunity_filters.setting, "");
assert.equal(opportunityShare.opportunity_filters.require_any_retailer, true);
assert.deepEqual(opportunityShare.opportunity_filters.must_have_retailers, ["OPSM", "Specsavers"]);
assert.deepEqual(opportunityShare.opportunity_filters.must_not_have_retailers, ["Oscar Wylee"]);

const appSource = fs.readFileSync(require.resolve("../assets/app.js"), "utf8");
const indexSource = fs.readFileSync(require.resolve("../index.html"), "utf8");
assert.ok(appSource.includes("const CENTRE_BAG_SVG"));
assert.ok(appSource.match(/CENTRE_BAG_SVG/g).length >= 4);
assert.ok(indexSource.includes("centre-bag-icon centre-layer-icon"));
assert.ok(indexSource.includes('data-view="health"'));
assert.ok(appSource.includes("renderDataHealthView"));
assert.ok(appSource.includes("eligible_for_analytics"));
assert.ok(appSource.includes("portfolio_white_space"));
assert.ok(appSource.includes("PROPERTY_CORRECTION_STORAGE_KEY"));
assert.ok(appSource.includes('centre.centre_class_evidence?.confidence || "Medium"'));
assert.ok(appSource.includes("relevantCompetitionEntries"));
assert.ok(appSource.includes("placeFocusLayer"));
assert.ok(appSource.includes('state.view === "opportunity"'));
console.log("Intelligence tests passed");
