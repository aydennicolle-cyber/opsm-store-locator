(function () {
  "use strict";

  const BRAND_ORDER = ["OPSM", "Specsavers", "Bailey Nelson"];
  const BRAND_CONFIG = {
    OPSM: { color: "#0087a1", slug: "opsm", short: "OPSM" },
    Specsavers: { color: "#4f7f31", slug: "specsavers", short: "SPEC" },
    "Bailey Nelson": { color: "#e05b44", slug: "bailey-nelson", short: "BN" },
  };
  const RADII = [0.5, 1, 2, 5, 10];
  const AUSTRALIA_VIEW = { center: [-25.8, 134.4], zoom: 4 };

  const elements = {
    search: document.getElementById("searchInput"),
    state: document.getElementById("stateSelect"),
    location: document.getElementById("locationSelect"),
    audiology: document.getElementById("audiologySelect"),
    status: document.getElementById("statusSelect"),
    service: document.getElementById("serviceInput"),
    visibleTotal: document.getElementById("visibleTotal"),
    freshness: document.getElementById("freshnessLabel"),
    resultCount: document.getElementById("resultCount"),
    storeList: document.getElementById("storeList"),
    detailPanel: document.getElementById("detailPanel"),
    detailContent: document.getElementById("detailContent"),
    loading: document.getElementById("loadingState"),
    modeNotice: document.getElementById("modeNotice"),
    compareButton: document.getElementById("compareButton"),
    candidateButton: document.getElementById("candidateButton"),
    compareTray: document.getElementById("compareTray"),
    compareA: document.getElementById("compareA"),
    compareB: document.getElementById("compareB"),
    compareDistance: document.getElementById("compareDistance"),
  };

  let allStores = [];
  let filteredStores = [];
  let metadata = {};
  let selectedId = "";
  let compareMode = false;
  let candidateMode = false;
  let compareStores = [];
  let compareLine = null;
  let candidateMarker = null;
  let candidatePoint = null;
  const markerById = new Map();

  const map = L.map("map", { zoomControl: false, preferCanvas: true }).setView(
    AUSTRALIA_VIEW.center,
    AUSTRALIA_VIEW.zoom
  );
  L.control.zoom({ position: "bottomright" }).addTo(map);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
  }).addTo(map);

  const clusters = L.markerClusterGroup({
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

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function formatDistance(km) {
    if (!Number.isFinite(km)) return "-";
    return km < 1 ? `${Math.round(km * 1000)} m` : `${km.toFixed(km < 10 ? 1 : 0)} km`;
  }

  function haversine(pointA, pointB) {
    const earthRadius = 6371.0088;
    const toRadians = (degrees) => (degrees * Math.PI) / 180;
    const lat1 = toRadians(pointA.latitude);
    const lat2 = toRadians(pointB.latitude);
    const deltaLat = toRadians(pointB.latitude - pointA.latitude);
    const deltaLon = toRadians(pointB.longitude - pointA.longitude);
    const a =
      Math.sin(deltaLat / 2) ** 2 +
      Math.cos(lat1) * Math.cos(lat2) * Math.sin(deltaLon / 2) ** 2;
    return earthRadius * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  }

  window.OpticalMapUtils = { haversine, formatDistance };

  function formatDate(value) {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value || "Not recorded";
    return new Intl.DateTimeFormat("en-AU", { day: "numeric", month: "short", year: "numeric" }).format(date);
  }

  function refreshIcons() {
    if (window.lucide) window.lucide.createIcons({ attrs: { "stroke-width": 1.8 } });
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

  function createMarkers() {
    allStores.forEach((store) => {
      const marker = L.marker([store.latitude, store.longitude], {
        icon: storeIcon(store),
        retailer: store.retailer,
        storeId: store.store_id,
        title: store.name,
      });
      marker.on("click", () => selectStore(store.store_id, false));
      marker.bindTooltip(`<strong>${escapeHtml(store.name)}</strong><br>${escapeHtml(store.suburb)}, ${escapeHtml(store.state)}`, {
        direction: "top",
        offset: [0, -8],
      });
      markerById.set(store.store_id, marker);
    });
  }

  function activeRetailers() {
    return new Set(
      Array.from(document.querySelectorAll('.retailer-option input[type="checkbox"]:checked')).map(
        (input) => input.value
      )
    );
  }

  function applyFilters() {
    const retailers = activeRetailers();
    const query = elements.search.value.trim().toLowerCase();
    const serviceQuery = elements.service.value.trim().toLowerCase();
    filteredStores = allStores.filter((store) => {
      const haystack = `${store.name} ${store.suburb} ${store.postcode} ${store.full_address} ${store.venue_name}`.toLowerCase();
      return (
        retailers.has(store.retailer) &&
        (!query || haystack.includes(query)) &&
        (!elements.state.value || store.state === elements.state.value) &&
        (!elements.location.value || store.location_type === elements.location.value) &&
        (!elements.audiology.value || String(store.audiology) === elements.audiology.value) &&
        (!elements.status.value || store.status === elements.status.value) &&
        (!serviceQuery || store.services.toLowerCase().includes(serviceQuery))
      );
    });
    renderFilteredNetwork();
  }

  function renderFilteredNetwork() {
    clusters.clearLayers();
    filteredStores.forEach((store) => clusters.addLayer(markerById.get(store.store_id)));
    elements.visibleTotal.textContent = filteredStores.length.toLocaleString("en-AU");
    elements.resultCount.textContent = `${filteredStores.length.toLocaleString("en-AU")} results`;
    BRAND_ORDER.forEach((brand) => {
      const count = filteredStores.filter((store) => store.retailer === brand).length;
      const id = brand === "OPSM" ? "opsmCount" : brand === "Specsavers" ? "specsaversCount" : "baileyCount";
      document.getElementById(id).textContent = count;
    });
    renderStoreList();
  }

  function renderStoreList() {
    const rows = filteredStores.slice(0, 100);
    elements.storeList.innerHTML = rows
      .map((store) => {
        const color = BRAND_CONFIG[store.retailer].color;
        return `<button class="store-row ${store.store_id === selectedId ? "active" : ""}" data-store-id="${escapeHtml(
          store.store_id
        )}" data-retailer="${escapeHtml(store.retailer)}" style="--row-color:${color}">
          <span class="row-marker"></span>
          <span class="row-copy"><strong>${escapeHtml(store.name)}</strong><small>${escapeHtml(
          `${store.suburb}, ${store.state} ${store.postcode}`
        )}</small></span>
          <span class="row-type">${escapeHtml(store.location_type)}</span>
        </button>`;
      })
      .join("");
    if (filteredStores.length > rows.length) {
      elements.storeList.insertAdjacentHTML(
        "beforeend",
        `<div class="list-limit">Showing the first ${rows.length} locations. Refine the filters to narrow the list.</div>`
      );
    }
    if (!rows.length) {
      elements.storeList.innerHTML = '<div class="list-limit">No locations match these filters.</div>';
    }
  }

  function distanceEntries(point, excludeId = "") {
    return allStores
      .filter((store) => store.store_id !== excludeId)
      .map((store) => ({ store, distance: haversine(point, store) }))
      .sort((a, b) => a.distance - b.distance || a.store.store_id.localeCompare(b.store.store_id));
  }

  function proximityModel(point, baseStore = null) {
    const distances = distanceEntries(point, baseStore ? baseStore.store_id : "");
    const nearestByBrand = Object.fromEntries(
      BRAND_ORDER.map((brand) => [brand, distances.find((entry) => entry.store.retailer === brand) || null])
    );
    const radiusCounts = RADII.map((radius) => {
      const inside = distances.filter(
        (entry) => entry.distance <= radius && (!baseStore || entry.store.retailer !== baseStore.retailer)
      );
      return {
        radius,
        counts: Object.fromEntries(BRAND_ORDER.map((brand) => [brand, inside.filter((entry) => entry.store.retailer === brand).length])),
        total: inside.length,
      };
    });
    const sameCentre = baseStore && baseStore.venue_id
      ? allStores.filter(
          (store) =>
            store.store_id !== baseStore.store_id &&
            store.retailer !== baseStore.retailer &&
            store.venue_id === baseStore.venue_id
        )
      : [];
    const competitors = baseStore ? distances.filter((entry) => entry.store.retailer !== baseStore.retailer) : distances;
    const withinTen = competitors.filter((entry) => entry.distance <= 10);
    const represented = new Set(withinTen.map((entry) => entry.store.retailer));
    const missingBrands = BRAND_ORDER.filter((brand) => !represented.has(brand));
    let signal = "";
    if (baseStore) {
      const withinFive = competitors.filter((entry) => entry.distance <= 5);
      if (!withinFive.length) {
        signal = `${baseStore.retailer} is the only represented optical brand within 5 km.`;
      } else if (competitors[0] && competitors[0].distance > 2) {
        signal = `Low immediate overlap: the nearest competing brand is ${formatDistance(competitors[0].distance)} away.`;
      } else if (missingBrands.length) {
        signal = `${missingBrands.join(" and ")} ${missingBrands.length === 1 ? "is" : "are"} not represented within 10 km.`;
      }
    } else if (missingBrands.length) {
      signal = `Candidate gap: ${missingBrands.join(" and ")} ${missingBrands.length === 1 ? "is" : "are"} not represented within 10 km.`;
    } else if (distances[0]) {
      signal = `All three brands are represented within 10 km; the nearest store is ${formatDistance(distances[0].distance)} away.`;
    }
    return { distances, nearestByBrand, radiusCounts, sameCentre, signal };
  }

  function nearestBrandHtml(model) {
    return BRAND_ORDER.map((brand) => {
      const entry = model.nearestByBrand[brand];
      return `<div class="nearest-brand"><span>${escapeHtml(brand)}</span><strong>${entry ? formatDistance(entry.distance) : "None"}</strong></div>`;
    }).join("");
  }

  function radiusTableHtml(model) {
    return `<table class="radius-table">
      <thead><tr><th>Radius</th><th>OPSM</th><th>SPEC</th><th>BN</th><th>Total</th></tr></thead>
      <tbody>${model.radiusCounts
        .map(
          (row) => `<tr><td>${row.radius < 1 ? `${row.radius * 1000} m` : `${row.radius} km`}</td><td>${
            row.counts.OPSM
          }</td><td>${row.counts.Specsavers}</td><td>${row.counts["Bailey Nelson"]}</td><td>${row.total}</td></tr>`
        )
        .join("")}</tbody>
    </table>`;
  }

  function nearRows(entries, limit = 10) {
    if (!entries.length) return '<p class="empty-note">No matching locations found.</p>';
    return entries
      .slice(0, limit)
      .map(
        (entry) => `<div class="near-row" style="--row-color:${BRAND_CONFIG[entry.store.retailer].color}">
          <span class="dot"></span><strong>${escapeHtml(entry.store.name)}</strong><span>${formatDistance(entry.distance)}</span>
        </div>`
      )
      .join("");
  }

  function openStoreDetail(store) {
    const config = BRAND_CONFIG[store.retailer];
    const services = store.services
      .split(/[;,]/)
      .map((value) => value.trim())
      .filter(Boolean);
    const model = proximityModel(store, store);
    const sameCentreEntries = model.sameCentre.map((match) => ({ store: match, distance: haversine(store, match) }));
    const phoneLink = store.phone ? `<a class="command-link" href="tel:${escapeHtml(store.phone.replace(/[^+\d]/g, ""))}"><i data-lucide="phone"></i>Call</a>` : "";
    elements.detailContent.innerHTML = `
      <header class="detail-header" style="--brand-color:${config.color}">
        <span class="retailer-tag"><span class="marker-key marker-${config.slug === "bailey-nelson" ? "bailey" : config.slug}"></span>${escapeHtml(
      store.retailer
    )}</span>
        <h2>${escapeHtml(store.name)}</h2>
        <address>${escapeHtml(store.full_address)}</address>
        <div class="link-row">${phoneLink}<a class="command-link primary" href="${escapeHtml(
      store.official_url
    )}" target="_blank" rel="noopener"><i data-lucide="external-link"></i>Official store</a></div>
      </header>
      <section class="detail-section">
        <h3>Leasing profile</h3>
        <div class="data-grid">
          <div class="data-point"><span>Location type</span><strong>${escapeHtml(store.location_type)}</strong></div>
          <div class="data-point"><span>Confidence</span><strong><span class="confidence">${escapeHtml(
            store.classification_confidence
          )}</span></strong></div>
          <div class="data-point"><span>Venue</span><strong>${escapeHtml(store.venue_name || "Not confirmed")}</strong></div>
          <div class="data-point"><span>Status</span><strong>${escapeHtml(store.status)}</strong></div>
        </div>
        <p class="empty-note">${escapeHtml(store.classification_basis)}</p>
        <div class="service-list">${services.length ? services.map((service) => `<span>${escapeHtml(service)}</span>`).join("") : "<span>No services listed</span>"}</div>
        <div class="link-row"><button class="detail-action" id="compareFromDetail" type="button"><i data-lucide="ruler"></i>Add to comparison</button></div>
      </section>
      <section class="detail-section">
        <h3>Nearest brand locations</h3>
        <div class="proximity-summary">${nearestBrandHtml(model)}</div>
        ${model.signal ? `<div class="signal">${escapeHtml(model.signal)}</div>` : ""}
        ${radiusTableHtml(model)}
      </section>
      <section class="detail-section">
        <h3>Same-centre competitors</h3>
        <div class="same-centre-list">${
          sameCentreEntries.length
            ? nearRows(sameCentreEntries, 10)
            : '<p class="empty-note">No reviewed same-centre competitor is recorded. Proximity alone is never used to assign a venue.</p>'
        }</div>
      </section>
      <section class="detail-section">
        <h3>Ten nearest stores</h3>
        <div class="nearest-list">${nearRows(model.distances, 10)}</div>
      </section>
      <section class="detail-section">
        <div class="data-grid">
          <div class="data-point"><span>Source refreshed</span><strong>${escapeHtml(formatDate(store.fetched_at))}</strong></div>
          <div class="data-point"><span>Store ID</span><strong>${escapeHtml(store.store_id)}</strong></div>
        </div>
      </section>`;
    elements.detailPanel.classList.add("open");
    elements.detailPanel.setAttribute("aria-hidden", "false");
    document.getElementById("compareFromDetail").addEventListener("click", () => {
      if (!compareMode) setCompareMode(true);
      addCompareStore(store);
    });
    refreshIcons();
  }

  function openCandidateDetail(point) {
    const model = proximityModel(point, null);
    elements.detailContent.innerHTML = `
      <header class="detail-header" style="--brand-color:#a24f93">
        <span class="retailer-tag"><i data-lucide="map-pin-plus"></i>Candidate site</span>
        <h2>Proposed leasing location</h2>
        <address>${point.latitude.toFixed(5)}, ${point.longitude.toFixed(5)}</address>
      </header>
      <section class="detail-section">
        <h3>Nearest brand locations</h3>
        <div class="proximity-summary">${nearestBrandHtml(model)}</div>
        ${model.signal ? `<div class="signal">${escapeHtml(model.signal)}</div>` : ""}
        ${radiusTableHtml(model)}
      </section>
      <section class="detail-section">
        <h3>Ten nearest stores</h3>
        <div class="nearest-list">${nearRows(model.distances, 10)}</div>
      </section>
      <section class="detail-section">
        <p class="empty-note">Distances are straight-line measures from the dropped pin. They do not represent driving time, pedestrian access or trade-area barriers.</p>
      </section>`;
    elements.detailPanel.classList.add("open");
    elements.detailPanel.setAttribute("aria-hidden", "false");
    refreshIcons();
  }

  function selectStore(storeId, moveMap = true) {
    const store = allStores.find((item) => item.store_id === storeId);
    if (!store) return;
    selectedId = storeId;
    if (compareMode) addCompareStore(store);
    openStoreDetail(store);
    renderStoreList();
    if (moveMap) {
      const marker = markerById.get(storeId);
      clusters.zoomToShowLayer(marker, () => map.setView([store.latitude, store.longitude], Math.max(map.getZoom(), 14)));
    }
  }

  function closeDetail() {
    selectedId = "";
    elements.detailPanel.classList.remove("open");
    elements.detailPanel.setAttribute("aria-hidden", "true");
    renderStoreList();
  }

  function setCompareMode(active) {
    compareMode = active;
    if (active) setCandidateMode(false);
    elements.compareButton.classList.toggle("active", active);
    elements.compareTray.hidden = !active;
    elements.modeNotice.hidden = !active;
    elements.modeNotice.textContent = active ? "Select any two stores from the map or list to compare straight-line distance." : "";
  }

  function addCompareStore(store) {
    if (compareStores.some((item) => item.store_id === store.store_id)) return;
    if (compareStores.length < 2) compareStores.push(store);
    else compareStores = [compareStores[1], store];
    renderComparison();
  }

  function renderComparison() {
    elements.compareA.textContent = compareStores[0]?.name || "Select first store";
    elements.compareB.textContent = compareStores[1]?.name || "Select second store";
    if (compareLine) {
      map.removeLayer(compareLine);
      compareLine = null;
    }
    if (compareStores.length === 2) {
      const distance = haversine(compareStores[0], compareStores[1]);
      elements.compareDistance.textContent = formatDistance(distance);
      const points = compareStores.map((store) => [store.latitude, store.longitude]);
      compareLine = L.polyline(points, { color: "#171b1f", weight: 3, dashArray: "8 7" }).addTo(map);
      map.fitBounds(points, { padding: [80, 80], maxZoom: 15 });
    } else {
      elements.compareDistance.textContent = "";
    }
  }

  function clearComparison() {
    compareStores = [];
    renderComparison();
  }

  function setCandidateMode(active) {
    candidateMode = active;
    if (active && compareMode) setCompareMode(false);
    elements.candidateButton.classList.toggle("active", active);
    document.body.classList.toggle("candidate-mode", active);
    elements.modeNotice.hidden = !active;
    elements.modeNotice.textContent = active ? "Click anywhere on the map to analyse a proposed leasing location." : "";
  }

  function dropCandidate(latlng) {
    candidatePoint = { latitude: latlng.lat, longitude: latlng.lng };
    if (candidateMarker) map.removeLayer(candidateMarker);
    candidateMarker = L.marker(latlng, {
      icon: L.divIcon({ className: "", html: '<div class="candidate-marker">+</div>', iconSize: [30, 30], iconAnchor: [15, 15] }),
      zIndexOffset: 1000,
    }).addTo(map);
    openCandidateDetail(candidatePoint);
  }

  function openSummary() {
    const byBrand = Object.fromEntries(BRAND_ORDER.map((brand) => [brand, allStores.filter((store) => store.retailer === brand).length]));
    const byState = countBy(allStores, "state");
    const byType = countBy(allStores, "location_type");
    const venueRetailers = new Map();
    const venueNames = new Map();
    allStores.forEach((store) => {
      if (!store.venue_id) return;
      if (!venueRetailers.has(store.venue_id)) venueRetailers.set(store.venue_id, new Set());
      venueRetailers.get(store.venue_id).add(store.retailer);
      venueNames.set(store.venue_id, store.venue_name);
    });
    const multiBrand = Array.from(venueRetailers.entries())
      .filter(([, retailers]) => retailers.size > 1)
      .sort((a, b) => b[1].size - a[1].size || venueNames.get(a[0]).localeCompare(venueNames.get(b[0])));
    const singleBrand = Array.from(venueRetailers.values()).filter((retailers) => retailers.size === 1).length;
    elements.detailContent.innerHTML = `
      <header class="detail-header" style="--brand-color:#171b1f">
        <span class="retailer-tag"><i data-lucide="chart-no-axes-combined"></i>Network summary</span>
        <h2>Australian optical footprint</h2>
        <address>Public brick-and-mortar network across OPSM, Specsavers and Bailey Nelson.</address>
      </header>
      <div class="summary-hero">
        <div class="summary-stat"><strong>${allStores.length}</strong><span>Total stores</span></div>
        <div class="summary-stat"><strong>${byBrand.OPSM}</strong><span>OPSM</span></div>
        <div class="summary-stat"><strong>${byBrand.Specsavers}</strong><span>Specsavers</span></div>
        <div class="summary-stat"><strong>${byBrand["Bailey Nelson"]}</strong><span>Bailey Nelson</span></div>
      </div>
      <section class="detail-section">
        <h3>States</h3>${summaryTable(byState)}
      </section>
      <section class="detail-section">
        <h3>Location types</h3>${summaryTable(byType)}
      </section>
      <section class="detail-section">
        <h3>Reviewed venue overlap</h3>
        <div class="data-grid">
          <div class="data-point"><span>Multi-brand centres</span><strong>${multiBrand.length}</strong></div>
          <div class="data-point"><span>Single-brand venues</span><strong>${singleBrand}</strong></div>
        </div>
        <div class="nearest-list">${multiBrand
          .slice(0, 30)
          .map(
            ([venueId, retailers]) => `<div class="near-row" style="--row-color:#171b1f"><span class="dot"></span><strong>${escapeHtml(
              venueNames.get(venueId)
            )}</strong><span>${escapeHtml(Array.from(retailers).join(" + "))}</span></div>`
          )
          .join("")}</div>
      </section>
      <section class="detail-section"><p class="empty-note">Venue overlap uses explicit official naming and reviewed venue IDs only. Nearby stores are not assumed to share a centre.</p></section>`;
    elements.detailPanel.classList.add("open");
    elements.detailPanel.setAttribute("aria-hidden", "false");
    refreshIcons();
  }

  function countBy(items, key) {
    return items.reduce((result, item) => {
      result[item[key]] = (result[item[key]] || 0) + 1;
      return result;
    }, {});
  }

  function summaryTable(values) {
    return `<table class="summary-table"><tbody>${Object.entries(values)
      .sort((a, b) => a[0].localeCompare(b[0]))
      .map(([label, value]) => `<tr><td>${escapeHtml(label)}</td><td>${value}</td></tr>`)
      .join("")}</tbody></table>`;
  }

  function csvEscape(value) {
    const text = String(value ?? "");
    return /[",\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
  }

  function downloadFilteredCsv() {
    const fields = [
      "retailer", "store_id", "name", "status", "state", "suburb", "postcode", "full_address", "phone",
      "latitude", "longitude", "official_url", "services", "audiology", "venue_name", "venue_id", "location_type",
      "classification_confidence", "classification_basis", "source_url", "fetched_at",
    ];
    const rows = [fields.join(",")].concat(
      filteredStores.map((store) => fields.map((field) => csvEscape(store[field])).join(","))
    );
    const blob = new Blob([rows.join("\n") + "\n"], { type: "text/csv;charset=utf-8" });
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
    document.querySelectorAll('.retailer-option input[type="checkbox"]').forEach((input) => (input.checked = true));
    [elements.search, elements.service].forEach((input) => (input.value = ""));
    [elements.state, elements.location, elements.audiology, elements.status].forEach((select) => (select.value = ""));
    setCompareMode(false);
    setCandidateMode(false);
    clearComparison();
    if (candidateMarker) map.removeLayer(candidateMarker);
    candidateMarker = null;
    candidatePoint = null;
    closeDetail();
    applyFilters();
    map.setView(AUSTRALIA_VIEW.center, AUSTRALIA_VIEW.zoom);
  }

  function populateFilters() {
    [...new Set(allStores.map((store) => store.state))]
      .sort()
      .forEach((state) => elements.state.insertAdjacentHTML("beforeend", `<option>${escapeHtml(state)}</option>`));
    [...new Set(allStores.map((store) => store.status))]
      .sort()
      .forEach((status) => elements.status.insertAdjacentHTML("beforeend", `<option>${escapeHtml(status)}</option>`));
  }

  function bindEvents() {
    [elements.search, elements.service].forEach((input) => input.addEventListener("input", applyFilters));
    [elements.state, elements.location, elements.audiology, elements.status].forEach((select) =>
      select.addEventListener("change", applyFilters)
    );
    document.querySelectorAll('.retailer-option input[type="checkbox"]').forEach((input) =>
      input.addEventListener("change", applyFilters)
    );
    elements.storeList.addEventListener("click", (event) => {
      const row = event.target.closest("[data-store-id]");
      if (row) selectStore(row.dataset.storeId, true);
    });
    document.getElementById("panelClose").addEventListener("click", closeDetail);
    document.getElementById("resetButton").addEventListener("click", resetAll);
    elements.compareButton.addEventListener("click", () => setCompareMode(!compareMode));
    elements.candidateButton.addEventListener("click", () => setCandidateMode(!candidateMode));
    document.getElementById("clearCompare").addEventListener("click", clearComparison);
    document.getElementById("summaryButton").addEventListener("click", openSummary);
    document.getElementById("downloadButton").addEventListener("click", downloadFilteredCsv);
    map.on("click", (event) => {
      if (candidateMode) dropCandidate(event.latlng);
    });
    window.addEventListener("resize", () => map.invalidateSize());
  }

  async function initialise() {
    try {
      const response = await fetch("data/optical_stores.geojson", { cache: "no-store" });
      if (!response.ok) throw new Error(`Store data returned ${response.status}`);
      const collection = await response.json();
      metadata = collection.metadata || {};
      allStores = collection.features.map((feature) => ({
        ...feature.properties,
        latitude: Number(feature.geometry.coordinates[1]),
        longitude: Number(feature.geometry.coordinates[0]),
      }));
      if (allStores.length !== metadata.store_count) throw new Error("Store data count does not match metadata");
      populateFilters();
      createMarkers();
      bindEvents();
      applyFilters();
      const freshness = Object.values(metadata.source_freshness || {}).sort();
      elements.freshness.textContent = freshness.length
        ? `Official sources refreshed ${formatDate(freshness[freshness.length - 1])}`
        : "Source freshness unavailable";
      elements.loading.classList.add("hidden");
      refreshIcons();
    } catch (error) {
      elements.loading.innerHTML = `<strong>Map data could not load</strong><span>${escapeHtml(error.message)}</span>`;
    }
  }

  refreshIcons();
  initialise();
})();
