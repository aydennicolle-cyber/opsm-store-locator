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
      color: "#6b5b4b",
      slug: "independent-other",
      short: "IND",
      mark: "IND",
      markerWidth: 34,
    },
  };
  const VIEW_CONFIG = {
    network: {
      eyebrow: "Retail footprint",
      title: "Network",
      subtitle: "Filter, inspect and compare the trans-Tasman optical network.",
    },
    centres: {
      eyebrow: "Landlord intelligence",
      title: "Places",
      subtitle: "Browse centres, plazas and high-street corridors with mapped optical tenants.",
    },
    opportunity: {
      eyebrow: "Lookalike screening",
      title: "Opportunity",
      subtitle: "Find centres and corridors that resemble Bailey Nelson's current footprint.",
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
    storeCompareButton: document.getElementById("storeCompareButton"),
    candidateButton: document.getElementById("candidateButton"),
    storeCompareTray: document.getElementById("storeCompareTray"),
    compareA: document.getElementById("compareA"),
    compareB: document.getElementById("compareB"),
    compareDistance: document.getElementById("compareDistance"),
    candidateDock: document.getElementById("candidateDock"),
    candidateDockCount: document.getElementById("candidateDockCount"),
    candidateCards: document.getElementById("candidateCards"),
    toast: document.getElementById("toast"),
    reportSheet: document.getElementById("reportSheet"),
    reportContent: document.getElementById("reportContent"),
  };

  const state = {
    view: "network",
    allStores: [],
    retailerRegistry: [],
    affiliations: [],
    filteredStores: [],
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
    placeTenantMetadata: {},
    glossary: [],
    developmentSignals: [],
    developmentMetadata: {},
    placeIdRemaps: {},
    placeShortlist: new Set(),
    performanceBenchmark: null,
    consultantCorrections: [],
    localPlaces: [],
    selectedStoreId: "",
    selectedCentreId: "",
    selectedCandidateId: "",
    focusedPlaceId: "",
    storeCompareMode: false,
    candidateDropMode: false,
    compareStores: [],
    candidates: [],
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
    activeLayers: new Set(["centres"]),
    amenityMarkers: [],
    amenitySummary: null,
  };

  const markerById = new Map();
  const centreMarkerById = new Map();
  const candidateMarkerById = new Map();
  let compareLine = null;
  let demographicLayer = null;
  let growthLayer = null;
  let saturationLayer = null;
  let amenityRequestController = null;
  let toastTimer = null;
  const CORRECTION_STORAGE_KEY = "bailey-leasing-place-corrections-v2";
  const LOCAL_PLACE_STORAGE_KEY = "bailey-leasing-local-places-v1";
  const PROPERTY_CORRECTION_STORAGE_KEY = "bailey-leasing-property-corrections-v1";
  const LOCAL_PROPERTY_GROUP_STORAGE_KEY = "bailey-leasing-local-property-groups-v1";
  const PLACE_SHORTLIST_STORAGE_KEY = "bailey-leasing-place-shortlist-v1";

  const map = L.map("map", { zoomControl: false, preferCanvas: true }).setView(
    AUSTRALIA_VIEW.center,
    AUSTRALIA_VIEW.zoom
  );
  L.control.zoom({ position: "bottomright" }).addTo(map);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
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
  const centreLayer = L.layerGroup().addTo(map);
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
      color: item.color,
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
    return Number.isFinite(number) ? `${number.toLocaleString("en-AU")}${suffix}` : "Not published";
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
    const width = BRAND_CONFIG[store.retailer].markerWidth;
    return L.divIcon({
      className,
      html: `<div class="store-logo-marker">${brandMarkHtml(store.retailer, "map")}</div>`,
      iconSize: [width, 26],
      iconAnchor: [width / 2, 13],
    });
  }

  function createStoreMarkers() {
    state.allStores.forEach((store) => {
      const marker = L.marker([store.latitude, store.longitude], {
        icon: storeIcon(store),
        retailer: store.retailer,
        storeId: store.store_id,
        title: store.name,
        baseLatitude: store.latitude,
        baseLongitude: store.longitude,
      });
      marker.on("click", () => selectStore(store.store_id, false));
      marker.bindTooltip(
        `<strong>${escapeHtml(store.name)}</strong><br>${escapeHtml(store.suburb)}, ${escapeHtml(store.state)}`,
        { direction: "top", offset: [0, -8] }
      );
      markerById.set(store.store_id, marker);
    });
  }

  function createCentreMarkers() {
    centreLayer.clearLayers();
    centreMarkerById.clear();
    state.centres.forEach((centre) => {
      if (!Number.isFinite(Number(centre.latitude)) || !Number.isFinite(Number(centre.longitude))) return;
      const isCorridor = centre.location_setting === "High Street";
      const marker = L.marker([centre.latitude, centre.longitude], {
        icon: L.divIcon({
          className: "",
          html: `<div class="centre-pin ${isCorridor ? "corridor-pin" : ""}">${
            isCorridor ? '<i data-lucide="route"></i>' : CENTRE_BAG_SVG
          }</div>`,
          iconSize: [26, 26],
          iconAnchor: [13, 13],
        }),
        title: centre.name,
        baseLatitude: Number(centre.latitude),
        baseLongitude: Number(centre.longitude),
        placeId: centre.place_id,
        zIndexOffset: 900,
      });
      marker.bindTooltip(
        `<strong>${escapeHtml(centre.name)}</strong><br>${escapeHtml(centre.place_type)} · ${centre.optical_store_count} mapped optical ${centre.optical_store_count === 1 ? "store" : "stores"}`,
        { direction: "top", offset: [0, -8] }
      );
      marker.on("click", () => openCentreDetail(centre));
      marker.addTo(centreLayer);
      centreMarkerById.set(centre.place_id, marker);
    });
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
    marker.setLatLng([marker.options.baseLatitude, marker.options.baseLongitude]);
  }

  function repositionCloseZoomMarkers() {
    markerById.forEach(resetMarkerPosition);
    centreMarkerById.forEach(resetMarkerPosition);
    if (map.getZoom() < 16) return;

    const groupedStores = new Map();
    state.filteredStores.forEach((store) => {
      const key = store.place_id || `${Number(store.latitude).toFixed(5)}:${Number(store.longitude).toFixed(5)}`;
      if (!groupedStores.has(key)) groupedStores.set(key, []);
      groupedStores.get(key).push(store);
    });
    groupedStores.forEach((stores) => {
      if (stores.length < 2) return;
      const centre = state.centres.find((place) => place.place_id === stores[0].place_id);
      const anchor = centre
        ? L.latLng(Number(centre.latitude), Number(centre.longitude))
        : L.latLng(
            stores.reduce((sum, store) => sum + Number(store.latitude), 0) / stores.length,
            stores.reduce((sum, store) => sum + Number(store.longitude), 0) / stores.length
          );
      const point = map.latLngToLayerPoint(anchor);
      const radius = stores.length > 4 ? 50 : 38;
      stores
        .slice()
        .sort((left, right) => left.store_id.localeCompare(right.store_id))
        .forEach((store, index) => {
          const angle = -Math.PI / 2 + (Math.PI * 2 * index) / stores.length;
          const offset = L.point(Math.cos(angle) * radius, Math.sin(angle) * radius);
          markerById.get(store.store_id)?.setLatLng(map.layerPointToLatLng(point.add(offset)));
        });
    });

    centreMarkerById.forEach((marker, placeId) => {
      if (!centreLayer.hasLayer(marker)) return;
      const place = state.centres.find((item) => item.place_id === placeId);
      const base = L.latLng(marker.options.baseLatitude, marker.options.baseLongitude);
      const point = map.latLngToLayerPoint(base);
      const mappedStoreCount = state.filteredStores.filter((store) => store.place_id === placeId).length;
      const distance = mappedStoreCount > 4 ? 110 : mappedStoreCount > 1 ? 90 : 58;
      const offset = place?.location_setting === "High Street" ? L.point(distance, 0) : L.point(-distance, 0);
      marker.setLatLng(map.layerPointToLatLng(point.add(offset)));
    });
  }

  function updateCentreMarkersForFilters() {
    const visibleVenueIds = state.view === "centres"
      ? new Set(filteredPlaces().map((place) => place.place_id))
      : state.view === "opportunity"
        ? new Set(performanceAdjustedLookalikes().map((place) => place.place_id))
        : new Set(state.filteredStores.map((store) => store.place_id).filter(Boolean));
    centreLayer.clearLayers();
    visibleVenueIds.forEach((venueId) => {
      const marker = centreMarkerById.get(venueId);
      if (marker) centreLayer.addLayer(marker);
    });
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
    state.view = view;
    document.body.dataset.activeView = view;
    document.querySelectorAll("[data-view]").forEach((button) => {
      button.classList.toggle("active", button.dataset.view === view);
    });
    const config = VIEW_CONFIG[view];
    elements.viewEyebrow.textContent = config.eyebrow;
    elements.viewTitle.textContent = config.title;
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
    updateCentreMarkersForFilters();
    updateShareUrl(false);
  }

  function renderView() {
    if (state.view === "network") renderNetworkView();
    else if (state.view === "centres") renderCentresView();
    else if (state.view === "opportunity") renderOpportunityView();
    else if (state.view === "trends") renderTrendsView();
    else if (state.view === "compare") renderCompareView();
    else renderDataHealthView();
    refreshIcons();
  }

  function retailerOptionsHtml() {
    let previousType = "";
    return BRAND_ORDER.map((retailer) => {
      const config = BRAND_CONFIG[retailer];
      const count = state.allStores.filter(
        (store) => store.retailer === retailer && storeMatchesFilters(store, true)
      ).length;
      const heading = config.networkType !== previousType
        ? `<span class="retailer-group-label">${config.networkType === "primary" ? "Core networks" : config.networkType === "additional" ? "Additional networks · markers from zoom 8" : "Background discovery · markers from zoom 10"}</span>`
        : "";
      previousType = config.networkType;
      return `${heading}<label class="retailer-option" data-retailer="${escapeHtml(retailer)}">
        <input type="checkbox" value="${escapeHtml(retailer)}" ${state.filters.retailers.has(retailer) ? "checked" : ""} />
        ${brandMarkHtml(retailer, "filter")}
        <span title="${escapeHtml(retailer)}">${escapeHtml(retailer)}</span><output>${count}</output>
      </label>`;
    }).join("");
  }

  function filterOptions(values, selected, emptyLabel) {
    return `<option value="">${emptyLabel}</option>${values
      .map((value) => `<option ${value === selected ? "selected" : ""}>${escapeHtml(value)}</option>`)
      .join("")}`;
  }

  function renderNetworkView() {
    const countryStores = state.filters.country
      ? state.allStores.filter((store) => store.country === state.filters.country)
      : state.allStores;
    const countries = [...new Set(state.allStores.map((store) => store.country))].sort();
    const states = [...new Set(countryStores.map((store) => store.state))].sort();
    const statuses = [...new Set(state.allStores.map((store) => store.status))].sort();
    elements.viewContent.innerHTML = `
      <section class="filters" aria-label="Network filters">
        <label class="search-field"><i data-lucide="search"></i><span class="sr-only">Search stores</span>
          <input id="searchInput" type="search" value="${escapeHtml(state.filters.search)}" placeholder="Store, suburb or postcode" autocomplete="off" />
        </label>
        <fieldset class="retailer-filter"><legend>Retailer</legend>
          <div class="retailer-filter-actions">
            <button id="selectAllRetailers" type="button">Select all</button>
            <button id="clearAllRetailers" type="button">Clear all</button>
          </div>
          ${retailerOptionsHtml()}
        </fieldset>
        <div class="select-grid">
          <label><span>Country</span><select id="countrySelect">${filterOptions(
            countries,
            state.filters.country,
            "Australia + New Zealand"
          )}</select></label>
          <label><span>State / region</span><select id="stateSelect">${filterOptions(
            states,
            state.filters.state,
            "All states / regions"
          )}</select></label>
          <label><span>Location setting</span><select id="locationSelect">${filterOptions(
            ["Shopping Centre", "High Street", "Other", "Uncertain"],
            state.filters.location,
            "All locations"
          )}</select></label>
          <label><span>Audiology</span><select id="audiologySelect">
            <option value="">Any</option><option value="true" ${state.filters.audiology === "true" ? "selected" : ""}>Available</option>
            <option value="false" ${state.filters.audiology === "false" ? "selected" : ""}>Not listed</option>
          </select></label>
          <label><span>Status</span><select id="statusSelect">${filterOptions(statuses, state.filters.status, "All statuses")}</select></label>
          <label><span>Affiliation</span><select id="affiliationSelect"><option value="">Any affiliation</option>${state.affiliations
            .map((item) => `<option value="${escapeHtml(item.affiliation_id)}" ${state.filters.affiliation === item.affiliation_id ? "selected" : ""}>${escapeHtml(item.name)}${item.status === "partial" ? " · partial coverage" : ""}</option>`)
            .join("")}</select></label>
        </div>
        <label class="service-field"><span>Service</span><input id="serviceInput" value="${escapeHtml(
          state.filters.service
        )}" type="search" placeholder="e.g. dry eye, contact lens" /></label>
      </section>
      <section class="result-section">
        <div class="section-heading"><h2>Locations</h2><span id="networkResultCount"></span></div>
        <div class="store-list" id="storeList"></div>
      </section>`;
    renderNetworkResults();
    bindNetworkView();
  }

  function renderNetworkResults() {
    const rows = state.filteredStores.slice(0, 100);
    const count = document.getElementById("networkResultCount");
    const list = document.getElementById("storeList");
    if (!count || !list) return;
    count.textContent = `${state.filteredStores.length.toLocaleString("en-AU")} results`;
    list.innerHTML = `${rows.map(storeRowHtml).join("")}${
      state.filteredStores.length > rows.length
        ? `<div class="list-limit">Showing the first ${rows.length} locations. Refine filters to narrow the list.</div>`
        : ""
    }${rows.length ? "" : '<div class="list-limit">No locations match these filters.</div>'}`;
    document.querySelectorAll(".retailer-option").forEach((option) => {
      const output = option.querySelector("output");
      if (!output) return;
      output.textContent = state.allStores
        .filter(
          (store) =>
            store.retailer === option.dataset.retailer && storeMatchesFilters(store, true)
        )
        .length.toLocaleString("en-AU");
    });
  }

  function storeRowHtml(store) {
    return `<button class="store-row ${store.store_id === state.selectedStoreId ? "active" : ""}" data-store-id="${escapeHtml(
      store.store_id
    )}" data-retailer="${escapeHtml(store.retailer)}">
      ${brandMarkHtml(store.retailer, "list")}<span class="row-copy"><strong>${escapeHtml(store.name)}</strong>
      <small>${escapeHtml(`${store.suburb}, ${store.state} ${store.postcode}`)}</small></span>
      <span class="row-type">${escapeHtml(store.location_type)}</span></button>`;
  }

  function bindNetworkView() {
    const search = document.getElementById("searchInput");
    const service = document.getElementById("serviceInput");
    search.addEventListener("input", () => {
      state.filters.search = search.value;
      applyFilters(false);
      renderNetworkResults();
    });
    service.addEventListener("input", () => {
      state.filters.service = service.value;
      applyFilters(false);
      renderNetworkResults();
    });
    [
      ["countrySelect", "country"],
      ["stateSelect", "state"],
      ["locationSelect", "location"],
      ["audiologySelect", "audiology"],
      ["statusSelect", "status"],
      ["affiliationSelect", "affiliation"],
    ].forEach(([id, key]) => {
      document.getElementById(id).addEventListener("change", (event) => {
        state.filters[key] = event.target.value;
        if (key === "affiliation" && event.target.value) {
          state.allStores
            .filter((store) => String(store.affiliations || "").split("|").includes(event.target.value))
            .forEach((store) => state.filters.retailers.add(store.retailer));
        }
        if (key === "country") state.filters.state = "";
        applyFilters();
        if (key === "country") {
          if (state.filters.country === "Australia") {
            map.setView(AUSTRALIA_VIEW.center, AUSTRALIA_VIEW.zoom);
          } else if (state.filters.country === "New Zealand") {
            map.setView(NEW_ZEALAND_VIEW.center, NEW_ZEALAND_VIEW.zoom);
          } else {
            map.fitBounds(NETWORK_BOUNDS, { padding: [18, 18] });
          }
        }
      });
    });
    document.querySelectorAll('.retailer-option input[type="checkbox"]').forEach((input) => {
      input.addEventListener("change", () => {
        if (input.checked) state.filters.retailers.add(input.value);
        else state.filters.retailers.delete(input.value);
        applyFilters(false);
        renderNetworkResults();
      });
    });
    document.getElementById("selectAllRetailers").addEventListener("click", () => {
      state.filters.retailers = new Set(BRAND_ORDER);
      document.querySelectorAll('.retailer-option input[type="checkbox"]').forEach((input) => { input.checked = true; });
      applyFilters(false);
      renderNetworkResults();
    });
    document.getElementById("clearAllRetailers").addEventListener("click", () => {
      state.filters.retailers.clear();
      document.querySelectorAll('.retailer-option input[type="checkbox"]').forEach((input) => { input.checked = false; });
      applyFilters(false);
      renderNetworkResults();
    });
    document.getElementById("storeList").addEventListener("click", (event) => {
      const row = event.target.closest("[data-store-id]");
      if (row) selectStore(row.dataset.storeId, true);
    });
  }

  function storeMatchesFilters(store, ignoreRetailer = false) {
    const query = state.filters.search.trim().toLowerCase();
    const serviceQuery = state.filters.service.trim().toLowerCase();
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
      (!state.filters.affiliation || String(store.affiliations || "").split("|").includes(state.filters.affiliation)) &&
      (!serviceQuery || store.services.toLowerCase().includes(serviceQuery))
    );
  }

  function applyFilters(render = true) {
    state.filteredStores = state.allStores.filter((store) => storeMatchesFilters(store));
    refreshStoreMarkerVisibility();
    updateCentreMarkersForFilters();
    if (state.view === "network") {
      elements.visibleTotal.textContent = state.filteredStores.length.toLocaleString("en-AU");
      elements.visibleTotalLabel.textContent = `selected of ${(Number(state.metadata.store_count) || state.allStores.length).toLocaleString("en-AU")} census stores`;
    }
    if (render && state.view === "network") renderNetworkView();
    updateSaturationLayer();
    updateShareUrl(false);
    window.requestAnimationFrame(repositionCloseZoomMarkers);
  }

  function refreshStoreMarkerVisibility() {
    storeClusters.clearLayers();
    if (state.focusedPlaceId) return;
    const zoom = map.getZoom();
    state.filteredStores.forEach((store) => {
      if (zoom < (BRAND_CONFIG[store.retailer]?.minMarkerZoom || 0)) return;
      const marker = markerById.get(store.store_id);
      if (marker) storeClusters.addLayer(marker);
    });
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
          if (!store || (entries.has(store.store_id) && entries.get(store.store_id).priority <= priority)) return;
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
    const inPlace = [...focusedStoreMarkerById.values()].filter((marker) => marker.options.focusCategory === "in_centre");
    if (inPlace.length) {
      const anchor = L.latLng(Number(place.latitude), Number(place.longitude));
      const point = map.latLngToLayerPoint(anchor);
      const radius = inPlace.length > 5 ? 68 : 54;
      inPlace
        .sort((left, right) => left.options.storeId.localeCompare(right.options.storeId))
        .forEach((marker, index) => {
          const angle = -Math.PI / 2 + (Math.PI * 2 * index) / inPlace.length;
          const offset = L.point(Math.cos(angle) * radius, Math.sin(angle) * radius);
          marker.setLatLng(map.layerPointToLatLng(point.add(offset)));
        });
    }
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
    if (!place || !Number.isFinite(Number(place.latitude)) || !Number.isFinite(Number(place.longitude))) return;
    clearPlaceFocus(false);
    state.focusedPlaceId = place.place_id;
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

  function renderCentresView() {
    const centres = state.centres.filter((place) => place.location_setting === "Shopping Centre").length;
    const corridors = state.centres.filter((place) => place.location_setting === "High Street").length;
    elements.viewContent.innerHTML = `
      <section class="filters">
        <label class="search-field"><i data-lucide="search"></i><span class="sr-only">Search retail places</span>
          <input id="centreSearch" type="search" value="${escapeHtml(state.placeFilters.search)}" placeholder="Centre, corridor, suburb, owner or manager" />
        </label>
        <div class="select-grid place-filter-grid">
          <label><span>Country</span><select id="placeCountry">${filterOptions(["Australia", "New Zealand"], state.placeFilters.country, "All countries")}</select></label>
          <label><span>Place type</span><select id="placeType">${filterOptions(["Shopping Centre", "High Street Corridor"], state.placeFilters.type, "Centres + corridors")}</select></label>
          <label><span>Bailey Nelson</span><select id="placeBailey">${filterOptions(["Present", "Absent"], state.placeFilters.bailey, "Present or absent")}</select></label>
          <label><span>Confidence</span><select id="placeConfidence">${filterOptions(["High", "Medium", "Uncertain"], state.placeFilters.confidence, "Any confidence")}</select></label>
          <label><span>Property group</span><select id="placeGroup"><option value="">All property groups</option>${state.propertyGroups
            .filter((group) => Number(state.groupPortfolios[group.group_id]?.property_count || 0))
            .sort((a, b) => a.canonical_name.localeCompare(b.canonical_name))
            .map((group) => `<option value="${escapeHtml(group.group_id)}" ${state.placeFilters.group_id === group.group_id ? "selected" : ""}>${escapeHtml(group.canonical_name)}</option>`).join("")}</select></label>
          <label><span>Leasing arrangement</span><select id="placeArrangement">${filterOptions(["In-house", "External agency", "Private landlord", "Unknown"], state.placeFilters.arrangement, "Any arrangement")}</select></label>
          <label><span>Portfolio overlap</span><select id="placeOverlap">${filterOptions(["SAME_CENTRE", "LEASING_CONTROLLER_OVERLAP", "PROPERTY_GROUP_OVERLAP", "EXTERNAL_AGENCY_OVERLAP", "NO_KNOWN_OVERLAP", "UNKNOWN"], state.placeFilters.overlap, "Any overlap status")}</select></label>
          <label><span>Centre class</span><select id="placeCentreClass">${filterOptions(["Super Regional", "Regional", "Sub-regional", "Neighbourhood", "CBD / Mixed-use", "Outlet", "Large Format", "Other", "Unknown"], state.placeFilters.centre_class, "Any centre class")}</select></label>
          <label><span>Minimum equivalised weekly income</span><input id="placeMinIncome" type="number" min="0" step="100" value="${escapeHtml(state.placeFilters.min_income)}" placeholder="No minimum" /></label>
          <label><span>Minimum nearest BN (km)</span><input id="placeMinBailey" type="number" min="0" step="1" value="${escapeHtml(state.placeFilters.min_bailey_distance)}" placeholder="No minimum" /></label>
          <label><span>Sort results</span><select id="placeSort">${filterOptions(["name", "optical_tenants", "household_income", "nearest_bailey", "portfolio_white_space"], state.placeFilters.sort, "Sort by")}</select></label>
        </div>
        <fieldset class="place-retailer-filter"><legend>Require every selected retailer</legend>${BRAND_ORDER.filter((brand) => BRAND_CONFIG[brand].networkType !== "background").map((brand) => `<label><input type="checkbox" value="${escapeHtml(brand)}" ${state.placeFilters.retailers.has(brand) ? "checked" : ""} />${brandMarkHtml(brand, "compact")}<span>${escapeHtml(brand)}</span></label>`).join("")}</fieldset>
        <div class="button-row place-actions">
          <button class="secondary-command" id="exportCorrections" type="button"><i data-lucide="download"></i>Export local corrections (${state.consultantCorrections.length})</button>
          <button class="secondary-command" id="importCorrections" type="button"><i data-lucide="upload"></i>Import corrections CSV</button>
          <input id="correctionFile" type="file" accept=".csv,text/csv" hidden />
          <button class="secondary-command" id="exportPropertyCorrections" type="button"><i data-lucide="building-2"></i>Export property corrections (${state.propertyCorrections.length + state.localPropertyGroups.length})</button>
          <button class="secondary-command" id="importPropertyCorrections" type="button"><i data-lucide="file-up"></i>Import property corrections</button>
          <input id="propertyCorrectionFile" type="file" accept=".csv,text/csv" hidden />
        </div>
        <div class="compact-metrics">
          <div><strong>${centres}</strong><span>centres and plazas</span></div>
          <div><strong>${corridors}</strong><span>high-street corridors</span></div>
          <div><strong>${state.centres.filter((place) => place.has_bailey).length}</strong><span>with Bailey Nelson</span></div>
        </div>
      </section>
      <section class="result-section">
        <div class="section-heading"><h2>Retail place profiles</h2><span id="centreResultCount"></span></div>
        <div class="centre-list" id="centreList"></div>
      </section>`;
    renderCentreResults();
    document.getElementById("centreSearch").addEventListener("input", (event) => {
      state.placeFilters.search = event.target.value;
      renderCentreResults();
    });
    [["placeCountry", "country"], ["placeType", "type"], ["placeBailey", "bailey"], ["placeConfidence", "confidence"], ["placeGroup", "group_id"], ["placeArrangement", "arrangement"], ["placeOverlap", "overlap"], ["placeCentreClass", "centre_class"], ["placeSort", "sort"]].forEach(([id, key]) => {
      document.getElementById(id).addEventListener("change", (event) => {
        state.placeFilters[key] = event.target.value;
        renderCentreResults();
      });
    });
    [["placeMinIncome", "min_income"], ["placeMinBailey", "min_bailey_distance"]].forEach(([id, key]) => {
      document.getElementById(id).addEventListener("input", (event) => {
        state.placeFilters[key] = event.target.value;
        renderCentreResults();
      });
    });
    document.querySelectorAll('.place-retailer-filter input[type="checkbox"]').forEach((input) => {
      input.addEventListener("change", () => {
        if (input.checked) state.placeFilters.retailers.add(input.value);
        else state.placeFilters.retailers.delete(input.value);
        renderCentreResults();
      });
    });
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
    document.getElementById("centreList").addEventListener("click", (event) => {
      const row = event.target.closest("[data-place-id]");
      if (!row) return;
      const centre = state.centres.find((item) => item.place_id === row.dataset.placeId);
      openCentreDetail(centre);
    });
  }

  function filteredPlaces() {
    const query = state.placeFilters.search.trim().toLowerCase();
    return state.centres.filter((place) => {
      const groupNames = (place.group_ids || []).map((groupId) => propertyGroup(groupId)?.canonical_name || "").join(" ");
      const haystack = `${place.name} ${(place.aliases || []).join(" ")} ${place.locality} ${place.suburb} ${place.state} ${place.owner} ${place.manager} ${groupNames}`.toLowerCase();
      const income = Number(place.market?.median_household_income || place.market?.median_equivalised_household_income_weekly_2021 || 0);
      const nearestBailey = Number(place.nearest_bailey_km);
      return (
        (!query || haystack.includes(query)) &&
        (!state.placeFilters.country || place.country === state.placeFilters.country) &&
        (!state.placeFilters.type || place.place_type === state.placeFilters.type) &&
        (!state.placeFilters.bailey || (state.placeFilters.bailey === "Present") === Boolean(place.has_bailey)) &&
        ([...state.placeFilters.retailers].every((retailer) => (place.retailers || []).includes(retailer))) &&
        (!state.placeFilters.confidence || place.mapping_confidence === state.placeFilters.confidence || place.confidence === state.placeFilters.confidence) &&
        (!state.placeFilters.group_id || (place.group_ids || []).includes(state.placeFilters.group_id)) &&
        (!state.placeFilters.arrangement || place.leasing_arrangement === state.placeFilters.arrangement) &&
        (!state.placeFilters.overlap || place.portfolio_overlap_status === state.placeFilters.overlap) &&
        (!state.placeFilters.centre_class || place.centre_class === state.placeFilters.centre_class) &&
        (!Number(state.placeFilters.min_income) || income >= Number(state.placeFilters.min_income)) &&
        (!Number(state.placeFilters.min_bailey_distance) || (Number.isFinite(nearestBailey) && nearestBailey >= Number(state.placeFilters.min_bailey_distance)))
      );
    });
  }

  function renderCentreResults() {
    const sorters = {
      name: (a, b) => a.name.localeCompare(b.name),
      optical_tenants: (a, b) => Number(b.optical_store_count) - Number(a.optical_store_count) || a.name.localeCompare(b.name),
      household_income: (a, b) => Number(b.market?.median_household_income || b.market?.median_equivalised_household_income_weekly_2021 || 0) - Number(a.market?.median_household_income || a.market?.median_equivalised_household_income_weekly_2021 || 0) || a.name.localeCompare(b.name),
      nearest_bailey: (a, b) => Number(b.nearest_bailey_km || -1) - Number(a.nearest_bailey_km || -1) || a.name.localeCompare(b.name),
      portfolio_white_space: (a, b) => Number(b.portfolio_white_space) - Number(a.portfolio_white_space) || Number(b.optical_store_count) - Number(a.optical_store_count) || a.name.localeCompare(b.name),
    };
    const centres = filteredPlaces().sort(sorters[state.placeFilters.sort] || sorters.name);
    const count = document.getElementById("centreResultCount");
    const list = document.getElementById("centreList");
    if (!count || !list) return;
    count.textContent = `${centres.length.toLocaleString("en-AU")} results`;
    elements.visibleTotal.textContent = centres.length.toLocaleString("en-AU");
    elements.visibleTotalLabel.textContent = "retail places visible";
    updateCentreMarkersForFilters();
    list.innerHTML = centres
      .slice(0, 300)
      .map(
        (centre) => `<button class="centre-row" data-place-id="${escapeHtml(centre.place_id)}">
          <span class="centre-row-icon ${centre.location_setting === "High Street" ? "corridor" : ""}">${centre.location_setting === "High Street" ? '<i data-lucide="route"></i>' : CENTRE_BAG_SVG}</span>
          <span><strong>${escapeHtml(centre.name)}</strong><small>${escapeHtml(
          `${centre.locality || centre.suburb || "Locality unrecorded"}${centre.state ? `, ${centre.state}` : ""} · ${centre.place_type}`
        )}</small></span>
          <span><strong>${centre.optical_store_count}</strong><small>${centre.retailers.length} brands${centre.has_bailey ? " · BN" : ""}${centre.portfolio_white_space ? " · portfolio white space" : ""}</small></span>
        </button>`
      )
      .join("");
    refreshIcons();
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
      .map((row) => ({ ...row, components: { ...row.components } }));
    const fields = ["population_2025", "population_growth_2021_2025_pct", "age_45_plus_pct_2021", "median_equivalised_household_income_weekly_2021"];
    rows.forEach((row) => {
      const benchmarks = selectedPerformanceBenchmarks(row.location_setting);
      if (!state.performanceBenchmark || benchmarks.length < 2) return;
      const similarities = fields.map((field) => {
        const value = Number(row.market_features?.[field]);
        const target = medianValue(benchmarks.map((benchmark) => Number(benchmark.market_features?.[field])));
        if (!Number.isFinite(value) || !Number.isFinite(target)) return null;
        return Math.max(0, 100 - (Math.abs(value - target) / Math.max(Math.abs(target), 1)) * 100);
      }).filter(Number.isFinite);
      if (similarities.length) row.components.bailey_footprint_similarity = Math.round(similarities.reduce((sum, value) => sum + value, 0) / similarities.length);
      const weights = { bailey_footprint_similarity: 40, bailey_whitespace: 30, optical_market_validation: 20, accessibility_retail_context: 10 };
      const available = Object.keys(weights).filter((key) => {
        const value = row.components[key];
        return value !== null && value !== undefined && value !== "" && Number.isFinite(Number(value));
      });
      row.screening_completeness = available.reduce((sum, key) => sum + weights[key], 0);
      row.score = row.screening_completeness
        ? Math.round(available.reduce((sum, key) => sum + Number(row.components[key]) * weights[key], 0) / row.screening_completeness)
        : null;
    });
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

  function lookalikeRowHtml(row) {
    const components = row.components || {};
    const saved = state.placeShortlist.has(resolvePlaceId(row.place_id));
    return `<div class="lookalike-row">
      <button class="lookalike-open" type="button" data-open-place-id="${escapeHtml(row.place_id)}" aria-label="Open ${escapeHtml(row.name)}">
      <span class="rank-number">${row.rank}</span>
      <span><strong>${escapeHtml(row.name)}</strong><small>${escapeHtml(`${row.location_setting} · ${row.locality || "Locality not recorded"}${row.state ? `, ${row.state}` : ""}`)}</small></span>
      <span class="lookalike-score"><strong>${row.score ?? "—"}</strong><small>lookalike</small></span>
      <span><strong>${row.screening_completeness}%</strong><small>complete</small></span>
      <span class="component-mini"><small>Footprint ${components.bailey_footprint_similarity ?? "—"} · Whitespace ${components.bailey_whitespace ?? "—"} · Optical ${components.optical_market_validation ?? "—"} · Context ${components.accessibility_retail_context ?? "—"}</small></span>
      </button>
      <button class="place-shortlist-toggle ${saved ? "saved" : ""}" type="button" data-shortlist-place-id="${escapeHtml(row.place_id)}" aria-label="${saved ? "Remove from" : "Add to"} shortlist" title="${saved ? "Remove from" : "Add to"} shortlist"><i data-lucide="bookmark${saved ? "-check" : ""}"></i></button>
    </div>`;
  }

  function opportunityShortlistHtml() {
    const entries = shortlistedPlaces();
    const available = entries.filter((item) => item.place);
    const unavailable = entries.length - available.length;
    return `<section class="place-shortlist-panel">
      <div><span><strong>${entries.length}</strong> saved place${entries.length === 1 ? "" : "s"}</span>${unavailable ? `<small>${unavailable} unavailable or awaiting a remap</small>` : ""}</div>
      <div class="button-row">
        <button class="secondary-command" id="exportShortlistSummary" type="button" ${available.length ? "" : "disabled"}>Summary CSV</button>
        <button class="secondary-command" id="exportShortlistTenants" type="button" ${available.length ? "" : "disabled"}>Tenant CSV</button>
        <button class="secondary-command" id="clearPlaceShortlist" type="button" ${entries.length ? "" : "disabled"}>Clear</button>
      </div>
    </section>`;
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
      renderOpportunityView();
      return;
    }
    const usesRank = uniqueMatched.some((row) => Number.isFinite(row.rank));
    uniqueMatched.sort((a, b) => usesRank ? (Number.isFinite(a.rank) ? a.rank : 999999) - (Number.isFinite(b.rank) ? b.rank : 999999) : (Number.isFinite(b.score) ? b.score : -Infinity) - (Number.isFinite(a.score) ? a.score : -Infinity));
    state.performanceBenchmark = { store_ids: uniqueMatched.map((row) => row.store_id).slice(0, 10), matched: uniqueMatched.length, unmatched };
    renderOpportunityView();
    showToast(`Using the best ${state.performanceBenchmark.store_ids.length} matched Bailey stores in memory`);
  }

  function renderOpportunityView() {
    const rows = performanceAdjustedLookalikes();
    elements.visibleTotal.textContent = rows.length.toLocaleString("en-AU");
    elements.visibleTotalLabel.textContent = "mapped Bailey-free places visible";
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
    const benchmarkLabel = state.performanceBenchmark
      ? `Top ${state.performanceBenchmark.store_ids.length} imported Bailey matches · ${state.performanceBenchmark.unmatched.length} unmatched rows`
      : state.opportunityFilters.setting
        ? "All current Bailey Nelson stores in this country and setting"
        : "All current Bailey Nelson stores, compared within each location setting";
    const settingLabel = state.opportunityFilters.setting || "All settings";
    elements.viewContent.innerHTML = `
      <section class="experimental-banner"><i data-lucide="scan-search"></i><div><strong>Lookalike screening rank</strong><span>Ranks mapped shopping centres and high-street corridors with no accepted Bailey Nelson tenancy; it is not every possible retail location. The result is a leasing screen, not a probability of store success, and missing evidence remains visible in completeness.</span></div></section>
      <section class="opportunity-form ranking-controls">
        <div class="select-grid">
          <label><span>Country</span><select id="lookalikeCountry">${filterOptions(["Australia", "New Zealand"], state.opportunityFilters.country, "Country")}</select></label>
          <label><span>Location setting</span><select id="lookalikeSetting">
            <option value="" ${state.opportunityFilters.setting ? "" : "selected"}>All settings</option>
            <option value="Shopping Centre" ${state.opportunityFilters.setting === "Shopping Centre" ? "selected" : ""}>Shopping centres</option>
            <option value="High Street" ${state.opportunityFilters.setting === "High Street" ? "selected" : ""}>High streets</option>
          </select></label>
        </div>
        <details class="opportunity-retailer-filters" ${retailerFilterCount ? "open" : ""}>
          <summary><span><strong>Retailer presence</strong><small>${escapeHtml(retailerFilterLabel)}</small></span><i data-lucide="chevron-down"></i></summary>
          <label class="opportunity-any-retailer"><input id="opportunityAnyRetailer" type="checkbox" ${state.opportunityFilters.require_any_retailer ? "checked" : ""} />
            <span><strong>At least one mapped optical retailer</strong><small>Any brand; useful for centres or corridors with existing optical validation.</small></span>
          </label>
          <div class="opportunity-retailer-columns">
            <fieldset><legend>Must have every selected retailer</legend>${retailerCheckboxes("must-have", state.opportunityFilters.must_have_retailers)}</fieldset>
            <fieldset><legend>Must not have any selected retailer</legend>${retailerCheckboxes("must-not-have", state.opportunityFilters.must_not_have_retailers)}</fieldset>
          </div>
          ${retailerFilterCount ? '<button class="secondary-command" id="clearOpportunityRetailers" type="button">Clear retailer filters</button>' : ""}
          <p class="form-note">Presence means an accepted mapping to this exact centre or corridor, not merely a nearby store.</p>
        </details>
        <div class="performance-import">
          <span><strong>Bailey benchmark</strong><small>${escapeHtml(benchmarkLabel)}</small></span>
          <button class="secondary-command" id="performanceImportButton" type="button" title="Optional private benchmark; processed only in this browser"><i data-lucide="upload"></i>Load private Bailey benchmark</button>
          ${state.performanceBenchmark ? '<button class="secondary-command" id="performanceClearButton" type="button">Use all Bailey stores</button>' : ""}
          <input id="performanceFile" type="file" accept=".csv,text/csv" hidden />
        </div>
        <p class="form-note"><strong>Optional:</strong> load a CSV with <code>store_id</code> or <code>store_name</code>, plus <code>rank</code> or <code>performance_score</code>. With at least five Bailey matches, the best ten become the lookalike benchmark. The file and raw values stay in browser memory only and are never uploaded, saved, exported or added to a share URL.</p>
      </section>
      <section class="result-section lookalike-section">
        <div class="section-heading"><h2>${escapeHtml(`${state.opportunityFilters.country} · ${settingLabel}`)}</h2><span>${rows.length} mapped Bailey-free places</span></div>
        ${opportunityShortlistHtml()}
        <div class="lookalike-list" id="lookalikeList">${rows.length ? rows.slice(0, 150).map(lookalikeRowHtml).join("") : '<div class="empty-state"><strong>No places match these filters</strong><span>Change the location setting or retailer presence requirements.</span></div>'}</div>
      </section>
      <details class="manual-screening"><summary>Screen a manual candidate point</summary><section class="opportunity-form">
        <label><span>Brand profile</span><select id="profileSelect">${profileOptions()}</select></label>
        <label><span>Candidate name</span><input id="candidateName" value="${escapeHtml(
          state.opportunityForm.name
        )}" placeholder="e.g. Parramatta option" /></label>
        <div class="input-grid">
          <label><span>Available area</span><div class="unit-input"><input id="candidateArea" type="number" min="1" value="${escapeHtml(
            state.opportunityForm.area_sqm
          )}" placeholder="Unknown" /><b>sqm</b></div></label>
          <label><span>Target minimum</span><div class="unit-input"><input id="targetMin" type="number" min="1" value="${escapeHtml(
            state.opportunityForm.target_min_sqm
          )}" placeholder="Unset" /><b>sqm</b></div></label>
          <label><span>Target maximum</span><div class="unit-input"><input id="targetMax" type="number" min="1" value="${escapeHtml(
            state.opportunityForm.target_max_sqm
          )}" placeholder="Unset" /><b>sqm</b></div></label>
        </div>
        <button class="primary-command" id="dropSiteButton" type="button"><i data-lucide="map-pin-plus"></i>Drop candidate on map</button>
        <p class="form-note">The index is a transparent heuristic, not a probability of store success. Unavailable components reduce screening completeness rather than being guessed.</p>
      </section>
      <section class="result-section">
        <div class="section-heading"><h2>Manual candidate shortlist</h2><span>${state.candidates.length} sites</span></div>
        <div class="candidate-list" id="candidateList">${
          state.candidates.length
            ? state.candidates.map(candidateListRow).join("")
            : '<div class="empty-state"><i data-lucide="map-pin-plus"></i><strong>No candidates yet</strong><span>Drop a site to begin a scored comparison.</span></div>'
        }</div>
      </section></details>`;
    bindOpportunityForm();
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
      renderOpportunityView();
      updateCentreMarkersForFilters();
    });
    document.getElementById("lookalikeSetting").addEventListener("change", (event) => {
      state.opportunityFilters.setting = event.target.value;
      renderOpportunityView();
      updateCentreMarkersForFilters();
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
        renderOpportunityView();
        updateCentreMarkersForFilters();
      });
    });
    document.getElementById("opportunityAnyRetailer").addEventListener("change", (event) => {
      state.opportunityFilters.require_any_retailer = event.target.checked;
      renderOpportunityView();
      updateCentreMarkersForFilters();
    });
    document.getElementById("clearOpportunityRetailers")?.addEventListener("click", () => {
      state.opportunityFilters.require_any_retailer = false;
      state.opportunityFilters.must_have_retailers.clear();
      state.opportunityFilters.must_not_have_retailers.clear();
      renderOpportunityView();
      updateCentreMarkersForFilters();
    });
    document.getElementById("performanceImportButton").addEventListener("click", () => document.getElementById("performanceFile").click());
    document.getElementById("performanceFile").addEventListener("change", (event) => {
      if (event.target.files[0]) importPerformanceBenchmark(event.target.files[0]);
    });
    document.getElementById("performanceClearButton")?.addEventListener("click", () => {
      state.performanceBenchmark = null;
      renderOpportunityView();
    });
    document.getElementById("lookalikeList").addEventListener("click", (event) => {
      const shortlistButton = event.target.closest("[data-shortlist-place-id]");
      if (shortlistButton) return togglePlaceShortlist(shortlistButton.dataset.shortlistPlaceId);
      const row = event.target.closest("[data-open-place-id]");
      if (!row) return;
      const place = state.centres.find((item) => item.place_id === row.dataset.openPlaceId);
      openCentreDetail(place);
    });
    document.getElementById("exportShortlistSummary")?.addEventListener("click", () => exportPlaceSummary([...state.placeShortlist]));
    document.getElementById("exportShortlistTenants")?.addEventListener("click", () => exportPlaceTenants([...state.placeShortlist]));
    document.getElementById("clearPlaceShortlist")?.addEventListener("click", () => {
      state.placeShortlist.clear();
      persistPlaceShortlist();
      renderOpportunityView();
    });
    [
      ["profileSelect", "profile_id"],
      ["candidateName", "name"],
      ["candidateArea", "area_sqm"],
      ["targetMin", "target_min_sqm"],
      ["targetMax", "target_max_sqm"],
    ].forEach(([id, key]) => {
      const control = document.getElementById(id);
      control.addEventListener("input", () => {
        state.opportunityForm[key] = control.value;
      });
    });
    document.getElementById("dropSiteButton").addEventListener("click", () => setCandidateDropMode(true));
    document.getElementById("candidateList").addEventListener("click", (event) => {
      const row = event.target.closest("[data-candidate-id]");
      if (!row) return;
      const candidate = state.candidates.find((item) => item.id === row.dataset.candidateId);
      openCandidateDetail(candidate);
      map.setView([candidate.latitude, candidate.longitude], 13);
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

  function renderCompareView() {
    elements.visibleTotal.textContent = state.candidates.length.toLocaleString("en-AU");
    elements.visibleTotalLabel.textContent = "manual candidates to compare";
    elements.viewContent.innerHTML = `
      <section class="compare-intro">
        <div class="workflow-note"><i data-lucide="info"></i><p><strong>Where to compare sites:</strong> the Candidate evidence table below is the side-by-side comparison. Each candidate is a column and each evidence measure is a row. Add a candidate, then click its exact map point so the tool can attach the containing public demographic area and nearby network evidence. Store distance is a separate two-store check shown in the map tray.</p></div>
        <div class="compact-metrics">
          <div><strong>${state.candidates.length}</strong><span>candidates</span></div>
          <div><strong>${state.compareStores.length}</strong><span>stores selected</span></div>
          <div><strong>${state.candidates.filter((candidate) => scoreCandidate(candidate).reliable).length}</strong><span>reliable scores</span></div>
        </div>
        <div class="button-row">
          <button class="secondary-command" id="compareDropButton" type="button"><i data-lucide="map-pin-plus"></i>Add candidate</button>
          <button class="secondary-command" id="compareStoresStart" type="button"><i data-lucide="ruler"></i>Store distance</button>
        </div>
      </section>
      <section class="comparison-table-wrap">
        <h2>Candidate evidence</h2>
        <p class="comparison-note"><strong>Screening index (0–100)</strong> combines the available public evidence for each manual site: local market demand, competitor white space, verified centre strength, accessibility, network spacing and tenancy-size fit. Missing evidence reduces completeness. It is a comparison aid, not a sales forecast.</p>
        ${
          state.candidates.length
            ? candidateComparisonTable(state.candidates)
            : '<div class="empty-state"><i data-lucide="columns-3"></i><strong>No shortlist to compare</strong><span>Add candidate sites from the Opportunity view.</span></div>'
        }
      </section>`;
    document.getElementById("compareDropButton").addEventListener("click", () => {
      setView("opportunity");
      setCandidateDropMode(true);
    });
    document.getElementById("compareStoresStart").addEventListener("click", () => setStoreCompareMode(true));
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
    if (state.placeShortlist.has(resolved)) state.placeShortlist.delete(resolved);
    else state.placeShortlist.add(resolved);
    persistPlaceShortlist();
    if (state.view === "opportunity") renderOpportunityView();
    if (state.selectedCentreId === resolved && elements.detailPanel.classList.contains("open")) {
      openCentreDetail(state.centres.find((item) => item.place_id === resolved));
    }
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
      location_setting_coverage: "Location setting coverage",
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
    const lowestDimension = Math.min(...Object.values(health.dimensions));
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
        <div class="health-status"><span>${health.certification_status === "Operational" ? "Operational first draft" : escapeHtml(health.certification_status)}</span><strong>${lowestDimension.toFixed(1)}%</strong><small>lowest health dimension · as of ${escapeHtml(health.coverage_as_of)}</small></div>
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

  function candidateComparisonTable(candidates) {
    const models = candidates.map((candidate) => ({ candidate, model: scoreCandidate(candidate) }));
    const rows = [
      ["Screening index (0–100)", (item) => item.model.score ?? "-"],
      ["Completeness", (item) => `${item.model.coverage}%`],
      ["Market demand", (item) => componentValue(item.model, "market_demand")],
      ["White space", (item) => componentValue(item.model, "competitive_white_space")],
      ["Centre strength", (item) => componentValue(item.model, "centre_strength")],
      ["Accessibility", (item) => componentValue(item.model, "accessibility")],
      ["Network fit", (item) => componentValue(item.model, "network_fit")],
      ["Format fit", (item) => componentValue(item.model, "format_fit")],
      ["5 km competitors", (item) => item.model.competitorCountFiveKm],
      ["Available area", (item) => (item.candidate.area_sqm ? `${item.candidate.area_sqm} sqm` : "Unknown")],
    ];
    return `<table class="comparison-table"><thead><tr><th>Measure</th>${models
      .map((item) => `<th>${escapeHtml(item.candidate.name)}</th>`)
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

  function proximityModel(point, baseStore = null, certifiedOnly = false) {
    const distances = distanceEntries(point, baseStore?.store_id || "", certifiedOnly);
    const nearestByBrand = Object.fromEntries(
      BRAND_ORDER.map((brand) => [brand, distances.find((entry) => entry.store.retailer === brand) || null])
    );
    const radiusCounts = STORE_RADII.map((radius) => {
      const inside = distances.filter(
        (entry) => entry.distance <= radius && (!baseStore || entry.store.retailer !== baseStore.retailer)
      );
      return {
        radius,
        counts: Object.fromEntries(
          BRAND_ORDER.map((brand) => [brand, inside.filter((entry) => entry.store.retailer === brand).length])
        ),
        total: inside.length,
      };
    });
    const sameCentre =
      baseStore && baseStore.place_id
        ? state.allStores.filter(
            (store) =>
              (!certifiedOnly || store.eligible_for_analytics) &&
              store.store_id !== baseStore.store_id &&
              store.retailer !== baseStore.retailer &&
              store.place_id === baseStore.place_id
          )
        : [];
    return { distances, nearestByBrand, radiusCounts, sameCentre };
  }

  function nearestBrandHtml(model, options = {}) {
    const maximumDistance = Number.isFinite(options.maxDistanceKm) ? options.maxDistanceKm : null;
    const entries = BRAND_ORDER.map((brand) => ({ brand, entry: model.nearestByBrand[brand] }))
      .filter(({ entry }) => maximumDistance === null || (entry && entry.distance <= maximumDistance));
    if (options.sortByDistance) {
      entries.sort((left, right) => (left.entry?.distance ?? Infinity) - (right.entry?.distance ?? Infinity) || left.brand.localeCompare(right.brand));
    }
    if (!entries.length) {
      return `<p class="empty-note">No mapped brand locations within ${escapeHtml(maximumDistance)} km.</p>`;
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
    if (!entries.length) return '<p class="empty-note">No matching locations found.</p>';
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
        <label><span>Location setting</span><select id="correctionSetting">${["Shopping Centre", "High Street", "Other", "Uncertain"].map((value) => `<option ${value === store.location_setting ? "selected" : ""}>${value}</option>`).join("")}</select></label>
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
        <h2>${escapeHtml(store.name)}</h2><address>${escapeHtml(store.full_address)}</address>
        <div class="link-row">${store.phone ? `<a class="command-link" href="tel:${escapeHtml(store.phone.replace(/[^+\d]/g, ""))}"><i data-lucide="phone"></i>Call</a>` : ""}
          ${storePublicLinksHtml(store)}</div>
      </header>
      <section class="detail-section">
        <h3>Leasing profile</h3>
        <div class="data-grid">
          <div class="data-point"><span>Location setting</span><strong>${escapeHtml(store.location_setting)}</strong></div>
          <div class="data-point"><span>Mapping confidence</span><strong><span class="confidence">${escapeHtml(
            store.mapping_confidence
          )}</span></strong></div>
          <div class="data-point"><span>Canonical place</span><strong>${escapeHtml(store.venue_name || "Not mapped")}</strong></div>
          <div class="data-point"><span>Status</span><strong>${escapeHtml(store.status)}</strong></div>
          <div class="data-point"><span>Affiliation</span><strong>${escapeHtml(
            String(store.affiliations || "").split("|").filter(Boolean)
              .map((id) => state.affiliations.find((item) => item.affiliation_id === id)?.name || id)
              .join(", ") || "None recorded"
          )}</strong></div>
          <div class="data-point"><span>Network usability</span><strong><span class="confidence ${store.usable_for_network ? "" : "uncertified"}">${store.usable_for_network ? "Usable" : "Background only"}</span></strong></div>
          <div class="data-point"><span>Source freshness</span><strong>${store.current_source ? "Current" : "Warning shown"}</strong></div>
          <div class="data-point"><span>Country</span><strong>${escapeHtml(store.country)}</strong></div>
          <div class="data-point"><span>State / region</span><strong>${escapeHtml(store.state)}</strong></div>
        </div>
        ${areaHtml(store)}
        <p class="empty-note">${escapeHtml(store.classification_basis)}</p>
        ${store.retailer === "Independent / Other optical" ? `<p class="empty-note">Public profile links are identity and discovery evidence. Confirm current trading status directly before relying on them.</p>` : ""}
        <div class="service-list">${services.length ? services.map((service) => `<span>${escapeHtml(service)}</span>`).join("") : "<span>No services listed</span>"}</div>
        <div class="link-row"><button class="detail-action" id="compareFromDetail" type="button"><i data-lucide="ruler"></i>Add to store comparison</button></div>
      </section>
      ${store.current_source ? "" : `<section class="detail-section certification-warning"><h3>Freshness warning</h3><p>This last-known store remains usable in network analysis, but its official source is outside the current freshness target.</p></section>`}
      ${correctionEditorHtml(store)}
      ${
        market
          ? marketEvidenceHtml(market.properties)
          : store.country === "New Zealand"
            ? `<section class="detail-section coverage-note"><h3>New Zealand demographics</h3>
              <p class="empty-note">Store, centre and proximity coverage is available. Stats NZ demographic catchments are not yet published in this build, so no Australian proxy is shown.</p></section>`
            : ""
      }
      <section class="detail-section"><h3>Nearest brand locations</h3>
        <div class="proximity-summary">${nearestBrandHtml(model)}</div>${radiusTableHtml(model)}
      </section>
      <section class="detail-section"><h3>Same-centre competitors</h3>
        <div class="nearest-list">${
          sameCentreEntries.length
            ? nearRows(sameCentreEntries)
            : '<p class="empty-note">No reviewed same-centre competitor is recorded. Proximity is never used to assign a venue.</p>'
        }</div></section>
      <section class="detail-section"><h3>Ten nearest stores</h3><div class="nearest-list">${nearRows(
        model.distances
      )}</div></section>
      <section class="detail-section source-block"><i data-lucide="database"></i><div><strong>${
        store.retailer === "Independent / Other optical"
          ? (String(store.affiliations || "").split("|").includes("provision") ? "Official ProVision practice source" : "Community-mapped public source")
          : "Official retailer source"
      }</strong>
        <span>Refreshed ${escapeHtml(formatDate(store.fetched_at))} · ${escapeHtml(
          store.store_id
        )}${store.retailer === "Independent / Other optical" && !String(store.affiliations || "").split("|").includes("provision") ? " · Non-exhaustive OSM coverage" : ""}</span></div></section>`;
    openDetailPanel();
    document.getElementById("compareFromDetail").addEventListener("click", () => {
      setStoreCompareMode(true);
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
    bailey_footprint_similarity: ["Footprint similarity", "How closely the public demographic and location context resembles Bailey Nelson places in the same country and setting."],
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
        <div><strong>#${row.rank} in ${escapeHtml(row.country)} · ${escapeHtml(row.location_setting)}</strong><p>${row.screening_completeness}% screening completeness. The score is a transparent comparison with Bailey Nelson’s mapped footprint, not a success probability.</p></div></div>
      <div class="lookalike-components">${Object.entries(LOOKALIKE_COMPONENTS).map(([key, [label, explanation]]) => {
        const value = row.components?.[key];
        return `<div><span><strong>${escapeHtml(label)}</strong><small>${escapeHtml(explanation)}</small></span><b>${hasLookalikeComponent(value) ? Math.round(Number(value)) : "N/A"}</b></div>`;
      }).join("")}</div>
      <div class="data-grid opportunity-facts">
        <div class="data-point"><span>Population 2025</span><strong>${formatNumber(market.population_2025)}</strong></div>
        <div class="data-point"><span>Population growth 2021–25</span><strong>${formatNumber(market.population_growth_2021_2025_pct, "%")}</strong></div>
        <div class="data-point"><span>Age 45+ (2021)</span><strong>${formatNumber(market.age_45_plus_pct_2021, "%")}</strong></div>
        <div class="data-point"><span>Equivalised weekly household income (2021)</span><strong>${market.median_equivalised_household_income_weekly_2021 ? `$${formatNumber(market.median_equivalised_household_income_weekly_2021)}` : "N/A"}</strong></div>
        <div class="data-point"><span>Nearest Bailey Nelson</span><strong>${Number.isFinite(Number(row.nearest_bailey_km)) ? Intel.formatDistance(Number(row.nearest_bailey_km)) : "Unknown"}</strong></div>
        <div class="data-point"><span>Exact-place optical stores</span><strong>${formatNumber(row.optical_store_count || 0)}</strong></div>
      </div>
      <p class="evidence-gaps"><strong>Evidence gaps:</strong> ${gaps.length ? escapeHtml(gaps.join(", ")) : "No weighted component is missing."}</p>
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
        <div class="data-point"><span>Comparison boundary</span><strong>800 m indicative corridor</strong></div>
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
        <div><strong>${escapeHtml(signal.title)}</strong><span>${escapeHtml(signal.status.replaceAll("_", " "))} · ${escapeHtml(signal.impact_horizon || "Timing not published")}</span></div>
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
    const row = publishedLookalike(centre.place_id) || {};
    const market = row.market_features || {};
    const relationships = state.propertyRelationships.filter((item) => item.place_id === centre.place_id && Intel.activeRelationship(item));
    const verifiedDates = relationships.map((item) => item.last_verified_at).filter(Boolean).sort();
    return {
      place_id: centre.place_id, place_name: centre.name, rank: row.rank ?? "", lookalike_score: row.score ?? "",
      screening_completeness_pct: row.screening_completeness ?? "",
      footprint_similarity: row.components?.bailey_footprint_similarity ?? "", bailey_whitespace: row.components?.bailey_whitespace ?? "",
      optical_validation: row.components?.optical_market_validation ?? "", retail_context: row.components?.accessibility_retail_context ?? "",
      location_setting: centre.location_setting, country: centre.country, state: centre.state, locality: centre.locality || centre.suburb || "", postcode: centre.postcode || "", address: centre.address || "",
      nearest_bailey_km: row.nearest_bailey_km ?? centre.nearest_bailey_km ?? "", population_2025: market.population_2025 ?? "",
      population_growth_2021_2025_pct: market.population_growth_2021_2025_pct ?? "", age_45_plus_pct_2021: market.age_45_plus_pct_2021 ?? "",
      median_equivalised_household_income_weekly_2021: market.median_equivalised_household_income_weekly_2021 ?? "", centre_class: centre.location_setting === "High Street" ? "Not applicable at corridor level" : centre.centre_class || "Unknown",
      property_groups: centre.location_setting === "High Street" ? "" : propertyGroupNames(centre).join(" | "), leasing_arrangement: centre.location_setting === "High Street" ? "Not applicable at corridor level" : centre.leasing_arrangement || "Unknown",
      portfolio_overlap: centre.location_setting === "High Street" ? "Not assessed at corridor level" : overlapLabel(centre.portfolio_overlap_status, "centre"),
      optical_store_count: centre.optical_store_count || 0, retailers: (centre.retailers || []).join(" | "),
      high_street_baseline_status: centre.location_setting === "High Street" && (state.placeTenantMetadata.researched_bailey_corridor_place_ids || []).includes(centre.place_id) ? "Baseline checked" : "",
      exact_place_optical_tenant_count: tenantsForPlace(centre.place_id).filter((row) => row.category === "Optical").length,
      key_cotenancy_count: tenantsForPlace(centre.place_id).filter((row) => row.category !== "Optical").length,
      place_evidence_date: centre.source_date || "", property_evidence_latest: verifiedDates.at(-1) || "", official_url: centre.official_url || centre.source_url || "",
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
    const records = centres.flatMap((centre) => tenantsForPlace(centre.place_id).map((tenant) => ({
      place_id: centre.place_id, place_name: centre.name, country: centre.country, state: centre.state,
      membership_type: tenant.category === "Optical" ? "Accepted exact-place optical membership" : "Researched key co-tenant",
      tenant_id: tenant.tenant_id, tenant_name: tenant.tenant_name, retailer: tenant.retailer || "", category: tenant.category,
      anchor_flag: tenant.anchor_flag ? "true" : "false", selection_basis: tenant.selection_basis, status: tenant.status,
      source_url: tenant.source_url, source_type: tenant.source_type, source_date: tenant.source_date || "", verified_at: tenant.verified_at, confidence: tenant.confidence,
    })));
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
    state.selectedCentreId = centre.place_id;
    const relationships = state.propertyRelationships.filter(
      (item) => item.place_id === centre.place_id && Intel.activeRelationship(item)
    );
    const publicUrl = centre.official_url || centre.source_url || centre.public_url;
    const isCorridor = centre.location_setting === "High Street";
    const placeLabel = isCorridor ? "corridor" : "centre";
    const saved = state.placeShortlist.has(resolvePlaceId(centre.place_id));
    elements.detailContent.innerHTML = `
      <header class="detail-header" style="--brand-color:#d29b27">
        <span class="retailer-tag">${centre.location_setting === "High Street" ? '<i data-lucide="route"></i>' : CENTRE_BAG_SVG}${escapeHtml(centre.place_type)}</span>
        <h2>${escapeHtml(centre.name)}</h2><address>${escapeHtml(centre.address || `${centre.locality || centre.suburb}, ${centre.state}`)}</address>
        <div class="link-row">
          <button class="detail-action ${saved ? "saved" : "primary"}" id="detailShortlist" type="button"><i data-lucide="bookmark${saved ? "-check" : ""}"></i>${saved ? "Shortlisted" : "Add to shortlist"}</button>
          <button class="detail-action" id="placeReport" type="button"><i data-lucide="file-down"></i>Print brief</button>
          <button class="detail-action" id="placeSummaryCsv" type="button">Summary CSV</button>
          <button class="detail-action" id="placeTenantCsv" type="button">Tenant CSV</button>
          ${publicUrl ? `<a class="command-link" href="${escapeHtml(publicUrl)}" target="_blank" rel="noopener"><i data-lucide="external-link"></i>Public source</a>` : ""}
        </div>
      </header>
      ${opportunitySummaryHtml(centre)}
      <section class="detail-section"><h3>Optical competition context</h3>${competitorContextHtml(centre)}
        <p class="empty-note">The map is focused on the competition shown above. IN ${isCorridor ? "CORRIDOR" : "CENTRE"} requires the same accepted canonical place ID; distance alone never establishes membership.</p>
      </section>
      ${highStreetProfileHtml(centre)}
      <section class="detail-section"><h3>Key co-tenancy profile</h3>${keyCoTenancyHtml(centre)}</section>
      ${developmentSignalsHtml(centre)}
      ${isCorridor ? `<section class="detail-section"><h3>High-street place context</h3><div class="data-grid property-summary-grid">
          <div class="data-point"><span>Place type</span><strong>High Street Corridor</strong></div>
          <div class="data-point"><span>Property intelligence</span><strong>Not assessed at corridor level</strong></div>
        </div><p class="empty-note">Centre class, ownership and leasing control describe an individual property. They are not applied to an entire street corridor.</p></section>` : `<section class="detail-section"><h3>Ownership, management and leasing</h3>
        <div class="data-grid property-summary-grid">
          <div class="data-point"><span>Centre class</span><strong>${escapeHtml(centre.centre_class || "Unknown")}</strong><small>${escapeHtml(centre.centre_class_method || "Not confirmed")}</small></div>
          <div class="data-point"><span>Leasing arrangement</span><strong>${escapeHtml(centre.leasing_arrangement || "Unknown")}</strong></div>
        </div>${relationshipCardsHtml(relationships)}</section>
      <section class="detail-section portfolio-overlap"><h3>Bailey Nelson portfolio overlap</h3>
        <strong>${escapeHtml(overlapLabel(centre.portfolio_overlap_status, placeLabel))}</strong>
        <p>${centre.portfolio_overlap_groups?.length ? centre.portfolio_overlap_groups.map((item) => `${escapeHtml(item.canonical_name)} (${escapeHtml(relationshipRoleLabel(item.role))}): ${item.bailey_store_count} Bailey store${item.bailey_store_count === 1 ? "" : "s"} across ${item.bailey_property_count} propert${item.bailey_property_count === 1 ? "y" : "ies"}`).join("<br>") : "No evidenced public portfolio overlap is available."}</p>
        <small>Portfolio overlap is derived from public property and tenancy evidence. It is not proof of a private commercial relationship.</small>
      </section>`}
      <section class="detail-section"><h3>Public ${isCorridor ? "corridor" : "centre"} metrics</h3><div class="data-grid">
        ${isCorridor ? `<div class="data-point"><span>Comparison boundary</span><strong>800 m indicative corridor</strong></div>
        <div class="data-point"><span>Exact mapped optical stores</span><strong>${formatNumber(centre.optical_store_count || 0)}</strong></div>` : `<div class="data-point"><span>Total GLA</span><strong>${centre.gla_sqm ? formatNumber(centre.gla_sqm, " sqm") : "Not published"}</strong></div>
        <div class="data-point"><span>Annual visits</span><strong>${formatNumber(centre.annual_visits)}</strong></div>
        <div class="data-point"><span>Retail tenancies</span><strong>${formatNumber(centre.tenancy_count)}</strong></div>
        <div class="data-point"><span>Trade area population</span><strong>${formatNumber(centre.trade_area_population)}</strong></div>`}
        <div class="data-point"><span>Nearest Bailey Nelson</span><strong>${Number.isFinite(Number(centre.nearest_bailey_km)) ? Intel.formatDistance(Number(centre.nearest_bailey_km)) : "Unknown"}</strong></div>
      </div>${!isCorridor && centre.source_url && (centre.gla_sqm || centre.annual_visits || centre.tenancy_count) ? `<p class="empty-note">Metric source: <a href="${escapeHtml(centre.source_url)}" target="_blank" rel="noopener">public owner material</a>${centre.source_date ? ` dated ${escapeHtml(formatDate(centre.source_date))}` : ""}${centre.last_verified_at ? ` · checked ${escapeHtml(formatDate(centre.last_verified_at))}` : ""}.</p>` : ""}</section>
      <section class="detail-section source-block"><i data-lucide="database"></i><div><strong>${escapeHtml(centre.source_basis || "Best available public place record")}</strong><span>${centre.source_date ? `Place evidence dated ${escapeHtml(formatDate(centre.source_date))}` : "Public metrics remain incomplete"}</span></div></section>
      <details class="technical-details"><summary>Technical record, methodology and public corrections</summary>
        <section class="detail-section"><h3>Technical record</h3><div class="data-grid">
          <div class="data-point"><span>Canonical place ID</span><strong>${escapeHtml(centre.place_id)}</strong></div>
          <div class="data-point"><span>Mapping confidence</span><strong>${escapeHtml(centre.mapping_confidence || centre.confidence)}</strong></div>
          <div class="data-point"><span>Research status</span><strong>${escapeHtml(centre.research_status || "Not researched")}</strong></div>
          <div class="data-point"><span>Location setting</span><strong>${escapeHtml(centre.location_setting)}</strong></div>
        </div><p class="empty-note">A canonical place ID is the stable record used to join stores, property facts and corrections without relying on changing names.</p></section>
        ${isCorridor ? '<p class="empty-note">Property ownership and centre-class corrections are available for shopping-centre records only.</p>' : propertyCorrectionEditorHtml(centre, relationships)}
      </details>`;
    openDetailPanel();
    bindNearRows();
    bindPropertyDetail(centre, relationships);
    document.getElementById("detailShortlist")?.addEventListener("click", () => togglePlaceShortlist(centre.place_id));
    document.getElementById("placeReport")?.addEventListener("click", () => generatePlaceReport(centre));
    document.getElementById("placeSummaryCsv")?.addEventListener("click", () => exportPlaceSummary([centre.place_id]));
    document.getElementById("placeTenantCsv")?.addEventListener("click", () => exportPlaceTenants([centre.place_id]));
    focusPlaceOnMap(centre);
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
    return Intel.findMarketFeature(point, state.markets);
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
      <section class="detail-section"><h3>Format and location</h3>
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
      <section class="detail-section"><h3>Nearest brand locations within 100 km</h3><div class="proximity-summary">${nearestBrandHtml(
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
    elements.detailPanel.classList.add("open");
    elements.detailPanel.setAttribute("aria-hidden", "false");
    refreshIcons();
  }

  function closeDetail() {
    state.selectedStoreId = "";
    state.selectedCentreId = "";
    state.selectedCandidateId = "";
    elements.detailPanel.classList.remove("open");
    elements.detailPanel.setAttribute("aria-hidden", "true");
    catchmentLayer.clearLayers();
    clearPlaceFocus();
  }

  function bindNearRows() {
    elements.detailContent.querySelectorAll("[data-store-id]").forEach((button) => {
      button.addEventListener("click", () => selectStore(button.dataset.storeId, true));
    });
  }

  function selectStore(storeId, moveMap = true) {
    const store = state.allStores.find((item) => item.store_id === storeId);
    if (!store) return;
    if (state.storeCompareMode) addCompareStore(store);
    openStoreDetail(store);
    if (state.view === "network") renderNetworkView();
    if (moveMap) {
      const marker = markerById.get(storeId);
      const targetZoom = Math.max(map.getZoom(), BRAND_CONFIG[store.retailer]?.minMarkerZoom || 0, 14);
      if (marker && storeClusters.hasLayer(marker)) {
        storeClusters.zoomToShowLayer(marker, () => map.setView([store.latitude, store.longitude], targetZoom));
      } else {
        map.setView([store.latitude, store.longitude], targetZoom);
      }
    }
  }

  function setStoreCompareMode(active) {
    state.storeCompareMode = active;
    if (active) setCandidateDropMode(false);
    elements.storeCompareButton.classList.toggle("active", active);
    elements.storeCompareTray.hidden = !active;
    elements.modeNotice.hidden = !active;
    elements.modeNotice.textContent = active
      ? "Select any two stores from the map or network list to compare straight-line distance."
      : "";
  }

  function addCompareStore(store) {
    if (state.compareStores.some((item) => item.store_id === store.store_id)) return;
    if (state.compareStores.length < 2) state.compareStores.push(store);
    else state.compareStores = [state.compareStores[1], store];
    renderStoreComparison();
  }

  function renderStoreComparison() {
    [elements.compareA, elements.compareB].forEach((element, index) => {
      const store = state.compareStores[index];
      element.innerHTML = store
        ? `${brandMarkHtml(store.retailer, "tray")}<span>${escapeHtml(store.name)}</span>`
        : `<span>Select ${index ? "second" : "first"} store</span>`;
    });
    if (compareLine) map.removeLayer(compareLine);
    compareLine = null;
    if (state.compareStores.length === 2) {
      const distance = Intel.haversine(state.compareStores[0], state.compareStores[1]);
      elements.compareDistance.textContent = Intel.formatDistance(distance);
      const points = state.compareStores.map((store) => [store.latitude, store.longitude]);
      compareLine = L.polyline(points, { color: "#171b1f", weight: 3, dashArray: "8 7" }).addTo(map);
      map.fitBounds(points, { padding: [80, 80], maxZoom: 15 });
    } else {
      elements.compareDistance.textContent = "";
    }
  }

  function clearStoreComparison() {
    state.compareStores = [];
    renderStoreComparison();
  }

  function setCandidateDropMode(active) {
    state.candidateDropMode = active;
    if (active && state.storeCompareMode) setStoreCompareMode(false);
    elements.candidateButton.classList.toggle("active", active);
    document.body.classList.toggle("candidate-mode", active);
    elements.modeNotice.hidden = !active;
    elements.modeNotice.textContent = active
      ? "Click anywhere on the map to add a candidate site. Public candidates contain location and area only."
      : "";
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
    state.candidates = state.candidates.filter((candidate) => candidate.id !== candidateId);
    const marker = candidateMarkerById.get(candidateId);
    if (marker) candidateLayer.removeLayer(marker);
    candidateMarkerById.delete(candidateId);
    closeDetail();
    renderCandidateDock();
    renderView();
    updateShareUrl(false);
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
    elements.candidateDock.hidden = !state.candidates.length;
    elements.candidateDockCount.textContent = `${state.candidates.length} ${state.candidates.length === 1 ? "site" : "sites"}`;
    elements.candidateCards.innerHTML = state.candidates
      .map((candidate) => {
        const model = scoreCandidate(candidate);
        return `<button data-candidate-id="${escapeHtml(candidate.id)}"><span class="score-badge ${
          model.reliable ? "" : "low-coverage"
        }">${model.score ?? "-"}</span><span><strong>${escapeHtml(candidate.name)}</strong><small>${escapeHtml(
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
      <section class="detail-section source-block"><i data-lucide="database"></i><div><strong>ABS Data by Region 2011–25</strong>
        <span>Released ${escapeHtml(formatDate(state.marketMetadata.source_release_date))} · High confidence</span></div></section>`;
    openDetailPanel();
  }

  function updateLayerVisibility() {
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
      state.filteredStores.map((store) => [store.latitude, store.longitude, 0.55]),
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
      <section><h3>Key co-tenancy profile</h3><p>${keyTenants.length ? keyTenants.map((item) => `${escapeHtml(item.tenant_name)} (${escapeHtml(item.category)})`).join(" · ") : "Key co-tenancy research has not been completed for this place."}</p></section>
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
    if (payload.filters) {
      state.filters.retailers = new Set(
        payload.filters.retailers?.filter((retailer) => BRAND_ORDER.includes(retailer)) || DEFAULT_RETAILERS
      );
      state.filters.country = payload.filters.country || "";
      state.filters.state = payload.filters.state || "";
      state.filters.location = payload.filters.location || "";
      state.filters.search = payload.filters.search || "";
      state.filters.affiliation = state.affiliations.some((item) => item.affiliation_id === payload.filters.affiliation)
        ? payload.filters.affiliation : "";
    }
    if (payload.place_filters) {
      state.placeFilters.search = payload.place_filters.search || "";
      state.placeFilters.country = payload.place_filters.country || "";
      state.placeFilters.type = payload.place_filters.type || "";
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
      const restored = {
        id: candidate.id || `shared-${index}`,
        name: candidate.name || `Candidate ${index + 1}`,
        latitude: candidate.latitude,
        longitude: candidate.longitude,
        area_sqm: candidate.area_sqm || "",
        target_min_sqm: "",
        target_max_sqm: "",
        profile_id: candidate.profile_id || "generic-optical",
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
    if (state.view === "opportunity") return exportPlaceSummary(performanceAdjustedLookalikes().map((place) => place.place_id));
    if (state.view === "compare") return downloadCandidateComparisonCsv();
    return downloadFilteredCsv();
  }

  function resetAll() {
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
    setStoreCompareMode(false);
    setCandidateDropMode(false);
    closeDetail();
    state.activeLayers = new Set(["centres"]);
    document.querySelectorAll("[data-layer]").forEach((input) => {
      input.checked = input.dataset.layer === "centres";
    });
    updateLayerVisibility();
    applyFilters(false);
    map.fitBounds(NETWORK_BOUNDS, { padding: [18, 18] });
    setView("network");
    renderCandidateDock();
    showToast("Workspace reset.");
  }

  function bindGlobalEvents() {
    document.querySelectorAll("[data-view]").forEach((button) =>
      button.addEventListener("click", () => setView(button.dataset.view))
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
      });
    });
    elements.storeCompareButton.addEventListener("click", () => setStoreCompareMode(!state.storeCompareMode));
    elements.candidateButton.addEventListener("click", () => {
      setView("opportunity");
      setCandidateDropMode(!state.candidateDropMode);
    });
    document.getElementById("clearStoreCompare").addEventListener("click", clearStoreComparison);
    document.getElementById("candidateDockClose").addEventListener("click", () => {
      elements.candidateDock.hidden = true;
    });
    document.getElementById("saveViewButton").addEventListener("click", saveView);
    document.getElementById("shareButton").addEventListener("click", () => updateShareUrl(true));
    document.getElementById("reportButton").addEventListener("click", generateContextReport);
    document.getElementById("downloadButton").addEventListener("click", downloadContextCsv);
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
        <li><strong>Places</strong><span>Browse canonical shopping centres and high-street corridors, their exact mapped optical tenants, and researched public property facts.</span></li>
        <li><strong>Opportunity</strong><span>Rank Bailey-free places using a transparent lookalike screen. Score means similarity; completeness means how much evidence was available.</span></li>
        <li><strong>Trends</strong><span>Review recorded openings, closures, relocations and source freshness. This depends on reconciled historical snapshots.</span></li>
        <li><strong>Compare</strong><span>Place hypothetical candidate points side by side. A candidate uses the public demographic area containing the clicked point plus nearby network evidence.</span></li>
        <li><strong>Data Health</strong><span>See what is mapped, current, researched or still incomplete before relying on a result.</span></li>
      </ol></section>
      <section class="detail-section"><h3>Map tools</h3><dl class="tour-actions">
        <div><dt>Layers</dt><dd>Turn demographics, population growth, development signals, competition and amenities on or off.</dd></div>
        <div><dt>Store distance</dt><dd>Select two existing store markers or list rows; the map draws their straight-line distance.</dd></div>
        <div><dt>Candidate</dt><dd>Click an exact hypothetical site on the map for screening. This is separate from inspecting an existing store or place.</dd></div>
        <div><dt>Save view</dt><dd>Save the current filters, map position and public candidate points in this browser. It is local, not shared.</dd></div>
        <div><dt>Share</dt><dd>Copy a public-safe URL containing the current view and filters. Local corrections, shortlist entries and private performance data are excluded.</dd></div>
        <div><dt>Brief</dt><dd>Print the open place’s client brief, or the selected candidate brief. Open the item you want first.</dd></div>
        <div><dt>Export</dt><dd>Download the records relevant to the current view: stores, places, opportunity results or candidate comparison.</dd></div>
      </dl></section>
      <section class="detail-section"><h3>Clicks and comparison</h3><p>Clicking a <strong>store</strong> opens that store and nearby retailers. Clicking a <strong>place</strong> opens the centre or corridor, exact-place optical tenants and nearby competition. Turning on <strong>Candidate</strong> changes a blank map click into a hypothetical site. Existing markers keep their normal detail behaviour, which avoids mixing inspection with candidate creation.</p></section>
      <section class="detail-section"><h3>Optional private Bailey benchmark</h3><p>The Opportunity CSV loader is only for a Bailey-supplied performance ranking. It needs a store ID or name plus rank or performance score, and at least five valid matches. It temporarily re-benchmarks the lookalike screen using the best ten matches. The file and raw values remain in browser memory and are not uploaded or saved.</p></section>
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
      const [stores, markets, places, links, events, profiles, dataHealth, lookalikes, propertyIntelligence, retailerRegistry, placeTenants, developmentSignals, glossary] = await Promise.all([
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
      ]);
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
      state.centres = places.places;
      state.placeIdRemaps = places.place_id_remaps || {};
      state.placeTenants = placeTenants.memberships || [];
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
      applyFilters(false);
      if (!restoredView) map.fitBounds(NETWORK_BOUNDS, { padding: [18, 18] });
      updateLayerVisibility();
      setView(state.view);
      renderCandidateDock();
      const freshness = Object.values(state.metadata.source_freshness || {}).sort();
      elements.freshness.textContent = freshness.length
        ? `Retailer sources refreshed ${formatDate(freshness[freshness.length - 1])}`
        : "Source freshness unavailable";
      elements.loading.classList.add("hidden");
      refreshIcons();
    } catch (error) {
      elements.loading.innerHTML = `<strong>Leasing intelligence could not load</strong><span>${escapeHtml(
        error.message
      )}</span>`;
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
