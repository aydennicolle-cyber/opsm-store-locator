(function () {
  "use strict";

  const Intel = window.LeasingIntel;
  const BRAND_ORDER = ["OPSM", "Specsavers", "Bailey Nelson"];
  const BRAND_CONFIG = {
    OPSM: { color: "#0087a1", slug: "opsm", short: "OPSM" },
    Specsavers: { color: "#4f7f31", slug: "specsavers", short: "SPEC" },
    "Bailey Nelson": { color: "#e05b44", slug: "bailey-nelson", short: "BN" },
  };
  const VIEW_CONFIG = {
    network: {
      eyebrow: "Retail footprint",
      title: "Network",
      subtitle: "Filter, inspect and compare the national optical network.",
    },
    centres: {
      eyebrow: "Landlord intelligence",
      title: "Centres",
      subtitle: "Review optical tenancy overlap and sourced centre metrics.",
    },
    opportunity: {
      eyebrow: "Site strategy",
      title: "Opportunity",
      subtitle: "Drop, score and shortlist prospective leasing locations.",
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
  };
  const STORE_RADII = [0.5, 1, 2, 5, 10];
  const CATCHMENT_RADII = [1, 3, 5, 10];
  const AUSTRALIA_VIEW = { center: [-25.8, 134.4], zoom: 4 };
  const PUBLIC_STORE_FIELDS = [
    "retailer",
    "store_id",
    "name",
    "status",
    "state",
    "suburb",
    "postcode",
    "full_address",
    "phone",
    "latitude",
    "longitude",
    "official_url",
    "services",
    "audiology",
    "venue_name",
    "venue_id",
    "location_type",
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
    filteredStores: [],
    metadata: {},
    centres: [],
    markets: [],
    storeLinks: {},
    events: {},
    profiles: [],
    selectedStoreId: "",
    selectedCentreId: "",
    selectedCandidateId: "",
    storeCompareMode: false,
    candidateDropMode: false,
    compareStores: [],
    candidates: [],
    filters: {
      retailers: new Set(BRAND_ORDER),
      search: "",
      state: "",
      location: "",
      audiology: "",
      status: "",
      service: "",
    },
    opportunityForm: {
      profile_id: "generic-optical",
      name: "",
      area_sqm: "",
      target_min_sqm: "",
      target_max_sqm: "",
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
      const color = retailers.size === 1 ? BRAND_CONFIG[children[0].options.retailer].color : "#171b1f";
      const size = children.length > 99 ? 42 : children.length > 19 ? 38 : 34;
      return L.divIcon({
        className: "",
        html: `<div class="cluster-icon" style="width:${size}px;height:${size}px;background:${color}">${children.length}</div>`,
        iconSize: [size, size],
      });
    },
  }).addTo(map);
  const centreLayer = L.layerGroup().addTo(map);
  const candidateLayer = L.layerGroup().addTo(map);
  const catchmentLayer = L.layerGroup().addTo(map);
  const amenityLayer = L.layerGroup().addTo(map);

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
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

  function storeIcon(store) {
    const config = BRAND_CONFIG[store.retailer];
    return L.divIcon({
      className: "store-marker",
      html: `<div class="store-pin ${config.slug}" style="--pin-color:${config.color}"></div>`,
      iconSize: [20, 20],
      iconAnchor: [10, 10],
    });
  }

  function createStoreMarkers() {
    state.allStores.forEach((store) => {
      const marker = L.marker([store.latitude, store.longitude], {
        icon: storeIcon(store),
        retailer: store.retailer,
        storeId: store.store_id,
        title: store.name,
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
      const marker = L.marker([centre.latitude, centre.longitude], {
        icon: L.divIcon({
          className: "",
          html: `<div class="centre-pin"><i></i></div>`,
          iconSize: [22, 22],
          iconAnchor: [11, 11],
        }),
        title: centre.name,
      });
      marker.bindTooltip(
        `<strong>${escapeHtml(centre.name)}</strong><br>${centre.optical_store_count} mapped optical ${centre.optical_store_count === 1 ? "store" : "stores"}`,
        { direction: "top", offset: [0, -8] }
      );
      marker.on("click", () => openCentreDetail(centre));
      marker.addTo(centreLayer);
      centreMarkerById.set(centre.centre_id, marker);
    });
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
    document.querySelectorAll("[data-view]").forEach((button) => {
      button.classList.toggle("active", button.dataset.view === view);
    });
    const config = VIEW_CONFIG[view];
    elements.viewEyebrow.textContent = config.eyebrow;
    elements.viewTitle.textContent = config.title;
    elements.viewSubtitle.textContent = config.subtitle;
    renderView();
    updateShareUrl(false);
  }

  function renderView() {
    if (state.view === "network") renderNetworkView();
    else if (state.view === "centres") renderCentresView();
    else if (state.view === "opportunity") renderOpportunityView();
    else if (state.view === "trends") renderTrendsView();
    else renderCompareView();
    refreshIcons();
  }

  function retailerOptionsHtml() {
    return BRAND_ORDER.map((retailer) => {
      const config = BRAND_CONFIG[retailer];
      const count = state.filteredStores.filter((store) => store.retailer === retailer).length;
      return `<label class="retailer-option" data-retailer="${escapeHtml(retailer)}">
        <input type="checkbox" value="${escapeHtml(retailer)}" ${state.filters.retailers.has(retailer) ? "checked" : ""} />
        <span class="marker-key marker-${config.slug === "bailey-nelson" ? "bailey" : config.slug}"></span>
        <span>${escapeHtml(retailer)}</span><output>${count}</output>
      </label>`;
    }).join("");
  }

  function filterOptions(values, selected, emptyLabel) {
    return `<option value="">${emptyLabel}</option>${values
      .map((value) => `<option ${value === selected ? "selected" : ""}>${escapeHtml(value)}</option>`)
      .join("")}`;
  }

  function renderNetworkView() {
    const states = [...new Set(state.allStores.map((store) => store.state))].sort();
    const statuses = [...new Set(state.allStores.map((store) => store.status))].sort();
    const rows = state.filteredStores.slice(0, 100);
    elements.viewContent.innerHTML = `
      <section class="filters" aria-label="Network filters">
        <label class="search-field"><i data-lucide="search"></i><span class="sr-only">Search stores</span>
          <input id="searchInput" type="search" value="${escapeHtml(state.filters.search)}" placeholder="Store, suburb or postcode" autocomplete="off" />
        </label>
        <fieldset class="retailer-filter"><legend>Retailer</legend>${retailerOptionsHtml()}</fieldset>
        <div class="select-grid">
          <label><span>State</span><select id="stateSelect">${filterOptions(states, state.filters.state, "All states")}</select></label>
          <label><span>Location</span><select id="locationSelect">${filterOptions(
            ["Shopping Centre", "Main Street / Street-front", "Other", "Unclassified"],
            state.filters.location,
            "All locations"
          )}</select></label>
          <label><span>Audiology</span><select id="audiologySelect">
            <option value="">Any</option><option value="true" ${state.filters.audiology === "true" ? "selected" : ""}>Available</option>
            <option value="false" ${state.filters.audiology === "false" ? "selected" : ""}>Not listed</option>
          </select></label>
          <label><span>Status</span><select id="statusSelect">${filterOptions(statuses, state.filters.status, "All statuses")}</select></label>
        </div>
        <label class="service-field"><span>Service</span><input id="serviceInput" value="${escapeHtml(
          state.filters.service
        )}" type="search" placeholder="e.g. dry eye, contact lens" /></label>
      </section>
      <section class="result-section">
        <div class="section-heading"><h2>Locations</h2><span>${state.filteredStores.length.toLocaleString("en-AU")} results</span></div>
        <div class="store-list" id="storeList">${rows.map(storeRowHtml).join("")}${
          state.filteredStores.length > rows.length
            ? `<div class="list-limit">Showing the first ${rows.length} locations. Refine filters to narrow the list.</div>`
            : ""
        }${rows.length ? "" : '<div class="list-limit">No locations match these filters.</div>'}</div>
      </section>`;
    bindNetworkView();
  }

  function storeRowHtml(store) {
    return `<button class="store-row ${store.store_id === state.selectedStoreId ? "active" : ""}" data-store-id="${escapeHtml(
      store.store_id
    )}" data-retailer="${escapeHtml(store.retailer)}" style="--row-color:${BRAND_CONFIG[store.retailer].color}">
      <span class="row-marker"></span><span class="row-copy"><strong>${escapeHtml(store.name)}</strong>
      <small>${escapeHtml(`${store.suburb}, ${store.state} ${store.postcode}`)}</small></span>
      <span class="row-type">${escapeHtml(store.location_type)}</span></button>`;
  }

  function bindNetworkView() {
    const search = document.getElementById("searchInput");
    const service = document.getElementById("serviceInput");
    search.addEventListener("input", () => {
      state.filters.search = search.value;
      applyFilters();
    });
    service.addEventListener("input", () => {
      state.filters.service = service.value;
      applyFilters();
    });
    [
      ["stateSelect", "state"],
      ["locationSelect", "location"],
      ["audiologySelect", "audiology"],
      ["statusSelect", "status"],
    ].forEach(([id, key]) => {
      document.getElementById(id).addEventListener("change", (event) => {
        state.filters[key] = event.target.value;
        applyFilters();
      });
    });
    document.querySelectorAll('.retailer-option input[type="checkbox"]').forEach((input) => {
      input.addEventListener("change", () => {
        if (input.checked) state.filters.retailers.add(input.value);
        else state.filters.retailers.delete(input.value);
        applyFilters();
      });
    });
    document.getElementById("storeList").addEventListener("click", (event) => {
      const row = event.target.closest("[data-store-id]");
      if (row) selectStore(row.dataset.storeId, true);
    });
  }

  function applyFilters(render = true) {
    const query = state.filters.search.trim().toLowerCase();
    const serviceQuery = state.filters.service.trim().toLowerCase();
    state.filteredStores = state.allStores.filter((store) => {
      const haystack =
        `${store.name} ${store.suburb} ${store.postcode} ${store.full_address} ${store.venue_name}`.toLowerCase();
      return (
        state.filters.retailers.has(store.retailer) &&
        (!query || haystack.includes(query)) &&
        (!state.filters.state || store.state === state.filters.state) &&
        (!state.filters.location || store.location_type === state.filters.location) &&
        (!state.filters.audiology || String(store.audiology) === state.filters.audiology) &&
        (!state.filters.status || store.status === state.filters.status) &&
        (!serviceQuery || store.services.toLowerCase().includes(serviceQuery))
      );
    });
    storeClusters.clearLayers();
    state.filteredStores.forEach((store) => storeClusters.addLayer(markerById.get(store.store_id)));
    elements.visibleTotal.textContent = state.filteredStores.length.toLocaleString("en-AU");
    if (render && state.view === "network") renderNetworkView();
    updateSaturationLayer();
    updateShareUrl(false);
  }

  function renderCentresView() {
    const query = state.filters.search.toLowerCase();
    const centres = state.centres
      .filter((centre) => !query || `${centre.name} ${centre.suburb} ${centre.state} ${centre.manager}`.toLowerCase().includes(query))
      .sort((a, b) => b.optical_store_count - a.optical_store_count || a.name.localeCompare(b.name));
    const enriched = state.centres.filter((centre) => centre.confidence === "High").length;
    elements.viewContent.innerHTML = `
      <section class="filters">
        <label class="search-field"><i data-lucide="search"></i><span class="sr-only">Search centres</span>
          <input id="centreSearch" type="search" value="${escapeHtml(state.filters.search)}" placeholder="Centre, owner or suburb" />
        </label>
        <div class="compact-metrics">
          <div><strong>${state.centres.length}</strong><span>reviewed venues</span></div>
          <div><strong>${state.centres.filter((centre) => centre.retailers.length > 1).length}</strong><span>multi-brand</span></div>
          <div><strong>${enriched}</strong><span>fully enriched</span></div>
        </div>
      </section>
      <section class="result-section">
        <div class="section-heading"><h2>Centre profiles</h2><span>${centres.length} results</span></div>
        <div class="centre-list" id="centreList">${centres
          .slice(0, 160)
          .map(
            (centre) => `<button class="centre-row" data-centre-id="${escapeHtml(centre.centre_id)}">
              <span class="centre-row-icon"><i data-lucide="building-2"></i></span>
              <span><strong>${escapeHtml(centre.name)}</strong><small>${escapeHtml(
              `${centre.suburb}, ${centre.state}`
            )}</small></span>
              <span><strong>${centre.optical_store_count}</strong><small>${centre.retailers.length} brands</small></span>
            </button>`
          )
          .join("")}</div>
      </section>`;
    document.getElementById("centreSearch").addEventListener("input", (event) => {
      state.filters.search = event.target.value;
      renderCentresView();
    });
    document.getElementById("centreList").addEventListener("click", (event) => {
      const row = event.target.closest("[data-centre-id]");
      if (!row) return;
      const centre = state.centres.find((item) => item.centre_id === row.dataset.centreId);
      openCentreDetail(centre);
      map.setView([centre.latitude, centre.longitude], 15);
    });
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

  function renderOpportunityView() {
    elements.viewContent.innerHTML = `
      <section class="opportunity-form">
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
        <p class="form-note">Scores use sourced ABS market data and visible network evidence. Unavailable components reduce coverage rather than being guessed.</p>
      </section>
      <section class="result-section">
        <div class="section-heading"><h2>Shortlist</h2><span>${state.candidates.length} sites</span></div>
        <div class="candidate-list" id="candidateList">${
          state.candidates.length
            ? state.candidates.map(candidateListRow).join("")
            : '<div class="empty-state"><i data-lucide="map-pin-plus"></i><strong>No candidates yet</strong><span>Drop a site to begin a scored comparison.</span></div>'
        }</div>
      </section>`;
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
        <div><span>ABS market indicators</span><strong>26 May 2026</strong></div>
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
    elements.viewContent.innerHTML = `
      <section class="compare-intro">
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

  function candidateComparisonTable(candidates) {
    const models = candidates.map((candidate) => ({ candidate, model: scoreCandidate(candidate) }));
    const rows = [
      ["Score", (item) => item.model.score ?? "-"],
      ["Coverage", (item) => `${item.model.coverage}%`],
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

  function distanceEntries(point, excludeId = "") {
    return state.allStores
      .filter((store) => store.store_id !== excludeId)
      .map((store) => ({ store, distance: Intel.haversine(point, store) }))
      .sort((a, b) => a.distance - b.distance || a.store.store_id.localeCompare(b.store.store_id));
  }

  function proximityModel(point, baseStore = null) {
    const distances = distanceEntries(point, baseStore?.store_id || "");
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
      baseStore && baseStore.venue_id
        ? state.allStores.filter(
            (store) =>
              store.store_id !== baseStore.store_id &&
              store.retailer !== baseStore.retailer &&
              store.venue_id === baseStore.venue_id
          )
        : [];
    return { distances, nearestByBrand, radiusCounts, sameCentre };
  }

  function nearestBrandHtml(model) {
    return BRAND_ORDER.map((brand) => {
      const entry = model.nearestByBrand[brand];
      return `<div class="nearest-brand"><span>${escapeHtml(brand)}</span><strong>${
        entry ? Intel.formatDistance(entry.distance) : "None"
      }</strong></div>`;
    }).join("");
  }

  function radiusTableHtml(model) {
    return `<table class="radius-table"><thead><tr><th>Radius</th><th>OPSM</th><th>SPEC</th><th>BN</th><th>Total</th></tr></thead>
      <tbody>${model.radiusCounts
        .map(
          (row) => `<tr><td>${row.radius < 1 ? `${row.radius * 1000} m` : `${row.radius} km`}</td>
            <td>${row.counts.OPSM}</td><td>${row.counts.Specsavers}</td><td>${row.counts["Bailey Nelson"]}</td><td>${row.total}</td></tr>`
        )
        .join("")}</tbody></table>`;
  }

  function nearRows(entries, limit = 10) {
    if (!entries.length) return '<p class="empty-note">No matching locations found.</p>';
    return entries
      .slice(0, limit)
      .map(
        (entry) => `<button class="near-row" data-store-id="${escapeHtml(entry.store.store_id)}" style="--row-color:${
          BRAND_CONFIG[entry.store.retailer].color
        }"><span class="dot"></span><strong>${escapeHtml(entry.store.name)}</strong><span>${Intel.formatDistance(
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
        <span class="retailer-tag"><span class="marker-key marker-${
          config.slug === "bailey-nelson" ? "bailey" : config.slug
        }"></span>${escapeHtml(store.retailer)}</span>
        <h2>${escapeHtml(store.name)}</h2><address>${escapeHtml(store.full_address)}</address>
        <div class="link-row">${store.phone ? `<a class="command-link" href="tel:${escapeHtml(store.phone.replace(/[^+\d]/g, ""))}"><i data-lucide="phone"></i>Call</a>` : ""}
          <a class="command-link primary" href="${escapeHtml(store.official_url)}" target="_blank" rel="noopener"><i data-lucide="external-link"></i>Official store</a></div>
      </header>
      <section class="detail-section">
        <h3>Leasing profile</h3>
        <div class="data-grid">
          <div class="data-point"><span>Location type</span><strong>${escapeHtml(store.location_type)}</strong></div>
          <div class="data-point"><span>Classification</span><strong><span class="confidence">${escapeHtml(
            store.classification_confidence
          )}</span></strong></div>
          <div class="data-point"><span>Venue</span><strong>${escapeHtml(store.venue_name || "Not confirmed")}</strong></div>
          <div class="data-point"><span>Status</span><strong>${escapeHtml(store.status)}</strong></div>
        </div>
        ${areaHtml(store)}
        <p class="empty-note">${escapeHtml(store.classification_basis)}</p>
        <div class="service-list">${services.length ? services.map((service) => `<span>${escapeHtml(service)}</span>`).join("") : "<span>No services listed</span>"}</div>
        <div class="link-row"><button class="detail-action" id="compareFromDetail" type="button"><i data-lucide="ruler"></i>Add to store comparison</button></div>
      </section>
      ${market ? marketEvidenceHtml(market.properties) : ""}
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
      <section class="detail-section source-block"><i data-lucide="database"></i><div><strong>Official retailer source</strong>
        <span>Refreshed ${escapeHtml(formatDate(store.fetched_at))} · ${escapeHtml(store.store_id)}</span></div></section>`;
    openDetailPanel();
    document.getElementById("compareFromDetail").addEventListener("click", () => {
      setStoreCompareMode(true);
      addCompareStore(store);
    });
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
        <div class="data-point"><span>Weekly household income</span><strong>$${formatNumber(
          properties.median_household_income_weekly_2021
        )}</strong></div>
        <div class="data-point"><span>Retail businesses 2025</span><strong>${formatNumber(
          properties.retail_businesses_2025
        )}</strong></div>
        <div class="data-point"><span>Unemployment 2021</span><strong>${formatNumber(
          properties.unemployment_rate_2021,
          "%"
        )}</strong></div>
      </div>
      <p class="empty-note">ABS Data by Region, released 26 May 2026. Census-derived measures retain their 2021 reference year.</p>
    </section>`;
  }

  function openCentreDetail(centre) {
    state.selectedCentreId = centre.centre_id;
    const stores = state.allStores.filter((store) => store.venue_id === centre.centre_id);
    elements.detailContent.innerHTML = `
      <header class="detail-header" style="--brand-color:#d29b27">
        <span class="retailer-tag"><i data-lucide="building-2"></i>Centre profile</span>
        <h2>${escapeHtml(centre.name)}</h2><address>${escapeHtml(`${centre.suburb}, ${centre.state}`)}</address>
        ${centre.public_url ? `<div class="link-row"><a class="command-link primary" href="${escapeHtml(
          centre.public_url
        )}" target="_blank" rel="noopener"><i data-lucide="external-link"></i>Public centre source</a></div>` : ""}
      </header>
      <section class="detail-section"><h3>Ownership and scale</h3>
        <div class="data-grid">
          <div class="data-point"><span>Owner</span><strong>${escapeHtml(centre.owner || "Not published")}</strong></div>
          <div class="data-point"><span>Manager</span><strong>${escapeHtml(centre.manager || "Not confirmed")}</strong></div>
          <div class="data-point"><span>Centre type</span><strong>${escapeHtml(centre.centre_type || "Not classified")}</strong></div>
          <div class="data-point"><span>Confidence</span><strong><span class="confidence">${escapeHtml(
            centre.confidence
          )}</span></strong></div>
          <div class="data-point"><span>Total GLA</span><strong>${centre.gla_sqm ? formatNumber(centre.gla_sqm, " sqm") : "Not published"}</strong></div>
          <div class="data-point"><span>Annual visits</span><strong>${formatNumber(centre.annual_visits)}</strong></div>
          <div class="data-point"><span>Trade area population</span><strong>${formatNumber(
            centre.trade_area_population
          )}</strong></div>
          <div class="data-point"><span>Tenancies</span><strong>${formatNumber(centre.tenancy_count)}</strong></div>
        </div>
      </section>
      <section class="detail-section"><h3>Optical representation</h3>
        <div class="brand-presence">${BRAND_ORDER.map(
          (brand) =>
            `<span class="${stores.some((store) => store.retailer === brand) ? "present" : ""}"><i style="--brand:${
              BRAND_CONFIG[brand].color
            }"></i>${escapeHtml(brand)}</span>`
        ).join("")}</div>
        <div class="nearest-list">${stores.map((store) => nearRows([{ store, distance: 0 }], 1)).join("")}</div>
      </section>
      <section class="detail-section"><h3>Anchors and activity</h3>
        <p>${centre.anchors.length ? escapeHtml(centre.anchors.join(", ")) : "Anchor mix not yet recorded."}</p>
        <p class="empty-note">${escapeHtml(centre.redevelopment_activity || "No sourced redevelopment note.")}</p>
      </section>
      <section class="detail-section source-block"><i data-lucide="database"></i><div><strong>${escapeHtml(
        centre.source_basis
      )}</strong><span>${centre.metrics_date ? `Metrics dated ${escapeHtml(formatDate(centre.metrics_date))}` : "Centre metrics remain incomplete"}</span></div></section>`;
    openDetailPanel();
    bindNearRows();
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
    return Intel.candidateScore({
      point: candidate,
      stores: state.allStores,
      markets: state.markets,
      market: marketForPoint(candidate),
      centres: state.centres,
      profile: selectedProfile(candidate),
      areaSqm: candidate.area_sqm,
      targetAreaMin: candidate.target_min_sqm,
      targetAreaMax: candidate.target_max_sqm,
      amenitySummary: candidate.amenity_summary || null,
    });
  }

  function openCandidateDetail(candidate) {
    state.selectedCandidateId = candidate.id;
    const model = scoreCandidate(candidate);
    const market = marketForPoint(candidate);
    const proximity = proximityModel(candidate);
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
          <strong>${model.score ?? "-"}</strong><span>site score</span>
        </div>
        <div><strong>${model.coverage}% evidence coverage</strong>
          <p>${model.reliable ? "Score meets the 70% evidence threshold." : "Directional only. Add area or local amenity evidence before ranking."}</p>
          <span class="confidence">${model.reliable ? "Reliable comparison" : "Low coverage"}</span>
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
            model.nearestCentre?.centre.name || "No reviewed centre within 750 m"
          )}</strong></div>
        </div>
      </section>
      ${market ? marketEvidenceHtml(market.properties) : ""}
      <section class="detail-section"><h3>Catchment estimates</h3>${catchmentTableHtml(catchments)}
        <p class="empty-note">Population uses whole SA2 areas intersecting each straight-line radius, so edge catchments can be overstated. It is not a drive-time or customer-origin trade area.</p>
      </section>
      <section class="detail-section"><h3>Nearest brand locations</h3><div class="proximity-summary">${nearestBrandHtml(
        proximity
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
      storeClusters.zoomToShowLayer(marker, () => map.setView([store.latitude, store.longitude], Math.max(map.getZoom(), 14)));
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
    elements.compareA.textContent = state.compareStores[0]?.name || "Select first store";
    elements.compareB.textContent = state.compareStores[1]?.name || "Select second store";
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
    const point = { latitude: latlng.lat, longitude: latlng.lng };
    const amenitySummary = state.amenityMarkers.reduce(
      (summary, marker) => {
        if (Intel.haversine(point, marker) <= 1) summary[marker.kind] += 1;
        return summary;
      },
      { health: 0, transport: 0, parking: 0 }
    );
    const candidate = {
      id: `candidate-${Date.now().toString(36)}`,
      name: state.opportunityForm.name.trim() || `Candidate ${state.candidates.length + 1}`,
      latitude: Number(latlng.lat.toFixed(6)),
      longitude: Number(latlng.lng.toFixed(6)),
      area_sqm: state.opportunityForm.area_sqm || "",
      target_min_sqm: state.opportunityForm.target_min_sqm || "",
      target_max_sqm: state.opportunityForm.target_max_sqm || "",
      profile_id: state.opportunityForm.profile_id || "generic-optical",
      amenity_summary: state.amenityMarkers.length ? amenitySummary : null,
      created_at: new Date().toISOString(),
    };
    state.candidates.push(candidate);
    createCandidateMarker(candidate);
    setCandidateDropMode(false);
    elements.candidateDock.hidden = false;
    renderCandidateDock();
    openCandidateDetail(candidate);
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
        <span>Released 26 May 2026 · High confidence</span></div></section>`;
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
    const proximity = proximityModel(target);
    document.getElementById("reportDate").textContent = formatDate(new Date().toISOString());
    elements.reportContent.innerHTML = `
      <section class="report-lead"><div><p>Candidate</p><h3>${escapeHtml(target.name)}</h3><span>${escapeHtml(
      marketLabel(target)
    )}</span></div><div class="report-score"><strong>${model.score ?? "-"}</strong><span>Site score</span><small>${
      model.coverage
    }% coverage</small></div></section>
      <section><h3>Executive evidence</h3><div class="report-grid">
        <div><span>Population 2025</span><strong>${formatNumber(market.population_2025)}</strong></div>
        <div><span>Growth 2021–25</span><strong>${formatNumber(market.population_growth_2021_2025_pct, "%")}</strong></div>
        <div><span>Age 45+</span><strong>${formatNumber(market.age_45_plus_pct_2021, "%")}</strong></div>
        <div><span>Weekly household income</span><strong>$${formatNumber(
          market.median_household_income_weekly_2021
        )}</strong></div>
        <div><span>5 km competitors</span><strong>${model.competitorCountFiveKm}</strong></div>
        <div><span>Nearest competing store</span><strong>${Intel.formatDistance(model.nearestCompetitorKm)}</strong></div>
      </div></section>
      <section><h3>Transparent score</h3>${scoreComponentsHtml(model)}</section>
      <section><h3>Straight-line catchments</h3>${catchmentTableHtml(catchments)}</section>
      <section><h3>Nearest networks</h3><div class="proximity-summary">${nearestBrandHtml(proximity)}</div></section>
      <section><h3>Risks and gaps</h3><ul>
        <li>${model.reliable ? "Evidence coverage meets the ranking threshold." : "Evidence coverage is below the 70% ranking threshold."}</li>
        <li>${target.area_sqm ? "Available area has been supplied for format testing." : "Available tenancy area has not been supplied."}</li>
        <li>${model.nearestCentre ? `Nearest reviewed centre is ${escapeHtml(model.nearestCentre.centre.name)}.` : "No reviewed shopping centre is recorded within 750 metres."}</li>
        <li>Driving time, pedestrian barriers, rent and lease terms are outside this public assessment.</li>
      </ul></section>
      <section><h3>Sources</h3><p>Australian Bureau of Statistics Data by Region 2011–25, official retailer locators, reviewed venue IDs and public landlord profiles where available. Every source retains its own reference date.</p></section>`;
    elements.reportSheet.setAttribute("aria-hidden", "false");
    window.print();
    window.setTimeout(() => elements.reportSheet.setAttribute("aria-hidden", "true"), 500);
  }

  function shareState() {
    const center = map.getCenter();
    return Intel.sanitiseShareState({
      view: state.view,
      filters: state.filters,
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
    showToast("View saved in this browser.");
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
    if (!payload) return;
    if (VIEW_CONFIG[payload.view]) state.view = payload.view;
    if (payload.filters) {
      state.filters.retailers = new Set(
        payload.filters.retailers?.filter((retailer) => BRAND_ORDER.includes(retailer)) || BRAND_ORDER
      );
      state.filters.state = payload.filters.state || "";
      state.filters.location = payload.filters.location || "";
      state.filters.search = payload.filters.search || "";
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
  }

  function csvEscape(value) {
    const text = String(value ?? "");
    return /[",\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
  }

  function downloadFilteredCsv() {
    const rows = [PUBLIC_STORE_FIELDS.join(",")].concat(
      state.filteredStores.map((store) => PUBLIC_STORE_FIELDS.map((field) => csvEscape(store[field])).join(","))
    );
    const blob = new Blob([`${rows.join("\n")}\n`], { type: "text/csv;charset=utf-8" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `optical-stores-filtered-${new Date().toISOString().slice(0, 10)}.csv`;
    document.body.appendChild(link);
    link.click();
    window.setTimeout(() => {
      URL.revokeObjectURL(link.href);
      link.remove();
    }, 1000);
  }

  function resetAll() {
    state.filters = {
      retailers: new Set(BRAND_ORDER),
      search: "",
      state: "",
      location: "",
      audiology: "",
      status: "",
      service: "",
    };
    state.candidates = [];
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
    map.setView(AUSTRALIA_VIEW.center, AUSTRALIA_VIEW.zoom);
    setView("network");
    renderCandidateDock();
    showToast("Workspace reset.");
  }

  function bindGlobalEvents() {
    document.querySelectorAll("[data-view]").forEach((button) =>
      button.addEventListener("click", () => setView(button.dataset.view))
    );
    document.getElementById("panelClose").addEventListener("click", closeDetail);
    document.getElementById("resetButton").addEventListener("click", resetAll);
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
    document.getElementById("reportButton").addEventListener("click", () => generateReport());
    document.getElementById("downloadButton").addEventListener("click", downloadFilteredCsv);
    map.on("click", (event) => {
      if (state.candidateDropMode) dropCandidate(event.latlng);
    });
    map.on("moveend", () => {
      if (["health", "transport", "parking"].some((layer) => state.activeLayers.has(layer))) loadAmenities();
      updateShareUrl(false);
    });
    window.addEventListener("resize", () => map.invalidateSize());
  }

  async function loadJson(path) {
    const response = await fetch(path, { cache: "no-store" });
    if (!response.ok) throw new Error(`${path} returned ${response.status}`);
    return response.json();
  }

  async function initialise() {
    try {
      const [stores, markets, centres, links, events, profiles] = await Promise.all([
        loadJson("data/optical_stores.geojson"),
        loadJson("data/sa2_market.geojson"),
        loadJson("data/centres.json"),
        loadJson("data/store_market_links.json"),
        loadJson("data/network_events.json"),
        loadJson("data/brand_profiles.json"),
      ]);
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
      state.centres = centres.centres;
      state.storeLinks = links.links;
      state.events = events;
      state.profiles = profiles.profiles;
      createStoreMarkers();
      createCentreMarkers();
      bindGlobalEvents();
      restoreShareState();
      applyFilters(false);
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
