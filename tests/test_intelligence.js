const assert = require("node:assert/strict");
const fs = require("node:fs");
const Intel = require("../assets/intelligence.js");

const selectedRow = {
  country: "New Zealand", location_setting: "Shopping Centre",
  market_features: { population_2025: null, population_growth_2021_2025_pct: null },
  components: { bailey_footprint_similarity: 95, bailey_whitespace: 80, optical_market_validation: 60, accessibility_retail_context: 40 },
};
const reference = (features, overrides = {}) => ({ country: selectedRow.country, location_setting: selectedRow.location_setting, market_features: features, ...overrides });
const absentDemographics = Intel.selectedBenchmarkLookalike(selectedRow, [reference({ population_2025: null }), reference({ population_2025: "" })]);
assert.equal(absentDemographics.components.bailey_footprint_similarity, null, "Missing NZ values must not become a perfect zero-to-zero match or retain an unrelated default score");
assert.equal(absentDemographics.screening_completeness, 60);
assert.equal(absentDemographics.score, 67, "Reweight only the remaining observed components");
assert.equal(selectedRow.components.bailey_footprint_similarity, 95, "Selected comparisons must not mutate the standard public screen");
const observedRow = { ...selectedRow, market_features: { population_2025: 100, population_growth_2021_2025_pct: 0 } };
const partialComparison = Intel.selectedBenchmarkLookalike(observedRow, [
  reference({ population_2025: 100, population_growth_2021_2025_pct: 0 }),
  reference({ population_2025: "100", population_growth_2021_2025_pct: "0" }),
  reference({ population_2025: null, population_growth_2021_2025_pct: "" }),
]);
assert.equal(partialComparison.components.bailey_footprint_similarity, 100, "Missing peers must not drag the median toward zero; observed zero growth is valid");
assert.equal(partialComparison.footprint_comparison.available_fields, 2);
assert.equal(partialComparison.footprint_comparison.comparisons[0].reference_count, 2);
assert.equal(Intel.selectedBenchmarkLookalike(observedRow, [reference({ population_2025: 100 }), reference({ population_2025: null })]).components.bailey_footprint_similarity, null, "One usable peer is not a two-store comparison");
assert.equal(Intel.selectedBenchmarkLookalike(observedRow, [reference({ population_2025: 100 }, { country: "Australia" }), reference({ population_2025: 100 }, { location_setting: "High Street" })]).components.bailey_footprint_similarity, null, "Do not borrow evidence across countries or settings");
assert.equal(Intel.selectedBenchmarkLookalike({ ...selectedRow, components: {}, market_features: {} }, []).score, null, "No observed components means no score, not zero");

const boundaryPoint = {latitude: 0.5, longitude: 0.5};
const boundaryFeatures = [
  {properties: {sa2_code: "coarse"}, geometry: {type: "Polygon", coordinates: [[[0,0],[1,0],[1,1],[0,1],[0,0]]]}},
  {properties: {sa2_code: "official"}, geometry: {type: "Polygon", coordinates: [[[2,2],[3,2],[3,3],[2,3],[2,2]]]}}
];
const boundaryLinks = {"0.5000000,0.5000000": {match_status: "Unique", sa2_code: "official"}};
assert.equal(Intel.findMarketFeature(boundaryPoint, boundaryFeatures, boundaryLinks).properties.sa2_code, "official");
assert.equal(Intel.findMarketFeature({...boundaryPoint, latitude: 0.51}, boundaryFeatures, boundaryLinks).properties.sa2_code, "coarse", "Moved points must not reuse an old coordinate assignment");
assert.equal(Intel.findMarketFeature(boundaryPoint, boundaryFeatures, {"0.5000000,0.5000000": {match_status: "Ambiguous"}}), null);
assert.equal(Intel.findMarketFeature(boundaryPoint, [boundaryFeatures[0], boundaryFeatures[0]]), null);

assert.deepEqual(
  Intel.normalisePlaceShortlist(["old-a", "current", "old-a", "missing"], {"old-a": "middle", "middle": "current"}),
  ["current", "missing"],
  "shortlist remaps should resolve chains and deduplicate without dropping unavailable place IDs"
);

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
  [{geometry: partialGeometry, properties: {population_2025: 1000, age_45_plus_pct_2021: 40, median_equivalised_household_income_weekly_2021: 1500}}]
);
assert.ok(apportioned.population > 0 && apportioned.population < 1000);
assert.equal(apportioned.apportionmentMethod, "SA2 area-overlap apportionment");

