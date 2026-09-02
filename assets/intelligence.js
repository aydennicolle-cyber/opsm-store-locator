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

  function projectedRing(point, ring) {
    const longitudeScale = Math.cos((point.latitude * Math.PI) / 180) * 111.32;
    return ring.map(([longitude, latitude]) => [
      (longitude - point.longitude) * longitudeScale,
      (latitude - point.latitude) * 111.32,
    ]);
  }

  function polygonArea(ring) {
    if (!ring || ring.length < 3) return 0;
    let area = 0;
    for (let index = 0; index < ring.length; index += 1) {
      const current = ring[index];
      const next = ring[(index + 1) % ring.length];
      area += current[0] * next[1] - next[0] * current[1];
    }
    return Math.abs(area) / 2;
  }

  function clipToConvexPolygon(subject, clip) {
    let output = subject.slice();
    const cross = (first, second, third) =>
      (second[0] - first[0]) * (third[1] - first[1]) -
      (second[1] - first[1]) * (third[0] - first[0]);
    const intersection = (start, end, clipStart, clipEnd) => {
      const subjectX = end[0] - start[0];
      const subjectY = end[1] - start[1];
      const clipX = clipEnd[0] - clipStart[0];
      const clipY = clipEnd[1] - clipStart[1];
      const denominator = subjectX * clipY - subjectY * clipX;
      if (Math.abs(denominator) < 1e-12) return end;
      const t = ((clipStart[0] - start[0]) * clipY - (clipStart[1] - start[1]) * clipX) / denominator;
      return [start[0] + t * subjectX, start[1] + t * subjectY];
    };
    for (let edge = 0; edge < clip.length && output.length; edge += 1) {
      const clipStart = clip[edge];
      const clipEnd = clip[(edge + 1) % clip.length];
      const input = output;
      output = [];
      let start = input[input.length - 1];
      for (const end of input) {
        const endInside = cross(clipStart, clipEnd, end) >= -1e-10;
        const startInside = cross(clipStart, clipEnd, start) >= -1e-10;
        if (endInside) {
          if (!startInside) output.push(intersection(start, end, clipStart, clipEnd));
          output.push(end);
        } else if (startInside) {
          output.push(intersection(start, end, clipStart, clipEnd));
        }
        start = end;
      }
    }
    return output;
  }

  function geometryOverlapFraction(point, geometry, radiusKm) {
    if (!geometry || radiusKm <= 0 || !geometryIntersectsRadius(point, geometry, radiusKm)) return 0;
    const circle = Array.from({ length: 64 }, (_, index) => {
      const angle = (index / 64) * Math.PI * 2;
      return [Math.cos(angle) * radiusKm, Math.sin(angle) * radiusKm];
    });
    const polygons = geometry.type === "Polygon" ? [geometry.coordinates] : geometry.coordinates;
    let totalArea = 0;
    let overlapArea = 0;
    polygons.forEach((polygon) => {
      polygon.forEach((ring, index) => {
        const projected = projectedRing(point, ring);
        const sign = index === 0 ? 1 : -1;
        totalArea += sign * polygonArea(projected);
        overlapArea += sign * polygonArea(clipToConvexPolygon(projected, circle));
      });
    });
    if (totalArea <= 0) return 0;
    return Math.max(0, Math.min(1, overlapArea / totalArea));
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
      placeId,
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
    const competitiveWhiteSpace = stores.length
      ? competitionCountScore * 0.6 + competitionDistanceScore * 0.4
      : null;

    const sameBrand = targetRetailer
      ? distances.filter((entry) => entry.store.retailer === targetRetailer)
      : distances;
    const nearestNetwork = sameBrand[0]?.distance;
    const networkFit = stores.length
      ? (Number.isFinite(nearestNetwork) ? Math.min(100, nearestNetwork * 10) : 100)
      : null;

    const nearbyCentres = centres
      .map((centre) => ({ centre, distance: haversine(point, centre) }))
      .sort((a, b) => a.distance - b.distance);
    const centre = placeId
      ? nearbyCentres.find((entry) => entry.centre.centre_id === placeId) || null
      : null;
    const nearbyCentreLead = nearbyCentres.find((entry) => entry.distance <= 0.75) || null;
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
      competitive_white_space: competitiveWhiteSpace === null ? null : Math.round(competitiveWhiteSpace),
      centre_strength: centreStrength === null ? null : Math.round(centreStrength),
      accessibility,
      network_fit: networkFit === null ? null : Math.round(networkFit),
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
      nearbyCentreLead,
      nearestStore: distances[0] || null,
      competitorCountFiveKm: withinFive.length,
      nearestCompetitorKm: nearestCompetitor,
    };
  }

  function catchmentSummary(point, radiusKm, markets) {
    const included = markets
      .map((feature) => ({ feature, fraction: geometryOverlapFraction(point, feature.geometry, radiusKm) }))
      .filter((entry) => entry.fraction > 0);
    const population = included.reduce(
      (sum, entry) => sum + (number(entry.feature.properties.population_2025) || 0) * entry.fraction,
      0
    );
    const weighted = (field) => {
      let denominator = 0;
      const numerator = included.reduce((sum, entry) => {
        const value = number(entry.feature.properties[field]);
        const populationValue = number(entry.feature.properties.population_2025);
        if (value === null || populationValue === null) return sum;
        const weight = populationValue * entry.fraction;
        denominator += weight;
        return sum + value * weight;
      }, 0);
      return denominator ? numerator / denominator : null;
    };
    return {
      radiusKm,
      sa2Count: included.length,
      population: Math.round(population),
      age45PlusPct: weighted("age_45_plus_pct_2021"),
      medianHouseholdIncomeWeekly: weighted("median_household_income_weekly_2021"),
      apportionmentMethod: "SA2 area-overlap apportionment",
    };
  }

  function activeRelationship(relationship, asOf = new Date()) {
    if (relationship.status !== "ACTIVE") return false;
    const stamp = asOf instanceof Date ? asOf.toISOString().slice(0, 10) : String(asOf || "");
    return (!relationship.valid_from || relationship.valid_from <= stamp) &&
      (!relationship.valid_to || relationship.valid_to >= stamp);
  }

  function deriveLeasingArrangement(relationships, groups = []) {
    const groupById = new Map(groups.map((group) => [group.group_id, group]));
    const active = (relationships || []).filter((item) => activeRelationship(item));
    if (active.some((item) => item.role === "EXTERNAL_LEASING_AGENT")) return "External agency";
    const controllers = new Set(active.filter((item) => item.role === "LEASING_CONTROLLER").map((item) => item.group_id));
    const operating = new Set(
      active
        .filter((item) => ["OWNER", "CO_OWNER", "MANAGER", "OPERATOR"].includes(item.role))
        .map((item) => item.group_id)
    );
    if ([...controllers].some((groupId) => operating.has(groupId))) return "In-house";
    if ([...controllers].some((groupId) => groupById.get(groupId)?.group_type === "PRIVATE_LANDLORD")) {
      return "Private landlord";
    }
    return "Unknown";
  }

  function portfolioOverlapStatus(input) {
    if (input.hasBailey) return "SAME_CENTRE";
    const groupPortfolio = input.groupPortfolio || {};
    const candidates = (input.relationships || [])
      .filter((item) => activeRelationship(item))
      .filter((item) => Number(groupPortfolio[item.group_id]?.bailey_property_count || 0) > 0);
    if (candidates.some((item) => item.role === "LEASING_CONTROLLER")) return "LEASING_CONTROLLER_OVERLAP";
    if (candidates.some((item) => ["OWNER", "CO_OWNER", "MANAGER", "OPERATOR"].includes(item.role))) {
      return "PROPERTY_GROUP_OVERLAP";
    }
    if (candidates.some((item) => item.role === "EXTERNAL_LEASING_AGENT")) return "EXTERNAL_AGENCY_OVERLAP";
    if (["Verified", "Verified unknown"].includes(input.researchStatus)) return "NO_KNOWN_OVERLAP";
    return "UNKNOWN";
  }

  function effectivePropertyRelationships(generated, corrections) {
    const effective = new Map((generated || []).map((item) => [item.relationship_id, { ...item }]));
    (corrections || [])
      .filter((item) => item.correction_type === "ASSET_RELATIONSHIP")
      .forEach((correction) => {
        if (correction.action === "REMOVE") effective.delete(correction.record_id);
        else if (correction.action === "UPSERT" && correction.record_id) {
          effective.set(correction.record_id, {
            ...(effective.get(correction.record_id) || {}),
            relationship_id: correction.record_id,
            place_id: correction.place_id,
            group_id: correction.group_id,
            role: correction.role,
            ownership_percentage: number(correction.ownership_percentage),
            status: "ACTIVE",
            source_url: correction.source_url || "",
            last_verified_at: correction.verified_at || "",
            confidence: correction.confidence || "Medium",
            public_note: correction.public_note || "",
            manual_override: true,
          });
        }
      });
    return [...effective.values()];
  }

  function competitorPropertyContext(place, stores) {
    const byRetailer = {};
    (stores || []).forEach((store) => {
      if (!Number.isFinite(Number(store.latitude)) || !Number.isFinite(Number(store.longitude))) return;
      const retailer = store.retailer || "Unknown";
      byRetailer[retailer] ||= { in_centre: [], nearby_unverified: [], catchment_2km: [] };
      const distance = haversine(place, store);
      const item = { store_id: store.store_id, name: store.name, distance_km: Math.round(distance * 100) / 100 };
      if (store.place_id && store.place_id === place.place_id) byRetailer[retailer].in_centre.push(item);
      else if (distance <= 0.25) byRetailer[retailer].nearby_unverified.push(item);
      else if (distance <= 2) byRetailer[retailer].catchment_2km.push(item);
    });
    return { by_retailer: byRetailer };
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
      place_filters: {
        search: state.placeFilters?.search || "",
        country: state.placeFilters?.country || "",
        type: state.placeFilters?.type || "",
        bailey: state.placeFilters?.bailey || "",
        retailers: Array.from(state.placeFilters?.retailers || []),
        confidence: state.placeFilters?.confidence || "",
        group_id: state.placeFilters?.group_id || "",
        arrangement: state.placeFilters?.arrangement || "",
        overlap: state.placeFilters?.overlap || "",
        centre_class: state.placeFilters?.centre_class || "",
        min_income: number(state.placeFilters?.min_income),
        min_bailey_distance: number(state.placeFilters?.min_bailey_distance),
        sort: state.placeFilters?.sort || "name",
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
        place_id: candidate.place_id || "",
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
    geometryOverlapFraction,
    marketDemandScore,
    formatFitScore,
    candidateScore,
    catchmentSummary,
    activeRelationship,
    deriveLeasingArrangement,
    portfolioOverlapStatus,
    effectivePropertyRelationships,
    competitorPropertyContext,
    sanitiseShareState,
  };
});
