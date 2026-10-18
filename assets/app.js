(function () {
  "use strict";

  const Intel = window.LeasingIntel;
  let BRAND_ORDER = [
    "OPSM",
    "Specsavers",
    "Bailey Nelson",
    "Oscar Wylee",
    "Independent / Other optical",
  ];
  let DEFAULT_RETAILERS = BRAND_ORDER.filter((retailer) => retailer !== "Independent / Other optical");
  const CENTRE_BAG_SVG = `<svg class="centre-bag-icon" viewBox="0 0 24 24" aria-hidden="true">
    <path d="M6 2 3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4Z"></path>
    <path d="M3 6h18"></path>
    <path d="M16 10a4 4 0 0 1-8 0"></path>
  </svg>`;
  const CORRIDOR_SVG = `<svg class="place-type-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="6" cy="5" r="3"/><circle cx="18" cy="19" r="3"/><path d="M9 5h8a4 4 0 0 1 0 8H7a4 4 0 0 0 0 8h8"/></svg>`;
  const MIXED_PLACES_SVG = `<svg class="place-type-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g transform="translate(7 0) scale(.7)"><path d="M6 2 3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4Z"/><path d="M3 6h18M16 10a4 4 0 0 1-8 0"/></g><g transform="translate(0 8) scale(.66)" stroke="#f6eddb" stroke-width="5"><circle cx="6" cy="5" r="3"/><circle cx="18" cy="19" r="3"/><path d="M9 5h8a4 4 0 0 1 0 8H7a4 4 0 0 0 0 8h8"/></g><g transform="translate(0 8) scale(.66)" stroke-width="2.5"><circle cx="6" cy="5" r="3"/><circle cx="18" cy="19" r="3"/><path d="M9 5h8a4 4 0 0 1 0 8H7a4 4 0 0 0 0 8h8"/></g></svg>`;

  function placeClusterPresentation(markers) {
    const places = markers.filter(marker => marker.options.placeId);
    const corridors = places.filter(marker => marker.options.placeKind === "corridor").length;
    const centres = places.filter(marker => marker.options.placeKind === "centre").length;
    const other = places.length - corridors - centres;
    const countLabel = (count, singular, plural) => `${count} ${count === 1 ? singular : plural}`;
    const parts = [];
    if (centres) parts.push(countLabel(centres, "shopping centre", "shopping centres"));
    if (corridors) parts.push(countLabel(corridors, "high-street corridor", "high-street corridors"));
    if (other) parts.push(countLabel(other, "other place", "other places"));
    return {
      count: places.length,
      icon: corridors === places.length && corridors ? CORRIDOR_SVG : centres === places.length && centres ? CENTRE_BAG_SVG : MIXED_PLACES_SVG,
      label: parts.join(" and "),
    };
  }

  function mapClusterLabel(markers) {
    const places = placeClusterPresentation(markers);
    const stores = markers.filter(marker => marker.options.storeId).length;
    const parts = [places.label, stores ? `${stores} ${stores === 1 ? "store" : "stores"}` : ""].filter(Boolean);
    return `${parts.join(" and ")} nearby. Click to zoom in. Proximity does not establish membership.`;
  }
  let BRAND_CONFIG = {
    OPSM: { color: "#211d1b", slug: "opsm", short: "OPSM", mark: "OPSM", markerWidth: 38 },
    Specsavers: {
      color: "#009b55",
      slug: "specsavers",
      short: "SPEC",
      mark: "Specsavers",
      markerWidth: 58,
    },
    "Bailey Nelson": {
      color: "#171717",
      slug: "bailey-nelson",
      short: "BN",
      mark: "BN",
      markerWidth: 50,
    },
    "Oscar Wylee": {
      color: "#2848a7",
      slug: "oscar-wylee",
      short: "OW",
      mark: "Oscar Wylee",
      markerWidth: 54,
    },
    "Independent / Other optical": {
      color: "#247775",
      slug: "independent-other",
      short: "IND",
      mark: "IND",
      markerWidth: 34,
    },
  };
  const VIEW_CONFIG = {
    overview: {eyebrow: "Explore locations", title: "Retail environments", subtitle: "Search public retail evidence and save hypotheses."},
    coverage: {eyebrow: "Network inventory", title: "Network & data coverage", subtitle: "Source coverage and recorded optical outlets."},
    network: {
      eyebrow: "Retail footprint",
      title: "Stores",
      subtitle: "Explore the optical footprint, then open a store to understand its market.",
    },
    centres: {
      eyebrow: "Landlord intelligence",
      title: "Places",
      subtitle: "Browse centres, plazas and high-street corridors with mapped optical tenants.",
    },
    opportunity: {
      eyebrow: "Lookalike screening",
      title: "Opportunities",
      subtitle: "Prioritise Bailey-free centres and corridors, with the evidence behind every rank.",
    },
    trends: {
      eyebrow: "Network movement",
      title: "Trends",
      subtitle: "Track openings, closures, relocations and source freshness.",
    },
    compare: {
      eyebrow: "Decision support",
      title: "Compare",
      subtitle: "Place shortlisted candidates side by side with transparent evidence.",
    },
    health: {
      eyebrow: "Census certification",
      title: "Data Health",
      subtitle: "Source freshness, completeness, classification and discovery reconciliation.",
    },
  };
  const STORE_RADII = [0.5, 1, 2, 5, 10];
  const MAX_CANDIDATE_BRAND_DISTANCE_KM = 100;
  const CATCHMENT_RADII = [1, 3, 5, 10];
  const AUSTRALIA_VIEW = { center: [-25.8, 134.4], zoom: 4 };
  const NEW_ZEALAND_VIEW = { center: [-41.15, 172.7], zoom: 5 };
  const NETWORK_BOUNDS = [
    [-47.6, 112],
    [-9, 179.5],
  ];
  const PUBLIC_STORE_FIELDS = [
    "retailer",
    "store_id",
    "affiliations",
    "name",
    "status",
    "country",
    "state",
    "suburb",
    "postcode",
    "full_address",
    "phone",
    "latitude",
    "longitude",
    "official_url",
    "website_url",
    "instagram_url",
    "facebook_url",
    "directory_url",
    "services",
    "audiology",
    "venue_name",
    "place_id",
    "location_setting",
    "mapping_confidence",
    "classification_confidence",
    "classification_basis",
    "store_area_sqm",
    "area_measure",
    "area_source",
    "area_date",
    "area_confidence",
    "source_url",
    "fetched_at",
  ];

  const elements = {
    viewContent: document.getElementById("viewContent"),
    viewEyebrow: document.getElementById("viewEyebrow"),
    viewTitle: document.getElementById("viewTitle"),
    viewSubtitle: document.getElementById("viewSubtitle"),
    visibleTotal: document.getElementById("visibleTotal"),
    visibleTotalLabel: document.getElementById("visibleTotalLabel"),
    freshness: document.getElementById("freshnessLabel"),
    detailPanel: document.getElementById("detailPanel"),
    detailContent: document.getElementById("detailContent"),
    loading: document.getElementById("loadingState"),
    modeNotice: document.getElementById("modeNotice"),
    layerPanel: document.getElementById("layerPanel"),
    candidateButton: document.getElementById("candidateButton"),
    candidateDock: document.getElementById("candidateDock"),
    candidateDockCount: document.getElementById("candidateDockCount"),
    candidateCards: document.getElementById("candidateCards"),
    siteFinderPanel: document.getElementById("siteFinderPanel"),
    siteFinderSearch: document.getElementById("siteFinderSearch"),
    siteFinderResults: document.getElementById("siteFinderResults"),
    toast: document.getElementById("toast"),
    reportSheet: document.getElementById("reportSheet"),
    reportContent: document.getElementById("reportContent"),
  };

  const state = {
    view: "overview",
    allStores: [],
    retailerRegistry: [],
    affiliations: [],
    filteredStores: [],
    privateOverlayActive: false,
    metadata: {},
    centres: [],
    markets: [],
    marketMetadata: {},
    storeLinks: {},
    events: {},
    profiles: [],
    dataHealth: null,
    propertyIntelligence: null,
    propertyGroups: [],
    propertyRelationships: [],
    basePropertyRelationships: [],
    propertySummaries: {},
    groupPortfolios: {},
    propertyCorrections: [],
    localPropertyGroups: [],
    lookalikes: { metadata: {}, rankings: {}, bailey_benchmarks: [] },
    placeTenants: [],
    destinationResearch: {},
    placeTenantMetadata: {},
    glossary: [],
    developmentSignals: [],
    developmentMetadata: {},
    placeIdRemaps: {},
    placeShortlist: new Set(),
    showShortlistOnly: false,
    performanceBenchmark: null,
    consultantCorrections: [],
    localPlaces: [],
    selectedStoreId: "",
    selectedCentreId: "",
    selectedCandidateId: "",
    focusedPlaceId: "",
    candidateDropMode: false,
    compareStores: [],
    candidates: [],
    comparisonConnectionsVisible: true,
    comparisonUndo: null,
    comparisonLibraryOpen: false,
    filters: {
      retailers: new Set(DEFAULT_RETAILERS),
      country: "",
      search: "",
      state: "",
      location: "",
      audiology: "",
      status: "",
      service: "",
      affiliation: "",
    },
    opportunityForm: {
      profile_id: "generic-optical",
      name: "",
      area_sqm: "",
      target_min_sqm: "",
      target_max_sqm: "",
    },
    opportunityFilters: {
      country: "Australia",
      setting: "",
      require_any_retailer: false,
      must_have_retailers: new Set(),
      must_not_have_retailers: new Set(),
    },
    placeFilters: {
      search: "", country: "", type: "", bailey: "", retailers: new Set(), confidence: "",
      group_id: "", arrangement: "", overlap: "", centre_class: "", min_income: "",
      min_bailey_distance: "", sort: "name",
    },
    activeLayers: new Set(["stores", "centres"]),
    sidebarPaneHeights: { network: 360, centres: 310, opportunity: 285 },
    amenityMarkers: [],
    amenitySummary: null,
  };

  const exploration = {
    drafts: {}, submitted: {}, mode: "network", panel: "", limit: 50,
    listScroll: 0, listFocus: "", returnMap: null, returnFocus: null,
    defaults: { network: structuredClone(state.filters), centres: structuredClone(state.placeFilters) },
  };
  const isMapView = () => ["network", "centres"].includes(state.view);
  const appliedFilters = () => state.view === "network" ? state.filters : state.placeFilters;
  const draftFilters = () => exploration.drafts[state.view] ||= structuredClone(appliedFilters());
  const markerById = new Map();
  const centreMarkerById = new Map();
  const candidateMarkerById = new Map();
  let demographicLayer = null;
  let growthLayer = null;
  let saturationLayer = null;
  let amenityRequestController = null;
  let toastTimer = null;
  let shortlistNoticeTimer = null;
  const CORRECTION_STORAGE_KEY = "bailey-leasing-place-corrections-v2";
  const LOCAL_PLACE_STORAGE_KEY = "bailey-leasing-local-places-v1";
  const PROPERTY_CORRECTION_STORAGE_KEY = "bailey-leasing-property-corrections-v1";
  const LOCAL_PROPERTY_GROUP_STORAGE_KEY = "bailey-leasing-local-property-groups-v1";
  const COMPARISON_STORAGE_KEY = "optical-leasing-comparisons-v1";
  const PLACE_SHORTLIST_STORAGE_KEY = "bailey-leasing-place-shortlist-v1";

  const map = L.map("map", { zoomControl: false, preferCanvas: true }).setView(
    AUSTRALIA_VIEW.center,
    AUSTRALIA_VIEW.zoom
  );
  L.control.zoom({ position: "bottomright" }).addTo(map);
  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    // OSM requires a referrer. Send only the origin, never saved-search URL data.
    referrerPolicy: "origin",
    attribution:
      '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> | ABS indicators',
  }).addTo(map);

  const storeClusters = L.markerClusterGroup({
    showCoverageOnHover: false,
    maxClusterRadius: 46,
    disableClusteringAtZoom: 16,
    spiderfyOnMaxZoom: true,
    iconCreateFunction(cluster) {
      const children = cluster.getAllChildMarkers();
      const retailers = new Set(children.map((marker) => marker.options.retailer));
      const size = children.length > 99 ? 42 : children.length > 19 ? 38 : 34;
      if (retailers.size === 1) {
        const retailer = children[0].options.retailer;
        return L.divIcon({
          className: "",
          html: `<div class="brand-cluster">${brandMarkHtml(retailer, "cluster")}<b>${children.length}</b></div>`,
          iconSize: [BRAND_CONFIG[retailer].markerWidth + 12, 30],
          iconAnchor: [(BRAND_CONFIG[retailer].markerWidth + 12) / 2, 15],
        });
      }
      return L.divIcon({
        className: "",
        html: `<div class="cluster-icon mixed" style="width:${size}px;height:${size}px">${children.length}</div>`,
        iconSize: [size, size],
      });
    },
  }).addTo(map);
  const centreLayer = L.markerClusterGroup({
    maxClusterRadius: 48,
    disableClusteringAtZoom: 14,
    showCoverageOnHover: false,
    spiderfyOnMaxZoom: true,
    iconCreateFunction(cluster) {
      const children = cluster.getAllChildMarkers();
      const places = placeClusterPresentation(children);
      const label = mapClusterLabel(children);
      return L.divIcon({
        className: "place-cluster-wrap",
        html: `<div class="place-cluster" title="${label}" aria-label="${label}">${places.icon}<strong>${places.count}</strong></div>`,
        iconSize: [48, 42],
      });
    },
  }).addTo(map);
  // A single geographic cluster at overview zoom; counts never imply place membership.
  const mixedOverviewLayer = L.markerClusterGroup({
    maxClusterRadius: 48,
    disableClusteringAtZoom: 14,
    showCoverageOnHover: false,
    spiderfyOnMaxZoom: true,
    iconCreateFunction(cluster) {
      const children = cluster.getAllChildMarkers();
      const placePresentation = placeClusterPresentation(children);
      const places = placePresentation.count;
      const stores = children.length - places;
      if (!places) return storeClusters.options.iconCreateFunction(cluster);
      if (!stores) return centreLayer.options.iconCreateFunction(cluster);
      const label = mapClusterLabel(children);
      return L.divIcon({
        className: "joined-cluster-wrap",
        html: `<div class="joined-cluster" title="${label}" aria-label="${label}"><span class="joined-places">${placePresentation.icon}<b>${places}</b></span><span class="joined-stores"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 10h18M5 10v11h14V10M3 10l2-7h14l2 7M9 21v-7h6v7"/></svg><b>${stores}</b></span></div>`,
        iconSize: [88, 30],
        iconAnchor: [44, 15],
      });
    },
  });
  [centreLayer, mixedOverviewLayer].forEach(layer => {
    layer.on("clustermouseover", event => {
      const label = mapClusterLabel(event.layer.getAllChildMarkers());
      event.layer.bindTooltip(label, {direction: "top", offset: [0, -12]}).openTooltip();
    });
    layer.on("clustermouseout", event => event.layer.closeTooltip());
  });
  let overviewRefreshFrame = 0;
  function scheduleOverviewRefresh() {
    cancelAnimationFrame(overviewRefreshFrame);
    overviewRefreshFrame = requestAnimationFrame(refreshOverviewClusters);
  }
  function refreshOverviewClusters() {
    const joined = map.getZoom() < 14 && !state.focusedPlaceId &&
      state.activeLayers.has("stores") && state.activeLayers.has("centres");
    mixedOverviewLayer.clearLayers();
    if (!joined) {
      if (map.hasLayer(mixedOverviewLayer)) map.removeLayer(mixedOverviewLayer);
      if (!map.hasLayer(storeClusters)) storeClusters.addTo(map);
      if (state.activeLayers.has("centres") && !map.hasLayer(centreLayer)) centreLayer.addTo(map);
      return;
    }
    // Separate marker instances preserve each normal layer's ownership and close-up behaviour.
    const originals = new Map([...storeClusters.getLayers(), ...centreLayer.getLayers()].map(marker => [marker.options.placeId ? `place:${marker.options.placeId}` : `store:${marker.options.storeId}`, marker]));
    const markers = [...originals.values()].map(original => {
      const marker = L.marker([original.options.baseLatitude, original.options.baseLongitude], {...original.options});
      const tooltip = original.getTooltip();
      if (tooltip) marker.bindTooltip(tooltip.getContent(), {...tooltip.options});
      marker.on("click", () => original.fire("click"));
      return marker;
    });
    if (map.hasLayer(storeClusters)) map.removeLayer(storeClusters);
    if (map.hasLayer(centreLayer)) map.removeLayer(centreLayer);
    mixedOverviewLayer.addLayers(markers);
    if (!map.hasLayer(mixedOverviewLayer)) mixedOverviewLayer.addTo(map);
    refreshIcons();
  }
  const selectionLayer = L.layerGroup().addTo(map);
  const comparisonLineRenderer = L.svg({padding: 0.5});
  const comparisonLineLayer = L.layerGroup().addTo(map);
  const candidateLayer = L.layerGroup().addTo(map);
  const catchmentLayer = L.layerGroup().addTo(map);
  const amenityLayer = L.layerGroup().addTo(map);
  const placeFocusLayer = L.layerGroup().addTo(map);
  const placeFocusCatchmentLayer = L.layerGroup().addTo(map);
  const developmentLayer = L.layerGroup();
  const focusedStoreMarkerById = new Map();

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function configureRetailers(payload) {
    const retailers = Array.isArray(payload?.retailers) ? payload.retailers : [];
    if (!retailers.length) return;
    state.retailerRegistry = retailers;
    state.affiliations = (Array.isArray(payload?.affiliations) ? payload.affiliations : [])
      .filter((item) => ["active", "partial"].includes(item.status));
    BRAND_ORDER = retailers.map((item) => item.name);
    DEFAULT_RETAILERS = retailers.filter((item) => item.default_visible).map((item) => item.name);
    BRAND_CONFIG = Object.fromEntries(retailers.map((item) => [item.name, {
      color: item.name === 'Independent / Other optical' ? '#247775' : item.color,
      slug: item.slug,
      short: item.short,
      mark: item.mark,
      logo: item.logo || "",
      markerWidth: Number(item.marker_width) || 40,
      networkType: item.network_type || "additional",
      minMarkerZoom: Number(item.min_marker_zoom) || 0,
    }]));
    state.filters.retailers = new Set(DEFAULT_RETAILERS);
  }

  function refreshIcons() {
    if (window.lucide) window.lucide.createIcons({ attrs: { "stroke-width": 1.8 } });
  }

  function formatDate(value) {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value || "Not recorded";
    return new Intl.DateTimeFormat("en-AU", {
      day: "numeric",
      month: "short",
      year: "numeric",
    }).format(date);
  }

  function formatNumber(value, suffix = "") {
    const number = value === null || value === undefined || value === "" ? null : Number(value);
    return Number.isFinite(number) ? `${number.toLocaleString("en-AU")}${suffix}` : "Not yet sourced";
  }

  function showToast(message, tone = "default") {
    window.clearTimeout(toastTimer);
    elements.toast.textContent = message;
    elements.toast.dataset.tone = tone;
    elements.toast.hidden = false;
    toastTimer = window.setTimeout(() => {
      elements.toast.hidden = true;
    }, 3200);
  }

  function brandMarkHtml(retailer, context = "inline") {
    const config = BRAND_CONFIG[retailer];
    if (retailer === 'Independent / Other optical') {
      return `<span class="retailer-logo independent-other ${context}" title="Independent / Other optical" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" focusable="false"><circle cx="12" cy="7" r="4"/><path d="M4 21v-2c0-4 3-6 8-6s8 2 8 6v2"/></svg></span>`;
    }
    if (retailer === "Bailey Nelson") {
      return `<span class="retailer-logo ${config.slug} ${context}" aria-hidden="true"><span class="bn-letter">B</span><i></i><span class="bn-letter">N</span></span>`;
    }
    if (config.logo) {
      return `<span class="retailer-logo ${config.slug} ${context} brand-asset" style="--brand-color:${escapeHtml(
        config.color
      )};--brand-logo-width:${config.markerWidth}px" aria-hidden="true"><img src="${escapeHtml(
        config.logo
      )}" alt="" /></span>`;
    }
    const generic = ["OPSM", "Specsavers", "Oscar Wylee", "Independent / Other optical"].includes(retailer)
      ? "" : " generic-network";
    return `<span class="retailer-logo ${config.slug} ${context}${generic}" style="--brand-color:${escapeHtml(config.color)}" aria-hidden="true"><span>${escapeHtml(
      config.mark
    )}</span></span>`;
  }

  function storeIcon(store, className = "store-marker") {
    if (!["Active", "Mapped"].includes(store.status)) className += " non-trading-store";
    const width = BRAND_CONFIG[store.retailer].markerWidth;
    const height = store.retailer === 'Independent / Other optical' ? 34 : 26;
    return L.divIcon({
      className,
      html: `<div class="store-logo-marker">${brandMarkHtml(store.retailer, "map")}${store.status === 'Opening Soon' ? '<span class="opening-soon-marker" title="Opening Soon" aria-label="Opening Soon">◷</span>' : ''}</div>`,
      iconSize: [width, height],
      iconAnchor: [width / 2, height / 2],
    });
  }

  function createStoreMarkers() {
    state.allStores.forEach((store) => {
      if (store.status === "Closed") return;
      const marker = L.marker([store.latitude, store.longitude], {
        icon: storeIcon(store),
        retailer: store.retailer,
        storeId: store.store_id,
        title: `${store.name}${store.status === 'Opening Soon' ? ' — Opening Soon' : ''}`,
        baseLatitude: store.latitude,
        baseLongitude: store.longitude,
      });
      marker.on("click", () => selectStore(store.store_id, false));
      marker.bindTooltip(
        `<strong>${escapeHtml(store.name)}</strong><br>${escapeHtml(store.status)} · ${escapeHtml(store.suburb)}, ${escapeHtml(store.state)}`,
        { direction: "top", offset: [0, -8] }
      );
      markerById.set(store.store_id, marker);
    });
  }

  function createCentreMarkers() {
    scheduleOverviewRefresh();
    centreLayer.clearLayers();
    centreMarkerById.clear();
    state.centres.forEach((centre) => {
      if (centre.latitude == null || centre.longitude == null || !Number.isFinite(Number(centre.latitude)) || !Number.isFinite(Number(centre.longitude))) return;
      const isCorridor = centre.location_setting === "High Street";
      const marker = L.marker([centre.latitude, centre.longitude], {
        icon: L.divIcon({
          className: "",
          html: `<div class="centre-pin ${isCorridor ? "corridor-pin" : ""}">${
            isCorridor ? CORRIDOR_SVG : CENTRE_BAG_SVG
          }</div>`,
          iconSize: [26, 26],
          iconAnchor: [13, 13],
        }),
        title: centre.name,
        baseLatitude: Number(centre.latitude),
        baseLongitude: Number(centre.longitude),
        placeId: centre.place_id,
        placeKind: isCorridor ? "corridor" : centre.location_setting === "Shopping Centre" ? "centre" : "other",
        zIndexOffset: 900,
      });
      marker.bindTooltip(
        `<strong>${escapeHtml(centre.name)}</strong><br>${escapeHtml(centre.place_type)} · ${centre.optical_store_count} mapped optical ${centre.optical_store_count === 1 ? "store" : "stores"}`,
        { direction: "top", offset: [0, -8] }
      );
      marker.on("click", () => inspectPlace(centre, false));
      centreMarkerById.set(centre.place_id, marker);
    });
    centreLayer.addLayers([...centreMarkerById.values()]);
    refreshIcons();
    repositionCloseZoomMarkers();
  }

  function createDevelopmentMarkers() {
    developmentLayer.clearLayers();
    state.developmentSignals.forEach((signal) => {
      if (!Number.isFinite(Number(signal.latitude)) || !Number.isFinite(Number(signal.longitude))) return;
      const marker = L.marker([Number(signal.latitude), Number(signal.longitude)], {
        icon: L.divIcon({
          className: "",
          html: `<div class="development-pin ${signal.evidence_status === "Lead" ? "lead" : ""}"><span aria-hidden="true">↗</span></div>`,
          iconSize: [28, 28],
          iconAnchor: [14, 14],
        }),
        title: signal.title,
        zIndexOffset: 1100,
      });
      marker.bindTooltip(`<strong>${escapeHtml(signal.title)}</strong><br>${escapeHtml(signal.status.replaceAll("_", " "))} · ${escapeHtml(signal.evidence_status)}`, { direction: "top", offset: [0, -9] });
      marker.on("click", () => {
        const place = state.centres.find((item) => item.place_id === signal.place_id);
        if (place) openCentreDetail(place);
      });
      marker.addTo(developmentLayer);
    });
    refreshIcons();
  }

  function resetMarkerPosition(marker) {
    if (!Number.isFinite(marker?.options?.baseLatitude) || !Number.isFinite(marker?.options?.baseLongitude)) return;
    const position = marker.getLatLng();
    if (position.lat === marker.options.baseLatitude && position.lng === marker.options.baseLongitude) return;
    marker.setLatLng([marker.options.baseLatitude, marker.options.baseLongitude]);
  }

  function repositionCloseZoomMarkers() {
    markerById.forEach(resetMarkerPosition);
    centreMarkerById.forEach(resetMarkerPosition);
    if (map.getZoom() < 16) return;

    const mapStores = storesForActiveMapView();
    // Keep store pins at their recorded coordinates; shared membership is not a shared point.

    centreMarkerById.forEach((marker, placeId) => {
      if (!centreLayer.hasLayer(marker)) return;
      const place = state.centres.find((item) => item.place_id === placeId);
      // A street reference must stay on its mapped road at every zoom level.
      // Lateral decluttering can otherwise move it into an unrelated property.
      if (place?.location_setting === "High Street") return;
      const base = L.latLng(marker.options.baseLatitude, marker.options.baseLongitude);
      const point = map.latLngToLayerPoint(base);
      const mappedStoreCount = mapStores.filter((store) => store.place_id === placeId).length;
      const distance = mappedStoreCount > 4 ? 110 : mappedStoreCount > 1 ? 90 : 58;
      const offset = L.point(-distance, 0);
      marker.setLatLng(map.layerPointToLatLng(point.add(offset)));
    });
  }

  function updateCentreMarkersForFilters() {
    scheduleOverviewRefresh();
    const visibleVenueIds = isMapView()
      ? new Set(filteredPlaces().map((place) => place.place_id))
      : state.view === "opportunity"
        ? new Set(visibleOpportunityRows().map((place) => place.place_id))
        : new Set(state.filteredStores.map((store) => store.place_id).filter(Boolean));
    centreLayer.clearLayers();
    centreLayer.addLayers([...visibleVenueIds].map(venueId => centreMarkerById.get(venueId)).filter(Boolean));
    window.requestAnimationFrame(repositionCloseZoomMarkers);
  }

  function storesForActiveMapView() {
    if (isMapView()) return state.filteredStores;
    if (state.view === "centres") {
      const placeIds = new Set(filteredPlaces().map((place) => place.place_id));
      return state.allStores.filter((store) => store.status !== "Closed" && store.place_id && placeIds.has(store.place_id));
    }
    if (state.view === "opportunity") {
      const placeIds = new Set(visibleOpportunityRows().map((place) => place.place_id));
      return state.allStores.filter((store) => store.status !== "Closed" && store.place_id && placeIds.has(store.place_id));
    }
    if (state.view === "compare" && state.candidates.length) {
      return state.allStores.filter((store) => store.status !== "Closed" && state.candidates.some((candidate) => Intel.haversine(candidate, store) <= MAX_CANDIDATE_BRAND_DISTANCE_KM));
    }
    return state.filteredStores;
  }

  function refreshActiveMapContext(clearFocus = false) {
    renderComparisonConnections();
    if (clearFocus && state.focusedPlaceId) clearPlaceFocus(false);
    refreshStoreMarkerVisibility();
    updateCentreMarkersForFilters();
    updateSaturationLayer();
    window.requestAnimationFrame(repositionCloseZoomMarkers);
  }

  function createCandidateMarker(candidate) {
    const marker = L.marker([candidate.latitude, candidate.longitude], {
      icon: L.divIcon({
        className: "",
        html: `<div class="candidate-marker">${state.candidates.indexOf(candidate) + 1}</div>`,
        iconSize: [32, 32],
        iconAnchor: [16, 16],
      }),
      zIndexOffset: 1200,
    });
    marker.on("click", () => openCandidateDetail(candidate));
    marker.addTo(candidateLayer);
    candidateMarkerById.set(candidate.id, marker);
  }

  function setView(view) {
    if (!VIEW_CONFIG[view]) return;
    exploration.flushPending?.();
    const sidebarOnly = isMapView() && ["network", "centres"].includes(view);
    if (view !== state.view && elements.detailPanel.classList.contains("open")) closeDetail();
    if (["network", "centres"].includes(view)) exploration.mode = view;
    state.view = view;
    document.getElementById("overviewDashboard").hidden = !["overview", "coverage"].includes(view);
    if (view !== "overview") window.requestAnimationFrame(() => map.invalidateSize());
    document.body.dataset.activeView = view;
    document.querySelectorAll("[data-view]").forEach((button) => {
      button.classList.toggle("active", button.dataset.view === view);
    });
    document.getElementById("mapNav").classList.toggle("active", isMapView());
    const config = VIEW_CONFIG[view];
    elements.viewEyebrow.textContent = config.eyebrow;
    elements.viewTitle.textContent = isMapView() ? "Explore the map" : ['opportunity', 'compare'].includes(view) ? 'Site planning' : config.title;
    document.getElementById('planningNav').classList.toggle('active', ['opportunity', 'compare'].includes(view));
    elements.viewSubtitle.textContent = config.subtitle;
    if (view === "health" && state.dataHealth) {
      elements.visibleTotal.textContent = Number(state.dataHealth.observed.stores).toLocaleString("en-AU");
      elements.visibleTotalLabel.textContent = "stores observed in census";
    } else if (view === "network") {
      elements.visibleTotal.textContent = state.filteredStores.length.toLocaleString("en-AU");
      elements.visibleTotalLabel.textContent = `selected of ${(Number(state.metadata.store_count) || state.allStores.length).toLocaleString("en-AU")} census stores`;
    }
    updateToolbarContext();
    renderView();
    if (!sidebarOnly) refreshActiveMapContext();
    updateShareUrl(false);
  }

  function renderView() {
    if (state.view === "overview") { renderEnvironmentExplorer(); return; }
    if (state.view === "coverage") { renderOverview(); return; }
    if (state.view === "network") renderNetworkView();
    else if (state.view === "centres") renderCentresView();
    else if (state.view === "opportunity") renderOpportunityView();
    else if (state.view === "trends") renderTrendsView();
    else if (state.view === "compare") renderCompareView();
    else renderDataHealthView();
    if (['opportunity', 'compare'].includes(state.view)) {
      elements.viewContent.insertAdjacentHTML('afterbegin', `<div class="exploration-modes planning-modes" role="group" aria-label="Site planning mode"><button type="button" data-planning-mode="discover" aria-pressed="${state.view === 'opportunity' && !state.showShortlistOnly}">Discover</button><button type="button" data-planning-mode="shortlist" aria-pressed="${state.view === 'opportunity' && state.showShortlistOnly}">Shortlist <b>${state.placeShortlist.size}</b></button><button type="button" data-planning-mode="compare" aria-pressed="${state.view === 'compare'}">Compare <b>${state.candidates.length + state.compareStores.length}</b></button></div>`);
      elements.viewContent.querySelectorAll('[data-planning-mode]').forEach(button => button.onclick = () => {
        state.showShortlistOnly = button.dataset.planningMode === 'shortlist';
        setView(button.dataset.planningMode === 'compare' ? 'compare' : 'opportunity');
        elements.viewContent.closest('.sidebar').scrollTop = 0;
      });
    }
    refreshIcons();
  }

  let environmentQuery = {};
  function renderEnvironmentExplorer() {
    window.EnvironmentExplorer.mount(document.getElementById('overviewDashboard'), state.environments, {
      initial: environmentQuery,
      onChange: query => { environmentQuery = structuredClone(query); },
      onCoverage: () => setView('coverage'),
      onShortlist: togglePlaceShortlist,
      isShortlisted: id => state.placeShortlist.has(id),
      onInspect: id => {
        const place = state.centres.find(p => p.place_id === id);
        if (!place) return;
        setView('centres'); inspectPlace(place, true);
      }
    });
  }

  let overviewRegion = '';
  function overviewBars(rows, max = Math.max(1, ...rows.map(row => row.count))) {
    return `<div class="overview-bars">${rows.map(row => `<div class="overview-bar"><span>${escapeHtml(row.label)}</span><div class="overview-bar-track"><i style="width:${100 * row.count / max}%"></i></div><b>${formatNumber(row.count)}</b></div>`).join('')}</div>`;
  }

  function renderOverview() {
    const host = document.getElementById('overviewDashboard');
    const data = window.LeasingOverview.summarise(state.allStores, state.centres, overviewRegion);
    const percent = data.centres.length ? Math.round(100 * data.absent.length / data.centres.length) : 0;
    const names = {gla_sqm:'Floor area recorded',annual_visits:'Annual visits recorded',tenancy_count:'Tenancy count recorded'};
    host.innerHTML = `<header class="overview-heading"><div><p class="eyebrow">Network inventory · Australian records</p><h1>Network & data coverage</h1><p>See the network, identify places to investigate, and understand the evidence behind them.</p></div><label>Focus area<select id="overviewRegion">${filterOptions(['NSW','VIC','QLD','WA','SA','TAS','ACT','NT'], overviewRegion, 'All Australia')}</select></label></header>
      <div class="overview-kpis">
        <article><span>Network-ready optical stores</span><strong>${formatNumber(data.network.length)}</strong><small>${formatNumber(data.stale)} carry a stale-source warning</small></article>
        <article><span>Shopping centres in our database</span><strong>${formatNumber(data.centres.length)}</strong><small>Canonical centres in this focus area</small></article>
        <article><span>No mapped Bailey Nelson</span><strong>${formatNumber(data.absent.length)}</strong><small>${percent}% of recorded shopping centres</small></article>
        <article><span>High-street corridors</span><strong>${formatNumber(data.corridors.length)}</strong><small>Recorded corridors, not a complete street census</small></article>
      </div>
      <div class="overview-grid">
        <article class="overview-card overview-whitespace"><header><h2>Bailey Nelson centre coverage</h2><p>Shopping centres in ${overviewRegion || 'Australia'}</p></header><div class="overview-donut-row"><div class="overview-donut" style="--share:${percent}%" role="img" aria-label="${data.absent.length} centres without a mapped Bailey Nelson; ${data.withBN} with one"><div><strong>${percent}%</strong><span>no mapped BN</span></div></div><div><p><b>${formatNumber(data.absent.length)}</b> no mapped BN</p><p><b>${formatNumber(data.withBN)}</b> with mapped BN</p><p><b>${formatNumber(data.validatedWhitespace)}</b> no mapped BN, but at least two optical retailer groups</p></div></div><button class="secondary-command" id="overviewWhitespace">Explore centres without mapped BN <span aria-hidden="true">↗</span></button><small>Absence in our records is a research lead, not confirmed vacancy or commercial opportunity.</small></article>
        <article class="overview-card"><header><h2>Optical stores by state</h2><p>Australia-wide context · stores certified for network use</p></header>${overviewBars(data.states)}<small>Last-known public records. Closed and unusable records are excluded; this is not live trading verification.</small></article>
        <article class="overview-card"><header><h2>How many optical outlets are recorded?</h2><p>Number of accepted optical outlets mapped to each centre</p></header>${overviewBars(data.distribution)}<small>Zero means no accepted optical mapping. Independents count as separate outlets. This is not the total tenant mix.</small></article>
        <article class="overview-card"><header><h2>Which optical networks reach the most centres?</h2><p>Top eight by shopping-centre presence in this focus area</p></header>${overviewBars(data.brands.slice(0,8))}<small>One count per named network per centre; independents are excluded from this brand chart and retain individual outlet identities.</small></article>
        <article class="overview-card"><header><h2>How much property evidence do we have?</h2><p>Coverage across ${formatNumber(data.centres.length)} shopping centres</p></header>${overviewBars(data.metrics.map(m=>({label:names[m.key],count:m.count})),Math.max(1,data.centres.length))}<small>Recorded figures may describe different periods. Coverage is not a quality or investment score.</small><button class="overview-text-link" id="overviewHealth">Open coverage & source checks ↗</button></article>
        <article class="overview-card overview-profile-teaser"><p class="eyebrow">Explore public evidence</p><h2>Find retail environments</h2><p>Select brands or categories, keep required features strict, and investigate exact or partial matches.</p><button class="secondary-command" id="overviewExplore">Explore locations ↗</button></article>
      </div><footer class="overview-footnote">Counts come from this tool’s Australian records, not a complete census of all Australian retail places. Map filters are separate from this overview. Dataset build: ${escapeHtml(formatDate(state.dataHealth.generated_at))}.</footer>`;
    document.getElementById('overviewRegion').onchange = event => { overviewRegion=event.target.value; renderOverview(); document.getElementById('overviewRegion').focus(); };
    document.getElementById('overviewHealth').onclick = () => setView('health');
    document.getElementById('overviewWhitespace').onclick = () => {
      state.placeFilters=structuredClone(exploration.defaults.centres);
      Object.assign(state.placeFilters,{country:'Australia',state:overviewRegion,type:'Shopping Centre',bailey:'Absent'});
      delete exploration.drafts.centres;
      state.activeLayers.add('centres');
      document.querySelector('[data-layer="centres"]').checked=true;
      setView('centres'); applyFilters(false); updateLayerVisibility(false); renderQuickResults();
      // Overview hides the map. Re-measure it after the visible layout has
      // settled, before fitting bounds; hidden-map dimensions give a bad zoom.
      window.requestAnimationFrame(() => {
        if (state.view !== 'centres') return;
        map.invalidateSize({pan: false});
        document.getElementById('fitResults')?.click();
      });
    };
    document.getElementById('overviewExplore').onclick = () => setView('overview');
  }

  function profileFactsHtml(facts) {
    return (facts || []).map(fact => `<div class="profile-research-fact"><h4>${escapeHtml(fact.label)}</h4><p>${escapeHtml(fact.value)}</p><a href="${escapeHtml(fact.source_url)}" target="_blank" rel="noopener">Source ↗</a><small>${fact.source_date ? `Source dated ${escapeHtml(formatDate(fact.source_date))}` : fact.source_period ? `Reference period ${escapeHtml(fact.source_period)}` : 'Source publication date not stated'} · reviewed ${escapeHtml(formatDate(fact.checked_at))}</small></div>`).join('');
  }

  function researchedPropertyHtml(centre) {
    const profile = state.destinationProfiles?.[centre.place_id];
    if (!profile?.completion_review) return '';
    return `<section class="detail-section"><h3>Ownership, management and leasing</h3>${profileFactsHtml(profile.property_facts.filter(f => ['Reported owners', 'Management', 'Centre format'].includes(f.label)))}${profileFactsHtml(profile.leasing_evidence)}</section>`;
  }

  function researchedMetricsHtml(centre) {
    const profile = state.destinationProfiles?.[centre.place_id];
    if (!profile?.completion_review) return '';
    return `<section class="detail-section"><h3>Public centre metrics</h3>${profileFactsHtml(profile.property_facts.filter(f => !['Reported owners', 'Management', 'Centre format'].includes(f.label)))}${profileFactsHtml(profile.trade_area_evidence)}<details><summary>Census measures and screening measures</summary>${profileFactsHtml(profile.census_context)}</details></section>`;
  }

  function visualDestinationProfile(centre) {
    if (centre.place_id !== 'place-au-nsw-ed-square-town-centre') return '';
    const profile = state.destinationProfiles?.[centre.place_id];
    const research = state.destinationResearch[centre.place_id];
    if (!research) return '';
    const categories = research.categories || [];
    return `<section class="visual-place-profile detail-section"><h3>Place at a glance</h3>
      <p>${profile?.completion_review ? `Public-source review completed ${escapeHtml(formatDate(profile.checked_at))}. Remaining evidence gaps are listed below.` : 'A directory-led view of the destination.'}</p>
      <div class="profile-visual-metrics"><div><strong>${formatNumber(research.in_scope_non_optical_listings)}</strong><span>non-optical directory listings</span></div><div><strong>${formatNumber(centre.optical_store_count)}</strong><span>mapped optical stores</span></div></div>
      ${profile?.anchors?.length ? `<h4>Source-identified anchors</h4><p>${profile.anchors.map(a => `<a href="${escapeHtml(a.source_url)}" target="_blank" rel="noopener">${escapeHtml(a.name)}</a>`).join(' · ')}</p>` : ''}
      <h4>Co-tenants by category</h4><p>Expand a category to see all its co-tenants. Categories may overlap.</p>
      <div class="profile-category-examples">${categories.map(c => `<details data-directory-category="${escapeHtml(c.name)}"><summary>${escapeHtml(c.name)} <span>${formatNumber(c.listing_count)}</span></summary><div class="category-directory-body"></div></details>`).join('')}</div>
      <details id="placeDirectory"><summary>Browse all ${formatNumber(research.source_listing_count)} directory listings</summary><div id="placeDirectoryBody"><p>Open to load the named businesses and services.</p></div></details>
      <p class="profile-evidence-note">Listing counts, not occupied tenancies, floor-area or sales shares. Full directory captured ${escapeHtml(formatDate(research.observed_at))}; individual category reviews retain their own dates.</p>
      <details><summary>Access and parking</summary>${profileFactsHtml(profile?.access)}</details>
    </section>`;
  }

  function retailerOptionsHtml(filters = state.filters) {
    const groups = [
      { type: "primary", label: "Major retail brands", hint: "Always visible", open: true },
      { type: "additional", label: "Other brands and banners", hint: "Visible at every zoom; clustered when needed" },
    ];
    const optionHtml = (retailer) => {
      const config = BRAND_CONFIG[retailer];
      const count = state.allStores.filter(
        (store) => store.retailer === retailer && storeMatchesFilters(store, true)
      ).length;
      return `<label class="retailer-option ${retailer === "Independent / Other optical" ? "independent-featured" : ""}" data-retailer="${escapeHtml(retailer)}" title="${escapeHtml(retailer)}">
        <input aria-label="${escapeHtml(retailer)}" type="checkbox" value="${escapeHtml(retailer)}" ${filters.retailers.has(retailer) ? "checked" : ""} />
        ${brandMarkHtml(retailer, "filter")}
        ${retailer === "Independent / Other optical" ? '<span class="independence-filter-label">Independent</span>' : ""}
        <output aria-label="${count} matching stores">${count}</output>
      </label>`;
    };
    return groups.map((group) => {
      const retailers = retailersForVisibleGroup(group.type);
      if (!retailers.length) return "";
      const selected = retailers.filter((retailer) => filters.retailers.has(retailer)).length;
      const options = retailers.map(optionHtml).join("");
      if (group.open) {
        return `<section class="retailer-group" data-network-type="${group.type}"><header><span><strong>${group.label}</strong><small>${group.hint}</small></span><b data-selection-count>${selected}/${retailers.length} selected</b></header><div class="retailer-option-grid">${options}</div></section>`;
      }
      return `<details class="retailer-group" data-network-type="${group.type}" ${selected ? "open" : ""}><summary><span><strong>${group.label}</strong><small>${group.hint}</small></span><b data-selection-count>${selected}/${retailers.length} selected</b><i data-lucide="chevron-down"></i></summary><div class="retailer-option-grid">${options}</div></details>`;
    }).join("");
  }

  function retailersForVisibleGroup(type) {
    const retailers = BRAND_ORDER.filter((retailer) => BRAND_CONFIG[retailer].networkType === type || (type === "additional" && retailer === "Independent / Other optical"));
    return type === "additional"
      ? retailers.sort((a, b) => Number(b === "Independent / Other optical") - Number(a === "Independent / Other optical"))
      : retailers;
  }

  function filterOptions(values, selected, emptyLabel) {
    return `<option value="">${emptyLabel}</option>${values
      .map((value) => `<option ${value === selected ? "selected" : ""}>${escapeHtml(value)}</option>`)
      .join("")}`;
  }

  function filterSignature(filters) {
    return JSON.stringify(filters, (_, value) => value instanceof Set ? [...value].sort() : value);
  }

  function setupExplorationSidebar() {
    const mode = state.view;
    const stores = mode === "network";
    const draft = draftFilters();
    const content = elements.viewContent;
    content.querySelector('.pane-resizer')?.remove();
    content.querySelector('.compact-metrics')?.remove();
    const oldControls = content.querySelector('.workspace-controls');
    const filterSection = oldControls.querySelector('.filters');
    const form = document.createElement('form');
    form.className = 'exploration-form';
    form.setAttribute('aria-label', stores ? 'Store search and filters' : 'Place search and filters');
    while (filterSection.firstChild) form.append(filterSection.firstChild);
    oldControls.replaceWith(form);
    content.insertAdjacentHTML('afterbegin', `<div class="exploration-modes" role="group" aria-label="Search mode"><button type="button" data-mode="network" aria-pressed="${stores}">Stores</button><button type="button" data-mode="centres" aria-pressed="${!stores}">Places</button></div>`);
    content.querySelectorAll('[data-mode]').forEach(button => button.onclick = () => setView(button.dataset.mode));
    const mappings = stores
      ? {searchInput:'search', countrySelect:'country', stateSelect:'state', locationSelect:'location', audiologySelect:'audiology', statusSelect:'status', affiliationSelect:'affiliation'}
      : {centreSearch:'search', placeCountry:'country', placeRegion:'state', placeType:'type', placeBailey:'bailey', placeArrangement:'arrangement', placeOverlap:'overlap', placeCentreClass:'centre_class', placeSort:'sort', placeMinIncome:'min_income', placeMinBailey:'min_bailey_distance'};
    if (stores) {
      const advanced = document.createElement('details');
      advanced.className = 'advanced-filters';
      advanced.innerHTML = '<summary>More filters <span>Audiology and affiliation</span></summary><div class="select-grid"></div>';
      ['audiologySelect','affiliationSelect'].forEach(id => advanced.querySelector('.select-grid').append(document.getElementById(id).closest('label')));
      form.append(advanced);
      const brands = form.querySelector('.retailer-filter');
      const brandDetails = document.createElement('details');
      brandDetails.className = 'advanced-filters brand-picker';
      brandDetails.innerHTML = `<summary>Retail brands <span id="draftBrandCount">${draft.retailers.size} selected</span></summary>`;
      brands.replaceWith(brandDetails); brandDetails.append(brands);
      document.getElementById('selectAllRetailers').onclick = () => changeBrands(true);
      document.getElementById('clearAllRetailers').onclick = () => changeBrands(false);
      function changeBrands(selected) {
        draft.retailers = new Set(selected ? BRAND_ORDER : []);
        form.querySelectorAll('.retailer-option input').forEach(input => { input.checked = selected; });
        queueFilterUpdate(false);
      }
    } else {
      const grid = form.querySelector('.primary-place-filters');
      grid.insertAdjacentHTML('beforeend', `<label><span>State / region</span><select id="placeRegion">${filterOptions([...new Set(state.centres.filter(place => !draft.country || place.country === draft.country).map(place => place.state).filter(Boolean))].sort(), draft.state || '', 'All states / regions')}</select></label>`);
      // The full list has a fixed geographic order; retain old sort values in old URLs only.
      document.getElementById('placeSort').closest('label').remove();
    }
    form.insertAdjacentHTML('beforeend', '<div class="search-actions"><button type="button" id="resetMode" class="secondary-command">Reset filters</button></div><p id="pendingFilters" role="status"></p>');
    const actions = form.querySelector('.search-actions');
    form.querySelector('.search-field').after(actions);
    actions.after(document.getElementById('pendingFilters'));
    const pending = () => {
      document.getElementById('pendingFilters').textContent = filterSignature(draft) === filterSignature(appliedFilters()) ? 'Map and results update automatically' : 'Updating results…';
      const count = document.getElementById('draftBrandCount');
      if (count) count.textContent = `${draft.retailers.size} selected`;
      form.querySelectorAll('.retailer-group[data-network-type]').forEach(group => {
        const brands = retailersForVisibleGroup(group.dataset.networkType);
        group.querySelector('[data-selection-count]').textContent = `${brands.filter(brand => draft.retailers.has(brand)).length}/${brands.length} selected`;
      });
    };
    let filterTimer = null;
    const applyLiveFilters = () => {
      clearTimeout(filterTimer);
      filterTimer = null;
      if (!form.isConnected || state.view !== mode) return;
      const showingResults = exploration.panel === 'results' && elements.detailPanel.classList.contains('open');
      if (!showingResults && elements.detailPanel.classList.contains('open')) {
        // Filtering keeps the user's current map position and typing focus.
        exploration.returnMap = null;
        exploration.returnFocus = null;
        closeDetail();
      }
      if (stores) state.filters = structuredClone(draft); else state.placeFilters = structuredClone(draft);
      exploration.submitted[mode] = true;
      exploration.limit = 50;
      const layer = stores ? 'stores' : 'centres';
      state.activeLayers.add(layer);
      document.querySelector(`[data-layer="${layer}"]`).checked = true;
      applyFilters(false);
      updateLayerVisibility(false);
      renderQuickResults();
      if (showingResults) showFullResults(false, true);
      form.querySelectorAll('.retailer-option').forEach(option => {
        const count = state.allStores.filter(store => store.retailer === option.dataset.retailer && storeMatchesFilters(store, true)).length;
        option.querySelector('output').textContent = count;
        option.querySelector('output').setAttribute('aria-label', `${count} matching stores`);
      });
      pending();
    };
    const queueFilterUpdate = (typing) => {
      clearTimeout(filterTimer);
      pending();
      if (typing) filterTimer = setTimeout(applyLiveFilters, 250);
      else applyLiveFilters();
    };
    exploration.flushPending = () => { if (filterTimer !== null) applyLiveFilters(); };
    Object.entries(mappings).forEach(([id,key]) => {
      const input = document.getElementById(id);
      if (!input) return;
      input.addEventListener(input.tagName === 'SELECT' ? 'change' : 'input', () => {
        draft[key] = input.value;
        if (key === 'country') {
          draft.state = '';
          const region = document.getElementById(stores ? 'stateSelect' : 'placeRegion');
          const records = stores ? state.allStores : state.centres;
          region.innerHTML = filterOptions([...new Set(records.filter(row => !draft.country || row.country === draft.country).map(row => row.state).filter(Boolean))].sort(), '', 'All states / regions');
        }
        if (key === 'affiliation' && draft.affiliation) {
          state.allStores.filter(row => String(row.affiliations || '').split('|').includes(draft.affiliation)).forEach(row => draft.retailers.add(row.retailer));
          form.querySelectorAll('.retailer-option input').forEach(input => { input.checked = draft.retailers.has(input.value); });
        }
        if (!stores && key === 'type') {
          const centreClass = document.getElementById('placeCentreClass');
          centreClass.disabled = draft.type === 'High Street Corridor';
          if (centreClass.disabled) { draft.centre_class = ''; centreClass.value = ''; }
        }
        queueFilterUpdate(input.tagName !== 'SELECT');
      });
    });
    form.querySelectorAll('.retailer-option input, .place-retailer-filter input').forEach(input => input.addEventListener('change', () => {
      if (input.checked) draft.retailers.add(input.value); else draft.retailers.delete(input.value);
      queueFilterUpdate(false);
    }));
    form.onsubmit = event => {
      event.preventDefault();
      applyLiveFilters();
    };
    document.getElementById('resetMode').onclick = () => {
      clearTimeout(filterTimer);
      filterTimer = null;
      Object.assign(draft, structuredClone(exploration.defaults[mode]));
      applyLiveFilters();
      renderView();
      document.getElementById('resetMode').focus();
      showToast('Filters reset for this search mode.');
    };
    if (!stores) {
      const centreClass = document.getElementById('placeCentreClass');
      centreClass.disabled = draft.type === 'High Street Corridor';
      centreClass.title = 'Shopping-centre classification; not applicable to high-street corridors';
      if (centreClass.disabled && draft.centre_class) {
        draft.centre_class = '';
        centreClass.value = '';
        applyLiveFilters();
      }
    }
    exploration.submitted[mode] = true;
    pending(); renderQuickResults();
  }

  function explorationRows() {
    const rows = state.view === 'network' ? state.filteredStores : filteredPlaces();
    const key = row => [row.country || 'Country unrecorded', row.state || 'Region unrecorded', row.suburb || row.locality || 'Locality unrecorded', row.name || ''].join('\u0000');
    return rows.slice().sort((a,b) => key(a).localeCompare(key(b), 'en-AU', {numeric:true}));
  }

  function explorationRowHtml(row) {
    const id = row.store_id || row.place_id;
    const selected = id === state.selectedStoreId || id === state.selectedCentreId;
    return `<button type="button" class="exploration-row ${selected ? 'selected' : ''}" data-result-id="${escapeHtml(id)}" aria-pressed="${selected}">
      ${row.store_id ? brandMarkHtml(row.retailer, 'list') : `<span class="result-place-mark" aria-hidden="true">${row.place_type === "High Street Corridor" ? CORRIDOR_SVG : CENTRE_BAG_SVG}</span>`}
      <span><strong>${escapeHtml(row.name)}</strong><small>${escapeHtml([row.suburb || row.locality, row.state, row.postcode].filter(Boolean).join(' · ') || 'Locality unrecorded')}</small><small>${escapeHtml(row.retailer || row.place_type || 'Place')}${row.status === 'Opening Soon' ? ' · ◷ Opening Soon' : ''}${selected ? ' · Selected' : ''}</small></span><span aria-hidden="true">↗</span></button>`;
  }

  function bindResultRows(container) {
    container.querySelectorAll('[data-result-id]').forEach(button => button.onclick = () => {
      if (exploration.panel === 'results') {
        exploration.listScroll = elements.detailPanel.scrollTop;
        exploration.listFocus = button.dataset.resultId;
      }
      const row = explorationRows().find(row => (row.store_id || row.place_id) === button.dataset.resultId);
      if (!row) return;
      if (row.store_id) selectStore(row.store_id, true); else inspectPlace(row, true);
    });
  }

  function renderQuickResults() {
    if (!isMapView()) return;
    const section = elements.viewContent.querySelector('.result-section');
    if (!section) return;
    section.className = 'result-section quick-results';
    const rows = explorationRows();
    document.querySelector('[data-layer="stores"]').closest("label").title = `${state.filteredStores.length} stores match the applied Stores filters`;
    document.querySelector('[data-layer="centres"]').closest("label").title = `${filteredPlaces().length} places match the applied Places filters`;
    const applied = appliedFilters();
    const values = Object.entries(applied).filter(([key,value]) => key !== 'retailers' && key !== 'sort' && value).map(([key,value]) => `${key.replaceAll('_',' ')}: ${value}`);
    values.push(state.view === 'network' ? `${applied.retailers.size} brands selected` : applied.retailers.size ? `${applied.retailers.size} required brands` : 'Any retailer mix');
    section.innerHTML = `<div class="applied-summary">${values.map(value => `<span>${escapeHtml(value)}</span>`).join('')}</div><p class="result-scope">All matching records—not limited to the visible map.</p>
      <div class="results-actions"><button type="button" id="browseResults" class="primary-command" ${rows.length ? '' : 'disabled'}>Open results list (${rows.length.toLocaleString('en-AU')})</button><button type="button" id="fitResults" class="secondary-command" ${rows.length ? '' : 'disabled'}>Fit results</button></div>
      ${exploration.submitted[state.view] ? `<h2>Quick results <small>${Math.min(5,rows.length)} of ${rows.length.toLocaleString('en-AU')}</small></h2>${rows.slice(0,5).map(explorationRowHtml).join('')}${rows.length ? '' : '<p class="empty-note">No matches. Try a broader search or reset the filters.</p>'}` : ''}`;
    elements.visibleTotal.textContent = rows.length.toLocaleString('en-AU');
    elements.visibleTotalLabel.textContent = `matching ${state.view === 'network' ? 'stores' : 'places'}`;
    document.getElementById('browseResults').onclick = () => { closeDetail(); exploration.returnFocus = document.getElementById('browseResults'); exploration.limit = 50; showFullResults(); };
    document.getElementById('fitResults').onclick = () => {
      map.invalidateSize({pan: false});
      const points = rows.filter(row => row.latitude != null && row.longitude != null && Number.isFinite(Number(row.latitude)) && Number.isFinite(Number(row.longitude))).map(row => [Number(row.latitude),Number(row.longitude)]);
      if (points.length) map.fitBounds(points, {padding:[45,45],maxZoom:15,animate:false}); else showToast('No mapped coordinates in these results.');
    };
    bindResultRows(section);
    refreshIcons();
  }

  function showFullResults(restore = false, keepFocus = false) {
    exploration.panel = 'results';
    const rows = explorationRows();
    let previousGroup = '';
    const html = rows.slice(0,exploration.limit).map(row => {
      const group = [row.country || 'Country unrecorded', row.state || 'Region unrecorded', row.suburb || row.locality || 'Locality unrecorded'].join(' · ');
      const heading = group === previousGroup ? '' : `<h3 class="result-group">${escapeHtml(group)}</h3>`;
      previousGroup = group;
      return heading + explorationRowHtml(row);
    }).join('');
    elements.detailContent.innerHTML = `<header class="results-header"><h2 tabindex="-1" id="resultsHeading">${state.view === 'network' ? 'Stores' : 'Places'}</h2><p>${rows.length.toLocaleString('en-AU')} matching records · alphabetical by area</p><p>All matching records—not limited to the visible map.</p></header><div class="full-results">${html || '<p>No matches. Broaden your search or reset filters.</p>'}${rows.length > exploration.limit ? '<button type="button" class="secondary-command" id="loadMoreResults">Load more</button>' : ''}<p class="list-progress">Showing ${Math.min(rows.length,exploration.limit)} of ${rows.length}</p></div>`;
    openDetailPanel(); bindResultRows(elements.detailContent);
    const more = document.getElementById('loadMoreResults');
    if (more) more.onclick = () => {
      const scroll = elements.detailPanel.scrollTop;
      const firstNew = rows[exploration.limit];
      exploration.limit += 50; showFullResults();
      const button = [...elements.detailContent.querySelectorAll('[data-result-id]')].find(button => button.dataset.resultId === (firstNew.store_id || firstNew.place_id));
      button?.focus({preventScroll:true}); elements.detailPanel.scrollTop = scroll;
    };
    if (restore) {
      const button = [...elements.detailContent.querySelectorAll('[data-result-id]')].find(button => button.dataset.resultId === exploration.listFocus);
      button?.focus({preventScroll:true}); elements.detailPanel.scrollTop = exploration.listScroll;
    } else { elements.detailPanel.scrollTop = 0; if (!keepFocus) document.getElementById('resultsHeading').focus({preventScroll:true}); }
  }

  function beginInspection() {
    if (!isMapView()) return;
    if (!exploration.returnMap) exploration.returnMap = {center:map.getCenter(),zoom:map.getZoom()};
    if (exploration.panel === 'results') exploration.panel = 'detail-from-results';
    else if (exploration.panel !== 'detail-from-results') {
      exploration.panel = 'detail'; exploration.returnFocus = document.activeElement;
    }
  }

  function restoreInspectionMap() {
    if (exploration.returnMap) {
      map.setView(exploration.returnMap.center,exploration.returnMap.zoom,{animate:false});
      exploration.returnMap = null;
    }
    selectionLayer.clearLayers();
  }

  function inspectPlace(place, moveMap) {
    beginInspection();
    openCentreDetail(place);
    if (moveMap && isMapView() && place.latitude != null && place.longitude != null && Number.isFinite(Number(place.latitude)) && Number.isFinite(Number(place.longitude))) map.setView([place.latitude,place.longitude],15,{animate:false});
    if (isMapView()) renderQuickResults();
  }

  function renderNetworkView() {
    const draft = draftFilters();
    const countryStores = draft.country
      ? state.allStores.filter((store) => store.country === draft.country)
      : state.allStores;
    const countries = [...new Set(state.allStores.map((store) => store.country))].sort();
    const states = [...new Set(countryStores.map((store) => store.state))].sort();
    const statuses = [...new Set(state.allStores.filter(store => store.status !== "Closed").map((store) => store.status))].sort();
    elements.viewContent.innerHTML = `
      <details class="workspace-controls" id="networkControls" open style="--pane-height:${state.sidebarPaneHeights.network}px">
        <summary><span><strong>Search and filters</strong><small>Collapse after choosing the brands and market</small></span><i data-lucide="chevron-down"></i></summary>
        <div class="workspace-controls-body"><section class="filters" aria-label="Network filters">
        <label class="search-field"><i data-lucide="search"></i><span class="sr-only">Search stores</span>
          <input id="searchInput" type="search" value="${escapeHtml(draft.search)}" placeholder="Store, suburb or postcode" autocomplete="off" />
        </label>
        <div class="select-grid">
          <label><span>Country</span><select id="countrySelect">${filterOptions(
            countries,
            draft.country,
            "Australia + New Zealand"
          )}</select></label>
          <label><span>State / region</span><select id="stateSelect">${filterOptions(
            states,
            draft.state,
            "All states / regions"
          )}</select></label>
          <label><span>Place type</span><select id="locationSelect">${filterOptions(
            ["Shopping Centre", "High Street", "Other", "Uncertain"],
            draft.location,
            "All places"
          )}</select></label>
          <label><span>Audiology</span><select id="audiologySelect">
            <option value="">Any</option><option value="true" ${draft.audiology === "true" ? "selected" : ""}>Available</option>
            <option value="false" ${draft.audiology === "false" ? "selected" : ""}>Not listed</option>
          </select></label>
          <label><span>Status</span><select id="statusSelect">${filterOptions(statuses, draft.status, "All statuses")}</select></label>
          <label><span>Affiliation</span><select id="affiliationSelect"><option value="">Any affiliation</option>${state.affiliations
            .map((item) => `<option value="${escapeHtml(item.affiliation_id)}" ${draft.affiliation === item.affiliation_id ? "selected" : ""}>${escapeHtml(item.name)}${item.status === "partial" ? " · partial coverage" : ""}</option>`)
            .join("")}</select></label>
        </div>
        <fieldset class="retailer-filter"><legend>Retail brands</legend>
          <div class="retailer-filter-actions">
            <button id="selectAllRetailers" type="button">Select all</button>
            <button id="clearAllRetailers" type="button">Clear all</button>
          </div>
          ${retailerOptionsHtml(draft)}
        </fieldset>
      </section></div>
      </details>
      <div class="pane-resizer" id="networkPaneResizer" role="separator" aria-label="Resize store filters and place results" aria-orientation="horizontal" tabindex="0"><i></i></div>
      <section class="result-section">
        <div class="section-heading"><h2>Places</h2><span id="networkResultCount"></span></div>
        <div class="store-list" id="storeList"></div>
      </section>`;
    setupExplorationSidebar();
  }

  function renderNetworkResults() { if (isMapView()) renderQuickResults(); }

  function storeRowHtml(store) {
    return `<button class="store-row ${store.store_id === state.selectedStoreId ? "active" : ""}" data-store-id="${escapeHtml(
      store.store_id
    )}" data-retailer="${escapeHtml(store.retailer)}">
      ${brandMarkHtml(store.retailer, "list")}<span class="row-copy"><strong>${escapeHtml(store.name)}</strong>
      <small>${escapeHtml(`${store.suburb}, ${store.state} ${store.postcode}`)}</small></span>
      <span class="row-type">${escapeHtml(store.location_type)}</span></button>`;
  }

  function storeMatchesFilters(store, ignoreRetailer = false) {
    if (store.status === "Closed") return false;
    const query = state.filters.search.trim().toLowerCase();
    const haystack =
      `${store.name} ${store.suburb} ${store.postcode} ${store.full_address} ${store.venue_name}`.toLowerCase();
    return (
      (ignoreRetailer || state.filters.retailers.has(store.retailer)) &&
      (!state.filters.country || store.country === state.filters.country) &&
      (!query || haystack.includes(query)) &&
      (!state.filters.state || store.state === state.filters.state) &&
      (!state.filters.location || store.location_type === state.filters.location) &&
      (!state.filters.audiology || String(store.audiology) === state.filters.audiology) &&
      (!state.filters.status || store.status === state.filters.status) &&
      (!state.filters.affiliation || String(store.affiliations || "").split("|").includes(state.filters.affiliation))
    );
  }

  function applyFilters(render = true) {
    state.filteredStores = state.allStores.filter((store) => storeMatchesFilters(store));
    refreshActiveMapContext();
    if (state.view === "network") {
      elements.visibleTotal.textContent = state.filteredStores.length.toLocaleString("en-AU");
      elements.visibleTotalLabel.textContent = `selected of ${(Number(state.metadata.store_count) || state.allStores.length).toLocaleString("en-AU")} census stores`;
    }
    if (render && state.view === "network") renderNetworkView();
    updateShareUrl(false);
    window.requestAnimationFrame(repositionCloseZoomMarkers);
  }

  function refreshStoreMarkerVisibility() {
    scheduleOverviewRefresh();
    storeClusters.clearLayers();
    if (state.focusedPlaceId) return;
    const zoom = map.getZoom();
    if (!state.activeLayers.has("stores")) return;
    const placeScopedView = state.view === "opportunity";
    if (placeScopedView && zoom < 8) return;
    storeClusters.addLayers(storesForActiveMapView()
      .filter(store => state.filters.search || zoom >= (BRAND_CONFIG[store.retailer]?.minMarkerZoom || 0))
      .map(store => markerById.get(store.store_id)).filter(Boolean));
  }

  function updateToolbarContext() {
    const reportButton = document.getElementById("reportButton");
    const downloadButton = document.getElementById("downloadButton");
    if (!reportButton || !downloadButton) return;
    reportButton.title = "Print a brief for the open place or candidate";
    const exportLabels = {
      network: "Export the currently selected store records",
      centres: "Export the currently filtered retail places",
      opportunity: "Export the current Bailey-free opportunity results",
      compare: "Export the candidate comparison",
      trends: "Export the currently selected store records",
      health: "Export the currently selected store records",
    };
    downloadButton.title = exportLabels[state.view] || "Export current public records";
  }

  function relevantCompetitionEntries(place) {
    const byRetailer = place?.competitor_context?.by_retailer || {};
    const categories = [
      ["in_centre", place.location_setting === "High Street" ? "IN CORRIDOR" : "IN CENTRE", 0],
      ["nearby_unverified", place.location_setting === "High Street" ? "NEARBY — NOT VERIFIED IN CORRIDOR" : "NEARBY — NOT VERIFIED IN CENTRE", 1],
      ["catchment_2km", "ELSEWHERE WITHIN 2 KM", 2],
    ];
    const entries = new Map();
    BRAND_ORDER.forEach((retailer) => {
      const context = byRetailer[retailer] || {};
      categories.forEach(([key, label, priority]) => {
        (context[key] || []).forEach((record) => {
          const store = state.allStores.find((item) => item.store_id === record.store_id);
          if (!store || store.status === "Closed" || (entries.has(store.store_id) && entries.get(store.store_id).priority <= priority)) return;
          entries.set(store.store_id, { store, category: key, label, priority, distance: Number(record.distance_km) });
        });
      });
    });
    return [...entries.values()].sort((left, right) => left.priority - right.priority || left.store.retailer.localeCompare(right.store.retailer) || left.store.name.localeCompare(right.store.name));
  }

  function repositionFocusedPlaceMarkers() {
    if (!state.focusedPlaceId) return;
    const place = state.centres.find((item) => item.place_id === state.focusedPlaceId);
    if (!place) return;
    focusedStoreMarkerById.forEach((marker) => resetMarkerPosition(marker));
    // Focusing a place must not replace its tenants’ coordinates with a decorative ring.
    const centreMarker = centreMarkerById.get(place.place_id);
    if (centreMarker) centreMarker.setLatLng([Number(place.latitude), Number(place.longitude)]);
  }

  function clearPlaceFocus(restoreNetworkMarkers = true) {
    state.focusedPlaceId = "";
    placeFocusLayer.clearLayers();
    placeFocusCatchmentLayer.clearLayers();
    focusedStoreMarkerById.clear();
    if (restoreNetworkMarkers) refreshStoreMarkerVisibility();
  }

  function focusPlaceOnMap(place) {
    if (!place || place.latitude == null || place.longitude == null || !Number.isFinite(Number(place.latitude)) || !Number.isFinite(Number(place.longitude))) return;
    clearPlaceFocus(false);
    state.focusedPlaceId = place.place_id;
    scheduleOverviewRefresh();
    storeClusters.clearLayers();
    const entries = relevantCompetitionEntries(place);
    const bounds = L.latLngBounds([[Number(place.latitude), Number(place.longitude)]]);
    entries.forEach(({ store, category, label, distance }) => {
      const marker = L.marker([store.latitude, store.longitude], {
        icon: storeIcon(store, "store-marker place-focus-store-marker"),
        retailer: store.retailer,
        storeId: store.store_id,
        title: store.name,
        baseLatitude: Number(store.latitude),
        baseLongitude: Number(store.longitude),
        focusCategory: category,
        zIndexOffset: category === "in_centre" ? 1400 : 1250,
      });
      marker.bindTooltip(
        `<strong>${escapeHtml(store.name)}</strong><br>${escapeHtml(label)}${Number.isFinite(distance) ? ` · ${escapeHtml(Intel.formatDistance(distance))}` : ""}`,
        { direction: "top", offset: [0, -8] }
      );
      marker.on("click", () => selectStore(store.store_id, false));
      marker.addTo(placeFocusLayer);
      focusedStoreMarkerById.set(store.store_id, marker);
      bounds.extend([Number(store.latitude), Number(store.longitude)]);
    });
    if (entries.some((entry) => entry.category !== "in_centre")) {
      L.circle([Number(place.latitude), Number(place.longitude)], {
        radius: 2000,
        color: "#927126",
        weight: 1,
        dashArray: "5 5",
        fillColor: "#d29b27",
        fillOpacity: 0.035,
        interactive: false,
      }).addTo(placeFocusCatchmentLayer);
    }
    const centreMarker = centreMarkerById.get(place.place_id);
    if (centreMarker && !centreLayer.hasLayer(centreMarker)) centreLayer.addLayer(centreMarker);
    if (entries.length) map.fitBounds(bounds, { padding: [70, 70], maxZoom: 15 });
    else map.setView([Number(place.latitude), Number(place.longitude)], 15);
    window.requestAnimationFrame(repositionFocusedPlaceMarkers);
  }

  function bindVerticalPaneResize(controlsId, resizerId, stateKey) {
    const controls = document.getElementById(controlsId);
    const resizer = document.getElementById(resizerId);
    if (!controls || !resizer) return;
    const resizeTo = (height) => {
      const available = elements.viewContent.getBoundingClientRect().height;
      const next = Math.round(Math.max(120, Math.min(height, Math.max(160, available - 170))));
      state.sidebarPaneHeights[stateKey] = next;
      controls.style.setProperty("--pane-height", `${next}px`);
      resizer.setAttribute("aria-valuenow", String(next));
    };
    resizer.addEventListener("pointerdown", (event) => {
      event.preventDefault();
      const startY = event.clientY;
      const startHeight = controls.getBoundingClientRect().height;
      resizer.classList.add("dragging");
      resizer.setPointerCapture(event.pointerId);
      const move = (moveEvent) => resizeTo(startHeight + moveEvent.clientY - startY);
      const finish = () => {
        resizer.classList.remove("dragging");
        resizer.removeEventListener("pointermove", move);
        resizer.removeEventListener("pointerup", finish);
        resizer.removeEventListener("pointercancel", finish);
      };
      resizer.addEventListener("pointermove", move);
      resizer.addEventListener("pointerup", finish);
      resizer.addEventListener("pointercancel", finish);
    });
    resizer.addEventListener("keydown", (event) => {
      if (!["ArrowUp", "ArrowDown"].includes(event.key)) return;
      event.preventDefault();
      resizeTo(state.sidebarPaneHeights[stateKey] + (event.key === "ArrowDown" ? 24 : -24));
    });
    resizeTo(state.sidebarPaneHeights[stateKey]);
  }

  function renderCentresView() {
    const centres = state.centres.filter((place) => place.location_setting === "Shopping Centre").length;
    const corridors = state.centres.filter((place) => place.location_setting === "High Street").length;
    const draft = draftFilters();
    const advancedFilterCount = Number(Boolean(draft.arrangement))
      + Number(Boolean(draft.overlap))
      + Number(Boolean(draft.centre_class))
      + Number(Boolean(Number(draft.min_income)))
      + Number(Boolean(Number(draft.min_bailey_distance)))
      + draft.retailers.size;
    elements.viewContent.innerHTML = `
      <details class="workspace-controls" id="placesControls" open style="--pane-height:${state.sidebarPaneHeights.centres}px">
        <summary><span><strong>Search and filters</strong><small>${advancedFilterCount ? `${advancedFilterCount} additional parameter${advancedFilterCount === 1 ? "" : "s"} active` : "Collapse after choosing your market"}</small></span><i data-lucide="chevron-down"></i></summary>
        <div class="workspace-controls-body"><section class="filters">
          <label class="search-field"><i data-lucide="search"></i><span class="sr-only">Search retail places</span>
            <input id="centreSearch" type="search" value="${escapeHtml(draft.search)}" placeholder="Centre, corridor, suburb, owner or manager" />
          </label>
          <div class="select-grid place-filter-grid primary-place-filters">
            <label><span>Country</span><select id="placeCountry">${filterOptions(["Australia", "New Zealand"], draft.country, "All countries")}</select></label>
            <label><span>Place type</span><select id="placeType">${filterOptions(["Shopping Centre", "High Street Corridor"], draft.type, "Centres + corridors")}</select></label>
            <label><span>Bailey Nelson</span><select id="placeBailey">${filterOptions(["Present", "Absent"], draft.bailey, "Present or absent")}</select></label>
            <label><span>Sort results</span><select id="placeSort">${filterOptions(["name", "optical_tenants", "household_income", "nearest_bailey", "portfolio_white_space"], draft.sort, "Sort by")}</select></label>
          </div>
          <details class="advanced-filters" ${advancedFilterCount ? "open" : ""}><summary><span><strong>More filters</strong><small>Leasing, centre class, thresholds and retailer presence</small></span><b>${advancedFilterCount || ""}</b><i data-lucide="sliders-horizontal"></i></summary>
            <div class="select-grid place-filter-grid">
              <label><span>Leasing arrangement</span><select id="placeArrangement">${filterOptions(["In-house", "External agency", "Private landlord", "Unknown"], draft.arrangement, "Any arrangement")}</select></label>
              <label><span>Portfolio overlap</span><select id="placeOverlap">${filterOptions(["SAME_CENTRE", "LEASING_CONTROLLER_OVERLAP", "PROPERTY_GROUP_OVERLAP", "EXTERNAL_AGENCY_OVERLAP", "NO_KNOWN_OVERLAP", "UNKNOWN"], draft.overlap, "Any overlap status")}</select></label>
              <label><span>Centre class</span><select id="placeCentreClass">${filterOptions(["Super Regional", "Regional", "Sub-regional", "Neighbourhood", "CBD / Mixed-use", "Outlet", "Large Format", "Other", "Unknown"], draft.centre_class, "Any centre class")}</select></label>
              <label><span>Minimum weekly income</span><input id="placeMinIncome" type="number" min="0" step="100" value="${escapeHtml(draft.min_income)}" placeholder="No minimum" /></label>
              <label><span>Minimum nearest BN (km)</span><input id="placeMinBailey" type="number" min="0" step="1" value="${escapeHtml(draft.min_bailey_distance)}" placeholder="No minimum" /></label>
            </div>
            <fieldset class="place-retailer-filter"><legend>Must include all selected retailers</legend><p class="form-note">Select OPSM and Specsavers to require both in the same place. Leave all unticked for any retailer mix.</p>${BRAND_ORDER.filter((brand) => BRAND_CONFIG[brand].networkType !== "background").map((brand) => `<label><input type="checkbox" value="${escapeHtml(brand)}" ${draft.retailers.has(brand) ? "checked" : ""} />${brandMarkHtml(brand, "compact")}<span>${escapeHtml(brand)}</span></label>`).join("")}</fieldset>
            <details class="correction-tools"><summary>Local public-data corrections</summary><div class="button-row place-actions">
              <button class="secondary-command" id="exportCorrections" type="button"><i data-lucide="download"></i>Export store mappings (${state.consultantCorrections.length})</button>
              <button class="secondary-command" id="importCorrections" type="button"><i data-lucide="upload"></i>Import store mappings</button>
              <input id="correctionFile" type="file" accept=".csv,text/csv" hidden />
              <button class="secondary-command" id="exportPropertyCorrections" type="button"><i data-lucide="building-2"></i>Export property corrections (${state.propertyCorrections.length + state.localPropertyGroups.length})</button>
              <button class="secondary-command" id="importPropertyCorrections" type="button"><i data-lucide="file-up"></i>Import property corrections</button>
              <input id="propertyCorrectionFile" type="file" accept=".csv,text/csv" hidden />
            </div></details>
          </details>
          <div class="compact-metrics">
            <div><strong>${centres}</strong><span>centres and plazas</span></div>
            <div><strong>${corridors}</strong><span>high-street corridors</span></div>
            <div><strong>${state.centres.filter((place) => place.has_bailey).length}</strong><span>with Bailey Nelson</span></div>
          </div>
        </section></div>
      </details>
      <div class="pane-resizer" id="placesPaneResizer" role="separator" aria-label="Resize search filters and place results" aria-orientation="horizontal" tabindex="0"><i></i></div>
      <section class="result-section">
        <div class="section-heading"><h2>Place profiles</h2><div class="section-heading-actions"><span id="centreResultCount"></span><button class="secondary-command compact-command" id="exportFilteredPlaces" type="button"><i data-lucide="download"></i>Export filtered</button></div></div>
        <div class="centre-list" id="centreList"></div>
      </section>`;
    setupExplorationSidebar();
    document.getElementById("exportCorrections").addEventListener("click", exportConsultantCorrections);
    document.getElementById("importCorrections").addEventListener("click", () => document.getElementById("correctionFile").click());
    document.getElementById("correctionFile").addEventListener("change", (event) => {
      if (event.target.files[0]) importConsultantCorrections(event.target.files[0]);
    });
    document.getElementById("exportPropertyCorrections").addEventListener("click", exportPropertyCorrections);
    document.getElementById("importPropertyCorrections").addEventListener("click", () => document.getElementById("propertyCorrectionFile").click());
    document.getElementById("propertyCorrectionFile").addEventListener("change", (event) => {
      if (event.target.files[0]) importPropertyCorrections(event.target.files[0]);
    });
  }

  function filteredPlaces() {
    const searchText = value => String(value).normalize('NFKD').replace(/[\u0300-\u036f]/g, '').toLowerCase().replace(/[^\p{L}\p{N}]+/gu, ' ').trim();
    const query = searchText(state.placeFilters.search);
    return state.centres.filter((place) => {
      const groupNames = (place.group_ids || []).map((groupId) => propertyGroup(groupId)?.canonical_name || "").join(" ");
      const haystack = searchText(`${place.name} ${(place.aliases || []).join(" ")} ${place.locality} ${place.suburb} ${place.state} ${place.owner} ${place.manager} ${groupNames}`);
      const income = Number(place.market?.median_household_income || place.market?.median_equivalised_household_income_weekly_2021 || 0);
      const nearestBailey = Number(place.nearest_bailey_km);
      return (
        (!query || haystack.includes(query)) &&
        (!state.placeFilters.country || place.country === state.placeFilters.country)
        && (!state.placeFilters.state || place.state === state.placeFilters.state) &&
        (!state.placeFilters.type || place.place_type === state.placeFilters.type) &&
        (!state.placeFilters.bailey || (state.placeFilters.bailey === "Present") === Boolean(place.has_bailey)) &&
        ([...state.placeFilters.retailers].every((retailer) => (place.retailers || []).includes(retailer))) &&
        (!state.placeFilters.arrangement || place.leasing_arrangement === state.placeFilters.arrangement) &&
        (!state.placeFilters.overlap || place.portfolio_overlap_status === state.placeFilters.overlap) &&
        (!state.placeFilters.centre_class || place.centre_class === state.placeFilters.centre_class) &&
        (!Number(state.placeFilters.min_income) || income >= Number(state.placeFilters.min_income)) &&
        (!Number(state.placeFilters.min_bailey_distance) || (Number.isFinite(nearestBailey) && nearestBailey >= Number(state.placeFilters.min_bailey_distance)))
      );
    });
  }

  function renderCentreResults() {
    if (state.view === "centres") renderQuickResults();
    refreshActiveMapContext();
  }

  function profileOptions() {
    return state.profiles
      .map(
        (profile) => `<option value="${escapeHtml(profile.id)}" ${
          profile.id === state.opportunityForm.profile_id ? "selected" : ""
        }>${escapeHtml(profile.name)}</option>`
      )
      .join("");
  }

  function lookalikeKeys() {
    const country = state.opportunityFilters.country === "Australia" ? "au" : "nz";
    const settings = state.opportunityFilters.setting === "Shopping Centre"
      ? ["shopping-centre"]
      : state.opportunityFilters.setting === "High Street"
        ? ["high-street"]
        : ["shopping-centre", "high-street"];
    return settings.map((setting) => `${country}-${setting}`);
  }

  function selectedPerformanceBenchmarks(setting = "") {
    if (!state.performanceBenchmark) return [];
    const selected = new Set(state.performanceBenchmark.store_ids);
    return (state.lookalikes.bailey_benchmarks || []).filter(
      (row) => selected.has(row.store_id)
        && row.country === state.opportunityFilters.country
        && (!setting || row.location_setting === setting)
    );
  }

  function medianValue(values) {
    const ordered = values.filter(Number.isFinite).sort((a, b) => a - b);
    if (!ordered.length) return null;
    const middle = Math.floor(ordered.length / 2);
    return ordered.length % 2 ? ordered[middle] : (ordered[middle - 1] + ordered[middle]) / 2;
  }

  function performanceAdjustedLookalikes() {
    const rows = lookalikeKeys().flatMap((key) => state.lookalikes.rankings?.[key] || [])
      .map((row) => state.performanceBenchmark
        ? Intel.selectedBenchmarkLookalike(row, selectedPerformanceBenchmarks(row.location_setting))
        : { ...row, components: { ...row.components } });
    const filtered = rows.filter((row) => Intel.placeMatchesRetailerFilters(
      row,
      state.opportunityFilters.must_have_retailers,
      state.opportunityFilters.must_not_have_retailers,
      state.opportunityFilters.require_any_retailer
    ));
    filtered.sort((a, b) => (a.screening_completeness < 60) - (b.screening_completeness < 60) || (b.score || 0) - (a.score || 0) || a.name.localeCompare(b.name));
    filtered.forEach((row, index) => { row.rank = index + 1; });
    return filtered;
  }

  function visibleOpportunityRows() {
    if (state.showShortlistOnly) return shortlistedOpportunityRows();
    return performanceAdjustedLookalikes();
  }

  function shortlistedOpportunityRows() {
    return shortlistedPlaces()
      .map(({ placeId, place }) => {
        const row = publishedLookalike(placeId);
        return place ? { ...(row || { place_id: placeId, name: place.name, country: place.country, location_setting: place.location_setting, nearest_bailey_km: place.nearest_bailey_km, score: null, screening_completeness: null }), place } : null;
      })
      .filter(Boolean)
      .sort((a, b) => (b.score || 0) - (a.score || 0) || (b.screening_completeness || 0) - (a.screening_completeness || 0) || a.name.localeCompare(b.name));
  }

  function lookalikeRowHtml(row) {
    const components = row.components || {};
    const saved = state.placeShortlist.has(resolvePlaceId(row.place_id));
    return `<div class="lookalike-row">
      <button class="lookalike-open" type="button" data-open-place-id="${escapeHtml(row.place_id)}" aria-label="Open ${escapeHtml(row.name)}">
      <span class="rank-number">${row.rank}</span>
      <span class="lookalike-identity"><strong>${escapeHtml(row.name)}</strong><small>${escapeHtml(`${row.location_setting} · ${row.locality || "Locality not recorded"}${row.state ? `, ${row.state}` : ""}`)}</small><small>${row.screening_completeness ?? '—'}% of screening inputs available</small></span>
      <span class="lookalike-score"><strong>${row.score ?? "—"}</strong><small>lookalike</small></span>
      <span class="component-mini"><span>Footprint <b>${components.bailey_footprint_similarity ?? "—"}</b></span><span>Whitespace <b>${components.bailey_whitespace ?? "—"}</b></span><span>Optical <b>${components.optical_market_validation ?? "—"}</b></span><span>Context <b>${components.accessibility_retail_context ?? "—"}</b></span></span>
      ${row.footprint_comparison ? `<span class="footprint-fields">Selected comparison: ${row.footprint_comparison.available_fields}/${row.footprint_comparison.total_fields} demographic fields</span>` : ''}
      </button>
      <button class="place-shortlist-toggle ${saved ? "saved" : ""}" type="button" data-shortlist-place-id="${escapeHtml(row.place_id)}" aria-label="${saved ? "Remove from" : "Add to"} shortlist" title="${saved ? "Remove from" : "Add to"} shortlist"><i data-lucide="bookmark${saved ? "-check" : ""}"></i></button>
    </div>`;
  }

  function averageValue(values) {
    const available = values.map(Number).filter(Number.isFinite);
    return available.length ? available.reduce((sum, value) => sum + value, 0) / available.length : null;
  }

  function opportunityDashboardHtml(rows) {
    const sufficientlyComplete = rows.filter((row) => Number(row.screening_completeness) >= 80).length;
    const portfolioWhiteSpace = rows.filter((row) => state.centres.find((place) => place.place_id === row.place_id)?.portfolio_white_space).length;
    const medianScore = medianValue(rows.map((row) => Number(row.score)));
    const top = rows[0];
    const centreCount = rows.filter((row) => row.location_setting === "Shopping Centre").length;
    const corridorCount = rows.filter((row) => row.location_setting === "High Street").length;
    return `<section class="opportunity-pulse" aria-label="Opportunity dashboard">
      <div class="opportunity-pulse-heading"><span><i data-lucide="sparkles"></i><strong>Opportunity pulse</strong></span><small>Live summary of the places matching the current screen.</small></div>
      <div class="opportunity-kpis">
        <div><strong>${formatNumber(rows.length)}</strong><span>places</span></div>
        <div><strong>${medianScore === null ? "—" : Math.round(medianScore)}</strong><span>median lookalike</span></div>
        <div><strong>${formatNumber(sufficientlyComplete)}</strong><span>80%+ complete</span></div>
        <div><strong>${formatNumber(portfolioWhiteSpace)}</strong><span>portfolio overlaps</span></div>
      </div>
      <div class="opportunity-pulse-footer"><span>${formatNumber(centreCount)} centres · ${formatNumber(corridorCount)} corridors</span>${top ? `<button type="button" data-open-place-id="${escapeHtml(top.place_id)}">Top screen: ${escapeHtml(top.name)} <b>${top.score ?? "—"}</b></button>` : ""}</div>
    </section>`;
  }

  function shortlistProfileHtml(row) {
    const place = row.place || state.centres.find((item) => item.place_id === row.place_id);
    if (!place) return "";
    const market = row.market_features || {};
    const exactTenants = tenantsForPlace(place.place_id);
    const coTenants = exactTenants.filter((tenant) => tenant.category !== "Optical");
    const retailers = (place.retailers || []).filter((retailer) => retailer !== "Bailey Nelson");
    const groups = propertyGroupNames(place);
    const gaps = Object.entries(LOOKALIKE_COMPONENTS).filter(([key]) => !hasLookalikeComponent(row.components?.[key])).map(([, [label]]) => label);
    const settingScope = `${row.country} · ${row.location_setting}`;
    const componentBars = Object.entries(LOOKALIKE_COMPONENTS).map(([key, [label]]) => {
      const value = row.components?.[key];
      const available = hasLookalikeComponent(value);
      return `<div class="shortlist-component"><span><b>${escapeHtml(label)}</b><em>${available ? Math.round(Number(value)) : "N/A"}</em></span><i><u style="--value:${available ? Math.max(0, Math.min(100, Number(value))) : 0}%"></u></i></div>`;
    }).join("");
    return `<article class="shortlist-profile-card" data-profile-place-id="${escapeHtml(place.place_id)}">
      <header><div class="shortlist-rank"><span>#${row.rank ?? "—"}</span><small>${escapeHtml(settingScope)}</small></div><button class="place-shortlist-toggle saved" type="button" data-shortlist-place-id="${escapeHtml(place.place_id)}" aria-label="Remove ${escapeHtml(place.name)} from shortlist" title="Remove from shortlist"><i data-lucide="bookmark-x"></i></button></header>
      <button class="shortlist-profile-title" type="button" data-open-place-id="${escapeHtml(place.place_id)}"><span><strong>${escapeHtml(place.name)}</strong><small>${escapeHtml(`${place.locality || place.suburb || "Locality not recorded"}${place.state ? `, ${place.state}` : ""}`)}</small></span><span class="shortlist-score"><b>${row.score ?? "—"}</b><small>lookalike</small></span></button>
      <div class="shortlist-readiness"><span><b>${row.screening_completeness == null ? "Not scored" : `${row.screening_completeness}%`}</b> screening completeness</span><i><u style="--value:${Math.max(0, Math.min(100, Number(row.screening_completeness) || 0))}%"></u></i></div>
      <div class="shortlist-component-grid">${componentBars}</div>
      <div class="shortlist-facts">
        <div><span>Population</span><strong>${formatNumber(market.population_2025)}</strong></div>
        <div><span>Growth 2021–25</span><strong>${formatNumber(market.population_growth_2021_2025_pct, "%")}</strong></div>
        <div><span>Weekly income</span><strong>${market.median_equivalised_household_income_weekly_2021 ? `$${formatNumber(market.median_equivalised_household_income_weekly_2021)}` : "N/A"}</strong></div>
        <div><span>Nearest Bailey</span><strong>${Number.isFinite(Number(row.nearest_bailey_km)) ? Intel.formatDistance(Number(row.nearest_bailey_km)) : "Unknown"}</strong></div>
      </div>
      <div class="shortlist-context-row"><span><i data-lucide="glasses"></i><b>${formatNumber(place.optical_store_count || 0)}</b> exact-place optical</span><span><i data-lucide="store"></i><b>${formatNumber(coTenants.length)}</b> key co-tenants</span></div>
      ${retailers.length ? `<div class="shortlist-chip-row" aria-label="Mapped optical retailers">${retailers.map((retailer) => `<span>${escapeHtml(retailer)}</span>`).join("")}</div>` : '<p class="shortlist-empty-signal">No competitor brand is accepted as an exact-place tenant.</p>'}
      <dl class="shortlist-property"><div><dt>${place.location_setting === "High Street" ? "Setting" : "Centre class"}</dt><dd>${escapeHtml(place.location_setting === "High Street" ? "High-street corridor" : place.centre_class || "Unknown")}</dd></div><div><dt>Leasing</dt><dd>${escapeHtml(place.location_setting === "High Street" ? "Not assessed at corridor level" : place.leasing_arrangement || "Unknown")}</dd></div><div><dt>Property groups</dt><dd>${escapeHtml(groups.length ? groups.join(", ") : place.location_setting === "High Street" ? "Not assessed at corridor level" : "Unknown")}</dd></div></dl>
      <footer><button class="secondary-command" type="button" data-compare-place-id="${escapeHtml(place.place_id)}">Compare place</button><span class="shortlist-evidence ${gaps.length ? "partial" : "complete"}">${gaps.length ? `${gaps.length} weighted evidence gap${gaps.length === 1 ? "" : "s"}` : "Weighted evidence complete"}</span><button class="secondary-command" type="button" data-open-place-id="${escapeHtml(place.place_id)}">Open full profile <i data-lucide="arrow-right"></i></button></footer>
    </article>`;
  }

  function shortlistDashboardHtml(rows) {
    const entries = shortlistedPlaces();
    const unavailable = entries.length - rows.length;
    if (!entries.length) return `<section class="shortlist-dashboard-empty"><i data-lucide="bookmark-plus"></i><strong>Build your opportunity shortlist</strong><p>Return to Explore and use the bookmark beside any place. Every saved place will be profiled here and retained in this browser.</p><button class="primary-command" type="button" id="emptyShortlistExplore">Explore opportunities</button></section>`;
    const averageScore = averageValue(rows.map((row) => row.score));
    const averageCompleteness = averageValue(rows.map((row) => row.screening_completeness));
    const centres = rows.filter((row) => row.location_setting === "Shopping Centre").length;
    const overlaps = rows.filter((row) => row.place?.portfolio_white_space).length;
    const retailerCounts = new Map();
    rows.forEach((row) => (row.place?.retailers || []).filter((retailer) => retailer !== "Bailey Nelson").forEach((retailer) => retailerCounts.set(retailer, (retailerCounts.get(retailer) || 0) + 1)));
    const sharedRetailers = [...retailerCounts.entries()].filter(([, count]) => count > 1).sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0])).slice(0, 4);
    return `<section class="shortlist-dashboard-hero">
      <div><span class="shortlist-kicker"><i data-lucide="layout-dashboard"></i>Decision workspace</span><h3>${formatNumber(rows.length)} opportunity profile${rows.length === 1 ? "" : "s"}</h3><p>Compare the strength, readiness, competition and leasing context of every saved place. Rankings remain separated by country and setting.</p></div>
      <div class="shortlist-dashboard-kpis"><div><strong>${averageScore === null ? "—" : Math.round(averageScore)}</strong><span>average lookalike</span></div><div><strong>${averageCompleteness === null ? "—" : `${Math.round(averageCompleteness)}%`}</strong><span>average completeness</span></div><div><strong>${centres}</strong><span>shopping centres</span></div><div><strong>${overlaps}</strong><span>portfolio overlaps</span></div></div>
      <div class="shortlist-shared-signals"><strong>Shared signals</strong><span>${sharedRetailers.length ? sharedRetailers.map(([retailer, count]) => `${escapeHtml(retailer)} at ${count}/${rows.length}`).join(" · ") : "No competitor brand appears across more than one saved place yet."}</span>${unavailable ? `<small>${unavailable} saved record${unavailable === 1 ? " is" : "s are"} unavailable or awaiting an ID remap.</small>` : ""}</div>
    </section><section class="shortlist-profile-stack"><div class="shortlist-profile-heading"><span><strong>Place profiles</strong><small>Ordered by lookalike score; click any card for complete evidence.</small></span><b>${rows.length}</b></div>${rows.map(shortlistProfileHtml).join("")}</section>`;
  }

  function opportunityShortlistHtml() {
    if (!state.showShortlistOnly) return '';
    return `<section class="place-shortlist-panel"><div class="shortlist-utility"><span>${state.placeShortlist.size} saved in this browser</span><button class="secondary-command" id="clearPlaceShortlist" type="button" ${state.placeShortlist.size ? '' : 'disabled'}>Clear shortlist</button></div><div class="shortlist-notice" id="shortlistNotice" role="status" aria-live="polite"></div></section>`;
  }

  function showShortlistNotice(message) {
    const notice = document.getElementById("shortlistNotice");
    if (!notice) return;
    window.clearTimeout(shortlistNoticeTimer);
    notice.textContent = message;
    notice.classList.remove("visible");
    window.requestAnimationFrame(() => notice.classList.add("visible"));
    shortlistNoticeTimer = window.setTimeout(() => notice.classList.remove("visible"), 1900);
  }

  async function importPerformanceBenchmark(file) {
    const rows = parseCsv(await file.text());
    if (!rows.length || !("store_id" in rows[0] || "store_name" in rows[0]) || !("rank" in rows[0] || "performance_score" in rows[0])) {
      showToast("Performance CSV needs store_id or store_name, plus rank or performance_score", "warning");
      return;
    }
    const bailey = state.allStores.filter((store) => store.retailer === "Bailey Nelson");
    const normalize = (value) => String(value || "").toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
    const matched = [];
    const unmatched = [];
    rows.forEach((row, index) => {
      const store = bailey.find((item) => row.store_id && item.store_id === row.store_id) || bailey.find((item) => row.store_name && normalize(item.name) === normalize(row.store_name));
      if (!store) unmatched.push(row.store_id || row.store_name || `row ${index + 2}`);
      else matched.push({ store_id: store.store_id, rank: row.rank === "" ? NaN : Number(row.rank), score: row.performance_score === "" ? NaN : Number(row.performance_score), index });
    });
    const uniqueMatched = [...new Map(matched.map((row) => [row.store_id, row])).values()];
    if (uniqueMatched.length < 5) {
      state.performanceBenchmark = null;
      showToast(`Only ${uniqueMatched.length} Bailey stores matched; using all Bailey stores`, "warning");
      renderView();
      return;
    }
    const usesRank = uniqueMatched.some((row) => Number.isFinite(row.rank));
    uniqueMatched.sort((a, b) => usesRank ? (Number.isFinite(a.rank) ? a.rank : 999999) - (Number.isFinite(b.rank) ? b.rank : 999999) : (Number.isFinite(b.score) ? b.score : -Infinity) - (Number.isFinite(a.score) ? a.score : -Infinity));
    state.performanceBenchmark = { store_ids: uniqueMatched.map((row) => row.store_id).slice(0, 10), matched: uniqueMatched.length, unmatched };
    renderView();
    showToast(`Using the best ${state.performanceBenchmark.store_ids.length} matched Bailey stores in memory`);
  }

  function renderOpportunityView() {
    const rows = visibleOpportunityRows();
    elements.visibleTotal.textContent = rows.length.toLocaleString("en-AU");
    elements.visibleTotalLabel.textContent = state.showShortlistOnly ? "saved places profiled" : "mapped Bailey-free places visible";
    const retailerChoices = BRAND_ORDER.filter((retailer) => retailer !== "Bailey Nelson");
    const retailerFilterCount = Number(state.opportunityFilters.require_any_retailer)
      + state.opportunityFilters.must_have_retailers.size
      + state.opportunityFilters.must_not_have_retailers.size;
    const retailerFilterLabel = retailerFilterCount
      ? `${state.opportunityFilters.require_any_retailer ? "At least one optical retailer · " : ""}${state.opportunityFilters.must_have_retailers.size} required · ${state.opportunityFilters.must_not_have_retailers.size} excluded`
      : "No retailer requirement";
    const retailerCheckboxes = (mode, selected) => retailerChoices.map((retailer) => `
      <label><input type="checkbox" data-opportunity-retailer="${escapeHtml(mode)}" value="${escapeHtml(retailer)}" ${selected.has(retailer) ? "checked" : ""} />
        <span>${escapeHtml(retailer)}</span>
      </label>`).join("");
    const settingLabel = state.opportunityFilters.setting || "All types";
    elements.viewContent.innerHTML = `
      <details class="workspace-controls" id="opportunityControls" ${state.showShortlistOnly ? "" : "open"}>
        <summary><span><strong>Opportunity filters</strong><small>${state.showShortlistOnly ? `Shortlist dashboard · all ${rows.length} saved profile${rows.length === 1 ? "" : "s"} shown` : retailerFilterCount ? `${retailerFilterCount} retailer condition${retailerFilterCount === 1 ? "" : "s"} active` : `${state.opportunityFilters.country} · ${settingLabel}`}</small></span><i data-lucide="chevron-down"></i></summary>
        <div class="workspace-controls-body">
          <section class="experimental-banner"><i data-lucide="scan-search"></i><div><strong>Lookalike screening rank</strong><span>Ranks mapped Bailey-free centres and corridors using available public evidence. It is a prioritisation screen, not a forecast.</span></div></section>
          ${state.performanceBenchmark ? '<p class="form-note">Explore uses your selected stores where at least two same-country, same-setting stores provide each demographic field. Missing fields remain unavailable; small samples are descriptive only. Saved profiles and exports retain the standard public screen.</p>' : ""}
          <section class="opportunity-form ranking-controls">
            <div class="select-grid">
              <label><span>Country</span><select id="lookalikeCountry">${filterOptions(["Australia", "New Zealand"], state.opportunityFilters.country, "Country")}</select></label>
              <label><span>Place type</span><select id="lookalikeSetting">
                <option value="" ${state.opportunityFilters.setting ? "" : "selected"}>All types</option>
                <option value="Shopping Centre" ${state.opportunityFilters.setting === "Shopping Centre" ? "selected" : ""}>Shopping centres</option>
                <option value="High Street" ${state.opportunityFilters.setting === "High Street" ? "selected" : ""}>High streets</option>
              </select></label>
            </div>
            <details class="opportunity-retailer-filters" ${retailerFilterCount ? "open" : ""}>
              <summary><span><strong>Retailer presence</strong><small>${escapeHtml(retailerFilterLabel)}</small></span><i data-lucide="chevron-down"></i></summary>
              <label class="opportunity-any-retailer"><input id="opportunityAnyRetailer" type="checkbox" ${state.opportunityFilters.require_any_retailer ? "checked" : ""} />
                <span><strong>At least one mapped optical retailer</strong><small>Any brand; useful for places with existing optical validation.</small></span>
              </label>
              <div class="opportunity-retailer-columns">
                <fieldset><legend>Must have every selected retailer</legend>${retailerCheckboxes("must-have", state.opportunityFilters.must_have_retailers)}</fieldset>
                <fieldset><legend>Must not have any selected retailer</legend>${retailerCheckboxes("must-not-have", state.opportunityFilters.must_not_have_retailers)}</fieldset>
              </div>
              ${retailerFilterCount ? '<button class="secondary-command" id="clearOpportunityRetailers" type="button">Clear retailer filters</button>' : ""}
              <p class="form-note">Presence means an accepted mapping to this exact centre or corridor, not merely a nearby store.</p>
            </details>
          </section>
        </div>
      </details>
      <section class="result-section lookalike-section">
        ${opportunityShortlistHtml()}
        <div class="section-heading"><h2>${escapeHtml(state.showShortlistOnly ? "Shortlist dashboard" : `${state.opportunityFilters.country} · ${settingLabel}`)}</h2><div class="section-heading-actions"><span>${rows.length} ${state.showShortlistOnly ? "saved profiles" : "mapped Bailey-free places"}</span></div></div>
        <div class="lookalike-list ${state.showShortlistOnly ? "shortlist-dashboard-scroll" : ""}" id="lookalikeList">${state.showShortlistOnly ? shortlistDashboardHtml(rows) : rows.length ? `${opportunityDashboardHtml(rows)}${rows.slice(0, 150).map(lookalikeRowHtml).join("")}` : '<div class="empty-state"><strong>No places match these filters</strong><span>Change the place type or retailer presence requirements.</span></div>'}</div>
      </section>
      `;
    bindOpportunityForm();
    if (state.showShortlistOnly) document.getElementById("opportunityControls").remove();
  }

  function candidateListRow(candidate) {
    const model = scoreCandidate(candidate);
    return `<button class="candidate-row" data-candidate-id="${escapeHtml(candidate.id)}">
      <span class="score-badge ${model.reliable ? "" : "low-coverage"}">${model.score ?? "-"}</span>
      <span><strong>${escapeHtml(candidate.name)}</strong><small>${marketLabel(candidate)}</small></span>
      <span><strong>${model.coverage}%</strong><small>coverage</small></span>
    </button>`;
  }

  function bindOpportunityForm() {
    document.getElementById("lookalikeCountry").addEventListener("change", (event) => {
      state.opportunityFilters.country = event.target.value;
      renderView();
      refreshActiveMapContext(true);
    });
    document.getElementById("lookalikeSetting").addEventListener("change", (event) => {
      state.opportunityFilters.setting = event.target.value;
      renderView();
      refreshActiveMapContext(true);
    });
    document.querySelectorAll("[data-opportunity-retailer]").forEach((input) => {
      input.addEventListener("change", () => {
        const isRequired = input.dataset.opportunityRetailer === "must-have";
        const target = isRequired ? state.opportunityFilters.must_have_retailers : state.opportunityFilters.must_not_have_retailers;
        const opposite = isRequired ? state.opportunityFilters.must_not_have_retailers : state.opportunityFilters.must_have_retailers;
        if (input.checked) {
          target.add(input.value);
          opposite.delete(input.value);
        } else {
          target.delete(input.value);
        }
        renderView();
        refreshActiveMapContext(true);
      });
    });
    document.getElementById("opportunityAnyRetailer").addEventListener("change", (event) => {
      state.opportunityFilters.require_any_retailer = event.target.checked;
      renderView();
      refreshActiveMapContext(true);
    });
    document.getElementById("clearOpportunityRetailers")?.addEventListener("click", () => {
      state.opportunityFilters.require_any_retailer = false;
      state.opportunityFilters.must_have_retailers.clear();
      state.opportunityFilters.must_not_have_retailers.clear();
      renderView();
      refreshActiveMapContext(true);
    });
    document.getElementById("lookalikeList").addEventListener("click", (event) => {
      const compareButton = event.target.closest('[data-compare-place-id]');
      if (compareButton) return addPlaceToComparison(state.centres.find(place => place.place_id === compareButton.dataset.comparePlaceId));
      const shortlistButton = event.target.closest("[data-shortlist-place-id]");
      if (shortlistButton) {
        event.preventDefault();
        event.stopPropagation();
        shortlistButton.disabled = true;
        return togglePlaceShortlist(shortlistButton.dataset.shortlistPlaceId);
      }
      const row = event.target.closest("[data-open-place-id]");
      if (!row) return;
      const place = state.centres.find((item) => item.place_id === row.dataset.openPlaceId);
      openCentreDetail(place);
    });
    document.getElementById("emptyShortlistExplore")?.addEventListener("click", () => {
      state.showShortlistOnly = false;
      renderView();
      refreshActiveMapContext(true);
    });
    document.getElementById("clearPlaceShortlist")?.addEventListener("click", () => {
      state.placeShortlist.clear();
      persistPlaceShortlist();
      renderView();
      showShortlistNotice("Shortlist cleared");
    });
  }

  function renderTrendsView() {
    const events = state.events.events || [];
    const sources = state.metadata.source_freshness || {};
    elements.viewContent.innerHTML = `
      <section class="trend-summary">
        <div class="compact-metrics">
          <div><strong>${events.filter((event) => event.type === "Opened").length}</strong><span>openings</span></div>
          <div><strong>${events.filter((event) => event.type === "Closed").length}</strong><span>closures</span></div>
          <div><strong>${events.filter((event) => event.type === "Relocated").length}</strong><span>moves</span></div>
        </div>
        <div class="baseline-note"><i data-lucide="history"></i><div><strong>${escapeHtml(
          state.events.note || "Network history unavailable."
        )}</strong><span>Baseline ${escapeHtml(state.events.baseline_date || "not recorded")}</span></div></div>
      </section>
      <section class="source-list">
        <h2>Source freshness</h2>${Object.entries(sources)
          .map(
            ([retailer, date]) => `<div><span>${escapeHtml(retailer)}</span><strong>${escapeHtml(formatDate(date))}</strong></div>`
          )
          .join("")}
        <div><span>ABS market indicators</span><strong>${escapeHtml(formatDate(state.marketMetadata.source_release_date))}</strong></div>
      </section>
      <section class="result-section">
        <div class="section-heading"><h2>Network events</h2><span>${events.length} events</span></div>
        <div class="event-list">${
          events.length
            ? events
                .map(
                  (event) => `<button class="event-row" data-store-id="${escapeHtml(event.store_id)}">
                    <span class="event-type ${event.type.toLowerCase()}">${escapeHtml(event.type)}</span>
                    <span><strong>${escapeHtml(event.name)}</strong><small>${escapeHtml(
                    `${event.suburb}, ${event.state}`
                  )}</small></span><time>${escapeHtml(formatDate(event.date))}</time>
                  </button>`
                )
                .join("")
            : '<div class="empty-state"><i data-lucide="history"></i><strong>Baseline captured</strong><span>Changes will appear after the next successful retailer refresh.</span></div>'
        }</div>
      </section>`;
    elements.viewContent.querySelector(".event-list")?.addEventListener("click", (event) => {
      const row = event.target.closest("[data-store-id]");
      if (row && markerById.has(row.dataset.storeId)) selectStore(row.dataset.storeId, true);
    });
  }

  function savedComparisons() {
    try {
      const entries = JSON.parse(localStorage.getItem(COMPARISON_STORAGE_KEY) || '[]');
      return Array.isArray(entries) ? entries.filter(entry => entry && typeof entry.id === 'string' && typeof entry.name === 'string' && Array.isArray(entry.candidates)) : [];
    } catch { return []; }
  }

  function currentComparisonSnapshot() {
    return { candidates: Intel.comparisonSnapshot(state.candidates), store_ids: state.compareStores.map(store => store.store_id), connections: state.comparisonConnectionsVisible };
  }

  function matchingSavedComparison() {
    const current = currentComparisonSnapshot();
    return savedComparisons().find(entry =>
      JSON.stringify(Intel.comparisonSnapshot(entry.candidates)) === JSON.stringify(current.candidates) &&
      JSON.stringify(entry.store_ids || []) === JSON.stringify(current.store_ids));
  }

  function comparisonLibraryHtml() {
    const saved = savedComparisons();
    const active = matchingSavedComparison();
    return `<details class="comparison-library" ${state.comparisonLibraryOpen ? 'open' : ''}><summary>Save / open comparisons <span>${saved.length} saved</span></summary>
      ${saved.length ? `<label for="savedComparison">Saved groups</label><div class="comparison-save-row"><select id="savedComparison" aria-describedby="savedComparisonHint"><option value="" ${active ? '' : 'selected'} disabled>Choose a group to show on the map</option>${saved.map(entry => `<option value="${escapeHtml(entry.id)}" ${entry.id === active?.id ? 'selected' : ''}>${escapeHtml(entry.name)} · ${entry.candidates.length} places · ${escapeHtml(new Date(entry.saved_at).toLocaleDateString('en-AU'))}</option>`).join('')}</select><button class="secondary-command" id="viewComparison" type="button" ${state.candidates.length || state.compareStores.length ? '' : 'disabled'}>View comparison</button></div><p id="savedComparisonHint">Selecting a group loads its places and fits the map. View comparison opens the detailed tables.</p>` : '<p>No saved comparisons yet.</p>'}
      ${state.comparisonUndo ? '<button class="secondary-command" id="undoOpenComparison" type="button">Restore previous selection</button>' : ''}
      ${active?.purpose ? `<p class="comparison-purpose"><strong>Local comparison:</strong> ${escapeHtml(active.purpose)}</p>` : ''}
      <details class="comparison-save-new"><summary>Save current selection</summary>
      <form id="saveComparisonForm"><label for="comparisonName">Comparison name</label><div class="comparison-save-row"><input id="comparisonName" maxlength="100" required placeholder="e.g. Southwest Sydney" /><button class="secondary-command" type="submit" ${state.candidates.length || state.compareStores.length ? '' : 'disabled'}>Save comparison</button></div><label for="comparisonPurpose">Why compare these places? (optional)</label><textarea id="comparisonPurpose" maxlength="700" rows="3" placeholder="Describe the local choice using public information only."></textarea></form>
      <p>Saved in this browser. Each save creates a separate snapshot; editing or clearing the current selection leaves saved groups intact. Use public place labels only.</p>
      </details>
    </details>`;
  }

  function restoreComparison(snapshot) {
    closeDetail();
    setCandidateDropMode(false);
    candidateLayer.clearLayers();
    candidateMarkerById.clear();
    state.candidates = Intel.comparisonSnapshot(snapshot.candidates).map(candidate => {
      const place = state.centres.find(place => place.place_id === resolvePlaceId(candidate.place_id));
      return {...candidate, place_id: place?.place_id || '', amenity_summary: null};
    });
    state.compareStores = (snapshot.store_ids || []).map(id => state.allStores.find(store => store.store_id === id)).filter(Boolean);
    state.comparisonConnectionsVisible = snapshot.connections !== false;
    state.candidates.forEach(createCandidateMarker);
    setView('compare');
    fitComparison();
  }

  function openComparisonDetails() {
    let dialog = document.getElementById('comparisonDetails');
    if (!dialog) {
      dialog = document.createElement('dialog');
      dialog.id = 'comparisonDetails';
      dialog.className = 'comparison-dialog';
      dialog.setAttribute('aria-labelledby', 'comparisonDetailsTitle');
      document.body.append(dialog);
    }
    const active = matchingSavedComparison();
    dialog.innerHTML = `<header><div><p>Place comparison</p><h2 id="comparisonDetailsTitle">${escapeHtml(active?.name || 'Current selection')}</h2></div><form method="dialog"><button class="secondary-command" autofocus>Back to map</button></form></header>
      <div class="comparison-dialog-body">${active?.purpose ? `<p><strong>Why these places:</strong> ${escapeHtml(active.purpose)}</p>` : ''}<p>Compare local alternatives using public evidence. Area demographics describe whole statistical areas, not measured customer catchments. Distances are straight line; nearby places can still serve different customers.</p>
      ${state.compareStores.length ? storeComparisonHtml(true) : ''}
      ${state.candidates.length ? `<div class="comparison-dialog-table" tabindex="0" role="region" aria-label="Place comparison table">${candidateComparisonTable(state.candidates, true)}</div>` : ''}</div>`;
    dialog.showModal();
  }

  function fitComparison() {
    const points = Intel.comparisonSnapshot([...state.candidates, ...state.compareStores]);
    if (points.length) map.fitBounds(L.latLngBounds(points.map(point => [point.latitude, point.longitude])), {padding: [45, 65], maxZoom: 14});
  }

  function comparisonAreaHtml() {
    if (!state.candidates.length) return '';
    const pairs = Intel.comparisonConnections(state.candidates);
    const areas = new Map();
    let unmatched = 0;
    state.candidates.forEach(candidate => {
      const feature = marketForPoint(candidate);
      if (!feature) { unmatched++; return; }
      const properties = feature.properties;
      areas.set(`${properties.state}|${properties.sa2_name}`, properties);
    });
    const populations = [...areas.values()].map(area => area.population_2025).filter(value => value != null && value !== '' && Number.isFinite(Number(value)));
    const distances = pairs.map(pair => pair.distance);
    return `<section class="comparison-area"><div class="section-heading"><h2>Selection overview</h2><button class="secondary-command" id="fitComparison" type="button">Fit selection</button></div>
      <div class="comparison-area-metrics"><div><strong>${state.candidates.length}</strong><span>places</span></div><div><strong>${areas.size}</strong><span>distinct statistical areas</span></div><div><strong>${distances.length ? Intel.formatDistance(Math.max(...distances)) : '—'}</strong><span>widest separation</span></div></div>
      <p>${[...areas.values()].map(area => escapeHtml(area.sa2_name)).join(' · ') || 'Statistical areas not matched'}${unmatched ? ` · ${unmatched} place(s) unmatched` : ''}</p>
      <p>${populations.length === areas.size && areas.size ? `${formatNumber(populations.reduce((total, value) => total + Number(value), 0))} residents across the ${areas.size} distinct whole statistical areas (2025). Each area counted once.` : 'A complete population total is unavailable for the matched areas.'} These areas extend beyond the selected points; this is not a catchment estimate or an enclosed-area population.</p>
      ${pairs.length ? `<label class="comparison-lines-toggle"><input id="comparisonLinesToggle" type="checkbox" ${state.comparisonConnectionsVisible ? 'checked' : ''} />Show distance connections</label><details class="comparison-distances"><summary>${pairs.length} straight-line distances · hover or tap a map line</summary><ul>${pairs.map(pair => `<li><span>${escapeHtml(pair.from.name)} ↔ ${escapeHtml(pair.to.name)}</span><strong>${Intel.formatDistance(pair.distance)}</strong></li>`).join('')}</ul></details>` : ''}
    </section>`;
  }

  function renderComparisonConnections() {
    comparisonLineLayer.clearLayers();
    if (state.view !== 'compare' || !state.comparisonConnectionsVisible) return;
    Intel.comparisonConnections(state.candidates).forEach(pair => {
      const text = `${escapeHtml(pair.from.name)} ↔ ${escapeHtml(pair.to.name)}<br><strong>${Intel.formatDistance(pair.distance)} straight line</strong>`;
      const line = L.polyline([[pair.from.latitude, pair.from.longitude], [pair.to.latitude, pair.to.longitude]], {renderer: comparisonLineRenderer, color: '#725180', weight: 3, opacity: 0.8, dashArray: '5 7', className: 'comparison-distance-line'}).addTo(comparisonLineLayer);
      const midpoint = L.latLng((pair.from.latitude + pair.to.latitude) / 2, (pair.from.longitude + pair.to.longitude) / 2);
      line.bindTooltip(text, {direction: 'top'}).bindPopup(text);
      const path = line.getElement();
      if (path) {
        path.setAttribute('tabindex', '0');
        path.setAttribute('role', 'button');
        path.setAttribute('aria-label', `${pair.from.name} to ${pair.to.name}: ${Intel.formatDistance(pair.distance)} straight line`);
        path.addEventListener('focus', () => line.openTooltip(midpoint));
        path.addEventListener('blur', () => line.closeTooltip());
        path.addEventListener('keydown', event => {
          if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); line.closeTooltip(); line.openPopup(midpoint); }
        });
      }
    });
  }

  function renderCompareView() {
    elements.visibleTotal.textContent = state.candidates.length.toLocaleString("en-AU");
    elements.visibleTotalLabel.textContent = "places to compare";
    elements.viewContent.innerHTML = `
      <section class="compare-intro">
        <div class="workflow-note"><i data-lucide="info"></i><p><strong>Where to compare sites:</strong> Choose a mapped centre or high street, or drop a new point. Each place becomes a column below, with public area evidence and straight-line distances. Reference pins are not exact tenancies.</p></div>
        <div class="button-row">
          <button class="secondary-command" id="compareDropButton" type="button"><i data-lucide="map-pin-plus"></i>Add place or map point</button>
          ${state.candidates.length ? '<button class="secondary-command" id="clearCandidates" type="button">Clear candidates</button>' : ''}
        </div>
      </section>
      ${comparisonLibraryHtml()}
      ${comparisonAreaHtml()}
      ${state.compareStores.length ? storeComparisonHtml() : ''}
      <section class="comparison-table-wrap">
        <h2>Place comparison</h2>
        <details class="comparison-method"><summary>How the comparison works</summary><p class="comparison-note"><strong>Screening index (0–100)</strong> combines the available public evidence for each selected place: local market demand, competitor white space, verified centre strength, accessibility, network spacing and tenancy-size fit. Missing evidence reduces completeness. This differs from the discovery lookalike rank. Area demographics describe the containing statistical area, not a measured customer catchment. It is a comparison aid, not a sales forecast.</p></details>
        ${
          state.candidates.length
            ? candidateComparisonTable(state.candidates)
            : '<div class="empty-state"><i data-lucide="columns-3"></i><strong>Choose your first place</strong><span>Use Compare this place in a place profile, or Add place or map point above.</span></div>'
        }
      </section>`;
    document.getElementById('saveComparisonForm').addEventListener('submit', event => {
      event.preventDefault();
      if (state.privateOverlayActive) return showToast('Close the private review before saving a public comparison.', 'warning');
      const name = document.getElementById('comparisonName').value.trim();
      if (!name || (!state.candidates.length && !state.compareStores.length)) return;
      const purpose = document.getElementById('comparisonPurpose').value.trim();
      const entry = {id: crypto.randomUUID(), name, purpose, saved_at: new Date().toISOString(), ...currentComparisonSnapshot()};
      try {
        localStorage.setItem(COMPARISON_STORAGE_KEY, JSON.stringify([entry, ...savedComparisons()]));
        state.comparisonLibraryOpen = true;
        renderView();
        const library = elements.viewContent.querySelector('.comparison-library');
        library.open = true;
        document.getElementById('savedComparison')?.focus();
        showToast(`Saved “${name}” in this browser.`);
      } catch { showToast('Comparison could not be saved. Browser storage may be full or unavailable.', 'warning'); }
    });
    elements.viewContent.querySelector('.comparison-library').addEventListener('toggle', event => {
      if (event.currentTarget.isConnected) state.comparisonLibraryOpen = event.currentTarget.open;
    });
    document.getElementById('savedComparison')?.addEventListener('change', event => {
      const entry = savedComparisons().find(entry => entry.id === event.target.value);
      if (!entry) return;
      state.comparisonUndo = currentComparisonSnapshot();
      state.comparisonLibraryOpen = true;
      restoreComparison(entry);
      document.getElementById('savedComparison')?.focus({preventScroll: true});
      showToast(`Showing “${entry.name}” on the map.`);
    });
    document.getElementById('viewComparison')?.addEventListener('click', openComparisonDetails);
    document.getElementById('undoOpenComparison')?.addEventListener('click', () => {
      const previous = state.comparisonUndo;
      state.comparisonUndo = null;
      if (previous) restoreComparison(previous);
    });
    document.getElementById('fitComparison')?.addEventListener('click', fitComparison);
    document.getElementById('comparisonLinesToggle')?.addEventListener('change', event => {
      state.comparisonConnectionsVisible = event.target.checked;
      renderComparisonConnections();
    });
    document.getElementById("compareDropButton").addEventListener("click", () => {
      setCandidateDropMode(true);
    });
    document.getElementById("clearComparedStores")?.addEventListener("click", () => { clearStoreComparison(); renderView(); });
    document.getElementById("clearCandidates")?.addEventListener("click", () => removeCandidates(state.candidates.map(candidate => candidate.id)));
    elements.viewContent.querySelectorAll('[data-remove-candidate]').forEach(button => {
      button.addEventListener('click', () => removeCandidate(button.dataset.removeCandidate));
    });
    elements.candidateDock.hidden = !state.candidates.length;
    renderCandidateDock();
  }

  function parseCsv(text) {
    const rows = [];
    let row = [];
    let value = "";
    let quoted = false;
    for (let index = 0; index < text.length; index += 1) {
      const character = text[index];
      if (character === '"' && quoted && text[index + 1] === '"') {
        value += '"';
        index += 1;
      } else if (character === '"') quoted = !quoted;
      else if (character === "," && !quoted) {
        row.push(value.trim());
        value = "";
      } else if ((character === "\n" || character === "\r") && !quoted) {
        if (character === "\r" && text[index + 1] === "\n") index += 1;
        row.push(value.trim());
        if (row.some(Boolean)) rows.push(row);
        row = [];
        value = "";
      } else value += character;
    }
    row.push(value.trim());
    if (row.some(Boolean)) rows.push(row);
    if (!rows.length) return [];
    const headers = rows.shift().map((header) => header.trim().toLowerCase());
    return rows.map((cells) => Object.fromEntries(headers.map((header, index) => [header, cells[index] || ""])));
  }

  function csvEscape(value) {
    const text = String(value ?? "");
    return /[",\n\r]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
  }

  function downloadText(filename, text, type = "text/csv;charset=utf-8") {
    const url = URL.createObjectURL(new Blob([text], { type }));
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);
  }

  function resolvePlaceId(placeId) {
    let current = String(placeId || "");
    const visited = new Set();
    while (current && state.placeIdRemaps[current] && !visited.has(current)) {
      visited.add(current);
      current = state.placeIdRemaps[current];
    }
    return current;
  }

  function loadPlaceShortlist() {
    try {
      const stored = JSON.parse(localStorage.getItem(PLACE_SHORTLIST_STORAGE_KEY) || "[]");
      const resolved = Intel.normalisePlaceShortlist(stored, state.placeIdRemaps);
      state.placeShortlist = new Set(resolved);
      persistPlaceShortlist();
    } catch {
      state.placeShortlist = new Set();
    }
  }

  function persistPlaceShortlist() {
    localStorage.setItem(PLACE_SHORTLIST_STORAGE_KEY, JSON.stringify([...state.placeShortlist]));
  }

  function togglePlaceShortlist(placeId) {
    const resolved = resolvePlaceId(placeId);
    if (!resolved) return;
    const place = state.centres.find((item) => item.place_id === resolved);
    const removing = state.placeShortlist.has(resolved);
    if (removing) state.placeShortlist.delete(resolved);
    else state.placeShortlist.add(resolved);
    persistPlaceShortlist();
    if (state.view === "opportunity") renderView();
    if (state.selectedCentreId === resolved && elements.detailPanel.classList.contains("open")) {
      openCentreDetail(state.centres.find((item) => item.place_id === resolved));
    }
    showShortlistNotice(`${place?.name || "Place"} ${removing ? "removed from" : "added to"} shortlist`);
  }

  function shortlistedPlaces() {
    return [...state.placeShortlist].map((placeId) => ({
      placeId,
      place: state.centres.find((item) => item.place_id === placeId) || null,
    }));
  }

  function allPublishedLookalikes() {
    return Object.values(state.lookalikes.rankings || {}).flat();
  }

  function publishedLookalike(placeId) {
    return allPublishedLookalikes().find((row) => row.place_id === resolvePlaceId(placeId)) || null;
  }

  function tenantsForPlace(placeId) {
    return state.placeTenants.filter((row) => row.place_id === resolvePlaceId(placeId));
  }

  function loadConsultantCorrections() {
    try {
      const parsed = JSON.parse(localStorage.getItem(CORRECTION_STORAGE_KEY) || "[]");
      state.consultantCorrections = Array.isArray(parsed) ? parsed : [];
    } catch (_error) {
      state.consultantCorrections = [];
    }
  }

  function placeSlug(value) {
    return String(value || "")
      .normalize("NFKD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-|-$/g, "");
  }

  function loadLocalPlaces() {
    try {
      const parsed = JSON.parse(localStorage.getItem(LOCAL_PLACE_STORAGE_KEY) || "[]");
      state.localPlaces = Array.isArray(parsed) ? parsed : [];
    } catch (_error) {
      state.localPlaces = [];
    }
    state.localPlaces.forEach((place) => {
      if (!state.centres.some((item) => item.place_id === place.place_id)) state.centres.push(place);
    });
  }

  function persistLocalPlaces() {
    localStorage.setItem(LOCAL_PLACE_STORAGE_KEY, JSON.stringify(state.localPlaces));
  }

  function createLocalPlace(store, fields, preferredId = "") {
    const name = String(fields.name || "").trim();
    const setting = fields.location_setting;
    if (!name || !["Shopping Centre", "High Street"].includes(setting)) return null;
    const code = store.country === "New Zealand" ? "nz" : "au";
    const baseId = setting === "Shopping Centre"
      ? `place-${code}-${placeSlug(store.state || "unknown")}-${placeSlug(name)}`
      : `corridor-${code}-${placeSlug(store.state || "unknown")}-${placeSlug(store.suburb || store.state || "unknown")}-${placeSlug(name)}`;
    let placeId = preferredId || baseId;
    const existing = state.centres.find((place) => place.place_id === placeId);
    if (existing && existing.name.toLowerCase() === name.toLowerCase()) return existing;
    if (existing) placeId = `${baseId}-local-${placeSlug(store.store_id)}`;
    const place = {
      place_id: placeId,
      centre_id: placeId,
      name,
      canonical_name: name,
      aliases: [],
      place_type: setting === "Shopping Centre" ? "Shopping Centre" : "High Street Corridor",
      location_setting: setting,
      country: store.country,
      state: store.state,
      locality: store.suburb,
      suburb: store.suburb,
      postcode: store.postcode,
      address: fields.address || store.full_address,
      latitude: Number(store.latitude),
      longitude: Number(store.longitude),
      owner: String(fields.owner || "").trim(),
      manager: String(fields.manager || "").trim(),
      centre_type: "",
      gla_sqm: "",
      annual_visits: "",
      trade_area_population: "",
      anchors: [],
      tenancy_count: "",
      redevelopment_activity: "",
      official_url: String(fields.official_url || "").trim(),
      source_url: String(fields.official_url || "").trim(),
      source_date: new Date().toISOString().slice(0, 10),
      status: "Active",
      confidence: fields.official_url ? "High" : "Medium",
      mapping_confidence: fields.official_url ? "High" : "Medium",
      source_basis: "Locally created from a consultant public-data correction",
      retailers: [],
      optical_store_count: 0,
      has_bailey: false,
      certification_status: "Local correction",
      evidence_tier: fields.official_url ? "Public URL" : "Consultant review",
      local_created: true,
    };
    state.localPlaces.push(place);
    state.centres.push(place);
    persistLocalPlaces();
    return place;
  }

  function applyConsultantCorrections() {
    state.consultantCorrections.forEach((correction) => {
      const store = state.allStores.find((item) => item.store_id === correction.store_id);
      if (!store) return;
      store.place_id = correction.place_id || "";
      store.location_setting = correction.location_setting || "Uncertain";
      store.mapping_confidence = correction.mapping_confidence || "Uncertain";
      store.mapping_evidence_url = correction.evidence_url || "";
      store.consultant_public_note = correction.public_note || "";
      store.local_mapping_override = true;
      const place = state.centres.find((item) => item.place_id === store.place_id);
      store.venue_id = store.place_id;
      store.venue_name = place?.name || "";
      store.location_type = store.location_setting;
    });
    state.centres.forEach((place) => {
      const mapped = state.allStores.filter((store) => store.place_id === place.place_id);
      place.retailers = [...new Set(mapped.map((store) => store.retailer))].sort();
      place.optical_store_count = mapped.length;
      place.has_bailey = mapped.some((store) => store.retailer === "Bailey Nelson");
    });
  }

  function loadPropertyCorrections() {
    try {
      const parsed = JSON.parse(localStorage.getItem(PROPERTY_CORRECTION_STORAGE_KEY) || "[]");
      state.propertyCorrections = Array.isArray(parsed) ? parsed : [];
    } catch (_error) {
      state.propertyCorrections = [];
    }
    try {
      const parsed = JSON.parse(localStorage.getItem(LOCAL_PROPERTY_GROUP_STORAGE_KEY) || "[]");
      state.localPropertyGroups = Array.isArray(parsed) ? parsed : [];
    } catch (_error) {
      state.localPropertyGroups = [];
    }
  }

  function propertyGroup(groupId) {
    return state.propertyGroups.find((group) => group.group_id === groupId) || null;
  }

  function applyPropertyCorrections() {
    const generatedGroups = state.propertyIntelligence?.groups || [];
    state.propertyGroups = generatedGroups.concat(
      state.localPropertyGroups.filter((local) => !generatedGroups.some((group) => group.group_id === local.group_id))
    );
    state.propertyRelationships = Intel.effectivePropertyRelationships(
      state.basePropertyRelationships,
      state.propertyCorrections
    );
    const active = state.propertyRelationships.filter((item) => Intel.activeRelationship(item));
    const baileyByPlace = new Map();
    state.allStores
      .filter((store) => store.retailer === "Bailey Nelson" && store.place_id)
      .forEach((store) => {
        const values = baileyByPlace.get(store.place_id) || [];
        values.push(store.store_id);
        baileyByPlace.set(store.place_id, values);
      });
    const portfolios = {};
    state.propertyGroups.forEach((group) => {
      const relationships = active.filter((item) => item.group_id === group.group_id);
      const propertyIds = [...new Set(relationships.map((item) => item.place_id))];
      const baileyPropertyIds = propertyIds.filter((placeId) => baileyByPlace.has(placeId));
      portfolios[group.group_id] = {
        group_id: group.group_id,
        property_count: propertyIds.length,
        bailey_property_count: baileyPropertyIds.length,
        bailey_store_count: baileyPropertyIds.reduce((sum, placeId) => sum + baileyByPlace.get(placeId).length, 0),
        property_ids: propertyIds,
        bailey_property_ids: baileyPropertyIds,
        white_space_property_ids: [],
      };
    });
    state.groupPortfolios = portfolios;

    const attributeOverrides = new Map(
      state.propertyCorrections
        .filter((item) => item.correction_type === "PROPERTY_ATTRIBUTE" && item.action === "UPSERT")
        .map((item) => [item.place_id, item])
    );
    state.centres.forEach((place) => {
      const base = state.propertyIntelligence?.property_summaries?.[place.place_id] || {};
      const relationships = active.filter((item) => item.place_id === place.place_id);
      const override = attributeOverrides.get(place.place_id);
      const hasBailey = Boolean(place.has_bailey || baileyByPlace.has(place.place_id));
      const researchStatus = base.research_status || (relationships.length ? "Partial" : "Not researched");
      const overlapStatus = Intel.portfolioOverlapStatus({
        hasBailey,
        relationships,
        groupPortfolio: portfolios,
        researchStatus,
      });
      const overlapGroups = relationships
        .filter((item) => Number(portfolios[item.group_id]?.bailey_property_count || 0) > 0)
        .map((item) => ({
          group_id: item.group_id,
          canonical_name: propertyGroup(item.group_id)?.canonical_name || item.group_id,
          role: item.role,
          bailey_property_count: portfolios[item.group_id].bailey_property_count,
          bailey_store_count: portfolios[item.group_id].bailey_store_count,
        }));
      const uniqueOverlap = overlapGroups.filter(
        (item, index, array) => array.findIndex((other) => other.group_id === item.group_id && other.role === item.role) === index
      );
      const whiteSpace = !hasBailey && [
        "LEASING_CONTROLLER_OVERLAP", "PROPERTY_GROUP_OVERLAP", "EXTERNAL_AGENCY_OVERLAP",
      ].includes(overlapStatus);
      uniqueOverlap.forEach((item) => {
        if (whiteSpace) portfolios[item.group_id].white_space_property_ids.push(place.place_id);
      });
      const competition = Intel.competitorPropertyContext(place, state.allStores);
      const ownerNames = relationships
        .filter((item) => ["OWNER", "CO_OWNER"].includes(item.role))
        .map((item) => propertyGroup(item.group_id)?.canonical_name || item.group_id);
      const managerNames = relationships
        .filter((item) => item.role === "MANAGER")
        .map((item) => propertyGroup(item.group_id)?.canonical_name || item.group_id);
      const nearestBailey = state.allStores
        .filter((store) => store.retailer === "Bailey Nelson")
        .map((store) => Intel.haversine(place, store))
        .sort((a, b) => a - b)[0];
      const summary = {
        ...base,
        place_id: place.place_id,
        centre_class: override?.centre_class || base.centre_class || "Unknown",
        centre_class_method: override?.classification_method || base.centre_class_method || "",
        centre_class_evidence: override || base.centre_class_evidence || {},
        research_status: researchStatus,
        leasing_arrangement: Intel.deriveLeasingArrangement(relationships, state.propertyGroups),
        relationship_ids: relationships.map((item) => item.relationship_id),
        group_ids: [...new Set(relationships.map((item) => item.group_id))],
        owner_names: [...new Set(ownerNames)],
        manager_names: [...new Set(managerNames)],
        has_bailey: hasBailey,
        bailey_store_count: baileyByPlace.get(place.place_id)?.length || 0,
        portfolio_overlap_status: overlapStatus,
        portfolio_overlap_groups: uniqueOverlap,
        portfolio_white_space: whiteSpace,
        nearest_bailey_km: Number.isFinite(nearestBailey) ? nearestBailey : null,
        competitor_context: competition,
      };
      state.propertySummaries[place.place_id] = summary;
      Object.assign(place, summary);
      place.owner = summary.owner_names.join(", ") || place.owner || "";
      place.manager = summary.manager_names.join(", ") || place.manager || "";
    });
  }

  function persistPropertyCorrection(correction) {
    const key = correction.record_id || `${correction.correction_type}-${correction.place_id}`;
    const index = state.propertyCorrections.findIndex(
      (item) => (item.record_id || `${item.correction_type}-${item.place_id}`) === key
    );
    if (index >= 0) state.propertyCorrections[index] = correction;
    else state.propertyCorrections.push(correction);
    localStorage.setItem(PROPERTY_CORRECTION_STORAGE_KEY, JSON.stringify(state.propertyCorrections));
    applyPropertyCorrections();
  }

  function containsPrivatePropertyData(row) {
    const prohibitedHeaders = [
      "rent", "sales", "revenue", "turnover", "profit", "margin", "lease_term", "lease_expiry",
      "negotiation", "private_contact", "email", "phone", "telephone",
    ];
    if (Object.keys(row).some((header) => prohibitedHeaders.some((word) => header.toLowerCase().includes(word)))) return true;
    const text = `${row.public_note || ""} ${row.canonical_name || ""}`;
    return /\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b/i.test(text) || /(?:\+\d{1,3}[\s-]?)?(?:\(?\d{2,4}\)?[\s-])\d{3,4}[\s-]\d{3,4}/.test(text);
  }

  function exportPropertyCorrections() {
    const fields = [
      "correction_type", "action", "record_id", "place_id", "group_id", "canonical_name", "brand_name",
      "parent_group_id", "group_type", "aliases", "role", "ownership_percentage", "centre_class",
      "classification_method", "confidence", "source_url", "public_note", "verified_at",
    ];
    const rows = state.propertyCorrections.concat(
      state.localPropertyGroups.map((group) => ({
        correction_type: "PROPERTY_GROUP", action: "UPSERT", record_id: group.group_id, ...group,
        aliases: (group.aliases || []).join("|"), verified_at: group.last_verified_at,
      }))
    );
    const csv = [fields.join(",")].concat(rows.map((row) => fields.map((field) => csvEscape(row[field])).join(",")));
    downloadText("bailey-leasing-public-property-corrections.csv", `${csv.join("\n")}\n`);
    showToast(`Exported ${rows.length} public property corrections`);
  }

  async function importPropertyCorrections(file) {
    const rows = parseCsv(await file.text());
    if (rows.some(containsPrivatePropertyData)) {
      showToast("Import blocked: property corrections cannot contain contacts or private commercial data", "warning");
      return;
    }
    const validTypes = new Set(["PROPERTY_GROUP", "ASSET_RELATIONSHIP", "PROPERTY_ATTRIBUTE"]);
    const validActions = new Set(["UPSERT", "REMOVE"]);
    const validRoles = new Set(["OWNER", "CO_OWNER", "MANAGER", "OPERATOR", "LEASING_CONTROLLER", "EXTERNAL_LEASING_AGENT"]);
    let imported = 0;
    rows.forEach((row) => {
      if (!validTypes.has(row.correction_type) || !validActions.has(row.action)) return;
      if (row.correction_type === "PROPERTY_GROUP") {
        if (!row.record_id || !row.canonical_name) return;
        const group = {
          group_id: row.record_id,
          canonical_name: row.canonical_name,
          brand_name: row.brand_name || "",
          parent_group_id: row.parent_group_id || "",
          group_type: row.group_type || "OTHER",
          aliases: (row.aliases || "").split("|").filter(Boolean),
          official_url: row.source_url || "",
          source_url: row.source_url || "",
          last_verified_at: row.verified_at || new Date().toISOString().slice(0, 10),
          confidence: row.confidence || "Medium",
          status: "Active",
          local_created: true,
        };
        const index = state.localPropertyGroups.findIndex((item) => item.group_id === group.group_id);
        if (index >= 0) state.localPropertyGroups[index] = group;
        else state.localPropertyGroups.push(group);
        imported += 1;
        return;
      }
      if (!row.place_id || !state.centres.some((place) => place.place_id === row.place_id)) return;
      if (row.correction_type === "ASSET_RELATIONSHIP" && (!row.record_id || !validRoles.has(row.role))) return;
      persistPropertyCorrection({ ...row, confidence: row.confidence || "Medium" });
      imported += 1;
    });
    localStorage.setItem(LOCAL_PROPERTY_GROUP_STORAGE_KEY, JSON.stringify(state.localPropertyGroups));
    applyPropertyCorrections();
    renderView();
    showToast(`Imported ${imported} valid public property corrections`);
  }

  function persistConsultantCorrection(correction) {
    const index = state.consultantCorrections.findIndex((item) => item.store_id === correction.store_id);
    if (index >= 0) state.consultantCorrections[index] = correction;
    else state.consultantCorrections.push(correction);
    localStorage.setItem(CORRECTION_STORAGE_KEY, JSON.stringify(state.consultantCorrections));
    applyConsultantCorrections();
  }

  function exportConsultantCorrections() {
    const fields = [
      "store_id", "previous_place_id", "place_id", "location_setting", "mapping_confidence", "evidence_url",
      "public_note", "verified_at", "new_place_name", "new_place_type", "new_place_owner", "new_place_manager",
      "new_place_official_url", "new_place_address",
    ];
    const rows = [fields.join(",")].concat(
      state.consultantCorrections.map((correction) => {
        const place = state.localPlaces.find((item) => item.place_id === correction.place_id);
        const row = place
          ? {
              ...correction,
              new_place_name: place.name,
              new_place_type: place.place_type,
              new_place_owner: place.owner,
              new_place_manager: place.manager,
              new_place_official_url: place.official_url,
              new_place_address: place.address,
            }
          : correction;
        return fields.map((field) => csvEscape(row[field])).join(",");
      })
    );
    downloadText("bailey-leasing-public-place-corrections.csv", `${rows.join("\n")}\n`);
    showToast(`Exported ${state.consultantCorrections.length} public corrections`);
  }

  async function importConsultantCorrections(file) {
    const rows = parseCsv(await file.text());
    const prohibited = ["rent", "sales", "revenue", "profit", "lease_term", "negotiation", "private_contact"];
    const headers = rows.length ? Object.keys(rows[0]) : [];
    if (headers.some((header) => prohibited.some((word) => header.includes(word)))) {
      showToast("Import blocked: this public format cannot contain private commercial fields", "warning");
      return;
    }
    const validSettings = new Set(["Shopping Centre", "High Street", "Other", "Uncertain"]);
    let imported = 0;
    rows.forEach((row) => {
      const store = state.allStores.find((item) => item.store_id === row.store_id);
      if (!store || !validSettings.has(row.location_setting)) return;
      let placeId = row.place_id || "";
      if (placeId && !state.centres.some((place) => place.place_id === placeId) && row.new_place_name) {
        const place = createLocalPlace(
          store,
          {
            name: row.new_place_name,
            location_setting: row.location_setting,
            owner: row.new_place_owner,
            manager: row.new_place_manager,
            official_url: row.new_place_official_url,
            address: row.new_place_address,
          },
          placeId
        );
        placeId = place?.place_id || "";
      }
      if (placeId && !state.centres.some((place) => place.place_id === placeId)) return;
      persistConsultantCorrection({
        store_id: row.store_id,
        previous_place_id: row.previous_place_id || "",
        place_id: placeId,
        location_setting: row.location_setting,
        mapping_confidence: row.mapping_confidence || "Medium",
        evidence_url: row.evidence_url || "",
        public_note: row.public_note || "",
        verified_at: row.verified_at || new Date().toISOString().slice(0, 10),
      });
      imported += 1;
    });
    createCentreMarkers();
    applyFilters(false);
    renderView();
    showToast(`Imported ${imported} valid public corrections`);
  }

  function healthDimensionLabel(key) {
    return {
      source_freshness: "Source freshness",
      usable_store_coverage: "Usable store coverage",
      location_setting_coverage: "Place type coverage",
      place_mapping_coverage: "Place mapping coverage",
      review_reconciliation: "Promoted review reconciliation",
      store_identity_integrity: "Duplicate store identity integrity",
      research_coverage: "Property research coverage",
      relationship_freshness: "Property relationship freshness",
      centre_class_coverage: "Centre class coverage",
      bailey_centre_research_coverage: "Bailey centre research coverage",
      bailey_centre_class_coverage: "Bailey centre class coverage",
      conflict_reconciliation: "Property conflict reconciliation",
      bailey_research_started: "Bailey co-tenancy research started",
      bailey_anchor_coverage: "Bailey accepted-anchor coverage",
      bailey_multi_category_coverage: "Bailey accepted multi-category coverage",
      evidence_freshness: "Co-tenancy evidence freshness",
      bailey_corridor_baseline_coverage: "Bailey corridor baseline coverage",
      bailey_corridor_retail_mix_coverage: "Bailey corridor retail-mix coverage",
    }[key] || key;
  }

  function renderDataHealthView() {
    const health = state.dataHealth;
    if (!health) {
      elements.viewContent.innerHTML = '<div class="empty-state"><i data-lucide="shield-alert"></i><strong>Data health unavailable</strong><span>Run the certification build to generate the health report.</span></div>';
      return;
    }
    const sources = health.sources || [];
    const blockers = health.blocking_counts || {};
    const requiredFeeds = sources.filter(source => source.required);
    const currentFeeds = requiredFeeds.filter(source => source.available && source.complete && source.fresh).length;
    const staleFeeds = requiredFeeds.filter(source => source.status === "stale").length;
    const partialFeeds = requiredFeeds.filter(source => !source.complete).length;
    const propertyHealth = health.property_intelligence || { dimensions: {}, counts: {} };
    const coTenancyHealth = health.co_tenancy || { dimensions: {}, counts: {} };
    const highStreetHealth = health.high_street_research || { dimensions: {}, counts: {} };
    const independentStores = state.allStores.filter((store) => store.retailer === "Independent / Other optical");
    const independentProfiles = {
      websites: independentStores.filter((store) => store.website_url).length,
      directories: independentStores.filter((store) => store.directory_url).length,
      social: independentStores.filter((store) => store.instagram_url || store.facebook_url).length,
      source_only: independentStores.filter((store) => !store.website_url && !store.directory_url && !store.instagram_url && !store.facebook_url).length,
    };
    elements.viewContent.innerHTML = `
      <section class="health-overview ${health.certification_status === "Operational" ? "certified" : "in-progress"}">
        <div class="health-status"><span>${health.certification_status === "Operational" ? "Operational first draft" : escapeHtml(health.certification_status)}</span><strong class="feed-summary">${currentFeeds} of ${requiredFeeds.length} required feeds current</strong><small>${staleFeeds} stale · ${partialFeeds} incomplete · as of ${escapeHtml(health.coverage_as_of)}</small></div>
        <p>Current means available, complete and within the source’s refresh threshold (30 days for named networks; 90 days for community sources). Rebuilding data does not refresh source evidence. This is not an accuracy score.</p>
        <div class="health-dimensions">${Object.entries(health.dimensions).map(([key, value]) => `<div><span>${escapeHtml(healthDimensionLabel(key))}</span><strong>${Number(value).toFixed(1)}%</strong><i><b style="width:${Number(value)}%"></b></i></div>`).join("")}</div>
        <p>${escapeHtml(health.coverage_statement)}</p>
      </section>
      <section class="health-counts">
        <div><span>Observed stores</span><strong>${formatNumber(health.observed.stores)}</strong><small>${health.changes_from_baseline.stores >= 0 ? "+" : ""}${health.changes_from_baseline.stores} vs baseline</small></div>
        <div><span>Usable named stores</span><strong>${formatNumber(health.observed.usable_named_network_stores)}</strong><small>of ${formatNumber(health.observed.named_network_stores)}</small></div>
        <div><span>Centres and plazas</span><strong>${formatNumber(health.observed.centres)}</strong><small>canonical records</small></div>
        <div><span>High-street corridors</span><strong>${formatNumber(health.observed.corridors)}</strong><small>800 m indicative catchments</small></div>
      </section>
      <section class="health-overview property-health">
        <div class="section-heading"><h2>Demographic intelligence health</h2><span>separate from store and property freshness</span></div>
        <div class="compact-metrics">
          <div><strong>${formatNumber(state.marketMetadata.feature_count || state.markets.length)}</strong><span>Australian SA2 areas</span></div>
          <div><strong>${escapeHtml(formatDate(state.marketMetadata.source_release_date))}</strong><span>ABS release</span></div>
          <div><strong>${formatNumber(state.markets.filter((item) => item.properties.population_2025 !== null).length)}</strong><span>2025 population values</span></div>
          <div><strong>${formatNumber(state.markets.filter((item) => item.properties.small_population_caution).length)}</strong><span>small-area cautions</span></div>
        </div>
        <p>Population uses ABS 2025 estimated resident population. Age and equivalised weekly household income retain their 2021 Census reference year. Very small-area rates are suppressed where Census perturbation can make percentages misleading.</p>
        <p class="empty-note">${escapeHtml(state.marketMetadata.consumer_spending_status || "Consumer spending is not included in this build.")}</p>
      </section>
      <section class="health-overview property-health">
        <div class="section-heading"><h2>Independent public profiles</h2><span>identity and discovery evidence</span></div>
        <div class="compact-metrics">
          <div><strong>${formatNumber(independentProfiles.websites)}</strong><span>business websites</span></div>
          <div><strong>${formatNumber(independentProfiles.directories)}</strong><span>directory profiles</span></div>
          <div><strong>${formatNumber(independentProfiles.social)}</strong><span>social profiles</span></div>
          <div><strong>${formatNumber(independentProfiles.source_only)}</strong><span>source-only records</span></div>
        </div>
        <p>Only explicitly sourced profile links are shown. Missing links are not guessed from business names.</p>
      </section>
      <section class="health-overview property-health">
        <div class="section-heading"><h2>Property intelligence health</h2><span>separate from store-census health</span></div>
        <div class="health-dimensions">${Object.entries(propertyHealth.dimensions || {}).map(([key, value]) => `<div><span>${escapeHtml(healthDimensionLabel(key))}</span><strong>${Number(value).toFixed(1)}%</strong><i><b style="width:${Number(value)}%"></b></i></div>`).join("")}</div>
        <div class="compact-metrics">
          <div><strong>${formatNumber(propertyHealth.counts?.groups || 0)}</strong><span>canonical groups</span></div>
          <div><strong>${formatNumber(propertyHealth.counts?.relationships || 0)}</strong><span>public relationships</span></div>
          <div><strong>${formatNumber(propertyHealth.counts?.researched_centres || 0)}</strong><span>centres researched</span></div>
          <div><strong>${formatNumber(propertyHealth.counts?.researched_bailey_centres || 0)}/${formatNumber(propertyHealth.counts?.bailey_centres || 0)}</strong><span>Bailey centres researched</span></div>
          <div><strong>${formatNumber(propertyHealth.counts?.classed_bailey_centres || 0)}/${formatNumber(propertyHealth.counts?.bailey_centres || 0)}</strong><span>Bailey centres classed</span></div>
          <div><strong>${formatNumber(propertyHealth.counts?.unmatched_active_portfolio_assets || 0)}</strong><span>active portfolio reviews</span></div>
          <div><strong>${formatNumber(propertyHealth.counts?.development_assets || 0)}</strong><span>monitored developments</span></div>
          <div><strong>${formatNumber(propertyHealth.counts?.conflicts || 0)}</strong><span>relationship conflicts</span></div>
        </div>
        <p>${escapeHtml(propertyHealth.coverage_statement || "Property relationship coverage is reported separately.")}</p>
        <p class="empty-note">${escapeHtml(propertyHealth.portfolio_overlap_note || "")}</p>
      </section>
      <section class="health-overview property-health">
        <div class="section-heading"><h2>Key co-tenancy research</h2><span>curated profiles, not complete directories</span></div>
        <div class="health-dimensions">${Object.entries(coTenancyHealth.dimensions || {}).map(([key, value]) => `<div><span>${escapeHtml(healthDimensionLabel(key))}</span><strong>${Number(value).toFixed(1)}%</strong><i><b style="width:${Number(value)}%"></b></i></div>`).join("")}</div>
        <div class="compact-metrics">
          <div><strong>${formatNumber(coTenancyHealth.counts?.pilot_places || 0)}</strong><span>opportunity pilot places</span></div>
          <div><strong>${formatNumber(coTenancyHealth.counts?.bailey_research_started || 0)}/${formatNumber(coTenancyHealth.counts?.bailey_centres || 0)}</strong><span>Bailey profiles started</span></div>
          <div><strong>${formatNumber(coTenancyHealth.counts?.bailey_anchor_profiled || 0)}/${formatNumber(coTenancyHealth.counts?.bailey_centres || 0)}</strong><span>Bailey centres with anchors</span></div>
          <div><strong>${formatNumber(coTenancyHealth.counts?.bailey_multi_category_profiled || 0)}/${formatNumber(coTenancyHealth.counts?.bailey_centres || 0)}</strong><span>Bailey accepted multi-category profiles</span></div>
        </div>
        <p>${escapeHtml(coTenancyHealth.coverage_statement || "Co-tenancy coverage is reported separately.")}</p>
      </section>
      <section class="health-overview property-health">
        <div class="section-heading"><h2>Bailey high-street research</h2><span>corridor baseline versus broader retail mix</span></div>
        <div class="health-dimensions">${Object.entries(highStreetHealth.dimensions || {}).map(([key, value]) => `<div><span>${escapeHtml(healthDimensionLabel(key))}</span><strong>${Number(value).toFixed(1)}%</strong><i><b style="width:${Number(value)}%"></b></i></div>`).join("")}</div>
        <div class="compact-metrics">
          <div><strong>${formatNumber(highStreetHealth.counts?.baseline_researched || 0)}/${formatNumber(highStreetHealth.counts?.bailey_corridors || 0)}</strong><span>corridor baselines checked</span></div>
          <div><strong>${formatNumber(highStreetHealth.counts?.key_tenant_profiled || 0)}/${formatNumber(highStreetHealth.counts?.bailey_corridors || 0)}</strong><span>broader retail-mix profiles</span></div>
        </div>
        <p>${escapeHtml(highStreetHealth.coverage_statement || "High-street research coverage is reported separately.")}</p>
      </section>
      <section class="health-overview property-health">
        <div class="section-heading"><h2>Intelligence layer roadmap</h2><span>public automation versus known gaps</span></div>
        <div class="health-source-list">${(health.intelligence_layer_register || []).map((layer) => `<div><span class="source-state ${["Operational", "In progress"].includes(layer.status) ? "current" : layer.status === "Pilot" ? "partial" : "stale"}">${escapeHtml(layer.status)}</span><span><strong>${escapeHtml(layer.label)}</strong><small>${escapeHtml(layer.current_boundary)}</small></span><b>${escapeHtml(layer.priority)}</b></div>`).join("")}</div>
        <p class="empty-note">Planned layers are not silently included in rankings. Open a generated data record or methodology note before relying on a metric.</p>
      </section>
      <section class="health-blockers">
        <h2>Promoted review exceptions</h2>
        ${Object.entries(blockers).map(([key, value]) => `<div class="${Number(value) ? "blocking" : "clear"}"><span>${escapeHtml(key.replaceAll("_", " "))}</span><strong>${formatNumber(value)}</strong></div>`).join("")}
        ${Object.entries(health.informational_counts || {}).map(([key, value]) => `<div class="clear"><span>${escapeHtml(key.replaceAll("_", " "))} · informational only</span><strong>${formatNumber(value)}</strong></div>`).join("")}
      </section>
      <section class="health-review-list">
        <div class="section-heading"><h2>Consultant mapping review</h2><span>${(health.unresolved_mapping_reviews || []).length} stores</span></div>
        ${(health.unresolved_mapping_reviews || []).map((review) => `<button class="health-review-row" data-health-store-id="${escapeHtml(review.store_id)}"><span><strong>${escapeHtml(review.store_name)}</strong><small>${escapeHtml(`${review.retailer} · ${review.state} · ${review.reason}`)}</small></span><i data-lucide="chevron-right"></i></button>`).join("")}
      </section>
      <section class="health-sources">
        <div class="section-heading"><h2>Declared sources</h2><span>${sources.filter((source) => source.status === "current").length}/${sources.length} current</span></div>
        <div class="health-source-list">${sources.map((source) => `<div><span class="source-state ${escapeHtml(source.status)}">${escapeHtml(source.status)}</span><span><strong>${escapeHtml(source.label)}</strong><small>${escapeHtml(source.scope)} · ${source.last_success ? formatDate(source.last_success) : "no successful refresh"}</small></span><b>${source.age_days === null ? "—" : `${source.age_days}d`}</b></div>`).join("")}</div>
      </section>`;
    elements.viewContent.querySelectorAll("[data-health-store-id]").forEach((button) => {
      button.addEventListener("click", () => {
        state.filters.location = "Uncertain";
        setView("network");
        applyFilters();
        selectStore(button.dataset.healthStoreId, true);
      });
    });
  }

  function candidateComparisonTable(candidates, readOnly = false) {
    const models = candidates.map((candidate) => ({ candidate, model: scoreCandidate(candidate), market: marketForPoint(candidate)?.properties || {} }));
    const rows = [
      ["Brand profile", item => state.profiles.find(profile => profile.id === item.candidate.profile_id)?.name || item.candidate.profile_id || "Generic optical"],
      ["Screening index (0–100)", (item) => item.model.score ?? "-"],
      ["Completeness", (item) => `${item.model.coverage}%`],
      ["Place basis", item => item.candidate.place_id ? "Mapped place reference point" : "User-selected map point"],
      ["Public statistical area", item => marketLabel(item.candidate)],
      ["Area population (2025)", item => formatNumber(item.market.population_2025)],
      ["Area population growth (2021–25)", item => formatNumber(item.market.population_growth_2021_2025_pct, "%")],
      ["Area weekly equivalised household income (2021)", item => item.market.median_equivalised_household_income_weekly_2021 == null ? "Unknown" : `$${formatNumber(item.market.median_equivalised_household_income_weekly_2021)}`],
      ["Market demand", (item) => componentValue(item.model, "market_demand")],
      ["White space", (item) => componentValue(item.model, "competitive_white_space")],
      ["Centre strength", (item) => componentValue(item.model, "centre_strength")],
      ["Accessibility", (item) => componentValue(item.model, "accessibility")],
      ["Network fit", (item) => componentValue(item.model, "network_fit")],
      ["Format fit", (item) => componentValue(item.model, "format_fit")],
      ["5 km competitors", (item) => item.model.competitorCountFiveKm],
      ...candidates.filter(() => candidates.length > 1).map(reference => [
        `Distance from ${reference.name} (straight line)`,
        item => item.candidate.id === reference.id ? "Same site" : Intel.formatDistance(Intel.haversine(reference, item.candidate)),
      ]),
      ["Available area", (item) => (item.candidate.area_sqm ? `${item.candidate.area_sqm} sqm` : "Unknown")],
    ];
    return `<table class="comparison-table"><thead><tr><th>Measure</th>${models
      .map((item) => `<th>${escapeHtml(item.candidate.name)}${readOnly ? '' : `<button class="secondary-command candidate-remove" type="button" data-remove-candidate="${escapeHtml(item.candidate.id)}" aria-label="Remove ${escapeHtml(item.candidate.name)}">Remove candidate</button>`}</th>`)
      .join("")}</tr></thead><tbody>${rows
      .map(
        ([label, getter]) =>
          `<tr><td>${escapeHtml(label)}</td>${models.map((item) => `<td>${escapeHtml(getter(item))}</td>`).join("")}</tr>`
      )
      .join("")}</tbody></table>`;
  }

  function componentValue(model, key) {
    const value = model.components[key];
    return value !== null && value !== undefined && value !== "" && Number.isFinite(Number(value))
      ? Math.round(Number(value))
      : "Not scored";
  }

  function distanceEntries(point, excludeId = "", certifiedOnly = false) {
    return state.allStores
      .filter((store) => store.store_id !== excludeId)
      .filter((store) => !certifiedOnly || store.eligible_for_analytics)
      .map((store) => ({ store, distance: Intel.haversine(point, store) }))
      .sort((a, b) => a.distance - b.distance || a.store.store_id.localeCompare(b.store.store_id));
  }

  function proximityModel(point, baseStore = null, certifiedOnly = true) {
    return Intel.proximityModel(point, state.allStores, BRAND_ORDER, STORE_RADII, baseStore, certifiedOnly);
  }

  function nearestBrandHtml(model, options = {}) {
    const maximumDistance = Number.isFinite(options.maxDistanceKm) ? options.maxDistanceKm : null;
    const entries = BRAND_ORDER.map((brand) => ({ brand, entry: model.nearestByBrand[brand] }))
      .filter(({ entry }) => maximumDistance === null || (entry && entry.distance <= maximumDistance));
    if (options.sortByDistance) {
      entries.sort((left, right) => (left.entry?.distance ?? Infinity) - (right.entry?.distance ?? Infinity) || left.brand.localeCompare(right.brand));
    }
    if (!entries.length) {
      return `<p class="empty-note">No mapped brand places within ${escapeHtml(maximumDistance)} km.</p>`;
    }
    return entries.map(({ brand, entry }) => {
      return `<div class="nearest-brand">${brandMarkHtml(brand, "summary")}<span class="sr-only">${escapeHtml(
        brand
      )}</span><strong>${
        entry ? Intel.formatDistance(entry.distance) : "None"
      }</strong></div>`;
    }).join("");
  }

  function radiusTableHtml(model) {
    return `<table class="radius-table"><thead><tr><th>Radius</th>${BRAND_ORDER.map(
      (brand) => `<th>${brandMarkHtml(brand, "table")}<span class="sr-only">${escapeHtml(brand)}</span></th>`
    ).join("")}<th>Total</th></tr></thead>
      <tbody>${model.radiusCounts
        .map(
          (row) => `<tr><td>${row.radius < 1 ? `${row.radius * 1000} m` : `${row.radius} km`}</td>
            ${BRAND_ORDER.map((brand) => `<td>${row.counts[brand]}</td>`).join("")}<td>${row.total}</td></tr>`
        )
        .join("")}</tbody></table>`;
  }

  function nearRows(entries, limit = 10) {
    if (!entries.length) return '<p class="empty-note">No matching places found.</p>';
    return entries
      .slice(0, limit)
      .map(
        (entry) => `<button class="near-row" data-store-id="${escapeHtml(entry.store.store_id)}">${brandMarkHtml(
          entry.store.retailer,
          "compact"
        )}<strong>${escapeHtml(entry.store.name)}</strong><span>${Intel.formatDistance(
          entry.distance
        )}</span></button>`
      )
      .join("");
  }

  function areaHtml(store) {
    if (!store.store_area_sqm) {
      return `<div class="area-record unknown"><span>Store area</span><strong>Not publicly verified</strong><small>No tenancy footprint is inferred.</small></div>`;
    }
    return `<div class="area-record ${String(store.area_measure).toLowerCase().includes("estimated") ? "estimated" : "verified"}">
      <span>Store area</span><strong>${formatNumber(store.store_area_sqm, " sqm")} ${escapeHtml(store.area_measure)}</strong>
      <small>${escapeHtml(store.area_source || "Public source")} · ${escapeHtml(formatDate(store.area_date))} · ${escapeHtml(
      store.area_confidence
    )}</small></div>`;
  }

  function correctionEditorHtml(store) {
    const placeOptions = state.centres
      .filter((place) => place.country === store.country)
      .sort((a, b) => a.name.localeCompare(b.name))
      .map((place) => `<option value="${escapeHtml(place.place_id)}" data-setting="${escapeHtml(place.location_setting)}" ${place.place_id === store.place_id ? "selected" : ""}>${escapeHtml(`${place.name} · ${place.locality || place.state || place.place_type}`)}</option>`)
      .join("");
    return `<section class="detail-section correction-editor">
      <h3>Consultant mapping correction</h3>
      <p class="empty-note"><strong>Canonical place</strong> simply means the one shared record for a real centre or street. Choose it if it exists, or create it here if it does not. Saved only in this browser until you export the public correction CSV.</p>
      <div class="correction-grid">
        <label><span>Place type</span><select id="correctionSetting">${["Shopping Centre", "High Street", "Other", "Uncertain"].map((value) => `<option ${value === store.location_setting ? "selected" : ""}>${value}</option>`).join("")}</select></label>
        <label><span>Confidence</span><select id="correctionConfidence">${["High", "Medium", "Uncertain"].map((value) => `<option ${value === store.mapping_confidence ? "selected" : ""}>${value}</option>`).join("")}</select></label>
        <label class="correction-place-search"><span>Find a centre or corridor</span><input id="correctionPlaceSearch" type="search" placeholder="Type Taree, Silverdale…" /></label>
        <label class="correction-place-select"><span>Canonical place</span><select id="correctionPlace"><option value="">No mapped place</option><option value="__new__">＋ Create a missing place…</option>${placeOptions}</select></label>
        <div class="new-place-fields" id="newPlaceFields" hidden>
          <p>Create a public place record. The centre owner/manager is the property organisation—not the optometry franchisee.</p>
          <label><span>Centre or corridor name</span><input id="newPlaceName" value="" placeholder="e.g. Taree Central" /></label>
          <label><span>Owner (optional)</span><input id="newPlaceOwner" value="" placeholder="Legal property owner" /></label>
          <label><span>Manager (optional)</span><input id="newPlaceManager" value="" placeholder="Property/centre manager" /></label>
          <label><span>Official public URL (optional)</span><input id="newPlaceUrl" type="url" value="" placeholder="https://…" /></label>
        </div>
        <label><span>Public evidence URL</span><input id="correctionEvidence" type="url" value="${escapeHtml(store.mapping_evidence_url || "")}" placeholder="https://…" /></label>
        <label class="correction-note"><span>Public-data note</span><textarea id="correctionNote" rows="2" placeholder="Public correction rationale only">${escapeHtml(store.consultant_public_note || "")}</textarea></label>
      </div>
      <button class="secondary-command" id="saveMappingCorrection" type="button"><i data-lucide="save"></i>Save local correction</button>
    </section>`;
  }

  function bindCorrectionEditor(store) {
    const settingInput = document.getElementById("correctionSetting");
    const placeInput = document.getElementById("correctionPlace");
    const searchInput = document.getElementById("correctionPlaceSearch");
    const newFields = document.getElementById("newPlaceFields");
    const updatePlaceChoices = () => {
      const setting = settingInput.value;
      const query = searchInput.value.trim().toLowerCase();
      const needsPlace = ["Shopping Centre", "High Street"].includes(setting);
      searchInput.closest("label").hidden = !needsPlace;
      placeInput.closest("label").hidden = !needsPlace;
      [...placeInput.options].forEach((option) => {
        if (!option.dataset.setting) return;
        option.hidden = option.dataset.setting !== setting || Boolean(query && !option.textContent.toLowerCase().includes(query));
      });
      if (placeInput.selectedOptions[0]?.dataset.setting && placeInput.selectedOptions[0].dataset.setting !== setting) {
        placeInput.value = "";
      }
      if (!needsPlace) placeInput.value = "";
      newFields.hidden = !needsPlace || placeInput.value !== "__new__";
    };
    settingInput.addEventListener("change", updatePlaceChoices);
    placeInput.addEventListener("change", updatePlaceChoices);
    searchInput.addEventListener("input", updatePlaceChoices);
    updatePlaceChoices();
    document.getElementById("saveMappingCorrection")?.addEventListener("click", () => {
      const setting = settingInput.value;
      let placeId = placeInput.value;
      const publicNote = document.getElementById("correctionNote").value.trim();
      if (/\b(rent|sales|revenue|profit|lease terms?|negotiation|phone|email|contact)\b/i.test(publicNote)) {
        showToast("Keep this note public: private commercial or contact data is not allowed", "warning");
        return;
      }
      if (placeId === "__new__") {
        const newName = document.getElementById("newPlaceName").value.trim();
        if (!newName) {
          showToast("Enter the centre or corridor name", "warning");
          return;
        }
        const newPlace = createLocalPlace(store, {
          name: newName,
          location_setting: setting,
          owner: document.getElementById("newPlaceOwner").value,
          manager: document.getElementById("newPlaceManager").value,
          official_url: document.getElementById("newPlaceUrl").value,
        });
        placeId = newPlace?.place_id || "";
      }
      if (["Shopping Centre", "High Street"].includes(setting) && !placeId) {
        showToast("Choose an existing place or create the missing one", "warning");
        return;
      }
      persistConsultantCorrection({
        store_id: store.store_id,
        previous_place_id: store.original_place_id || "",
        place_id: placeId,
        location_setting: setting,
        mapping_confidence: document.getElementById("correctionConfidence").value,
        evidence_url: document.getElementById("correctionEvidence").value.trim(),
        public_note: publicNote,
        verified_at: new Date().toISOString().slice(0, 10),
      });
      createCentreMarkers();
      applyFilters(false);
      openStoreDetail(store);
      showToast("Local mapping correction saved");
    });
  }

  function storePublicLinksHtml(store) {
    const links = [];
    const seen = new Set();
    const add = (url, label, icon, primary = false) => {
      const value = String(url || "").trim();
      if (!/^https?:\/\//i.test(value) || seen.has(value)) return;
      seen.add(value);
      links.push(`<a class="command-link ${primary ? "primary" : ""}" href="${escapeHtml(value)}" target="_blank" rel="noopener"><i data-lucide="${icon}"></i>${label}</a>`);
    };
    if (store.retailer !== "Independent / Other optical") {
      add(store.official_url, "Official store", "external-link", true);
      return links.join("");
    }
    const website = store.website_url || (
      store.official_url && !/openstreetmap\.org|provision\.com\.au\/practice\//i.test(store.official_url)
        ? store.official_url
        : ""
    );
    add(website, "Website", "globe-2", true);
    add(store.instagram_url, "Instagram", "instagram");
    add(store.facebook_url, "Facebook", "facebook");
    add(store.directory_url, "Directory listing", "contact");
    if (/openstreetmap\.org/i.test(store.source_url || "")) {
      add(store.source_url, "Map source", "map-pin");
    } else {
      add(store.source_url, "Source", "file-search");
    }
    return links.join("") || `<span class="empty-note">No verified public profile recorded</span>`;
  }

  function openStoreDetail(store) {
    state.selectedCentreId = "";
    state.selectedStoreId = store.store_id;
    const config = BRAND_CONFIG[store.retailer];
    const services = store.services.split(/[;,]/).map((item) => item.trim()).filter(Boolean);
    const model = proximityModel(store, store);
    const market = marketForStore(store);
    const sameCentreEntries = model.sameCentre.map((match) => ({
      store: match,
      distance: Intel.haversine(store, match),
    }));
    elements.detailContent.innerHTML = `
      <header class="detail-header" style="--brand-color:${config.color}">
        <span class="retailer-tag">${brandMarkHtml(store.retailer, "detail")}${escapeHtml(store.retailer)}</span>
        <h2>${escapeHtml(store.name)}</h2><address>${escapeHtml(store.full_address || "Address not recorded")}</address>
        <p class="record-status">Recorded status: <strong>${escapeHtml(store.status || "Unknown")}</strong></p>
        ${store.current_source ? "" : `<p class="record-warning">Source check overdue or incomplete. Last source capture: ${escapeHtml(formatDate(store.fetched_at))}. Recorded status is not a current trading confirmation.</p>`}
        <button class="detail-action" id="compareFromDetail" type="button">Add to Compare</button>
        <div class="link-row">${store.phone ? `<a class="command-link" href="tel:${escapeHtml(store.phone.replace(/[^+\d]/g, ""))}"><i data-lucide="phone"></i>Call</a>` : ""}
          ${storePublicLinksHtml(store)}</div>
      </header>
      <section class="detail-section">
        <h3>Leasing profile</h3>
        <div class="data-grid">
          <div class="data-point"><span>Place type</span><strong>${escapeHtml(store.location_setting)}</strong></div>
          <div class="data-point"><span>Mapping confidence</span><strong><span class="confidence">${escapeHtml(
            store.mapping_confidence
          )}</span></strong></div>
          <div class="data-point"><span>Canonical place</span><strong>${escapeHtml(store.venue_name || "Not mapped")}</strong></div>
          <div class="data-point"><span>Status</span><strong>${escapeHtml(store.status)}</strong></div>
          ${store.coordinate_confidence ? `<div class="data-point"><span>Coordinate evidence</span><strong>${escapeHtml(store.coordinate_confidence)}</strong></div>` : ""}
          <div class="data-point"><span>Affiliation</span><strong>${escapeHtml(
            String(store.affiliations || "").split("|").filter(Boolean)
              .map((id) => state.affiliations.find((item) => item.affiliation_id === id)?.name || id)
              .join(", ") || "None recorded"
          )}</strong></div>
          <div class="data-point"><span>Network usability</span><strong><span class="confidence ${store.usable_for_network ? "" : "uncertified"}">${store.usable_for_network ? "Usable" : "Background only"}</span></strong></div>
          <div class="data-point"><span>Source freshness</span><strong>${store.current_source ? "Current" : "Source check overdue or incomplete"}</strong></div>
          <div class="data-point"><span>Country</span><strong>${escapeHtml(store.country)}</strong></div>
          <div class="data-point"><span>State / region</span><strong>${escapeHtml(store.state)}</strong></div>
        </div>
        ${areaHtml(store)}
        <p class="empty-note">${escapeHtml(store.classification_basis)}</p>
        ${store.public_facts_verified_at ? `<p class="empty-note">Public facts reviewed ${escapeHtml(store.public_facts_verified_at)}: ${escapeHtml(store.public_facts_reason || "")} <a href="${escapeHtml(store.public_facts_evidence_url)}" target="_blank" rel="noopener noreferrer">View evidence</a></p>` : ""}
        ${store.coordinate_confidence && store.coordinate_reason && store.coordinate_reason !== store.classification_basis ? `<p class="empty-note">${escapeHtml(store.coordinate_reason)}</p>` : ""}
        ${store.retailer === "Independent / Other optical" ? `<p class="empty-note">Public profile links are identity and discovery evidence. Confirm current trading status directly before relying on them.</p>` : ""}
        <div class="service-list">${services.length ? services.map((service) => `<span>${escapeHtml(service)}</span>`).join("") : "<span>No services listed</span>"}</div>

      </section>
      ${store.current_source ? "" : `<section class="detail-section certification-warning"><h3>Freshness warning</h3><p>This source is outside its freshness target or is incomplete. Network usability is assessed separately.</p></section>`}
      <details class="technical-details"><summary>Public mapping corrections</summary>${correctionEditorHtml(store)}</details>
      ${
        market
          ? marketEvidenceHtml(market.properties)
          : store.country === "New Zealand"
            ? `<section class="detail-section coverage-note"><h3>New Zealand demographics</h3>
              <p class="empty-note">Store, centre and proximity coverage is available. Stats NZ demographic catchments are not yet published in this build, so no Australian proxy is shown.</p></section>`
            : ""
      }
      <section class="detail-section"><h3>Nearest current brand places</h3>
        <div class="proximity-summary">${nearestBrandHtml(model)}</div>${radiusTableHtml(model)}
      </section>
      <section class="detail-section"><h3>Same-centre competitors</h3>
        <div class="nearest-list">${
          sameCentreEntries.length
            ? nearRows(sameCentreEntries)
            : '<p class="empty-note">No reviewed same-centre competitor is recorded. Proximity is never used to assign a venue.</p>'
        }</div></section>
      <section class="detail-section"><h3>Ten nearest current stores</h3><div class="nearest-list">${nearRows(
        model.distances
      )}</div></section>
      <details class="technical-details"><summary>Source record and identifier</summary><section class="detail-section source-block"><i data-lucide="database"></i><div><strong>${
        store.retailer === "Independent / Other optical"
          ? (store.store_id.startsWith("independent-other-optical-reviewed-") ? "Reviewed public practice evidence" : String(store.affiliations || "").split("|").includes("provision") ? "Official ProVision practice source" : "Community-mapped public source")
          : "Official retailer source"
      }</strong>
        <span>Refreshed ${escapeHtml(formatDate(store.fetched_at))} · ${escapeHtml(
          store.store_id
        )}${store.retailer === "Independent / Other optical" ? " · Coverage remains non-exhaustive" : ""}</span></div></section></details>`;
    openDetailPanel();
    document.getElementById("compareFromDetail").addEventListener("click", () => {
      addCompareStore(store);
    });
    bindCorrectionEditor(store);
    bindNearRows();
  }

  function marketEvidenceHtml(properties) {
    return `<section class="detail-section">
      <div class="section-title-row"><h3>Local market · ${escapeHtml(properties.sa2_name)}</h3><span class="source-pill">ABS</span></div>
      <div class="data-grid">
        <div class="data-point"><span>Population 2025</span><strong>${formatNumber(properties.population_2025)}</strong></div>
        <div class="data-point"><span>Residents added 2021–25</span><strong>${formatNumber(properties.population_growth_2021_2025_number)}</strong></div>
        <div class="data-point"><span>Growth 2021–25</span><strong>${formatNumber(
          properties.population_growth_2021_2025_pct,
          "%"
        )}</strong></div>
        <div class="data-point"><span>Age 45+ 2021</span><strong>${formatNumber(properties.age_45_plus_pct_2021, "%")}</strong></div>
        <div class="data-point"><span>Equivalised weekly household income</span><strong>$${formatNumber(
          properties.median_equivalised_household_income_weekly_2021
        )}</strong></div>
        <div class="data-point"><span>Retail businesses 2025</span><strong>${formatNumber(
          properties.retail_businesses_2025
        )}</strong></div>
        <div class="data-point"><span>Unemployment 2021</span><strong>${formatNumber(
          properties.unemployment_rate_2021,
          "%"
        )}</strong></div>
      </div>
      <p class="empty-note">ABS Data by Region released ${escapeHtml(formatDate(state.marketMetadata.source_release_date))}. Census-derived measures retain their 2021 reference year. Equivalised household income is not consumer spending. ${escapeHtml(properties.quality_note || "")}</p>
    </section>`;
  }

  function relationshipRoleLabel(role) {
    return {
      OWNER: "Owner", CO_OWNER: "Co-owner", MANAGER: "Manager", OPERATOR: "Operator",
      LEASING_CONTROLLER: "Leasing controller", EXTERNAL_LEASING_AGENT: "External leasing agency",
    }[role] || role;
  }

  function overlapLabel(value, placeLabel = "centre") {
    return {
      SAME_CENTRE: `Bailey Nelson in this ${placeLabel}`,
      LEASING_CONTROLLER_OVERLAP: "Known BN leasing-controller portfolio overlap",
      PROPERTY_GROUP_OVERLAP: "Known BN property-group portfolio overlap",
      EXTERNAL_AGENCY_OVERLAP: "Known BN external-agency portfolio overlap",
      NO_KNOWN_OVERLAP: "No known overlap after verified research",
      UNKNOWN: "Unknown — property research is incomplete",
    }[value] || value || "Unknown";
  }

  function relationshipCardsHtml(relationships) {
    if (!relationships.length) return '<p class="empty-note">No public ownership, management or leasing relationship has been confirmed.</p>';
    return `<div class="relationship-list">${relationships.map((relationship) => {
      const group = propertyGroup(relationship.group_id);
      return `<article class="relationship-card">
        <div><span>${escapeHtml(relationshipRoleLabel(relationship.role))}</span>
          <a href="#property-group=${encodeURIComponent(relationship.group_id)}" class="text-button" data-property-group-id="${escapeHtml(relationship.group_id)}"><strong>${escapeHtml(group?.canonical_name || relationship.group_id)}</strong></a>
          ${relationship.ownership_percentage !== null && relationship.ownership_percentage !== "" ? `<b>${escapeHtml(relationship.ownership_percentage)}%</b>` : ""}
        </div>
        <small>${escapeHtml(relationship.confidence || "Unknown")} confidence · verified ${escapeHtml(formatDate(relationship.last_verified_at))}</small>
        <p>${escapeHtml(relationship.public_note || relationship.source_type || "Public property evidence")}</p>
        <div class="link-row"><a href="${escapeHtml(relationship.source_url)}" target="_blank" rel="noopener">Source</a>
          <button type="button" class="text-button" data-edit-property-relationship="${escapeHtml(relationship.relationship_id)}">Edit</button>
          <button type="button" class="text-button danger" data-remove-property-relationship="${escapeHtml(relationship.relationship_id)}">Remove locally</button></div>
        ${groupPortfolioInlineHtml(relationship.group_id)}
      </article>`;
    }).join("")}</div>`;
  }

  function groupPortfolioInlineHtml(groupId) {
    const portfolio = state.groupPortfolios[groupId] || {};
    const group = propertyGroup(groupId);
    const ids = portfolio.property_ids || Object.keys(state.propertyIntelligence?.group_portfolios?.[groupId]?.asset_roles || {});
    const places = ids.map((placeId) => state.centres.find((item) => item.place_id === placeId)).filter(Boolean)
      .sort((a, b) => a.name.localeCompare(b.name));
    if (!places.length) return "";
    return `<details class="inline-portfolio"><summary>View ${escapeHtml(group?.canonical_name || groupId)} matched portfolio (${places.length})</summary>
      <div>${places.map((place) => `<button type="button" data-group-place-id="${escapeHtml(place.place_id)}"><span>${escapeHtml(place.name)}</span><b>${place.has_bailey ? "BN present" : place.portfolio_white_space ? "white space" : "BN absent"}</b></button>`).join("")}</div>
    </details>`;
  }

  function competitorContextHtml(centre) {
    if (centre.latitude == null || centre.longitude == null) return '<p class="empty-note">Map point unresolved; nearby distances are unavailable. See the directory evidence for recorded optical listings.</p>';
    const context = centre.competitor_context?.by_retailer || {};
    const placeLabel = centre.location_setting === "High Street" ? "CORRIDOR" : "CENTRE";
    const placeLabelLower = placeLabel.toLowerCase();
    const brands = BRAND_ORDER.map((brand) => {
      const values = context[brand] || { in_centre: [], nearby_unverified: [], catchment_2km: [] };
      return { brand, values };
    }).filter(({ values }) => values.in_centre.length || values.nearby_unverified.length || values.catchment_2km.length);
    if (!brands.length) return '<p class="empty-note">No mapped optical competition within the selected place or its 2 km context.</p>';
    const storeRows = (records, label) => records.map((record) => `<button type="button" class="competition-store-row" data-store-id="${escapeHtml(record.store_id)}">
      <span>${escapeHtml(record.name)}</span><b>${escapeHtml(label)}${Number.isFinite(Number(record.distance_km)) ? ` · ${escapeHtml(Intel.formatDistance(Number(record.distance_km)))}` : ""}</b>
    </button>`).join("");
    return `<div class="competitor-context">${brands.map(({ brand, values }) => `<div><strong>${brandMarkHtml(brand, "compact")}<span class="competitor-brand-name">${escapeHtml(brand)}</span></strong>
        <span>${values.in_centre.length ? `${values.in_centre.length} IN ${placeLabel}` : `Not mapped in ${placeLabelLower}`}</span>
        ${values.nearby_unverified.length ? `<small>${values.nearby_unverified.length} NEARBY ≤250M — NOT VERIFIED IN ${placeLabel}</small>` : ""}
        ${values.catchment_2km.length ? `<small>${values.catchment_2km.length} elsewhere within 2 km straight-line catchment</small>` : ""}
        <div class="competition-store-list">
          ${storeRows(values.in_centre, `IN ${placeLabel}`)}
          ${storeRows(values.nearby_unverified, `NEARBY — NOT VERIFIED IN ${placeLabel}`)}
          ${storeRows(values.catchment_2km, "WITHIN 2 KM")}
        </div>
      </div>`).join("")}</div>`;
  }

  const LOOKALIKE_COMPONENTS = {
    bailey_footprint_similarity: ["Footprint similarity", "How closely the public demographic and place context resembles Bailey Nelson places in the same country and setting."],
    bailey_whitespace: ["Bailey whitespace", "How much geographic room exists from the nearest current Bailey Nelson store."],
    optical_market_validation: ["Optical validation", "Demand signal from optical stores accepted as members of this exact centre or corridor."],
    accessibility_retail_context: ["Retail context", "Available public evidence for centre scale or established high-street activity."],
  };

  function hasLookalikeComponent(value) {
    return value !== null && value !== undefined && value !== "" && Number.isFinite(Number(value));
  }

  function opportunitySummaryHtml(centre) {
    const row = publishedLookalike(centre.place_id);
    if (!row) {
      return `<section class="detail-section opportunity-summary"><div class="section-title-row"><h3>Opportunity summary</h3><span class="source-pill">Decision screen</span></div>
        <p>${centre.has_bailey ? "Bailey Nelson is already mapped to this place, so it is not included in the Bailey-free opportunity ranking." : "This place does not currently have a published lookalike ranking."}</p>
        <div class="data-grid"><div class="data-point"><span>Bailey Nelson</span><strong>${centre.has_bailey ? "Present" : "Not mapped"}</strong></div><div class="data-point"><span>Mapped optical stores</span><strong>${formatNumber(centre.optical_store_count || 0)}</strong></div></div>
      </section>`;
    }
    const market = row.market_features || {};
    const gaps = Object.entries(LOOKALIKE_COMPONENTS).filter(([key]) => !hasLookalikeComponent(row.components?.[key])).map(([, value]) => value[0]);
    return `<section class="detail-section opportunity-summary">
      <div class="section-title-row"><h3>Opportunity summary</h3><span class="source-pill">Bailey-free rank</span></div>
      <div class="opportunity-lead"><div class="score-ring ${row.screening_completeness < 60 ? "low-coverage" : ""}" style="--score:${row.score || 0}"><strong>${row.score ?? "—"}</strong><span>lookalike</span></div>
        <div><strong>#${row.rank} in ${escapeHtml(row.country)} · ${escapeHtml(row.location_setting)}</strong><p>${row.screening_completeness}% of weighted screening inputs available. This does not measure local census completeness or investment confidence. The score compares Bailey Nelson’s mapped footprint; it is not a success probability.</p></div></div>
      <div class="lookalike-components">${Object.entries(LOOKALIKE_COMPONENTS).map(([key, [label, explanation]]) => {
        const value = row.components?.[key];
        return `<div><span><strong>${escapeHtml(label)}</strong><small>${escapeHtml(explanation)}</small></span><b>${hasLookalikeComponent(value) ? Math.round(Number(value)) : "N/A"}</b></div>`;
      }).join("")}</div>
      <div class="data-grid opportunity-facts">
        <div class="data-point"><span>Population 2025</span><strong>${formatNumber(market.population_2025)}</strong></div>
        <div class="data-point"><span>Residents added 2021–25</span><strong>${formatNumber(market.population_growth_2021_2025_number)}</strong></div>
        <div class="data-point"><span>Population growth 2021–25</span><strong>${formatNumber(market.population_growth_2021_2025_pct, "%")}</strong></div>
        <div class="data-point"><span>Age 45+ (2021)</span><strong>${formatNumber(market.age_45_plus_pct_2021, "%")}</strong></div>
        <div class="data-point"><span>Equivalised weekly household income (2021)</span><strong>${market.median_equivalised_household_income_weekly_2021 ? `$${formatNumber(market.median_equivalised_household_income_weekly_2021)}` : "N/A"}</strong></div>
        <div class="data-point"><span>Nearest Bailey Nelson</span><strong>${Number.isFinite(Number(row.nearest_bailey_km)) ? Intel.formatDistance(Number(row.nearest_bailey_km)) : "Unknown"}</strong></div>
        <div class="data-point"><span>Exact-place optical stores</span><strong>${formatNumber(row.optical_store_count || 0)}</strong></div>
      </div>
      <p class="evidence-gaps"><strong>Evidence gaps:</strong> ${gaps.length ? escapeHtml(gaps.join(", ")) : "No weighted component is missing."}</p>
    </section>`;
  }

  function publicMetricSourcesHtml(centre) {
    const labels = {gla_sqm: "GLA", annual_visits: "Annual visits", tenancy_count: "Retail tenancies"};
    const evidence = Object.entries(centre.metric_evidence || {}).filter(([key, value]) => labels[key] && value.source_url);
    if (evidence.length) return `<p class="empty-note">${evidence.map(([key, value]) => `<a href="${escapeHtml(value.source_url)}" target="_blank" rel="noopener">${labels[key]} source</a>${value.source_date ? ` dated ${escapeHtml(formatDate(value.source_date))}` : value.source_period ? ` (${escapeHtml(value.source_period)})` : ""}${value.last_verified_at ? ` · checked ${escapeHtml(formatDate(value.last_verified_at))}` : ""}`).join("<br>")}. Historical measures retain their source period.</p>`;
    if (!centre.source_url || !(centre.gla_sqm || centre.annual_visits || centre.tenancy_count)) return "";
    return `<p class="empty-note">Metric source: <a href="${escapeHtml(centre.source_url)}" target="_blank" rel="noopener">public owner material</a>${centre.source_date ? ` dated ${escapeHtml(formatDate(centre.source_date))}` : ""}${centre.last_verified_at ? ` · checked ${escapeHtml(formatDate(centre.last_verified_at))}` : ""}.</p>`;
  }

  function destinationResearchHtml(centre) {
    const research = state.destinationResearch[resolvePlaceId(centre.place_id)];
    if (!research) return "";
    const categories = research.categories || [];
    return `<section class="detail-section destination-research"><h3>Retail mix research</h3>
      <p><strong>${formatNumber(research.in_scope_non_optical_listings)} non-optical directory listings</strong> in the researched scope · checked ${escapeHtml(formatDate(research.observed_at))}</p>
      <p>${categories.slice(0, 5).map(item => `${escapeHtml(item.name)}: ${formatNumber(item.listing_count)}`).join(" · ")}</p>
      ${categories.length > 5 ? `<details><summary>All researched categories</summary><p>${categories.map(item => `${escapeHtml(item.name)}: ${formatNumber(item.listing_count)}`).join(" · ")}</p></details>` : ""}
      <p class="empty-note">${escapeHtml(research.scope)}</p>
      <p class="empty-note">${formatNumber(research.source_listing_count)} source listings; ${formatNumber(research.coming_soon_listings)} labelled coming soon; ${formatNumber(research.held_scope_listings)} held for scope/identity review; ${formatNumber(research.unclassified_listings)} unclassified in this scope. Directory presence is not an independent trading check. Counts are listings, not occupied tenancies or floor-area shares; categories can overlap.</p>
      <div class="link-row">${(research.source_urls || []).map(url => `<a class="command-link" href="${escapeHtml(url)}" target="_blank" rel="noopener">Directory source</a>`).join("")}<a class="command-link" href="data/destination_directory.json" download>Detailed research database</a><a class="command-link" href="data/destination_directory_comparisons.json" download>Directory comparisons</a><a class="command-link" href="data/destination_profiles.html" target="_blank" rel="noopener">Full destination profiles</a><a class="command-link" href="data/destination_profile_comparisons.csv" download>Profile comparison CSV</a></div>
    </section>`;
  }

  function keyCoTenancyHtml(centre) {
    const tenants = tenantsForPlace(centre.place_id);
    const keyTenants = tenants.filter((row) => row.category !== "Optical");
    if (!keyTenants.length) {
      const wording = centre.location_setting === "High Street"
        ? "A broader street-retail mix has not yet been curated for this corridor. This does not mean those tenant categories are absent."
        : "Key co-tenancy research has not yet been completed for this place. This does not mean those tenant categories are absent.";
      return `<p class="empty-note">${wording}</p>`;
    }
    const grouped = Object.groupBy
      ? Object.groupBy(keyTenants, (row) => row.category)
      : keyTenants.reduce((result, row) => ((result[row.category] ||= []).push(row), result), {});
    return `<div class="co-tenancy-profile">${Object.entries(grouped).sort(([a], [b]) => a.localeCompare(b)).map(([category, rows]) => `<div><strong>${escapeHtml(category)}</strong><span>${rows.map((row) => `<a href="${escapeHtml(row.source_url)}" target="_blank" rel="noopener" title="${escapeHtml(row.source_date ? `Source dated ${formatDate(row.source_date)}` : `Checked ${formatDate(row.verified_at)}`)}">${escapeHtml(row.tenant_name)}${row.anchor_flag ? " · anchor" : ""}${row.status === "Uncertain" ? " · uncertain" : ""}</a>`).join("")}</span></div>`).join("")}</div>
      <p class="empty-note">Curated key co-tenants only—not a complete centre directory. Evidence checked ${escapeHtml(formatDate(state.placeTenantMetadata.verified_at))}; stale or uncertain records are labelled individually.</p>`;
  }

  function highStreetProfileHtml(centre) {
    if (centre.location_setting !== "High Street") return "";
    const tenants = tenantsForPlace(centre.place_id);
    const exactOptical = tenants.filter((row) => row.category === "Optical");
    const opticalCompetitors = exactOptical.filter((row) => row.retailer !== "Bailey Nelson");
    const keyTenants = tenants.filter((row) => row.category !== "Optical");
    const researched = (state.placeTenantMetadata.researched_bailey_corridor_place_ids || []).includes(centre.place_id);
    return `<section class="detail-section high-street-profile">
      <div class="section-title-row"><h3>High-street research profile</h3><span class="source-pill">${researched ? "Baseline checked" : "Not checked"}</span></div>
      <div class="data-grid">
        <div class="data-point"><span>Comparison boundary</span><strong>Named street and locality</strong></div>
        <div class="data-point"><span>Accepted optical tenants</span><strong>${formatNumber(exactOptical.length)}</strong></div>
        <div class="data-point"><span>Optical competitors</span><strong>${formatNumber(opticalCompetitors.length)}</strong></div>
        <div class="data-point"><span>Curated key co-tenants</span><strong>${formatNumber(keyTenants.length)}</strong></div>
      </div>
      <p>${researched ? "Bailey Nelson’s published address and the accepted optical memberships have been reconciled to this canonical street-and-locality corridor." : "This corridor still needs its Bailey Nelson address and accepted optical memberships reconciled."}</p>
      <p class="empty-note">Exact corridor membership is address-based; proximity alone is never used. High streets usually lack a single authoritative directory, so broader fashion, hospitality, visitation and footfall coverage remains explicit when unavailable.</p>
    </section>`;
  }

  function developmentSignalsHtml(centre) {
    const signals = state.developmentSignals.filter((item) => item.place_id === centre.place_id);
    if (!signals.length) return "";
    return `<section class="detail-section"><div class="section-title-row"><h3>Growth & development signals</h3><span class="source-pill">Selective public evidence</span></div>
      <div class="development-signal-list">${signals.map((signal) => `<article>
        <div><strong>${escapeHtml(signal.title)}</strong><span>${escapeHtml(signal.status.replaceAll("_", " "))} · ${escapeHtml(signal.impact_horizon || "Timing not yet sourced")}</span></div>
        <span class="source-state ${signal.evidence_status === "Verified" ? "current" : "partial"}">${escapeHtml(signal.evidence_status)}</span>
        <p>${escapeHtml(signal.summary)}</p>
        <dl><div><dt>Temporary</dt><dd>${escapeHtml(signal.temporary_impact || "Unknown")}</dd></div><div><dt>Long term</dt><dd>${escapeHtml(signal.long_term_impact || "Unknown")}</dd></div></dl>
        <a href="${escapeHtml(signal.source_url)}" target="_blank" rel="noopener">${escapeHtml(signal.source_type)} · checked ${escapeHtml(formatDate(signal.last_verified_at))}</a>
      </article>`).join("")}</div>
      <p class="empty-note">This is a selective signal register, not a complete development pipeline. Early-stage proposals may change or not proceed.</p>
    </section>`;
  }

  function propertyGroupNames(centre) {
    return [...new Set(state.propertyRelationships.filter((item) => item.place_id === centre.place_id && Intel.activeRelationship(item)).map((item) => propertyGroup(item.group_id)?.canonical_name || item.group_id))];
  }

  function placeSummaryRecord(centre) {
    const evidence = state.environments?.places.find(p => p.place_id === centre.place_id);
    const row = publishedLookalike(centre.place_id) || {};
    const market = row.market_features || {};
    const relationships = state.propertyRelationships.filter((item) => item.place_id === centre.place_id && Intel.activeRelationship(item));
    const verifiedDates = relationships.map((item) => item.last_verified_at).filter(Boolean).sort();
    const relationshipNames = (role) => relationships
      .filter((item) => item.role === role)
      .map((item) => {
        const name = propertyGroup(item.group_id)?.canonical_name || item.group_id;
        return item.ownership_percentage ? `${name} (${item.ownership_percentage}%)` : name;
      })
      .join(" | ");
    return {
      place_id: centre.place_id, place_name: centre.name, rank: row.rank ?? "", lookalike_score: row.score ?? "",
      screening_completeness_pct: row.screening_completeness ?? "",
      footprint_similarity: row.components?.bailey_footprint_similarity ?? "", bailey_whitespace: row.components?.bailey_whitespace ?? "",
      optical_validation: row.components?.optical_market_validation ?? "", retail_context: row.components?.accessibility_retail_context ?? "",
      location_setting: centre.location_setting, place_type: centre.place_type || "", country: centre.country, state: centre.state, locality: centre.locality || centre.suburb || "", postcode: centre.postcode || "", address: centre.address || "",
      latitude: centre.latitude ?? "", longitude: centre.longitude ?? "", bailey_nelson_present: centre.has_bailey ? "Yes" : "No",
      mapping_confidence: centre.mapping_confidence || centre.confidence || "", research_status: centre.research_status || "Not researched",
      nearest_bailey_km: row.nearest_bailey_km ?? centre.nearest_bailey_km ?? "", population_2025: market.population_2025 ?? "",
      population_growth_2021_2025_pct: market.population_growth_2021_2025_pct ?? "", age_45_plus_pct_2021: market.age_45_plus_pct_2021 ?? "",
      median_equivalised_household_income_weekly_2021: market.median_equivalised_household_income_weekly_2021 ?? "", centre_class: centre.location_setting === "High Street" ? "Not applicable at corridor level" : centre.centre_class || "Unknown",
      centre_class_method: centre.location_setting === "High Street" ? "" : centre.centre_class_method || "", centre_class_confidence: centre.location_setting === "High Street" ? "" : centre.centre_class_evidence?.confidence || "",
      property_groups: centre.location_setting === "High Street" ? "" : propertyGroupNames(centre).join(" | "), owners: relationshipNames("OWNER"), co_owners: relationshipNames("CO_OWNER"),
      managers: relationshipNames("MANAGER"), operators: relationshipNames("OPERATOR"), leasing_controllers: relationshipNames("LEASING_CONTROLLER"), external_leasing_agents: relationshipNames("EXTERNAL_LEASING_AGENT"),
      leasing_arrangement: centre.location_setting === "High Street" ? "Not applicable at corridor level" : centre.leasing_arrangement || "Unknown",
      portfolio_overlap: centre.location_setting === "High Street" ? "Not assessed at corridor level" : overlapLabel(centre.portfolio_overlap_status, "centre"),
      optical_store_count: centre.optical_store_count || 0, retailers: (centre.retailers || []).join(" | "),
      high_street_baseline_status: centre.location_setting === "High Street" && (state.placeTenantMetadata.researched_bailey_corridor_place_ids || []).includes(centre.place_id) ? "Baseline checked" : "",
      exact_place_optical_tenant_count: tenantsForPlace(centre.place_id).filter((row) => row.category === "Optical").length,
      key_cotenancy_count: evidence?.local_evidence ? evidence.observations.filter(o => o.role !== "Optical").length : tenantsForPlace(centre.place_id).filter((row) => row.category !== "Optical").length,
      evidence_snapshot: state.environments?.metadata?.snapshot_id || "public build",
      directory_optical_listings: evidence?.optical_reconciliation?.directory_listed_count ?? "Not assessed",
      optical_listing_reviews: evidence?.optical_reconciliation?.review_count ?? "Not assessed",
      directory_research_date: evidence?.local_evidence ? evidence.coverage.observed_dates?.at(-1) || "" : state.destinationResearch[centre.place_id]?.observed_at || "",
      directory_non_optical_listings: evidence?.local_evidence ? evidence.observations.filter(o => o.role !== "Optical").length : state.destinationResearch[centre.place_id]?.in_scope_non_optical_listings ?? "",
      directory_scope: evidence?.local_evidence ? evidence.scope : state.destinationResearch[centre.place_id]?.scope || "",
      gla_sqm: centre.gla_sqm || "", annual_visits: centre.annual_visits || "", retail_tenancy_count: centre.tenancy_count || "", trade_area_population: centre.trade_area_population || "",
      place_evidence_date: centre.source_date || "", place_last_verified_at: centre.last_verified_at || "", property_evidence_latest: verifiedDates.at(-1) || "", official_url: centre.official_url || centre.source_url || "",
    };
  }

  function exportRecords(filename, records) {
    if (!records.length) return showToast("No available places to export.", "warning");
    const fields = Object.keys(records[0]);
    const lines = [fields.join(","), ...records.map((record) => fields.map((field) => csvEscape(record[field])).join(","))];
    downloadText(filename, `${lines.join("\n")}\n`);
  }

  function exportPlaceSummary(placeIds) {
    const centres = [...new Set(placeIds.map(resolvePlaceId))].map((id) => state.centres.find((item) => item.place_id === id)).filter(Boolean);
    exportRecords(`bailey-place-summary-${new Date().toISOString().slice(0, 10)}.csv`, centres.map(placeSummaryRecord));
  }

  function exportPlaceTenants(placeIds) {
    const centres = [...new Set(placeIds.map(resolvePlaceId))].map((id) => state.centres.find((item) => item.place_id === id)).filter(Boolean);
    const records = centres.flatMap((centre) => {
      const evidence = state.environments?.places.find(p => p.place_id === centre.place_id && p.local_evidence);
      const listings = evidence ? evidence.observations.map(o => ({tenant_id:o.source_id, tenant_name:o.name, category:o.role === "Optical" ? "Optical directory listing" : (o.categories || []).join(" | "), selection_basis:o.scope_basis, status:"Directory listed; trading not independently verified", source_url:o.source_url, source_type:"Captured directory evidence", source_date:o.source_date, verified_at:o.observed_at, confidence:"Documented presence"})) : tenantsForPlace(centre.place_id);
      return listings.map((tenant) => ({
      place_id: centre.place_id, place_name: centre.name, country: centre.country, state: centre.state,
      membership_type: evidence ? "Captured directory listing; census link assessed separately" : tenant.category === "Optical" ? "Accepted exact-place optical membership" : "Researched key co-tenant",
      tenant_id: tenant.tenant_id, tenant_name: tenant.tenant_name, retailer: tenant.retailer || "", category: tenant.category,
      anchor_flag: tenant.anchor_flag ? "true" : "false", selection_basis: tenant.selection_basis, status: tenant.status,
      source_url: tenant.source_url, source_type: tenant.source_type, source_date: tenant.source_date || "", verified_at: tenant.verified_at, confidence: tenant.confidence,
    })); });
    exportRecords(`bailey-place-tenants-${new Date().toISOString().slice(0, 10)}.csv`, records);
  }

  function propertyCorrectionEditorHtml(centre, relationships) {
    const groupOptions = state.propertyGroups.slice().sort((a, b) => a.canonical_name.localeCompare(b.canonical_name))
      .map((group) => `<option value="${escapeHtml(group.group_id)}">${escapeHtml(group.canonical_name)}</option>`).join("");
    return `<section class="detail-section property-editor"><h3>Local public-data correction</h3>
      <p class="empty-note">Saved only in this browser. Export the CSV to share it; private contacts and commercial terms are prohibited.</p>
      <form id="centreClassCorrectionForm" class="correction-grid">
        <label><span>Centre class</span><select name="centre_class">${filterOptions(["Super Regional", "Regional", "Sub-regional", "Neighbourhood", "CBD / Mixed-use", "Outlet", "Large Format", "Other", "Unknown"], centre.centre_class || "Unknown", "Class")}</select></label>
        <label><span>Method</span><select name="classification_method">${filterOptions(["Confirmed", "Inferred", "Manual"], centre.centre_class_method || "Manual", "Method")}</select></label>
        <label><span>Confidence</span><select name="confidence">${filterOptions(["High", "Medium", "Low"], centre.centre_class_evidence?.confidence || "Medium", "Confidence")}</select></label>
        <label class="wide"><span>Public evidence URL</span><input name="source_url" type="url" value="${escapeHtml(centre.centre_class_evidence?.source_url || "")}" placeholder="https://…" /></label>
        <button class="detail-action" type="submit">Save centre class</button>
      </form>
      <form id="relationshipCorrectionForm" class="correction-grid">
        <input name="record_id" type="hidden" />
        <label><span>Role</span><select name="role">${filterOptions(["OWNER", "CO_OWNER", "MANAGER", "OPERATOR", "LEASING_CONTROLLER", "EXTERNAL_LEASING_AGENT"], "", "Choose role")}</select></label>
        <label><span>Canonical group</span><select name="group_id"><option value="">Choose group</option>${groupOptions}</select></label>
        <label><span>Ownership % (owners only)</span><input name="ownership_percentage" type="number" min="0.01" max="100" step="0.01" /></label>
        <label><span>Confidence</span><select name="confidence">${filterOptions(["High", "Medium", "Low"], "Medium", "Confidence")}</select></label>
        <label class="wide"><span>Public evidence URL</span><input name="source_url" type="url" required placeholder="https://…" /></label>
        <label class="wide"><span>Public note</span><input name="public_note" maxlength="240" placeholder="Public evidence only; no contacts or commercial terms" /></label>
        <button class="detail-action" type="submit">Add or update relationship</button>
        <button class="detail-action" id="resetRelationshipForm" type="button">Clear edit</button>
      </form>
      <details><summary>Add a canonical public group</summary>
        <form id="newPropertyGroupForm" class="correction-grid">
          <label><span>Canonical name</span><input name="canonical_name" required /></label>
          <label><span>Brand name</span><input name="brand_name" /></label>
          <label><span>Group type</span><select name="group_type">${filterOptions(["PROPERTY_COMPANY", "INVESTMENT_VEHICLE", "ASSET_MANAGER", "CENTRE_OPERATOR", "EXTERNAL_AGENCY", "PRIVATE_LANDLORD", "OTHER"], "OTHER", "Type")}</select></label>
          <label><span>Aliases (separate with |)</span><input name="aliases" /></label>
          <label class="wide"><span>Official public URL</span><input name="source_url" type="url" required /></label>
          <button class="detail-action" type="submit">Create local canonical group</button>
        </form>
      </details>
    </section>`;
  }

  function openCentreDetail(centre) {
    if (!centre) return;
    beginInspection();
    state.selectedStoreId = "";
    state.selectedCentreId = centre.place_id;
    const relationships = state.propertyRelationships.filter(
      (item) => item.place_id === centre.place_id && Intel.activeRelationship(item)
    );
    const publicUrl = centre.official_url || centre.source_url || centre.public_url;
    const isCorridor = centre.location_setting === "High Street";
    const placeLabel = isCorridor ? "corridor" : "centre";
    const saved = state.placeShortlist.has(resolvePlaceId(centre.place_id));
    const localEvidence = state.environments?.places.find(p => p.place_id === centre.place_id && p.local_evidence);
    elements.detailContent.innerHTML = `<div class="place-detail-content">
      <header class="detail-header" style="--brand-color:#d29b27">
        <span class="retailer-tag">${centre.location_setting === "High Street" ? '<i data-lucide="route"></i>' : CENTRE_BAG_SVG}${escapeHtml(centre.place_type)}</span>
        <h2>${escapeHtml(centre.name)}</h2><address>${escapeHtml(state.destinationProfiles?.[centre.place_id]?.display_address || state.environments?.places.find(p => p.place_id === centre.place_id)?.address || `${centre.locality || centre.suburb}, ${centre.state} · centre address not yet sourced`)}</address>
        <div class="link-row place-primary-actions">
          <button class="detail-action ${saved ? "saved" : ""}" id="detailShortlist" type="button" aria-pressed="${saved}" title="${saved ? 'Remove from shortlist' : 'Add to shortlist'}"><i data-lucide="bookmark${saved ? "-check" : ""}"></i>${saved ? "Shortlisted ✓" : "Add to shortlist"}</button>
          <button class="detail-action primary" id="explorePlaceOpportunity" type="button" aria-describedby="explorePlaceHint"><i data-lucide="arrow-right"></i>${isMapView() ? 'Explore opportunity' : 'Compare this place'}</button>
        </div>
        <p class="place-action-hint" id="explorePlaceHint">Carry this place into Compare, then add another place or a point on the map.</p>
        <div class="place-utility-row">
          <details class="place-export-menu"><summary><i data-lucide="download" aria-hidden="true"></i><span>Export…</span><i data-lucide="chevron-down" aria-hidden="true"></i></summary>
            <div class="place-export-options" role="group" aria-label="Export options">
              <button id="placeReport" type="button"><i data-lucide="printer" aria-hidden="true"></i>Print brief</button>
              <button id="placeSummaryCsv" type="button"><i data-lucide="file-spreadsheet" aria-hidden="true"></i>Summary CSV</button>
              <button id="placeTenantCsv" type="button"><i data-lucide="list" aria-hidden="true"></i>Tenant CSV</button>
            </div>
          </details>
          ${publicUrl ? `<a class="place-source-link" href="${escapeHtml(publicUrl)}" target="_blank" rel="noopener">Public source <i data-lucide="external-link" aria-hidden="true"></i></a>` : ""}
        </div>
      </header>
      ${localEvidence ? window.EnvironmentExplorer.evidencePanel(localEvidence) : visualDestinationProfile(centre)}
      ${researchedPropertyHtml(centre)}
      ${researchedMetricsHtml(centre)}
      ${opportunitySummaryHtml(centre)}
      <section class="detail-section"><h3>Optical competition context</h3>${competitorContextHtml(centre)}
        <p class="empty-note">${isMapView() ? "The map keeps your applied store and retail-place filters." : "The map is focused on the competition shown above."} IN ${isCorridor ? "CORRIDOR" : "CENTRE"} requires the same accepted canonical place ID; distance alone never establishes membership.</p>
      </section>
      ${localEvidence ? "" : highStreetProfileHtml(centre)}
      ${localEvidence || centre.place_id === "place-au-nsw-ed-square-town-centre" ? "" : destinationResearchHtml(centre) || `<section class="detail-section"><h3>Key co-tenancy profile</h3>${keyCoTenancyHtml(centre)}</section>`}
      ${developmentSignalsHtml(centre)}
      ${isCorridor ? `<section class="detail-section"><h3>High-street place context</h3><div class="data-grid property-summary-grid">
          <div class="data-point"><span>Place type</span><strong>High Street Corridor</strong></div>
          <div class="data-point"><span>Property intelligence</span><strong>Not assessed at corridor level</strong></div>
        </div><p class="empty-note">Centre class, ownership and leasing control describe an individual property. They are not applied to an entire street corridor.</p></section>` : `${state.destinationProfiles?.[centre.place_id]?.completion_review ? "" : `<section class="detail-section"><h3>Ownership, management and leasing</h3>
        <div class="data-grid property-summary-grid">
          <div class="data-point"><span>Centre class</span><strong>${escapeHtml(centre.centre_class || "Unknown")}</strong><small>${escapeHtml(centre.centre_class_method || "Not confirmed")}</small></div>
          <div class="data-point"><span>Leasing arrangement</span><strong>${escapeHtml(centre.leasing_arrangement || "Unknown")}</strong></div>
        </div>${relationshipCardsHtml(relationships)}</section>`}
      <section class="detail-section portfolio-overlap"><h3>Bailey Nelson portfolio overlap</h3>
        <strong>${escapeHtml(state.destinationProfiles?.[centre.place_id]?.completion_review && centre.portfolio_overlap_status === "UNKNOWN" ? "Not established in the mapped public portfolio" : overlapLabel(centre.portfolio_overlap_status, placeLabel))}</strong>
        <p>${centre.portfolio_overlap_groups?.length ? centre.portfolio_overlap_groups.map((item) => `${escapeHtml(item.canonical_name)} (${escapeHtml(relationshipRoleLabel(item.role))}): ${item.bailey_store_count} Bailey store${item.bailey_store_count === 1 ? "" : "s"} across ${item.bailey_property_count} propert${item.bailey_property_count === 1 ? "y" : "ies"}`).join("<br>") : "No evidenced public portfolio overlap is available."}</p>${state.destinationProfiles?.[centre.place_id]?.completion_review && centre.portfolio_overlap_status === "UNKNOWN" ? `<p>Reported owners and manager are now recorded. Establishing a Bailey Nelson overlap also requires accepted store membership and property relationships at other centres; absence here does not establish no relationship.</p>` : ""}
        <small>Portfolio overlap is derived from public property and tenancy evidence. It is not proof of a private commercial relationship.</small>
      </section>`}
      ${state.destinationProfiles?.[centre.place_id]?.completion_review ? "" : `<section class="detail-section"><h3>Public ${isCorridor ? "corridor" : "centre"} metrics</h3><div class="data-grid">
        ${isCorridor ? `<div class="data-point"><span>Comparison boundary</span><strong>Named street and locality</strong></div>
        <div class="data-point"><span>Exact mapped optical stores</span><strong>${formatNumber(centre.optical_store_count || 0)}</strong></div>` : `<div class="data-point"><span>Total GLA</span><strong>${centre.gla_sqm ? formatNumber(centre.gla_sqm, " sqm") : "Not yet sourced"}</strong></div>
        <div class="data-point"><span>Annual visits</span><strong>${formatNumber(centre.annual_visits)}</strong></div>
        <div class="data-point"><span>Retail tenancies</span><strong>${formatNumber(centre.tenancy_count)}</strong></div>
        <div class="data-point"><span>Trade area population</span><strong>${formatNumber(centre.trade_area_population)}</strong></div>`}
        <div class="data-point"><span>Nearest Bailey Nelson</span><strong>${Number.isFinite(Number(centre.nearest_bailey_km)) ? Intel.formatDistance(Number(centre.nearest_bailey_km)) : "Unknown"}</strong></div>
      </div>${!isCorridor ? publicMetricSourcesHtml(centre) : ""}</section>`}
      ${state.destinationProfiles?.[centre.place_id]?.completion_review ? `<section class="detail-section"><h3>Research limits and next steps</h3><ul class="profile-research-gaps">${state.destinationProfiles[centre.place_id].limitations.map(x => `<li>${escapeHtml(x)}</li>`).join('')}</ul></section>` : ''}
      ${centre.coordinate_confidence ? `<section class="detail-section"><h3>Map position</h3><p class="empty-note">${escapeHtml(centre.coordinate_confidence)} confidence. ${escapeHtml(centre.coordinate_reason || "Approximate property reference point.")}</p></section>` : ''}
      <details class="technical-details"><summary>Sources, methodology and public corrections</summary>
        <section class="detail-section source-block"><div><strong>${escapeHtml(centre.source_basis || 'Best available public place record')}</strong><p>${centre.source_date ? `Place evidence dated ${escapeHtml(formatDate(centre.source_date))}` : 'See the dated evidence beside each researched claim.'}</p></div></section>
        <section class="detail-section"><h3>Technical record</h3><div class="data-grid">
          <div class="data-point"><span>Canonical place ID</span><strong>${escapeHtml(centre.place_id)}</strong></div>
          <div class="data-point"><span>Mapping confidence</span><strong>${escapeHtml(centre.mapping_confidence || centre.confidence)}</strong></div>
          <div class="data-point"><span>Research status</span><strong>${escapeHtml(centre.research_status || 'Not researched')}</strong></div>
          <div class="data-point"><span>Place type</span><strong>${escapeHtml(centre.location_setting)}</strong></div>
        </div><p class="empty-note">The canonical place ID joins stores, property facts and corrections without relying on changing names.</p></section>
        ${centre.place_id === 'place-au-nsw-ed-square-town-centre' ? '<section class="detail-section"><a href="data/destination_profiles.html" target="_blank" rel="noopener">Full research profiles and sources ↗</a></section>' : ''}
        ${isCorridor ? '<p class="empty-note">Property ownership and centre-class corrections are available for shopping-centre records only.</p>' : propertyCorrectionEditorHtml(centre, relationships)}
      </details></div>`;
    openDetailPanel();
    bindNearRows();
    bindPropertyDetail(centre, relationships);
    bindPlaceDirectory(centre);
    const exportMenu = elements.detailContent.querySelector('.place-export-menu');
    exportMenu.addEventListener('keydown', event => {
      if (event.key === 'Escape') {
        exportMenu.open = false;
        exportMenu.querySelector('summary').focus();
        event.stopPropagation();
      }
    });
    exportMenu.addEventListener('focusout', event => {
      if (!exportMenu.contains(event.relatedTarget)) exportMenu.open = false;
    });
    exportMenu.querySelectorAll('button').forEach(button => button.addEventListener('click', () => {
      exportMenu.open = false;
      exportMenu.querySelector('summary').focus();
    }));
    document.getElementById("detailShortlist")?.addEventListener("click", (event) => {
      event.preventDefault();
      event.currentTarget.disabled = true;
      togglePlaceShortlist(centre.place_id);
    });
    document.getElementById("placeReport")?.addEventListener("click", () => generatePlaceReport(centre));
    document.getElementById("explorePlaceOpportunity")?.addEventListener("click", () => {
      const placeId = resolvePlaceId(centre.place_id);
      state.placeShortlist.add(placeId);
      persistPlaceShortlist();
      addPlaceToComparison(centre);

    });
    document.getElementById("placeSummaryCsv")?.addEventListener("click", () => exportPlaceSummary([centre.place_id]));
    document.getElementById("placeTenantCsv")?.addEventListener("click", async (event) => {
      if (!state.destinationResearch[centre.place_id]) return exportPlaceTenants([centre.place_id]);
      const button = event.currentTarget;
      button.disabled = true;
      try {
        const directory = await loadJson('data/destination_directory.json');
        const rows = (directory.records || []).filter(row => row.place_id === centre.place_id);
        if (!rows.length) return showToast('No directory listings are available for this place.', 'warning');
        exportRecords('place-directory.csv', rows.map(row => ({
          place_id: row.place_id, place_name: centre.name, source_record_id: row.source_record_id,
          name: row.display_name, categories: (row.categories || []).join('; '),
          location: row.source_location || '', scope_status: row.scope_status,
          listing_status: row.listing_status, source_url: row.source_url,
          observed_at: row.observed_at, source_effective_date: row.source_effective_date || '',
          research_notes: (row.exceptions || []).join('; ')
        })));
        showToast(`Download requested: ${rows.length} directory listings.`);
      } catch (error) {
        showToast('The directory could not be loaded. Please try again.', 'warning');
      } finally { button.disabled = false; }
    });
    if (!isMapView()) focusPlaceOnMap(centre);
  }

  let destinationDirectoryPromise;
  function bindPlaceDirectory(centre) {
    elements.detailContent.querySelectorAll('[data-directory-category]').forEach(disclosure => {
      const body = disclosure.querySelector('.category-directory-body');
      let loading = false;
      let loaded = false;
      disclosure.addEventListener('toggle', async () => {
        if (!disclosure.open || loading || loaded) return;
        loading = true;
        body.innerHTML = '<p role="status">Loading co-tenants…</p>';
        try {
          destinationDirectoryPromise ||= loadJson('data/destination_directory.json').catch(error => {
            destinationDirectoryPromise = null;
            throw error;
          });
          const directory = await destinationDirectoryPromise;
          if (!body.isConnected) return;
          const rows = (directory.records || []).filter(row => row.place_id === centre.place_id
            && row.scope_status === 'In declared research scope'
            && row.listing_status === 'Directory listed; trading not independently checked'
            && row.role !== 'Optical'
            && (row.categories || []).includes(disclosure.dataset.directoryCategory))
            .sort((a, b) => a.display_name.localeCompare(b.display_name));
          body.innerHTML = `<ul class="directory-listings">${rows.map(row => `<li><a href="${escapeHtml(row.source_url)}" target="_blank" rel="noopener">${escapeHtml(row.display_name)} ↗</a>${(row.exceptions || []).length ? `<small>${escapeHtml(row.exceptions.join('; '))}</small>` : ''}</li>`).join('')}</ul>`;
          loaded = true;
        } catch (error) {
          body.innerHTML = '<p role="status">Could not load co-tenants. Close and reopen to retry.</p>';
        } finally { loading = false; }
      });
    });
    const disclosure = document.getElementById('placeDirectory');
    const body = document.getElementById('placeDirectoryBody');
    if (!disclosure || !body) return;
    let loading = false;
    let loaded = false;
    disclosure.addEventListener('toggle', async () => {
      if (!disclosure.open || loading || loaded) return;
      loading = true;
      body.innerHTML = '<p role="status">Loading directory…</p>';
      try {
        destinationDirectoryPromise ||= loadJson('data/destination_directory.json').catch(error => {
          destinationDirectoryPromise = null;
          throw error;
        });
        const directory = await destinationDirectoryPromise;
        if (!body.isConnected) return;
        const rows = (directory.records || []).filter(row => row.place_id === centre.place_id)
          .sort((a, b) => a.display_name.localeCompare(b.display_name));
        const categories = [...new Set(rows.flatMap(row => row.categories || []))].sort();
        body.innerHTML = `<p class="profile-evidence-note">Directory captured ${escapeHtml(formatDate(directory.metadata.observed_at))}. Listings include businesses and services; current trading and occupied tenancies are not independently verified.</p>
          <label class="directory-filter">Find a co-tenant<input id="directorySearch" type="search" placeholder="Business or service name" /></label>
          <label class="directory-filter">Category<select id="directoryCategory"><option value="">All categories</option>${categories.map(category => `<option>${escapeHtml(category)}</option>`).join('')}</select></label>
          <p id="directoryCount" role="status" aria-live="polite"></p><ul id="directoryListings" class="directory-listings"></ul>`;
        const search = body.querySelector('#directorySearch');
        const category = body.querySelector('#directoryCategory');
        const render = () => {
          const query = search.value.trim().toLocaleLowerCase();
          const matches = rows.filter(row => row.display_name.toLocaleLowerCase().includes(query) && (!category.value || (row.categories || []).includes(category.value)));
          body.querySelector('#directoryCount').textContent = `${matches.length} of ${rows.length} listings`;
          body.querySelector('#directoryListings').innerHTML = matches.length ? matches.map(row => `<li><a href="${escapeHtml(row.source_url)}" target="_blank" rel="noopener">${escapeHtml(row.display_name)} ↗</a><span>${escapeHtml((row.categories || []).join(' · ') || 'Unclassified')}${row.source_location ? ` · ${escapeHtml(row.source_location)}` : ''}</span>${row.canonical_optical_store_id ? '<small>Mapped optical business</small>' : ''}${(row.exceptions || []).length ? `<small>Research note: ${escapeHtml(row.exceptions.join('; '))}</small>` : ''}</li>`).join('') : '<li>No matching directory listings. Try another name or category.</li>';
        };
        search.addEventListener('input', render);
        category.addEventListener('change', render);
        render();
        loaded = true;
      } catch (error) {
        body.innerHTML = '<p role="status">Directory could not be loaded. Close and reopen this section to retry.</p>';
      } finally {
        loading = false;
      }
    });
  }

  function bindPropertyDetail(centre, relationships) {
    elements.detailContent.querySelectorAll("[data-property-group-id]").forEach((button) => {
      button.addEventListener("click", () => openPropertyGroupDetail(button.dataset.propertyGroupId));
    });
    const relationshipForm = document.getElementById("relationshipCorrectionForm");
    elements.detailContent.querySelectorAll("[data-edit-property-relationship]").forEach((button) => {
      button.addEventListener("click", () => {
        const relationship = relationships.find((item) => item.relationship_id === button.dataset.editPropertyRelationship);
        if (!relationship || !relationshipForm) return;
        Object.entries({
          record_id: relationship.relationship_id, role: relationship.role, group_id: relationship.group_id,
          ownership_percentage: relationship.ownership_percentage ?? "", confidence: relationship.confidence,
          source_url: relationship.source_url, public_note: relationship.public_note || "",
        }).forEach(([key, value]) => { relationshipForm.elements[key].value = value; });
        relationshipForm.scrollIntoView({ behavior: "smooth", block: "center" });
      });
    });
    elements.detailContent.querySelectorAll("[data-remove-property-relationship]").forEach((button) => {
      button.addEventListener("click", () => {
        persistPropertyCorrection({
          correction_type: "ASSET_RELATIONSHIP", action: "REMOVE",
          record_id: button.dataset.removePropertyRelationship, place_id: centre.place_id,
          verified_at: new Date().toISOString().slice(0, 10),
        });
        openCentreDetail(state.centres.find((item) => item.place_id === centre.place_id));
      });
    });
    document.getElementById("centreClassCorrectionForm")?.addEventListener("submit", (event) => {
      event.preventDefault();
      const fields = Object.fromEntries(new FormData(event.currentTarget));
      if (containsPrivatePropertyData(fields)) return showToast("Correction blocked: public property data only", "warning");
      persistPropertyCorrection({
        correction_type: "PROPERTY_ATTRIBUTE", action: "UPSERT", record_id: `attribute-${centre.place_id}`,
        place_id: centre.place_id, centre_class: fields.centre_class, classification_method: fields.classification_method,
        confidence: fields.confidence, source_url: fields.source_url, public_note: "Local public centre-class correction",
        verified_at: new Date().toISOString().slice(0, 10),
      });
      showToast("Centre class saved locally");
      openCentreDetail(state.centres.find((item) => item.place_id === centre.place_id));
    });
    relationshipForm?.addEventListener("submit", (event) => {
      event.preventDefault();
      const fields = Object.fromEntries(new FormData(event.currentTarget));
      if (!fields.role || !fields.group_id || !fields.source_url) return showToast("Choose a role and group and add a public evidence URL", "warning");
      if (containsPrivatePropertyData(fields)) return showToast("Correction blocked: public property data only", "warning");
      const recordId = fields.record_id || `local-rel-${placeSlug(centre.place_id)}-${placeSlug(fields.group_id)}-${fields.role.toLowerCase()}-${Date.now().toString(36)}`;
      persistPropertyCorrection({
        correction_type: "ASSET_RELATIONSHIP", action: "UPSERT", record_id: recordId,
        place_id: centre.place_id, group_id: fields.group_id, role: fields.role,
        ownership_percentage: fields.ownership_percentage, confidence: fields.confidence,
        source_url: fields.source_url, public_note: fields.public_note,
        verified_at: new Date().toISOString().slice(0, 10),
      });
      showToast("Property relationship saved locally");
      openCentreDetail(state.centres.find((item) => item.place_id === centre.place_id));
    });
    document.getElementById("resetRelationshipForm")?.addEventListener("click", () => relationshipForm?.reset());
    document.getElementById("newPropertyGroupForm")?.addEventListener("submit", (event) => {
      event.preventDefault();
      const fields = Object.fromEntries(new FormData(event.currentTarget));
      if (containsPrivatePropertyData(fields)) return showToast("Group blocked: public property data only", "warning");
      const groupId = `group-local-${placeSlug(fields.canonical_name)}`;
      if (state.propertyGroups.some((group) => group.group_id === groupId)) return showToast("That canonical group already exists", "warning");
      state.localPropertyGroups.push({
        group_id: groupId, canonical_name: fields.canonical_name, brand_name: fields.brand_name || "",
        parent_group_id: "", group_type: fields.group_type, aliases: (fields.aliases || "").split("|").map((item) => item.trim()).filter(Boolean),
        official_url: fields.source_url, source_url: fields.source_url, last_verified_at: new Date().toISOString().slice(0, 10),
        confidence: "Medium", status: "Active", local_created: true,
      });
      localStorage.setItem(LOCAL_PROPERTY_GROUP_STORAGE_KEY, JSON.stringify(state.localPropertyGroups));
      applyPropertyCorrections();
      showToast("Canonical group created locally");
      openCentreDetail(state.centres.find((item) => item.place_id === centre.place_id));
    });
  }

  function openPropertyGroupDetail(groupId) {
    const group = propertyGroup(groupId);
    if (!group) return;
    const portfolio = state.groupPortfolios[groupId] || {};
    const relationships = state.propertyRelationships.filter((item) => item.group_id === groupId && Intel.activeRelationship(item));
    const assetRows = [...new Set(relationships.map((item) => item.place_id))].map((placeId) => {
      const place = state.centres.find((item) => item.place_id === placeId);
      const roles = relationships.filter((item) => item.place_id === placeId).map((item) => relationshipRoleLabel(item.role));
      return { place, roles };
    }).filter((item) => item.place);
    elements.detailContent.innerHTML = `<header class="detail-header" style="--brand-color:#775d9b">
      <span class="retailer-tag"><i data-lucide="landmark"></i>Property group</span><h2>${escapeHtml(group.canonical_name)}</h2>
      <address>${escapeHtml(group.group_type.replaceAll("_", " "))}${group.parent_group_id ? ` · Parent: ${escapeHtml(propertyGroup(group.parent_group_id)?.canonical_name || group.parent_group_id)}` : ""}</address>
      <div class="link-row"><a class="command-link primary" href="${escapeHtml(group.official_url || group.source_url)}" target="_blank" rel="noopener">Official public source</a></div>
    </header>
    <section class="detail-section"><h3>Portfolio overlap</h3><div class="data-grid">
      <div class="data-point"><span>Matched properties</span><strong>${formatNumber(portfolio.property_count || 0)}</strong></div>
      <div class="data-point"><span>Bailey properties</span><strong>${formatNumber(portfolio.bailey_property_count || 0)}</strong></div>
      <div class="data-point"><span>Mapped Bailey stores</span><strong>${formatNumber(portfolio.bailey_store_count || 0)}</strong></div>
      <div class="data-point"><span>Bailey-free overlap assets</span><strong>${formatNumber(portfolio.white_space_property_ids?.length || 0)}</strong></div>
    </div><p class="empty-note">Aliases: ${escapeHtml((group.aliases || []).join(", ") || "None recorded")}</p></section>
    <section class="detail-section"><h3>Complete matched public portfolio</h3><div class="group-portfolio-list">${assetRows.length ? assetRows.sort((a, b) => a.place.name.localeCompare(b.place.name)).map((item) => `<button data-group-place-id="${escapeHtml(item.place.place_id)}"><span><strong>${escapeHtml(item.place.name)}</strong><small>${escapeHtml(item.roles.join(", "))}</small></span><b>${item.place.has_bailey ? "BN present" : item.place.portfolio_white_space ? "white space" : "BN absent"}</b></button>`).join("") : '<p class="empty-note">No matched public assets yet.</p>'}</div></section>
    <section class="detail-section source-block"><i data-lucide="shield-check"></i><div><strong>${escapeHtml(group.confidence || "Unknown")} confidence group identity</strong><span>Verified ${escapeHtml(formatDate(group.last_verified_at))}</span></div></section>`;
    openDetailPanel();
    elements.detailContent.querySelectorAll("[data-group-place-id]").forEach((button) => {
      button.addEventListener("click", () => openCentreDetail(state.centres.find((item) => item.place_id === button.dataset.groupPlaceId)));
    });
  }

  function marketForStore(store) {
    const link = state.storeLinks[store.store_id];
    return link ? state.markets.find((feature) => feature.properties.sa2_code === link.sa2_code) || null : null;
  }

  function marketForPoint(point) {
    return Intel.findMarketFeature(point, state.markets, state.marketPointLinks || {});
  }

  function marketLabel(candidate) {
    const market = marketForPoint(candidate);
    return market ? `${market.properties.sa2_name}, ${market.properties.state}` : "Market area not matched";
  }

  function selectedProfile(candidate) {
    return (
      state.profiles.find((profile) => profile.id === candidate.profile_id) ||
      state.profiles.find((profile) => profile.id === "generic-optical")
    );
  }

  function scoreCandidate(candidate) {
    const certifiedStores = state.allStores.filter((store) => store.eligible_for_analytics);
    return Intel.candidateScore({
      point: candidate,
      stores: certifiedStores,
      markets: state.markets,
      market: marketForPoint(candidate),
      centres: state.centres,
      profile: selectedProfile(candidate),
      areaSqm: candidate.area_sqm,
      targetAreaMin: candidate.target_min_sqm,
      targetAreaMax: candidate.target_max_sqm,
      amenitySummary: candidate.amenity_summary || null,
      placeId: candidate.place_id || "",
    });
  }

  function openCandidateDetail(candidate) {
    state.selectedCandidateId = candidate.id;
    const model = scoreCandidate(candidate);
    const market = marketForPoint(candidate);
    const proximity = proximityModel(candidate, null, true);
    const catchments = CATCHMENT_RADII.map((radius) => Intel.catchmentSummary(candidate, radius, state.markets));
    drawCandidateCatchments(candidate);
    elements.detailContent.innerHTML = `
      <header class="detail-header candidate-header" style="--brand-color:#a24f93">
        <span class="retailer-tag"><i data-lucide="map-pin-plus"></i>Candidate site</span>
        <h2>${escapeHtml(candidate.name)}</h2><address>${candidate.latitude.toFixed(5)}, ${candidate.longitude.toFixed(5)} · ${escapeHtml(
      marketLabel(candidate)
    )}</address>
      </header>
      <section class="score-section">
        <div class="score-ring ${model.reliable ? "" : "low-coverage"}" style="--score:${model.score || 0}">
          <strong>${model.score ?? "-"}</strong><span>screening index</span>
        </div>
        <div><strong>${model.coverage}% screening completeness</strong>
          <p><strong>Screening index:</strong> a 0–100 comparison of available public evidence for this manual site, including demand, competition, verified centre context, accessibility, network spacing and tenancy-size fit. It is not a sales forecast.</p>
          <p>${model.reliable ? "The index meets the 70% completeness threshold." : "Directional only. Required evidence is unavailable."}</p>
          <span class="confidence">${model.reliable ? "Screening complete" : "Low completeness"}</span>
        </div>
      </section>
      <section class="detail-section"><h3>Score components</h3>${scoreComponentsHtml(model)}</section>
      <section class="detail-section"><h3>Format and place</h3>
        <div class="data-grid">
          <div class="data-point"><span>Available area</span><strong>${candidate.area_sqm ? `${escapeHtml(candidate.area_sqm)} sqm` : "Unknown"}</strong></div>
          <div class="data-point"><span>Brand profile</span><strong>${escapeHtml(selectedProfile(candidate).name)}</strong></div>
          <div class="data-point"><span>Target range</span><strong>${
            candidate.target_min_sqm && candidate.target_max_sqm
              ? `${escapeHtml(candidate.target_min_sqm)}–${escapeHtml(candidate.target_max_sqm)} sqm`
              : "Not configured"
          }</strong></div>
          <div class="data-point"><span>Nearest centre</span><strong>${escapeHtml(
            model.nearestCentre?.centre.name || "No verified place selected"
          )}</strong></div>
          <div class="data-point"><span>Nearby centre lead</span><strong>${escapeHtml(
            model.nearbyCentreLead?.centre.name || "None within 750 m"
          )}</strong></div>
        </div>
      </section>
      ${market ? marketEvidenceHtml(market.properties) : ""}
      <section class="detail-section"><h3>Catchment estimates</h3>${catchmentTableHtml(catchments)}
        <p class="empty-note">Population is apportioned by the share of each SA2 polygon inside the straight-line radius. It assumes population is evenly distributed within each SA2 and is not a drive-time or customer-origin trade area.</p>
      </section>
      <section class="detail-section"><h3>Nearest brand places within 100 km</h3><div class="proximity-summary">${nearestBrandHtml(
        proximity, { maxDistanceKm: MAX_CANDIDATE_BRAND_DISTANCE_KM, sortByDistance: true }
      )}</div>${radiusTableHtml(proximity)}</section>
      <section class="detail-section"><div class="button-row">
        <button class="detail-action primary" id="candidateReport" type="button"><i data-lucide="file-down"></i>Client report</button>
        <button class="detail-action" id="removeCandidate" type="button"><i data-lucide="trash-2"></i>Remove</button>
      </div></section>
      <section class="detail-section source-block"><i data-lucide="shield-check"></i><div><strong>Sanitised public candidate</strong>
        <span>No rent, landlord contact, negotiation or private note is stored in this public site.</span></div></section>`;
    openDetailPanel();
    document.getElementById("candidateReport").addEventListener("click", () => generateReport(candidate));
    document.getElementById("removeCandidate").addEventListener("click", () => removeCandidate(candidate.id));
    renderCandidateDock();
  }

  function scoreComponentsHtml(model) {
    const labels = {
      market_demand: "Market demand",
      competitive_white_space: "Competitive white space",
      centre_strength: "Centre / precinct strength",
      accessibility: "Accessibility",
      network_fit: "Network fit",
      format_fit: "Format fit",
    };
    return `<div class="score-components">${Object.entries(labels)
      .map(([key, label]) => {
        const value = model.components[key];
        return `<div><span>${escapeHtml(label)}<small>${model.weights[key]}% weight</small></span>${
          value !== null && value !== undefined && value !== "" && Number.isFinite(Number(value))
            ? `<b>${Math.round(Number(value))}</b><i><em style="width:${Math.round(Number(value))}%"></em></i>`
            : `<b class="not-scored">N/A</b><i><em style="width:0"></em></i>`
        }</div>`;
      })
      .join("")}</div>`;
  }

  function catchmentTableHtml(catchments) {
    return `<table class="radius-table"><thead><tr><th>Radius</th><th>Population</th><th>Age 45+</th><th>Weekly income</th></tr></thead>
      <tbody>${catchments
        .map(
          (item) => `<tr><td>${item.radiusKm} km</td><td>${formatNumber(item.population)}</td><td>${formatNumber(
            item.age45PlusPct,
            "%"
          )}</td><td>${item.medianHouseholdIncomeWeekly ? `$${formatNumber(Math.round(item.medianHouseholdIncomeWeekly))}` : "N/A"}</td></tr>`
        )
        .join("")}</tbody></table>`;
  }

  function openDetailPanel() {
    if (state.view === "overview") setView("centres");
    document.getElementById("backToResults").hidden = exploration.panel !== "detail-from-results";
    elements.detailPanel.inert = false;
    if (isMapView() && exploration.panel !== 'results') {
      selectionLayer.clearLayers();
      const selected = state.allStores.find(row => row.store_id === state.selectedStoreId) || state.centres.find(row => row.place_id === state.selectedCentreId);
      if (selected && selected.status !== "Closed" && selected.latitude != null && selected.longitude != null) L.circleMarker([selected.latitude,selected.longitude], {radius:22,weight:3,color:'#006d77',fill:false,interactive:false}).addTo(selectionLayer);
      elements.detailPanel.scrollTop = 0;
      window.requestAnimationFrame(() => document.getElementById(document.getElementById('backToResults').hidden ? 'panelClose' : 'backToResults').focus({preventScroll:true}));
    }
    elements.detailPanel.classList.add("open");
    elements.detailPanel.setAttribute("aria-hidden", "false");
    refreshIcons();
  }

  function closeDetail() {
    document.getElementById("backToResults").hidden = true;
    elements.detailPanel.inert = true;
    exploration.panel = "";
    state.selectedStoreId = "";
    state.selectedCentreId = "";
    state.selectedCandidateId = "";
    elements.detailPanel.classList.remove("open");
    elements.detailPanel.setAttribute("aria-hidden", "true");
    catchmentLayer.clearLayers();
    if (state.focusedPlaceId) clearPlaceFocus();
    restoreInspectionMap();
    if (isMapView()) renderQuickResults();
    const original = exploration.returnFocus;
    const target = original?.dataset?.resultId
      ? [...elements.viewContent.querySelectorAll('[data-result-id]')].find(button => button.dataset.resultId === original.dataset.resultId)
      : original?.id ? document.getElementById(original.id) : original;
    target?.focus?.({ preventScroll: true });
    exploration.returnFocus = null;
  }

  function bindNearRows() {
    elements.detailContent.querySelectorAll("[data-store-id]").forEach((button) => {
      button.addEventListener("click", () => selectStore(button.dataset.storeId, true));
    });
  }

  function selectStore(storeId, moveMap = true) {
    beginInspection();
    const store = state.allStores.find((item) => item.store_id === storeId);
    if (!store) return;
    openStoreDetail(store);
    if (isMapView()) renderQuickResults();
    if (moveMap) {
      const marker = markerById.get(storeId);
      const targetZoom = Math.max(map.getZoom(), BRAND_CONFIG[store.retailer]?.minMarkerZoom || 0, 14);
      if (marker && map.hasLayer(storeClusters) && storeClusters.hasLayer(marker)) {
        storeClusters.zoomToShowLayer(marker, () => map.setView([store.latitude, store.longitude], targetZoom));
      } else {
        map.setView([store.latitude, store.longitude], targetZoom);
      }
    }
  }

  function storeComparisonHtml(readOnly = false) {
    return `<section class="store-comparison-section"><h2>Store comparison</h2>
      <p>Open a store and choose Add to Compare. Up to two stores are retained; a third replaces the oldest selection.</p>
      <ol>${state.compareStores.map(store => `<li><strong>${escapeHtml(store.name)}</strong><span>${escapeHtml(store.retailer)} · ${escapeHtml(store.full_address || "Address not recorded")}</span></li>`).join("")}</ol>
      ${state.compareStores.length === 2
        ? `<div class="store-separation"><span>Straight-line distance</span><strong>${escapeHtml(Intel.formatDistance(Intel.haversine(...state.compareStores)))}</strong></div><p>Geographic separation, not driving distance or proof of shared place membership.</p>`
        : `<p>${state.compareStores.length ? "Add one more store to see the distance." : "No stores selected yet."}</p>`}
      ${state.compareStores.length && !readOnly ? '<button class="secondary-command" type="button" id="clearComparedStores">Clear stores</button>' : ''}</section>`;
  }

  function addCompareStore(store) {
    if (state.compareStores.some(item => item.store_id === store.store_id)) { showToast("This store is already in Compare."); return; }
    state.compareStores = [...state.compareStores.slice(-1), store];
    renderCandidateDock();
    showToast(`${state.compareStores.length} of 2 stores added. Open Compare to see their distance.`);
  }

  function clearStoreComparison() {
    state.compareStores = [];
    renderCandidateDock();
  }

  function renderSiteFinderResults(query = "") {
    const normalise = (value) => String(value || "").normalize("NFKD").replace(/[\u0300-\u036f]/g, "").toLowerCase().replace(/[^\p{L}\p{N}]+/gu, " ").trim();
    const search = normalise(query).trim();
    if (!search) {
      elements.siteFinderResults.innerHTML = "<p>Choose a mapped place to add it directly, or click a new point on the map.</p>";
      return;
    }
    const places = state.centres.filter((place) => normalise(`${place.name} ${place.locality} ${place.suburb} ${place.state} ${place.postcode}`).includes(search))
      .slice(0, 5)
      .map((place) => ({ type: "place", id: place.place_id, name: place.name, context: `${place.locality || place.suburb || "Locality unrecorded"}${place.state ? `, ${place.state}` : ""}`, latitude: place.latitude, longitude: place.longitude }));
    const stores = state.allStores.filter((store) => store.status !== "Closed" && normalise(`${store.name} ${store.retailer} ${store.suburb} ${store.state} ${store.postcode}`).includes(search))
      .slice(0, Math.max(0, 8 - places.length))
      .map((store) => ({ type: "store", id: store.store_id, name: store.name, context: `${store.retailer} · ${store.suburb}, ${store.state}`, latitude: store.latitude, longitude: store.longitude }));
    const matches = [...places, ...stores].filter((item) => item.latitude != null && item.longitude != null && Number.isFinite(Number(item.latitude)) && Number.isFinite(Number(item.longitude)));
    elements.siteFinderResults.innerHTML = matches.length
      ? matches.map((item) => `<button type="button" data-site-finder-type="${item.type}" data-site-finder-id="${escapeHtml(item.id)}" data-latitude="${Number(item.latitude)}" data-longitude="${Number(item.longitude)}"><i data-lucide="${item.type === "place" ? "building-2" : "store"}"></i><span><strong>${escapeHtml(item.name)}</strong><small>${escapeHtml(item.context)}${item.type === "place" ? " · Add to Compare" : " · Move map"}</small></span><i data-lucide="arrow-right"></i></button>`).join("")
      : "<p>No mapped place or store matches that search. Pan the map manually and click the site.</p>";
    refreshIcons();
  }

  function setCandidateDropMode(active) {
    state.candidateDropMode = active;
    elements.candidateButton.classList.toggle("active", active);
    document.body.classList.toggle("candidate-mode", active);
    elements.siteFinderPanel.hidden = !active;
    if (active) {
      elements.layerPanel.hidden = true;
      if (!document.getElementById('siteCandidateOptions')) {
        elements.siteFinderPanel.insertAdjacentHTML('beforeend', `<details id="siteCandidateOptions" class="advanced-filters"><summary>Candidate options</summary><section class="opportunity-form"><label><span>Candidate name</span><input data-candidate-field="name" placeholder="Optional public site name" /></label><label><span>Brand profile</span><select data-candidate-field="profile_id">${profileOptions()}</select></label><div class="select-grid">${[['area_sqm','Available area'],['target_min_sqm','Target minimum'],['target_max_sqm','Target maximum']].map(([key,label]) => `<label><span>${label} (sqm)</span><input data-candidate-field="${key}" type="number" min="1" placeholder="Unknown" /></label>`).join('')}</div></section></details>`);
        elements.siteFinderPanel.querySelectorAll('[data-candidate-field]').forEach(input => {
          input.value = state.opportunityForm[input.dataset.candidateField] || '';
          input.addEventListener('input', () => { state.opportunityForm[input.dataset.candidateField] = input.value; });
        });
      }
      renderSiteFinderResults(elements.siteFinderSearch.value);
      window.setTimeout(() => elements.siteFinderSearch.focus(), 0);
    }
    elements.modeNotice.hidden = true;
    elements.modeNotice.textContent = active
      ? "Site placement is active. Search to move the map, then click the exact site."
      : "";
  }

  function addPlaceToComparison(place) {
    if (!place) return;
    if (place.latitude == null || place.longitude == null || !Number.isFinite(Number(place.latitude)) || !Number.isFinite(Number(place.longitude))) {
      showToast('This place has no verified reference point. Choose a map point for area analysis.', 'warning');
      return;
    }
    const placeId = resolvePlaceId(place.place_id);
    if (!state.candidates.some(candidate => resolvePlaceId(candidate.place_id) === placeId)) {
      const candidate = { id: `place-${placeId}`, place_id: placeId, name: place.name,
        latitude: Number(place.latitude), longitude: Number(place.longitude),
        profile_id: state.opportunityForm.profile_id || 'generic-optical', area_sqm: '',
        amenity_summary: null };
      state.candidates.push(candidate);
      createCandidateMarker(candidate);
    }
    const currentMap = { center: map.getCenter(), zoom: map.getZoom() };
    setCandidateDropMode(false);
    closeDetail();
    setView('compare');
    map.setView(currentMap.center, currentMap.zoom, {animate: false});
    elements.viewContent.closest('.sidebar').scrollTop = 0;
    document.getElementById('compareDropButton')?.focus({preventScroll: true});
    showToast(`${place.name} is in Compare. Add another place to compare.`);
  }

  function dropCandidate(latlng) {
    const candidate = {
      id: `candidate-${Date.now().toString(36)}`,
      name: state.opportunityForm.name.trim() || `Candidate ${state.candidates.length + 1}`,
      latitude: Number(latlng.lat.toFixed(6)),
      longitude: Number(latlng.lng.toFixed(6)),
      area_sqm: state.opportunityForm.area_sqm || "",
      target_min_sqm: state.opportunityForm.target_min_sqm || "",
      target_max_sqm: state.opportunityForm.target_max_sqm || "",
      profile_id: state.opportunityForm.profile_id || "generic-optical",
      amenity_summary: null,
      amenity_evidence: { status: "pending", radius_km: 1, source: "OpenStreetMap Overpass" },
      created_at: new Date().toISOString(),
    };
    state.candidates.push(candidate);
    createCandidateMarker(candidate);
    setCandidateDropMode(false);
    elements.candidateDock.hidden = false;
    renderCandidateDock();
    openCandidateDetail(candidate);
    refreshCandidateAmenities(candidate);
    if (state.view === "opportunity" || state.view === "compare") renderView();
    updateShareUrl(false);
  }

  function removeCandidate(candidateId) {
    removeCandidates([candidateId]);
  }

  function removeCandidates(candidateIds) {
    const removedIds = new Set(candidateIds);
    state.candidates = state.candidates.filter(candidate => !removedIds.has(candidate.id));
    removedIds.forEach(candidateId => {
      const marker = candidateMarkerById.get(candidateId);
      if (marker) candidateLayer.removeLayer(marker);
      candidateMarkerById.delete(candidateId);
    });
    catchmentLayer.clearLayers();
    closeDetail();
    renderCandidateDock();
    renderView();
    refreshActiveMapContext();
    updateShareUrl(false);
    document.getElementById('compareDropButton')?.focus({preventScroll: true});
  }

  function drawCandidateCatchments(candidate) {
    catchmentLayer.clearLayers();
    CATCHMENT_RADII.slice()
      .reverse()
      .forEach((radius, index) => {
        L.circle([candidate.latitude, candidate.longitude], {
          radius: radius * 1000,
          color: "#a24f93",
          weight: radius === 1 ? 2 : 1,
          fillColor: "#a24f93",
          fillOpacity: 0.025 + index * 0.008,
          dashArray: radius === 1 ? "" : "5 5",
          interactive: false,
        }).addTo(catchmentLayer);
      });
  }

  function renderCandidateDock() {
    renderComparisonConnections();
    state.candidates.forEach((candidate, index) => {
      const element = candidateMarkerById.get(candidate.id)?.getElement()?.querySelector(".candidate-marker");
      if (element) element.textContent = index + 1;
    });
    elements.candidateDock.hidden = !state.candidates.length;
    const compareLabel = document.querySelector('#planningNav span');
    if (compareLabel) compareLabel.textContent = `Site planning${state.candidates.length + state.compareStores.length ? ` (${state.candidates.length + state.compareStores.length})` : ''}`;
    elements.candidateDockCount.textContent = `${state.candidates.length} ${state.candidates.length === 1 ? "site" : "sites"}`;
    elements.candidateCards.innerHTML = state.candidates
      .map((candidate, index) => {
        const model = scoreCandidate(candidate);
        return `<button data-candidate-id="${escapeHtml(candidate.id)}"><span class="score-badge ${
          model.reliable ? "" : "low-coverage"
        }">${model.score ?? "-"}</span><span><small class="candidate-slot">Site ${String.fromCharCode(65 + index)}</small><strong>${escapeHtml(candidate.name)}</strong><small>${escapeHtml(
          marketLabel(candidate)
        )}</small></span><span>${model.coverage}%</span></button>`;
      })
      .join("");
    elements.candidateCards.querySelectorAll("[data-candidate-id]").forEach((button) => {
      button.addEventListener("click", () => {
        const candidate = state.candidates.find((item) => item.id === button.dataset.candidateId);
        openCandidateDetail(candidate);
        map.setView([candidate.latitude, candidate.longitude], 13);
      });
    });
  }

  function marketStyle(field, feature) {
    const properties = feature.properties;
    let value = null;
    let fillColor = "#d9dfdc";
    if (field === "demographic") {
      value = Intel.marketDemandScore(feature, state.markets);
      fillColor =
        value >= 80 ? "#006d77" : value >= 60 ? "#4d9a98" : value >= 40 ? "#9cc7bb" : value >= 20 ? "#d6dfc5" : "#f0e8c9";
    } else {
      value =
        properties.population_growth_2021_2025_pct === null
          ? null
          : Number(properties.population_growth_2021_2025_pct);
      fillColor =
        value === null
          ? "#d9dfdc"
          : value >= 15
            ? "#2f7d32"
            : value >= 8
              ? "#76a744"
              : value >= 2
                ? "#bed06c"
                : value >= 0
                  ? "#eadc8d"
                  : "#d98d73";
    }
    return { color: "#ffffff", weight: 0.5, fillColor, fillOpacity: 0.68 };
  }

  function buildMarketLayer(field) {
    return L.geoJSON(
      { type: "FeatureCollection", features: state.markets },
      {
        style: (feature) => marketStyle(field, feature),
        onEachFeature(feature, layer) {
          const properties = feature.properties;
          layer.bindTooltip(
            `<strong>${escapeHtml(properties.sa2_name)}</strong><br>Population ${formatNumber(
              properties.population_2025
            )}<br>Growth ${formatNumber(properties.population_growth_2021_2025_pct, "%")}`,
            { sticky: true }
          );
          layer.on("click", () => openMarketDetail(feature));
        },
      }
    );
  }

  function openMarketDetail(feature) {
    const properties = feature.properties;
    const point = {
      latitude: properties.centroid_latitude,
      longitude: properties.centroid_longitude,
    };
    const nearby = distanceEntries(point).filter((entry) => entry.distance <= 10);
    elements.detailContent.innerHTML = `
      <header class="detail-header" style="--brand-color:#006d77"><span class="retailer-tag"><i data-lucide="chart-spline"></i>ABS market</span>
        <h2>${escapeHtml(properties.sa2_name)}</h2><address>${escapeHtml(properties.state)} · SA2 ${escapeHtml(
      properties.sa2_code
    )}</address></header>
      ${marketEvidenceHtml(properties)}
      <section class="detail-section"><h3>Network within 10 km of SA2 centre</h3>
        <div class="data-grid">${BRAND_ORDER.map(
          (brand) =>
            `<div class="data-point"><span>${escapeHtml(brand)}</span><strong>${
              nearby.filter((entry) => entry.store.retailer === brand).length
            }</strong></div>`
        ).join("")}</div></section>
      <details class="technical-details"><summary>Source record and identifier</summary><section class="detail-section source-block"><i data-lucide="database"></i><div><strong>ABS Data by Region 2011–25</strong>
        <span>Released ${escapeHtml(formatDate(state.marketMetadata.source_release_date))} · High confidence</span></div></section>`;
    openDetailPanel();
  }

  function updateLayerVisibility(refreshStores = true) {
    scheduleOverviewRefresh();
    if (refreshStores) refreshStoreMarkerVisibility();
    if (!state.activeLayers.has("stores")) placeFocusLayer.clearLayers();
    if (state.activeLayers.has("centres")) {
      if (!map.hasLayer(centreLayer)) centreLayer.addTo(map);
    } else if (map.hasLayer(centreLayer)) map.removeLayer(centreLayer);
    if (state.activeLayers.has("demographic")) {
      demographicLayer ||= buildMarketLayer("demographic");
      demographicLayer.addTo(map);
    } else if (demographicLayer && map.hasLayer(demographicLayer)) map.removeLayer(demographicLayer);
    if (state.activeLayers.has("growth")) {
      growthLayer ||= buildMarketLayer("growth");
      growthLayer.addTo(map);
    } else if (growthLayer && map.hasLayer(growthLayer)) map.removeLayer(growthLayer);
    if (state.activeLayers.has("development")) {
      if (!map.hasLayer(developmentLayer)) developmentLayer.addTo(map);
    } else if (map.hasLayer(developmentLayer)) map.removeLayer(developmentLayer);
    updateSaturationLayer();
    loadAmenities();
  }

  function updateSaturationLayer() {
    if (saturationLayer && map.hasLayer(saturationLayer)) map.removeLayer(saturationLayer);
    saturationLayer = null;
    if (!state.activeLayers.has("saturation") || !window.L.heatLayer) return;
    saturationLayer = L.heatLayer(
      storesForActiveMapView().map((store) => [store.latitude, store.longitude, 0.55]),
      { radius: 24, blur: 19, maxZoom: 11, gradient: { 0.2: "#f6d55c", 0.55: "#ed8b45", 0.85: "#b23a48" } }
    ).addTo(map);
  }

  async function loadAmenities() {
    const selected = ["health", "transport", "parking"].filter((layer) => state.activeLayers.has(layer));
    amenityLayer.clearLayers();
    state.amenityMarkers = [];
    state.amenitySummary = null;
    if (!selected.length) return;
    if (map.getZoom() < 12) {
      showToast("Zoom into a precinct to load transport, parking and health amenities.");
      return;
    }
    amenityRequestController?.abort();
    amenityRequestController = new AbortController();
    const bounds = map.getBounds();
    const bbox = `${bounds.getSouth()},${bounds.getWest()},${bounds.getNorth()},${bounds.getEast()}`;
    const parts = [];
    if (selected.includes("health")) {
      parts.push(`nwr["amenity"~"pharmacy|clinic|hospital|doctors"](${bbox});nwr["healthcare"](${bbox});`);
    }
    if (selected.includes("transport")) {
      parts.push(`nwr["public_transport"](${bbox});nwr["railway"~"station|tram_stop|halt"](${bbox});nwr["highway"="bus_stop"](${bbox});`);
    }
    if (selected.includes("parking")) parts.push(`nwr["amenity"="parking"](${bbox});`);
    const query = `[out:json][timeout:18];(${parts.join("")});out center 350;`;
    try {
      const response = await fetch("https://overpass-api.de/api/interpreter", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8" },
        body: `data=${encodeURIComponent(query)}`,
        signal: amenityRequestController.signal,
      });
      if (!response.ok) throw new Error(`OpenStreetMap returned ${response.status}`);
      const payload = await response.json();
      const seen = new Set();
      payload.elements.forEach((item) => {
        const latitude = item.lat ?? item.center?.lat;
        const longitude = item.lon ?? item.center?.lon;
        if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) return;
        const tags = item.tags || {};
        const kind =
          tags.amenity === "parking"
            ? "parking"
            : tags.public_transport || tags.railway || tags.highway === "bus_stop"
              ? "transport"
              : "health";
        if (!selected.includes(kind)) return;
        const key = `${kind}-${latitude.toFixed(5)}-${longitude.toFixed(5)}`;
        if (seen.has(key)) return;
        seen.add(key);
        const marker = L.circleMarker([latitude, longitude], {
          radius: 5,
          weight: 1.5,
          color: "#ffffff",
          fillColor: kind === "health" ? "#c43d5d" : kind === "transport" ? "#2870a8" : "#d29b27",
          fillOpacity: 0.92,
        }).bindTooltip(escapeHtml(tags.name || kind[0].toUpperCase() + kind.slice(1)), { direction: "top" });
        marker.addTo(amenityLayer);
        state.amenityMarkers.push({ latitude, longitude, kind });
      });
      showToast(`Loaded ${state.amenityMarkers.length} OpenStreetMap amenities in this precinct.`);
    } catch (error) {
      if (error.name !== "AbortError") showToast("Local amenity data is temporarily unavailable.", "warning");
    }
  }

  async function refreshCandidateAmenities(candidate) {
    const radiusMetres = 1000;
    const query = `[out:json][timeout:18];(nwr["amenity"~"pharmacy|clinic|hospital|doctors"](around:${radiusMetres},${candidate.latitude},${candidate.longitude});nwr["healthcare"](around:${radiusMetres},${candidate.latitude},${candidate.longitude});nwr["public_transport"](around:${radiusMetres},${candidate.latitude},${candidate.longitude});nwr["railway"~"station|tram_stop|halt"](around:${radiusMetres},${candidate.latitude},${candidate.longitude});nwr["highway"="bus_stop"](around:${radiusMetres},${candidate.latitude},${candidate.longitude});nwr["amenity"="parking"](around:${radiusMetres},${candidate.latitude},${candidate.longitude}););out center 500;`;
    try {
      const response = await fetch("https://overpass-api.de/api/interpreter", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8" },
        body: `data=${encodeURIComponent(query)}`,
      });
      if (!response.ok) throw new Error(`OpenStreetMap returned ${response.status}`);
      const payload = await response.json();
      const summary = { health: 0, transport: 0, parking: 0 };
      const seen = new Set();
      payload.elements.forEach((item) => {
        const tags = item.tags || {};
        const kind = tags.amenity === "parking"
          ? "parking"
          : tags.public_transport || tags.railway || tags.highway === "bus_stop"
            ? "transport"
            : "health";
        const key = `${item.type}-${item.id}-${kind}`;
        if (!seen.has(key)) {
          seen.add(key);
          summary[kind] += 1;
        }
      });
      candidate.amenity_summary = summary;
      candidate.amenity_evidence = {
        status: "current",
        radius_km: 1,
        source: "OpenStreetMap Overpass",
        queried_at: new Date().toISOString(),
      };
      renderCandidateDock();
      if (state.view === "opportunity" || state.view === "compare") renderView();
      if (state.selectedCandidateId === candidate.id && elements.detailPanel.classList.contains("open")) {
        openCandidateDetail(candidate);
      }
    } catch (error) {
      candidate.amenity_summary = null;
      candidate.amenity_evidence = {
        status: "failed",
        radius_km: 1,
        source: "OpenStreetMap Overpass",
        queried_at: new Date().toISOString(),
        error: String(error.message || error),
      };
      if (state.selectedCandidateId === candidate.id && elements.detailPanel.classList.contains("open")) {
        openCandidateDetail(candidate);
      }
    }
  }

  function showReport(title, content) {
    document.getElementById("reportDate").textContent = formatDate(new Date().toISOString());
    document.querySelector("#reportSheet header h2").textContent = title;
    elements.reportContent.innerHTML = content;
    elements.reportSheet.setAttribute("aria-hidden", "false");
    window.print();
    window.setTimeout(() => elements.reportSheet.setAttribute("aria-hidden", "true"), 500);
  }

  function generatePlaceReport(centre) {
    if (!centre) return;
    const row = publishedLookalike(centre.place_id) || {};
    const record = placeSummaryRecord(centre);
    const localEvidence = state.environments?.places.find(p => p.place_id === centre.place_id && p.local_evidence);
    const tenants = tenantsForPlace(centre.place_id);
    const optical = tenants.filter((item) => item.category === "Optical");
    const keyTenants = tenants.filter((item) => item.category !== "Optical");
    const gaps = Object.entries(LOOKALIKE_COMPONENTS).filter(([key]) => !hasLookalikeComponent(row.components?.[key])).map(([, value]) => value[0]);
    const componentHtml = `<div class="score-components">${Object.entries(LOOKALIKE_COMPONENTS).map(([key, [label]]) => {
      const value = row.components?.[key];
      return `<div><span>${escapeHtml(label)}</span><b>${hasLookalikeComponent(value) ? Math.round(Number(value)) : "N/A"}</b><i><em style="width:${hasLookalikeComponent(value) ? Math.round(Number(value)) : 0}%"></em></i></div>`;
    }).join("")}</div>`;
    showReport("Selected place brief", `
      <section class="report-lead"><div><p>${escapeHtml(centre.location_setting)}</p><h3>${escapeHtml(centre.name)}</h3><span>${escapeHtml(`${centre.locality || centre.suburb || "Locality unrecorded"}${centre.state ? `, ${centre.state}` : ""}`)}</span></div>
        <div class="report-score"><strong>${row.score ?? "—"}</strong><span>Lookalike score</span><small>${row.screening_completeness ?? "—"}% complete${row.rank ? ` · rank #${row.rank}` : ""}</small></div></section>
      <section><h3>Opportunity evidence</h3><div class="report-grid">
        <div><span>Population 2025</span><strong>${formatNumber(record.population_2025)}</strong></div>
        <div><span>Growth 2021–25</span><strong>${formatNumber(record.population_growth_2021_2025_pct, "%")}</strong></div>
        <div><span>Age 45+</span><strong>${formatNumber(record.age_45_plus_pct_2021, "%")}</strong></div>
        <div><span>Equivalised weekly household income</span><strong>${record.median_equivalised_household_income_weekly_2021 ? `$${formatNumber(record.median_equivalised_household_income_weekly_2021)}` : "N/A"}</strong></div>
        <div><span>Nearest Bailey Nelson</span><strong>${Number.isFinite(Number(record.nearest_bailey_km)) ? Intel.formatDistance(Number(record.nearest_bailey_km)) : "Unknown"}</strong></div>
        <div><span>Exact-place optical stores</span><strong>${formatNumber(centre.optical_store_count || 0)}</strong></div>
      </div></section>
      <section><h3>Why it ranks</h3>${componentHtml}<p>Lookalike score compares public evidence with Bailey Nelson’s mapped footprint. It is a screening heuristic, not a forecast of store success.</p></section>
      <section><h3>Exact-place optical tenants</h3><p>${optical.length ? optical.map((item) => escapeHtml(item.tenant_name)).join(" · ") : "No accepted exact-place optical membership is recorded."}</p></section>
      ${localEvidence ? window.EnvironmentExplorer.evidencePanel(localEvidence) : `<section><h3>Key co-tenancy profile</h3><p>${keyTenants.length ? keyTenants.map((item) => `${escapeHtml(item.tenant_name)} (${escapeHtml(item.category)})`).join(" · ") : "Key co-tenancy research has not been completed for this place."}</p></section>`}
      ${centre.location_setting === "High Street" ? '<section><h3>High-street place context</h3><p>Centre class, ownership, leasing arrangement and property portfolio overlap are not applied to a whole street corridor.</p></section>' : `<section><h3>Property and leasing</h3><div class="report-grid">
        <div><span>Centre class</span><strong>${escapeHtml(record.centre_class)}</strong></div>
        <div><span>Property groups</span><strong>${escapeHtml(record.property_groups || "Unknown")}</strong></div>
        <div><span>Leasing arrangement</span><strong>${escapeHtml(record.leasing_arrangement)}</strong></div>
      </div><p>${escapeHtml(record.portfolio_overlap)}</p></section>`}
      <section><h3>Evidence gaps and cautions</h3><ul>
        <li>${gaps.length ? `${escapeHtml(gaps.join(", "))} are not scored because evidence is unavailable.` : "All four weighted screening components have public evidence."}</li>
        <li>Nearby retailers are not treated as tenants unless they share the accepted canonical place ID.</li>
        <li>Key co-tenancy profiles are curated and are not complete centre directories.</li>
        <li>Rent, lease terms, pedestrian barriers and private Bailey Nelson performance are outside this public brief.</li>
      </ul></section>
      <section><h3>Sources</h3><p>${record.official_url ? `Primary place source: ${escapeHtml(record.official_url)}. ` : ""}Demographics use the Australian public market dataset described in the application methodology. Property and tenant facts retain their own evidence dates in the CSV exports.</p></section>`);
  }

  function generateReport(candidate = null) {
    const target =
      candidate ||
      state.candidates.find((item) => item.id === state.selectedCandidateId) ||
      state.candidates[0];
    if (!target) {
      showToast("Add a candidate site before creating a report.", "warning");
      return;
    }
    const model = scoreCandidate(target);
    const market = marketForPoint(target)?.properties || {};
    const catchments = CATCHMENT_RADII.map((radius) => Intel.catchmentSummary(target, radius, state.markets));
    const proximity = proximityModel(target, null, true);
    showReport("Candidate site brief", `
      <section class="report-lead"><div><p>Candidate</p><h3>${escapeHtml(target.name)}</h3><span>${escapeHtml(
      marketLabel(target)
    )}</span></div><div class="report-score"><strong>${model.score ?? "-"}</strong><span>Site score</span><small>${
      model.coverage
    }% coverage</small></div></section>
      <section><h3>Executive evidence</h3><div class="report-grid">
        <div><span>Population 2025</span><strong>${formatNumber(market.population_2025)}</strong></div>
        <div><span>Growth 2021–25</span><strong>${formatNumber(market.population_growth_2021_2025_pct, "%")}</strong></div>
        <div><span>Age 45+</span><strong>${formatNumber(market.age_45_plus_pct_2021, "%")}</strong></div>
        <div><span>Equivalised weekly household income</span><strong>$${formatNumber(
          market.median_equivalised_household_income_weekly_2021
        )}</strong></div>
        <div><span>5 km competitors</span><strong>${model.competitorCountFiveKm}</strong></div>
        <div><span>Nearest competing store</span><strong>${Intel.formatDistance(model.nearestCompetitorKm)}</strong></div>
      </div></section>
      <section><h3>Transparent score</h3>${scoreComponentsHtml(model)}</section>
      <section><h3>Straight-line catchments</h3>${catchmentTableHtml(catchments)}</section>
      <section><h3>Nearest networks within 100 km</h3><div class="proximity-summary">${nearestBrandHtml(proximity, { maxDistanceKm: MAX_CANDIDATE_BRAND_DISTANCE_KM, sortByDistance: true })}</div></section>
      <section><h3>Risks and gaps</h3><ul>
        <li>${model.reliable ? "Evidence coverage meets the ranking threshold." : "Evidence coverage is below the 70% ranking threshold."}</li>
        <li>${target.area_sqm ? "Available area has been supplied for format testing." : "Available tenancy area has not been supplied."}</li>
        <li>${model.nearestCentre ? `Verified place is ${escapeHtml(model.nearestCentre.centre.name)}.` : "No verified centre membership is attached to this candidate."}</li>
        <li>${model.nearbyCentreLead ? `${escapeHtml(model.nearbyCentreLead.centre.name)} is nearby and requires evidence before centre strength can apply.` : "No reviewed shopping-centre lead is recorded within 750 metres."}</li>
        <li>Driving time, pedestrian barriers, rent and lease terms are outside this public assessment.</li>
      </ul></section>
      <section><h3>Sources</h3><p>Australian Bureau of Statistics Data by Region 2011–25, Stats NZ regional boundaries, official retailer locators, OpenStreetMap contributors, reviewed venue IDs and public landlord profiles where available. Every source retains its own reference date and coverage label.</p></section>`);
  }

  function generateContextReport() {
    const selectedPlace = state.centres.find((item) => item.place_id === state.selectedCentreId);
    if (selectedPlace && elements.detailPanel.classList.contains("open")) return generatePlaceReport(selectedPlace);
    return generateReport();
  }

  function shareState() {
    const center = map.getCenter();
    return Intel.sanitiseShareState({
      view: state.view,
      activeLayers: state.activeLayers,
      filters: state.filters,
      placeFilters: state.placeFilters,
      opportunityFilters: state.opportunityFilters,
      map: { latitude: center.lat, longitude: center.lng, zoom: map.getZoom() },
      candidates: state.candidates,
    });
  }

  function encodeShare(value) {
    const bytes = new TextEncoder().encode(JSON.stringify(value));
    let binary = "";
    bytes.forEach((byte) => {
      binary += String.fromCharCode(byte);
    });
    return btoa(binary).replaceAll("+", "-").replaceAll("/", "_").replaceAll("=", "");
  }

  function decodeShare(value) {
    const padded = value.replaceAll("-", "+").replaceAll("_", "/") + "=".repeat((4 - (value.length % 4)) % 4);
    const binary = atob(padded);
    const bytes = Uint8Array.from(binary, (character) => character.charCodeAt(0));
    return JSON.parse(new TextDecoder().decode(bytes));
  }

  function updateShareUrl(copy) {
    if (state.privateOverlayActive) {
      const clean = new URL(window.location.href); clean.search = ""; clean.hash = "";
      window.history.replaceState(null, "", clean);
      if (copy) showToast("Close the private local review before sharing a public view.");
      return;
    }
    const url = new URL(window.location.href);
    url.searchParams.set("share", encodeShare(shareState()));
    window.history.replaceState(null, "", url);
    if (copy) {
      navigator.clipboard
        .writeText(url.toString())
        .then(() => showToast("Sanitised public link copied."))
        .catch(() => showToast("Copy the current browser address to share this view.", "warning"));
    }
  }

  function saveView() {
    if (state.privateOverlayActive) { showToast("Close the private local review before saving a public view."); return; }
    localStorage.setItem("optical-leasing-saved-view", JSON.stringify(shareState()));
    showToast("View saved in this browser and will reopen on your next base-page visit.");
  }

  function restoreShareState() {
    let payload = null;
    const encoded = new URLSearchParams(window.location.search).get("share");
    if (encoded) {
      try {
        payload = decodeShare(encoded);
      } catch {
        showToast("The shared view could not be read.", "warning");
      }
    }
    if (!payload) {
      try {
        payload = JSON.parse(localStorage.getItem("optical-leasing-saved-view") || "null");
      } catch {
        localStorage.removeItem("optical-leasing-saved-view");
      }
    }
    if (!payload) return false;
    if (VIEW_CONFIG[payload.view]) state.view = payload.view;
    state.activeLayers = new Set(Intel.sanitiseLayers(payload.layers));
    document.querySelectorAll("[data-layer]").forEach(input => { input.checked = state.activeLayers.has(input.dataset.layer); });
    if (payload.filters) {
      state.filters.retailers = new Set(
        payload.filters.retailers?.filter((retailer) => BRAND_ORDER.includes(retailer)) || DEFAULT_RETAILERS
      );
      state.filters.country = payload.filters.country || "";
      state.filters.state = payload.filters.state || "";
      state.filters.location = payload.filters.location || "";
      state.filters.audiology = ["true", "false"].includes(payload.filters.audiology) ? payload.filters.audiology : "";
      state.filters.status = payload.filters.status === "Closed" ? "" : payload.filters.status || "";
      state.filters.search = payload.filters.search || "";
      state.filters.affiliation = state.affiliations.some((item) => item.affiliation_id === payload.filters.affiliation)
        ? payload.filters.affiliation : "";
    }
    if (payload.place_filters) {
      state.placeFilters.search = payload.place_filters.search || "";
      state.placeFilters.country = payload.place_filters.country || "";
      state.placeFilters.type = payload.place_filters.type || "";
      state.placeFilters.state = payload.place_filters.state || "";
      state.placeFilters.bailey = payload.place_filters.bailey || "";
      state.placeFilters.retailers = new Set(
        (payload.place_filters.retailers || []).filter((retailer) => BRAND_ORDER.includes(retailer))
      );
      state.placeFilters.confidence = payload.place_filters.confidence || "";
      state.placeFilters.group_id = payload.place_filters.group_id || "";
      state.placeFilters.arrangement = payload.place_filters.arrangement || "";
      state.placeFilters.overlap = payload.place_filters.overlap || "";
      state.placeFilters.centre_class = payload.place_filters.centre_class || "";
      state.placeFilters.min_income = payload.place_filters.min_income ?? "";
      state.placeFilters.min_bailey_distance = payload.place_filters.min_bailey_distance ?? "";
      state.placeFilters.sort = payload.place_filters.sort || "name";
    }
    if (payload.opportunity_filters) {
      state.opportunityFilters.country = ["Australia", "New Zealand"].includes(payload.opportunity_filters.country)
        ? payload.opportunity_filters.country : "Australia";
      state.opportunityFilters.setting = ["Shopping Centre", "High Street"].includes(payload.opportunity_filters.setting)
        ? payload.opportunity_filters.setting : "";
      state.opportunityFilters.require_any_retailer = Boolean(payload.opportunity_filters.require_any_retailer);
      state.opportunityFilters.must_have_retailers = new Set(
        (payload.opportunity_filters.must_have_retailers || []).filter((retailer) => BRAND_ORDER.includes(retailer) && retailer !== "Bailey Nelson")
      );
      state.opportunityFilters.must_not_have_retailers = new Set(
        (payload.opportunity_filters.must_not_have_retailers || []).filter((retailer) => BRAND_ORDER.includes(retailer) && retailer !== "Bailey Nelson")
      );
      state.opportunityFilters.must_have_retailers.forEach((retailer) => state.opportunityFilters.must_not_have_retailers.delete(retailer));
    }
    (payload.candidates || []).forEach((candidate, index) => {
      if (!Number.isFinite(candidate.latitude) || !Number.isFinite(candidate.longitude)) return;
      const linkedPlace = state.centres.find(place => place.place_id === resolvePlaceId(candidate.place_id));
      const restored = {
        id: candidate.id || `shared-${index}`,
        name: candidate.name || `Candidate ${index + 1}`,
        latitude: candidate.latitude,
        longitude: candidate.longitude,
        area_sqm: candidate.area_sqm || "",
        target_min_sqm: "",
        target_max_sqm: "",
        profile_id: candidate.profile_id || "generic-optical",
        place_id: linkedPlace?.place_id || "",
        created_at: "",
      };
      state.candidates.push(restored);
      createCandidateMarker(restored);
    });
    if (Number.isFinite(payload.map?.latitude) && Number.isFinite(payload.map?.longitude)) {
      map.setView([payload.map.latitude, payload.map.longitude], payload.map.zoom || 10);
    }
    return true;
  }

  function downloadFilteredCsv() {
    const rows = [PUBLIC_STORE_FIELDS.join(",")].concat(
      state.filteredStores.map((store) => PUBLIC_STORE_FIELDS.map((field) => csvEscape(store[field])).join(","))
    );
    downloadText(`optical-stores-filtered-${new Date().toISOString().slice(0, 10)}.csv`, `${rows.join("\n")}\n`);
  }

  function downloadCandidateComparisonCsv() {
    const records = state.candidates.map((candidate) => {
      const score = scoreCandidate(candidate);
      const market = marketForPoint(candidate)?.properties || {};
      return {
        candidate_id: candidate.id,
        candidate_name: candidate.name,
        latitude: candidate.latitude,
        longitude: candidate.longitude,
        brand_profile: candidate.profile_id,
        available_area_sqm: candidate.area_sqm || "",
        screening_score: score.score ?? "",
        evidence_coverage_pct: score.coverage ?? "",
        population_2025: market.population_2025 ?? "",
        population_growth_2021_2025_pct: market.population_growth_2021_2025_pct ?? "",
        age_45_plus_pct_2021: market.age_45_plus_pct_2021 ?? "",
        median_equivalised_household_income_weekly_2021: market.median_equivalised_household_income_weekly_2021 ?? "",
        nearest_competitor_km: score.nearestCompetitorKm ?? "",
        competitors_within_5km: score.competitorCountFiveKm ?? "",
      };
    });
    exportRecords(`candidate-comparison-${new Date().toISOString().slice(0, 10)}.csv`, records);
  }

  function downloadContextCsv() {
    if (state.view === "centres") return exportPlaceSummary(filteredPlaces().map((place) => place.place_id));
    if (state.view === "opportunity") return exportPlaceSummary(visibleOpportunityRows().map((place) => place.place_id));
    if (state.view === "compare") return downloadCandidateComparisonCsv();
    return downloadFilteredCsv();
  }

  function resetAll() {
    state.placeFilters = structuredClone(exploration.defaults.centres);
    state.filters = {
      retailers: new Set(DEFAULT_RETAILERS),
      country: "",
      search: "",
      state: "",
      location: "",
      audiology: "",
      status: "",
      service: "",
      affiliation: "",
    };
    state.candidates = [];
    localStorage.removeItem("optical-leasing-saved-view");
    candidateLayer.clearLayers();
    candidateMarkerById.clear();
    catchmentLayer.clearLayers();
    clearStoreComparison();
    elements.modeNotice.hidden = true;
    setCandidateDropMode(false);
    closeDetail();
    exploration.drafts = {};
    exploration.submitted = {};
    state.activeLayers = new Set(["stores", "centres"]);
    document.querySelectorAll("[data-layer]").forEach((input) => {
      input.checked = ["stores", "centres"].includes(input.dataset.layer);
    });
    updateLayerVisibility(false);
    applyFilters(false);
    map.fitBounds(NETWORK_BOUNDS, { padding: [18, 18], animate: false });
    setView("network");
    renderCandidateDock();
    showToast("Workspace reset.");
  }

  function bindPlanningWidthResize() {
    const shell = document.querySelector('.app-shell');
    const handle = document.getElementById('planningWidthHandle');
    const storageKey = 'optical-leasing-planning-width-v1';
    let preferredWidth = 400;
    try {
      const saved = Number(localStorage.getItem(storageKey));
      if (Number.isFinite(saved) && saved >= 320) preferredWidth = saved;
    } catch { /* Resizing still works when browser storage is unavailable. */ }
    const maximum = () => Math.max(320, Math.min(960, shell.clientWidth - 320));
    const apply = () => {
      const width = Math.round(Math.min(maximum(), Math.max(320, preferredWidth)));
      shell.style.setProperty('--planning-width', `${width}px`);
      handle.setAttribute('aria-valuemin', '320');
      handle.setAttribute('aria-valuemax', String(maximum()));
      handle.setAttribute('aria-valuenow', String(width));
      handle.setAttribute('aria-valuetext', `${width} pixels`);
    };
    const save = () => { try { localStorage.setItem(storageKey, String(preferredWidth)); } catch {} };
    handle.addEventListener('pointerdown', event => {
      if (event.button !== 0) return;
      event.preventDefault();
      handle.setPointerCapture(event.pointerId);
      handle.classList.add('dragging');
      document.body.classList.add('planning-width-dragging');
    });
    handle.addEventListener('pointermove', event => {
      if (!handle.hasPointerCapture(event.pointerId)) return;
      preferredWidth = Math.min(maximum(), Math.max(320, event.clientX - shell.getBoundingClientRect().left));
      apply();
    });
    const finish = () => {
      handle.classList.remove('dragging');
      document.body.classList.remove('planning-width-dragging');
      save();
    };
    handle.addEventListener('pointerup', finish);
    handle.addEventListener('pointercancel', finish);
    handle.addEventListener('lostpointercapture', finish);
    handle.addEventListener('keydown', event => {
      if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
      event.preventDefault();
      const current = Number(handle.getAttribute('aria-valuenow'));
      preferredWidth = event.key === 'Home' ? 400 : event.key === 'End' ? maximum() : Math.min(maximum(), Math.max(320, current + (event.key === 'ArrowRight' ? 20 : -20)));
      apply(); save();
    });
    handle.addEventListener('dblclick', () => { preferredWidth = 400; apply(); save(); });
    window.addEventListener('resize', apply);
    new ResizeObserver(() => map.invalidateSize({pan: false})).observe(document.querySelector('.map-workspace'));
    apply();
  }

  function bindGlobalEvents() {
    bindPlanningWidthResize();
    document.getElementById('backToResults').onclick = () => {
      restoreInspectionMap(); showFullResults(true);
    };
    document.addEventListener('keydown', event => {
      if (event.key === 'Escape' && elements.detailPanel.classList.contains('open')) { event.preventDefault(); closeDetail(); }
    });
    const overflowMenus = [...document.querySelectorAll(".nav-overflow, .toolbar-overflow")];
    overflowMenus.forEach((menu) => menu.addEventListener("toggle", () => {
      if (!menu.open) return;
      overflowMenus.filter((candidate) => candidate !== menu).forEach((candidate) => candidate.removeAttribute("open"));
    }));
    document.addEventListener("click", (event) => {
      if (event.target.closest(".nav-overflow, .toolbar-overflow")) return;
      overflowMenus.forEach((menu) => menu.removeAttribute("open"));
    });
    document.querySelectorAll("[data-view]").forEach((button) =>
      button.addEventListener("click", () => {
        button.closest("details")?.removeAttribute("open");
        setView(button.id === "mapNav" ? exploration.mode : button.dataset.view);
      })
    );
    document.getElementById("panelClose").addEventListener("click", closeDetail);
    elements.detailContent.addEventListener("click", (event) => {
      const groupButton = event.target.closest("[data-property-group-id]");
      if (groupButton) openPropertyGroupDetail(groupButton.dataset.propertyGroupId);
      const placeButton = event.target.closest("[data-group-place-id]");
      if (placeButton) openCentreDetail(state.centres.find((item) => item.place_id === placeButton.dataset.groupPlaceId));
    });
    window.addEventListener("hashchange", () => {
      const match = window.location.hash.match(/^#property-group=(.+)$/);
      if (match) openPropertyGroupDetail(decodeURIComponent(match[1]));
    });
    document.getElementById("resetButton").addEventListener("click", resetAll);
    document.getElementById("tourButton").addEventListener("click", openTourDetail);
    document.getElementById("glossaryButton").addEventListener("click", openGlossaryDetail);
    document.getElementById("layersButton").addEventListener("click", () => {
      elements.layerPanel.hidden = !elements.layerPanel.hidden;
    });
    document.getElementById("layerClose").addEventListener("click", () => {
      elements.layerPanel.hidden = true;
    });
    document.querySelectorAll("[data-layer]").forEach((input) => {
      input.addEventListener("change", () => {
        if (input.checked) state.activeLayers.add(input.dataset.layer);
        else state.activeLayers.delete(input.dataset.layer);
        if (input.dataset.layer === "demographic" && input.checked) {
          const growth = document.querySelector('[data-layer="growth"]');
          growth.checked = false;
          state.activeLayers.delete("growth");
        }
        if (input.dataset.layer === "growth" && input.checked) {
          const demographic = document.querySelector('[data-layer="demographic"]');
          demographic.checked = false;
          state.activeLayers.delete("demographic");
        }
        updateLayerVisibility();
        updateShareUrl(false);
      });
    });
    elements.candidateButton.addEventListener("click", () => {
      setCandidateDropMode(!state.candidateDropMode);
    });
    document.getElementById("siteFinderClose").addEventListener("click", () => setCandidateDropMode(false));
    elements.siteFinderSearch.addEventListener("input", () => renderSiteFinderResults(elements.siteFinderSearch.value));
    elements.siteFinderResults.addEventListener("click", (event) => {
      const target = event.target.closest("[data-site-finder-id]");
      if (!target) return;
      if (target.dataset.siteFinderType === 'place') {
        addPlaceToComparison(state.centres.find(place => place.place_id === target.dataset.siteFinderId));
        return;
      }
      const latitude = Number(target.dataset.latitude);
      const longitude = Number(target.dataset.longitude);
      if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) return;
      map.setView([latitude, longitude], Math.max(map.getZoom(), target.dataset.siteFinderType === "place" ? 15 : 16));
      showToast("Map moved. Click the exact tenancy or site position to add it.");
    });
    document.getElementById("candidateDockAdd").addEventListener("click", () => setCandidateDropMode(true));
    document.getElementById("candidateDockClose").addEventListener("click", () => {
      elements.candidateDock.hidden = true;
    });
    document.getElementById("saveViewButton").addEventListener("click", () => { document.querySelector(".toolbar-overflow")?.removeAttribute("open"); saveView(); });
    document.getElementById("shareButton").addEventListener("click", () => { document.querySelector(".toolbar-overflow")?.removeAttribute("open"); updateShareUrl(true); });
    document.getElementById("reportButton").addEventListener("click", () => { document.querySelector(".toolbar-overflow")?.removeAttribute("open"); generateContextReport(); });
    document.getElementById("downloadButton").addEventListener("click", () => { document.querySelector(".toolbar-overflow")?.removeAttribute("open"); downloadContextCsv(); });
    map.on("click", (event) => {
      if (state.candidateDropMode) dropCandidate(event.latlng);
    });
    map.on("zoomstart", () => {
      markerById.forEach(resetMarkerPosition);
      centreMarkerById.forEach(resetMarkerPosition);
    });
    map.on("zoomend", () => {
      refreshStoreMarkerVisibility();
      repositionCloseZoomMarkers();
      repositionFocusedPlaceMarkers();
    });
    map.on("moveend", () => {
      if (["health", "transport", "parking"].some((layer) => state.activeLayers.has(layer))) loadAmenities();
      repositionCloseZoomMarkers();
      repositionFocusedPlaceMarkers();
      updateShareUrl(false);
    });
    window.addEventListener("resize", () => map.invalidateSize());
  }

  function openGlossaryDetail() {
    elements.detailContent.innerHTML = `
      <header class="detail-header glossary-header" style="--brand-color:#168095">
        <span class="retailer-tag"><i data-lucide="book-open"></i>Plain-English reference</span>
        <h2>Leasing intelligence glossary</h2>
        <address>Definitions used throughout the public tool.</address>
      </header>
      <section class="detail-section glossary-intro"><p>These definitions explain how the tool uses each term. They are working leasing-intelligence definitions, not legal or accounting advice.</p></section>
      <section class="detail-section"><dl class="glossary-list">${state.glossary.map((item) => `<div><dt>${escapeHtml(item.term)}</dt><dd>${escapeHtml(item.definition)}</dd></div>`).join("")}</dl></section>`;
    openDetailPanel();
    refreshIcons();
  }

  function openTourDetail() {
    elements.detailContent.innerHTML = `
      <header class="detail-header tour-header" style="--brand-color:#168095">
        <span class="retailer-tag"><i data-lucide="compass"></i>Five-minute platform tour</span>
        <h2>From market map to client brief</h2>
        <address>The quickest path through the public leasing-intelligence workflow.</address>
      </header>
      <section class="detail-section tour-intro"><p><strong>Recommended client flow:</strong> find an opportunity, understand why it ranks, inspect competition and leasing, save it to the shortlist, then export a brief.</p></section>
      <section class="detail-section"><h3>The six main views</h3><ol class="tour-steps">
        <li><strong>Network</strong><span>Filter and inspect individual optical stores. The headline shows the selected subset and the full census total.</span></li>
        <li><strong>Places</strong><span>Browse recognised shopping centres and high-street corridors, their exact mapped optical tenants, and researched public property facts.</span></li>
        <li><strong>Opportunity</strong><span>Rank Bailey-free places using a transparent lookalike screen. Score means similarity; completeness means how much evidence was available.</span></li>
        <li><strong>Trends</strong><span>Review recorded openings, closures, relocations and source freshness. This depends on reconciled historical snapshots.</span></li>
        <li><strong>Compare</strong><span>Place hypothetical candidate points side by side. A candidate uses the public demographic area containing the clicked point plus nearby network evidence.</span></li>
        <li><strong>Data Health</strong><span>See what is mapped, current, researched or still incomplete before relying on a result.</span></li>
      </ol></section>
      <section class="detail-section"><h3>Map tools</h3><dl class="tour-actions">
        <div><dt>Layers</dt><dd>Turn demographics, population growth, development signals, competition and amenities on or off.</dd></div>
        <div><dt>Store comparison</dt><dd>Add two stores from their details, then open Compare to see their straight-line distance.</dd></div>
        <div><dt>Candidate</dt><dd>Click an exact hypothetical site on the map for screening. This is separate from inspecting an existing store or place.</dd></div>
        <div><dt>Save view</dt><dd>Save the current filters, map position and public candidate points in this browser. It is local, not shared.</dd></div>
        <div><dt>Share</dt><dd>Copy a public-safe URL containing the current view and filters. Local corrections, shortlist entries and private performance data are excluded.</dd></div>
        <div><dt>Brief</dt><dd>Print the open place’s client brief, or the selected candidate brief. Open the item you want first.</dd></div>
        <div><dt>Export</dt><dd>Download the records relevant to the current view: stores, places, opportunity results or candidate comparison.</dd></div>
      </dl></section>
      <section class="detail-section"><h3>Clicks and comparison</h3><p>Clicking a <strong>store</strong> opens that store and nearby retailers. Clicking a <strong>place</strong> opens the centre or corridor, exact-place optical tenants and nearby competition. Turning on <strong>Candidate</strong> changes a blank map click into a hypothetical site. Existing markers keep their normal detail behaviour, which avoids mixing inspection with candidate creation.</p></section>
      <section class="detail-section"><h3>Retail environment search</h3><p>Explore locations supports required and preferred brands or categories. Commercial comparison inputs belong in the separate private workspace.</p></section>
      <section class="detail-section source-block"><i data-lucide="shield-check"></i><div><strong>Use Data Health as the caveat page</strong><span>The map is broad; property research, co-tenancy and demographic availability are not equally complete for every place.</span></div></section>`;
    openDetailPanel();
    refreshIcons();
  }

  async function loadJson(path) {
    const response = await fetch(path, { cache: "no-store" });
    if (!response.ok) throw new Error(`${path} returned ${response.status}`);
    return response.json();
  }

  async function initialise() {
    try {
      const [stores, markets, places, links, events, profiles, dataHealth, lookalikes, propertyIntelligence, retailerRegistry, placeTenants, developmentSignals, glossary, marketPoints, destinationResearch, destinationProfiles, environments] = await Promise.all([
        loadJson("data/optical_stores.geojson"),
        loadJson("data/sa2_market.geojson"),
        loadJson("data/retail_places.json"),
        loadJson("data/store_market_links.json"),
        loadJson("data/network_events.json"),
        loadJson("data/brand_profiles.json"),
        loadJson("data/data_health.json"),
        loadJson("data/lookalike_places.json"),
        loadJson("data/property_intelligence.json"),
        loadJson("data/retailer_registry.json"),
        loadJson("data/place_tenants.json"),
        loadJson("data/growth_development_signals.json"),
        loadJson("data/glossary.json"),
        loadJson("data/market_point_links.json"),
        loadJson("data/destination_research.json"),
        loadJson("data/destination_profiles.json"),
        loadJson("data/retail_environments.json"),
      ]);
      state.environments = environments;
      state.privateOverlayActive = Boolean(environments.metadata?.local_evidence);
      if (state.privateOverlayActive) updateShareUrl(false);
      configureRetailers(retailerRegistry);
      state.metadata = stores.metadata || {};
      state.allStores = stores.features.map((feature) => ({
        ...feature.properties,
        latitude: Number(feature.geometry.coordinates[1]),
        longitude: Number(feature.geometry.coordinates[0]),
      }));
      if (state.allStores.length !== state.metadata.store_count) {
        throw new Error("Store data count does not match metadata");
      }
      state.markets = markets.features;
      state.marketMetadata = markets.metadata || {};
      state.marketPointLinks = marketPoints.links || {};
      state.centres = places.places;
      state.placeIdRemaps = places.place_id_remaps || {};
      state.placeTenants = placeTenants.memberships || [];
      state.destinationResearch = Object.fromEntries((destinationResearch.profiles || []).map(profile => [profile.place_id, profile]));
      state.destinationProfiles = Object.fromEntries((destinationProfiles.profiles || []).map(profile => [profile.place_id, profile]));
      state.placeTenantMetadata = placeTenants.metadata || {};
      state.developmentSignals = developmentSignals.signals || [];
      state.developmentMetadata = developmentSignals.metadata || {};
      state.glossary = glossary.terms || [];
      loadLocalPlaces();
      state.storeLinks = links.links;
      state.events = events;
      state.profiles = profiles.profiles;
      state.dataHealth = dataHealth;
      state.lookalikes = lookalikes;
      state.propertyIntelligence = propertyIntelligence;
      state.propertyGroups = propertyIntelligence.groups || [];
      state.basePropertyRelationships = propertyIntelligence.relationships || [];
      state.propertyRelationships = state.basePropertyRelationships.slice();
      state.propertySummaries = propertyIntelligence.property_summaries || {};
      state.groupPortfolios = propertyIntelligence.group_portfolios || {};
      state.allStores.forEach((store) => {
        const certification = dataHealth.store_certification?.[store.store_id] || {};
        store.operational_status = certification.operational_status || "Limited";
        store.usable_for_network = certification.usable_for_network === "true";
        store.current_source = certification.current_source === "true";
        store.eligible_for_analytics = certification.eligible_for_analytics === "true";
        store.eligible_for_place_analytics = certification.eligible_for_place_analytics === "true";
        store.certification_issues = certification.issues || "Certification record missing";
        store.location_setting = certification.location_setting || "Uncertain";
        store.place_id = certification.place_id || "";
        store.mapping_confidence = certification.mapping_confidence || "Uncertain";
        store.original_place_id = store.place_id;
        store.mapping_evidence_url = store.source_url || store.official_url || "";
        const place = state.centres.find((item) => item.place_id === store.place_id);
        store.venue_id = store.place_id;
        store.venue_name = place?.name || "";
        store.location_type = store.location_setting;
      });
      loadConsultantCorrections();
      applyConsultantCorrections();
      loadPropertyCorrections();
      applyPropertyCorrections();
      loadPlaceShortlist();
      createStoreMarkers();
      createCentreMarkers();
      createDevelopmentMarkers();
      bindGlobalEvents();
      const restoredView = restoreShareState();
      exploration.defaults.network.retailers = new Set(DEFAULT_RETAILERS);
      elements.detailPanel.inert = true;
      applyFilters(false);
      if (!restoredView) map.fitBounds(NETWORK_BOUNDS, { padding: [18, 18] });
      updateLayerVisibility();
      setView(state.view);
      renderCandidateDock();
      elements.freshness.textContent = environments.metadata?.local_evidence
        ? `Unified local evidence · ${environments.metadata.snapshot_id} · source dates vary`
        : dataHealth.generated_at
        ? `Data built ${formatDate(dataHealth.generated_at)} · source dates vary`
        : "Build date unavailable · source dates vary";
      document.getElementById("evidenceButton").addEventListener("click", () => setView("health"));
      elements.loading.classList.add("hidden");
      refreshIcons();
      window.LocalCoverageView?.initialise({map, onPrivacyChange: active => {
        state.privateOverlayActive = active;
        document.getElementById('candidateButton').disabled = active;
        if (active) updateShareUrl(false);
      }});
    } catch (error) {
      elements.loading.innerHTML = `<strong>Leasing intelligence could not load</strong><span>${escapeHtml(error.message)}</span><button type="button" id="retryLoad">Retry loading</button>`;
      document.getElementById("retryLoad").onclick = () => window.location.reload();
    }
  }

  window.OpticalMapUtils = {
    haversine: Intel.haversine,
    formatDistance: Intel.formatDistance,
    candidateScore: Intel.candidateScore,
  };
  refreshIcons();
  initialise();
})();