const markets = [
  {properties: {population_2025: 1000, population_growth_2021_2025_pct: 2, age_45_plus_pct_2021: 40, median_equivalised_household_income_weekly_2021: 1500}},
  {properties: {population_2025: 2000, population_growth_2021_2025_pct: 4, age_45_plus_pct_2021: 50, median_equivalised_household_income_weekly_2021: 2000}},
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

const independentBrand = "Independent / Other optical";
const localRetailers = [independentBrand, "OPSM", "Specsavers"];
const inspectedPractice = {store_id: "practice", retailer: independentBrand, latitude: 0, longitude: 0, place_id: "centre", eligible_for_analytics: true};
const nearbyPractices = [
  inspectedPractice,
  {store_id: "another-independent", retailer: independentBrand, latitude: 0, longitude: 0.001, place_id: "centre", eligible_for_analytics: true},
  {store_id: "unassigned-independent", retailer: independentBrand, latitude: 0, longitude: 0.002, place_id: "", eligible_for_analytics: true},
  {store_id: "opsm", retailer: "OPSM", latitude: 0, longitude: 0.003, place_id: "centre", eligible_for_analytics: true},
  {store_id: "unverified", retailer: independentBrand, latitude: 0, longitude: 0.001, place_id: "centre", eligible_for_analytics: false},
  {store_id: "distant", retailer: "Specsavers", latitude: 1, longitude: 1, place_id: "elsewhere", eligible_for_analytics: true},
];
const independentCompetition = Intel.proximityModel(inspectedPractice, nearbyPractices, localRetailers, [0.5], inspectedPractice, true);
assert.equal(independentCompetition.radiusCounts[0].counts[independentBrand], 2, "other independent practices must remain competitors, including unassigned settings");
assert.equal(independentCompetition.radiusCounts[0].total, 3);
assert.deepEqual(independentCompetition.sameCentre.map((store) => store.store_id), ["another-independent", "opsm"], "only matching accepted place IDs establish co-tenancy");
assert.equal(independentCompetition.distances.some((entry) => entry.store.store_id === "practice" || entry.store.store_id === "unverified"), false);
assert.equal(independentCompetition.nearestByBrand[independentBrand].store.store_id, "another-independent");
const unmappedPractice = {...inspectedPractice, place_id: ""};
assert.deepEqual(Intel.proximityModel(unmappedPractice, nearbyPractices, localRetailers, [0.5], unmappedPractice, true).sameCentre, []);
const chainPractice = {...inspectedPractice, retailer: "OPSM"};
const chainCompetition = Intel.proximityModel(chainPractice, nearbyPractices, localRetailers, [0.5], chainPractice, true);
assert.equal(chainCompetition.radiusCounts[0].counts.OPSM, 0, "another branch of the same named chain is still excluded from competitor counts");
assert.equal(chainCompetition.radiusCounts[0].counts[independentBrand], 2);
assert.deepEqual(chainCompetition.sameCentre.map((store) => store.store_id), ["another-independent"]);
const proposedSiteCompetition = Intel.proximityModel(inspectedPractice, nearbyPractices, localRetailers, [0.5], null, true);
assert.equal(proposedSiteCompetition.radiusCounts[0].total, 4, "a hypothetical site has no existing store identity to exclude");

// The store-detail call uses default eligibility. A mappable unknown practice
// must not become a current competitor merely because it has coordinates.
const statusNeighbours = ["Unknown", "Closed", "Opening Soon", "Temporarily Closed"].map((status, index) => ({
  store_id: `non-current-${index}`, retailer: independentBrand, status,
  latitude: 0, longitude: 0.0001 * (index + 1), place_id: "centre",
  usable_for_network: true, eligible_for_analytics: false,
}));
const staleCurrent = {store_id: "stale-current", retailer: independentBrand, status: "Mapped", latitude: 0, longitude: 0.002,
  place_id: "centre", current_source: false, usable_for_network: true, eligible_for_analytics: true};
const defaultCompetition = Intel.proximityModel(inspectedPractice, [inspectedPractice, ...statusNeighbours, staleCurrent], localRetailers, [0.5], inspectedPractice);
assert.equal(defaultCompetition.radiusCounts[0].total, 1, "default store competition excludes non-current records but retains eligible stale-source stores");
assert.equal(defaultCompetition.nearestByBrand[independentBrand].store.store_id, "stale-current");
assert.deepEqual(defaultCompetition.distances.map((entry) => entry.store.store_id), ["stale-current"]);
assert.deepEqual(defaultCompetition.sameCentre.map((store) => store.store_id), ["stale-current"]);

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
assert.ok(indexSource.includes('data-layer="centres"'));
assert.ok(indexSource.includes('data-view="health"'));
assert.ok(appSource.includes("renderDataHealthView"));
assert.ok(appSource.includes("eligible_for_analytics"));
assert.ok(appSource.includes("portfolio_white_space"));
assert.ok(appSource.includes("PROPERTY_CORRECTION_STORAGE_KEY"));
assert.ok(appSource.includes('centre.centre_class_evidence?.confidence || "Medium"'));
assert.ok(appSource.includes("relevantCompetitionEntries"));
assert.ok(appSource.includes("placeFocusLayer"));
assert.ok(appSource.includes('state.view === "opportunity"'));
assert.ok(appSource.includes('id="selectAllRetailers"'));
assert.ok(appSource.includes('id="clearAllRetailers"'));
assert.ok(appSource.includes("Map and results update automatically"));
assert.equal(appSource.includes("Search / Apply"), false);
assert.ok(indexSource.includes('class="nav-overflow"'));
assert.ok(indexSource.includes('class="toolbar-overflow"'));
assert.ok(indexSource.includes("<span>Site planning</span>"));
assert.ok(indexSource.includes("<span>Map</span>"));
assert.equal(indexSource.includes('data-view="centres"'), false);
assert.ok(appSource.includes("Major retail brands"));
assert.ok(appSource.includes("Other brands and banners"));
assert.ok(appSource.includes('id="networkControls"'));
assert.ok(appSource.includes("independent-featured"));
assert.equal(appSource.includes('id="serviceInput"'), false);
assert.ok(appSource.includes('data-planning-mode="shortlist"'));
assert.ok(appSource.includes('data-planning-mode="discover"'));
assert.ok(appSource.includes('id="shortlistNotice"'));
assert.ok(appSource.includes("visibleOpportunityRows"));
assert.ok(appSource.includes("shortlistedOpportunityRows"));
assert.ok(appSource.includes("opportunityDashboardHtml"));
assert.ok(appSource.includes("shortlistDashboardHtml"));
assert.ok(appSource.includes("shortlistProfileHtml"));
require("node:child_process").execFileSync(process.execPath,
  [require("node:path").join(__dirname, "test_oscar_wylee_nz_importer.mjs")], { stdio: "inherit" });
console.log("Intelligence tests passed");

// Old links default to both public record layers; explicit empty arrays stay empty.
assert.deepEqual(Intel.sanitiseLayers(undefined), ["stores", "centres"]);
assert.deepEqual(Intel.sanitiseLayers([]), []);
assert.deepEqual(Intel.sanitiseLayers(["stores", "private", "stores", "centres"]), ["stores", "centres"]);
const explorationShare = Intel.sanitiseShareState({view:"centres", activeLayers:new Set(["centres", "private"]), filters:{search:"applied", audiology:"true", status:"Active"}, placeFilters:{state:"WA"}, drafts:{search:"private draft"}, map:{}, candidates:[]});
assert.deepEqual(explorationShare.layers, ["centres"]);
assert.equal(explorationShare.filters.search, "applied");
assert.equal(explorationShare.filters.audiology, "true");
assert.equal(explorationShare.filters.status, "Active");
assert.equal(explorationShare.place_filters.state, "WA");
assert.equal(explorationShare.drafts, undefined);

// Named groups keep an independent public snapshot, including point-analysis settings.
const comparisonOriginal = [{id:'one', name:'First', latitude:-33.9, longitude:151.1, place_id:'place-one', target_min_sqm:100, target_max_sqm:150, private_note:'excluded'}, {id:'two', name:'Second', latitude:-34, longitude:151.2}];
const comparisonCopy = Intel.comparisonSnapshot(comparisonOriginal);
comparisonOriginal[0].name = 'Edited';
assert.equal(comparisonCopy[0].name, 'First');
assert.equal(comparisonCopy[0].target_min_sqm, 100);
assert.equal(comparisonCopy[0].private_note, undefined);
assert.equal(Intel.comparisonSnapshot([{latitude:null,longitude:10},{latitude:91,longitude:10}]).length,0);
assert.equal(Intel.comparisonConnections([]).length,0);
assert.equal(Intel.comparisonConnections(comparisonCopy.slice(0,1)).length,0);
const comparisonEdges = Intel.comparisonConnections(comparisonCopy);
assert.equal(comparisonEdges.length,1);
assert.ok(Math.abs(comparisonEdges[0].distance - Intel.haversine(comparisonCopy[0], comparisonCopy[1])) < 0.00001);
const fivePoints = Array.from({length:5}, (_,i)=>({id:String(i), latitude:-33-i/100, longitude:151}));
assert.equal(Intel.comparisonConnections(fivePoints).length,10);
assert.equal(Intel.comparisonConnections([fivePoints[0], {...fivePoints[0],id:'same-position'}])[0].distance,0);
