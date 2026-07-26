(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  root.LeasingIntel = api;
})(typeof globalThis !== "undefined" ? globalThis : window, function () {
  "use strict";

  const EARTH_RADIUS_KM = 6371.0088;

  function number(value) {
    if (value === null || value === undefined || value === "") return null;
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }

  function haversine(first, second) {
    const toRadians = (degrees) => (degrees * Math.PI) / 180;
    const lat1 = toRadians(Number(first.latitude));
    const lat2 = toRadians(Number(second.latitude));
    const deltaLat = toRadians(Number(second.latitude) - Number(first.latitude));
    const deltaLon = toRadians(Number(second.longitude) - Number(first.longitude));
    const value =
      Math.sin(deltaLat / 2) ** 2 +
      Math.cos(lat1) * Math.cos(lat2) * Math.sin(deltaLon / 2) ** 2;
    return EARTH_RADIUS_KM * 2 * Math.atan2(Math.sqrt(value), Math.sqrt(1 - value));
  }

  function formatDistance(km) {
    if (!Number.isFinite(km)) return "-";
    return km < 1 ? `${Math.round(km * 1000)} m` : `${km.toFixed(km < 10 ? 1 : 0)} km`;
  }

  function percentile(values, target) {
    const numeric = values.map(number).filter((value) => value !== null).sort((a, b) => a - b);
    const value = number(target);
    if (value === null || !numeric.length) return null;
    if (numeric.length === 1) return 100;
    let below = 0;
    let equal = 0;
    for (const item of numeric) {
      if (item < value) below += 1;
      else if (item === value) equal += 1;
      else break;
    }
    return Math.round(((below + equal * 0.5) / numeric.length) * 100);
  }

  function pointInRing(longitude, latitude, ring) {
    let inside = false;
    let previous = ring[ring.length - 1];
    for (const current of ring) {
      const [x1, y1] = previous;
      const [x2, y2] = current;
      if ((y1 > latitude) !== (y2 > latitude)) {
        const boundaryX = ((x2 - x1) * (latitude - y1)) / (y2 - y1 || 1e-12) + x1;
        if (longitude < boundaryX) inside = !inside;
      }
      previous = current;
    }
    return inside;
  }

  function pointInGeometry(point, geometry) {
    if (!geometry) return false;
    const polygons = geometry.type === "Polygon" ? [geometry.coordinates] : geometry.coordinates;
    for (const polygon of polygons) {
      if (!polygon?.length || !pointInRing(point.longitude, point.latitude, polygon[0])) continue;
      if (!polygon.slice(1).some((hole) => pointInRing(point.longitude, point.latitude, hole))) {
        return true;
      }
    }
    return false;
  }

  function findMarketFeature(point, features) {
    return features.find((feature) => pointInGeometry(point, feature.geometry)) || null;
  }

  function pointToSegmentKm(point, first, second) {
    const latitudeScale = 111.32;
    const longitudeScale = Math.cos((point.latitude * Math.PI) / 180) * 111.32;
    const ax = (first[0] - point.longitude) * longitudeScale;
    const ay = (first[1] - point.latitude) * latitudeScale;
    const bx = (second[0] - point.longitude) * longitudeScale;
    const by = (second[1] - point.latitude) * latitudeScale;
    const dx = bx - ax;
    const dy = by - ay;
    const lengthSquared = dx * dx + dy * dy;
    const position = lengthSquared ? Math.max(0, Math.min(1, -(ax * dx + ay * dy) / lengthSquared)) : 0;
    return Math.hypot(ax + position * dx, ay + position * dy);
  }

  function geometryIntersectsRadius(point, geometry, radiusKm) {
    if (!geometry || radiusKm < 0) return false;
    if (pointInGeometry(point, geometry)) return true;
    const polygons = geometry.type === "Polygon" ? [geometry.coordinates] : geometry.coordinates;
    return polygons.some((polygon) =>
      polygon.some((ring) =>
        ring.some((coordinate, index) =>
          pointToSegmentKm(point, coordinate, ring[index ? index - 1 : ring.length - 1]) <= radiusKm
        )
      )
    );
  }

  function averageAvailable(parts) {
    const available = parts.filter((part) => number(part.value) !== null);
    if (!available.length) return null;
    const weight = available.reduce((sum, part) => sum + part.weight, 0);
    return available.reduce((sum, part) => sum + Number(part.value) * part.weight, 0) / weight;
  }

  function marketDemandScore(market, markets) {
    if (!market) return null;
    const properties = market.properties || market;
    const all = markets.map((item) => item.properties || item);
    return averageAvailable([
      {
        value: percentile(all.map((item) => item.population_2025), properties.population_2025),
        weight: 30,
      },
      {
        value: percentile(
          all.map((item) => item.population_growth_2021_2025_pct),
          properties.population_growth_2021_2025_pct
        ),
        weight: 25,
      },
      {
        value: percentile(all.map((item) => item.age_45_plus_pct_2021), properties.age_45_plus_pct_2021),
        weight: 25,
      },
      {
        value: percentile(
          all.map((item) => item.median_household_income_weekly_2021),
          properties.median_household_income_weekly_2021
        ),
        weight: 20,
      },
    ]);
  }

  function formatFitScore(area, minimum, maximum) {
    const candidateArea = number(area);
    const min = number(minimum);
    const max = number(maximum);
    if (candidateArea === null || min === null || max === null || min <= 0 || max < min) return null;
    if (candidateArea >= min && candidateArea <= max) return 100;
    const distance = candidateArea < min ? min - candidateArea : candidateArea - max;
    const tolerance = Math.max(max - min, min * 0.5, 1);
    return Math.max(0, Math.round(100 - (distance / tolerance) * 100));
  }

  function candidateScore(input) {
    const {
      point,
      stores,
      markets,
      market,
      centres,
      profile,
      areaSqm,
      targetAreaMin,
      targetAreaMax,
      amenitySummary,
    } = input;
    const distances = stores
      .map((store) => ({ store, distance: haversine(point, store) }))
      .sort((a, b) => a.distance - b.distance);
    const targetRetailer = profile?.retailer || "";
    const competitors = distances.filter((entry) => !targetRetailer || entry.store.retailer !== targetRetailer);
    const withinFive = competitors.filter((entry) => entry.distance <= 5);
    const nearestCompetitor = competitors[0]?.distance ?? 10;
    const competitionCountScore = Math.max(0, 100 - withinFive.length * 8);
    const competitionDistanceScore = Math.min(100, nearestCompetitor * 20);
    const competitiveWhiteSpace = competitionCountScore * 0.6 + competitionDistanceScore * 0.4;

    const sameBrand = targetRetailer
      ? distances.filter((entry) => entry.store.retailer === targetRetailer)
      : distances;
    const nearestNetwork = sameBrand[0]?.distance;
    const networkFit = Number.isFinite(nearestNetwork) ? Math.min(100, nearestNetwork * 10) : 100;

    const nearbyCentres = centres
      .map((centre) => ({ centre, distance: haversine(point, centre) }))
      .sort((a, b) => a.distance - b.distance);
    const centre = nearbyCentres.find((entry) => entry.distance <= 0.75) || null;
    let centreStrength = null;
    if (centre) {
      const profileParts = [
        { value: number(centre.centre.annual_visits) === null ? null : Math.min(100, Number(centre.centre.annual_visits) / 200000), weight: 35 },
        { value: number(centre.centre.gla_sqm) === null ? null : Math.min(100, Number(centre.centre.gla_sqm) / 1800), weight: 30 },
        { value: number(centre.centre.trade_area_population) === null ? null : Math.min(100, Number(centre.centre.trade_area_population) / 15000), weight: 25 },
        { value: Math.min(100, Number(centre.centre.optical_store_count || 0) * 20), weight: 10 },
      ];
      centreStrength = averageAvailable(profileParts) ?? 55;
    }

    const accessibility = amenitySummary
      ? Math.min(
          100,
          Number(amenitySummary.transport || 0) * 8 +
            Number(amenitySummary.parking || 0) * 10 +
            Number(amenitySummary.health || 0) * 4
        )
      : null;
    const minimum = number(targetAreaMin) ?? number(profile?.preferred_area_min_sqm);
    const maximum = number(targetAreaMax) ?? number(profile?.preferred_area_max_sqm);
    const formatFit = formatFitScore(areaSqm, minimum, maximum);
    const weights = profile?.weights || {
      market_demand: 25,
      competitive_white_space: 25,
      centre_strength: 20,
      accessibility: 10,
      network_fit: 10,
      format_fit: 10,
    };
    const componentValues = {
      market_demand: marketDemandScore(market, markets),
      competitive_white_space: Math.round(competitiveWhiteSpace),
      centre_strength: centreStrength === null ? null : Math.round(centreStrength),
      accessibility,
      network_fit: Math.round(networkFit),
      format_fit: formatFit,
    };
    const availableKeys = Object.keys(componentValues).filter((key) => number(componentValues[key]) !== null);
    const coverage = availableKeys.reduce((sum, key) => sum + Number(weights[key] || 0), 0);
    const weighted = availableKeys.reduce(
      (sum, key) => sum + Number(componentValues[key]) * Number(weights[key] || 0),
      0
    );
    return {
      score: coverage ? Math.round(weighted / coverage) : null,
      coverage,
      reliable: coverage >= 70,
      components: componentValues,
      weights,
      nearestCentre: centre,
      nearestStore: distances[0] || null,
      competitorCountFiveKm: withinFive.length,
      nearestCompetitorKm: nearestCompetitor,
    };
  }

  function catchmentSummary(point, radiusKm, markets) {
    const included = markets.filter((feature) => geometryIntersectsRadius(point, feature.geometry, radiusKm));
    const population = included.reduce(
      (sum, feature) => sum + (number(feature.properties.population_2025) || 0),
      0
    );
    const weighted = (field) => {
      if (!population) return null;
      const numerator = included.reduce((sum, feature) => {
        const value = number(feature.properties[field]);
        const weight = number(feature.properties.population_2025);
        return sum + (value === null || weight === null ? 0 : value * weight);
      }, 0);
      return numerator / population;
    };
    return {
      radiusKm,
      sa2Count: included.length,
      population,
      age45PlusPct: weighted("age_45_plus_pct_2021"),
      medianHouseholdIncomeWeekly: weighted("median_household_income_weekly_2021"),
    };
  }

  function sanitiseShareState(state) {
    return {
      view: state.view || "network",
      filters: {
        retailers: Array.from(state.filters?.retailers || []),
        country: state.filters?.country || "",
        state: state.filters?.state || "",
        location: state.filters?.location || "",
        search: state.filters?.search || "",
      },
      map: {
        latitude: number(state.map?.latitude),
        longitude: number(state.map?.longitude),
        zoom: number(state.map?.zoom),
      },
      candidates: (state.candidates || []).map((candidate) => ({
        id: candidate.id,
        name: candidate.name,
        latitude: number(candidate.latitude),
        longitude: number(candidate.longitude),
        area_sqm: number(candidate.area_sqm),
        profile_id: candidate.profile_id || "generic-optical",
      })),
    };
  }

  return {
    haversine,
    formatDistance,
    percentile,
    pointInGeometry,
    findMarketFeature,
    geometryIntersectsRadius,
    marketDemandScore,
    formatFitScore,
    candidateScore,
    catchmentSummary,
    sanitiseShareState,
  };
});
