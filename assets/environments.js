(function (root) {
  'use strict';
  const unique = values => [...new Set(values || [])];
  function featureState(place, id) {
    const present = Boolean(place?.features?.[id]?.length);
    const absent = Boolean(place?.absent_features?.[id]?.length);
    return present && absent ? 'conflict' : present ? 'present' : absent ? 'absent' : 'unknown';
  }
  function criteria(input = {}) {
    const all = unique(input.all), any = unique(input.any), preferred = unique(input.preferred);
    return {...input, all, any, preferred, mode: input.mode === 'partial' ? 'partial' : 'exact',
      minimum: Math.max(0, Math.floor(Number(input.minimum) || 0))};
  }
  function match(place, input) {
    const q = criteria(input);
    const selected = unique([...q.all, ...q.any, ...q.preferred]);
    const states = Object.fromEntries(selected.map(id => [id, featureState(place, id)]));
    const matched = selected.filter(id => states[id] === 'present');
    const missing = selected.filter(id => states[id] === 'absent');
    const unknown = selected.filter(id => ['unknown', 'conflict'].includes(states[id]));
    const required = q.all.every(id => states[id] === 'present') && (!q.any.length || q.any.some(id => states[id] === 'present'));
    const preferredCount = q.preferred.filter(id => states[id] === 'present').length;
    const threshold = q.mode === 'exact' ? q.preferred.length : q.minimum;
    const presence = (filter, value) => !filter || filter === 'any' || filter === value ? 'met'
      : value === 'not_recorded' && filter !== 'not_recorded' ? 'unknown' : 'failed';
    const bnState = presence(q.bn, place.bn_presence), otherState = presence(q.other, place.other_optical_presence);
    if (bnState === 'unknown') unknown.push('Bailey Nelson presence');
    if (otherState === 'unknown') unknown.push('Other optical presence');
    const geography = (!q.place_ids?.length || q.place_ids.includes(place.place_id))
      && (!q.country || place.country === q.country) && (!q.state || place.state === q.state)
      && (!q.format || place.format === q.format) && (!q.positioning || place.positioning.includes(q.positioning))
      && (!q.search || `${place.name} ${(place.aliases || []).join(' ')} ${place.locality} ${place.state}`.toLowerCase().includes(q.search.toLowerCase()));
    const inScope = geography
      && (q.coverage !== 'directory' || place.coverage?.directory_complete === true);
    const possible = q.all.every(id => states[id] !== 'absent')
      && (!q.any.length || q.any.some(id => states[id] !== 'absent'))
      && q.preferred.filter(id => states[id] !== 'absent').length >= threshold
      && bnState !== 'failed' && otherState !== 'failed';
    return {place, eligible: inScope && required && preferredCount >= threshold && bnState === 'met' && otherState === 'met', inScope, possible,
      required, preferredCount, preferredTotal: q.preferred.length, threshold, matched, missing, unknown,
      exact: required && preferredCount === q.preferred.length, states};
  }
  function searchSummary(places, input) {
    const scoped = places.map(p => match(p, input)).filter(r => r.inScope);
    return {total: scoped.length, matches: scoped.filter(r => r.eligible),
      unresolved: scoped.filter(r => !r.eligible && r.possible),
      excluded: scoped.filter(r => !r.eligible && !r.possible)};
  }
  function search(places, input) {
    return places.map(p => match(p, input)).filter(r => r.eligible)
      .sort((a, b) => b.preferredCount - a.preferredCount || a.place.name.localeCompare(b.place.name));
  }
  function groupComparison(rows, featureIds, places, format = '', size = '', coverage = '') {
    const lookup = new Map(places.map(p => [p.place_id, p]));
    const scale = p => !p?.scale?.gla_sqm ? 'unknown' : Number(p.scale.gla_sqm) < 20000 ? 'under20' : Number(p.scale.gla_sqm) < 50000 ? '20to50' : 'over50';
    const included = rows.filter(r => (!format || lookup.get(r.place_id)?.format === format)
      && (!size || scale(lookup.get(r.place_id)) === size)
      && (coverage !== 'directory' || (r.analysis_eligible !== false && lookup.get(r.place_id)?.coverage?.directory_complete === true)));
    const groups = unique(rows.map(r => r.group));
    return featureIds.map(id => ({id, groups: groups.map(group => {
      const members = included.filter(r => r.group === group);
      const counts = {group, total: members.length, present: 0, absent: 0, unknown: 0};
      members.forEach(r => { const status = r.analysis_eligible === false ? 'unknown' : featureState(lookup.get(r.place_id), id); counts[status === 'conflict' ? 'unknown' : status]++; });
      counts.known = counts.present + counts.absent;
      counts.percent_total = counts.total ? 100 * counts.present / counts.total : null;
      counts.percent_known = counts.known ? 100 * counts.present / counts.known : null;
      return counts;
    })}));
  }
  const api = {featureState, criteria, match, search, searchSummary, groupComparison};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.RetailEnvironments = api;
})(typeof window !== 'undefined' ? window : globalThis);
