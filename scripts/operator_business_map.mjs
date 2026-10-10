/** Resolve an operator-linked business identity, never a map viewport. */
export function mapIdentity(mapUrl) {
  const url = new URL(mapUrl);
  if (url.protocol !== 'https:' || !['www.google.com', 'maps.google.com'].includes(url.hostname)
      || url.pathname !== '/maps/embed' || url.username || url.password) {
    throw new Error('Unsupported operator map URL');
  }
  const payloads = url.searchParams.getAll('pb');
  const identities = new Set([...((payloads.length === 1 ? payloads[0] : '').matchAll(/!1s(0x[0-9a-f]+:0x[0-9a-f]+)(?=!|$)/ig))].map(m => m[1]));
  if (identities.size !== 1) throw new Error('Operator map has no unique business identity');
  return [...identities][0];
}
function cid(value) {
  if (typeof value !== 'string' || !/^0x[0-9a-f]+:0x[0-9a-f]+$/i.test(value)) throw new Error('Invalid business identity');
  // CIDs exceed JavaScript's exact Number range; only the final hex component identifies the business.
  return BigInt(value.split(':')[1]);
}
function payload(page) {
  const marker = /\binitEmbed\s*\(/.exec(page);
  if (!marker) throw new Error('Map response has no business payload');
  const start = marker.index + marker[0].length;
  const text = page.slice(start).trimStart();
  if (!text.startsWith('[')) throw new Error('Invalid business payload');
  let depth = 0, quoted = false, escaped = false;
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (quoted) {
      if (escaped) escaped = false;
      else if (ch === '\\') escaped = true;
      else if (ch === '"') quoted = false;
      continue;
    }
    if (ch === '"') quoted = true;
    else if (ch === '[') depth++;
    else if (ch === ']' && --depth === 0) return JSON.parse(text.slice(0, i + 1));
  }
  throw new Error('Truncated business payload');
}
export function businessPoint(page, expectedId, { allowClosed = false } = {}) {
  const features = [];
  function visit(value) {
    if (!Array.isArray(value)) return;
    if (value.length > 17 && Array.isArray(value[0]) && value[0].length > 2
        && typeof value[0][0] === 'string' && value[0][0].startsWith('0x') && typeof value[1] === 'string') features.push(value);
    value.forEach(visit);
  }
  visit(payload(page));
  if (features.length !== 1) throw new Error('Map must identify exactly one business');
  const f = features[0];
  if (cid(f[0][0]) !== cid(expectedId)) throw new Error('Map business differs from operator identity');
  if (f[17] !== null && !(allowClosed && f[17] === 1)) throw new Error('Map status requires branch review');
  const point = f[0][2];
  if (!Array.isArray(point) || point.length !== 2 || point.some(v => typeof v !== 'number' || !Number.isFinite(v))) throw new Error('Invalid business point');
  const [latitude, longitude] = point;
  if (latitude < -48 || latitude > -33.5 || longitude < 165 || longitude > 179.5) throw new Error('Business point is outside New Zealand');
  if (!f[1].trim() || typeof f[13] !== 'string' || !f[13].trim()) throw new Error('Business lacks written name/address');
  return { latitude, longitude, feature_id: f[0][0], name: f[1], address: f[13], closure_flag: f[17] };
}
export async function resolveBusinessPoint(mapUrl, fetchText, options = {}) {
  const expected = mapIdentity(mapUrl);
  return { ...businessPoint(await fetchText(mapUrl), expected, options), map_url: mapUrl,
    method: 'Exact operator-linked business CID; approximate premises point' };
}
export function branchStatus(details) {
  const headings = details.status_headings || '';
  const text = details.main_text || '';
  if (/temporarily closed/i.test(headings)) return 'Temporarily Closed';
  if (/permanently closed/i.test(headings) || /\boscar wylee\b[^.!?]{0,120}\bstore has closed\b/i.test(text)) return 'Closed';
  if (/opening (?:soon|in\s+\w+)|coming soon/i.test(headings)) return 'Opening Soon';
  return 'Active';
}
export function validateLocator(links, priorUrls = []) {
  if (!links.length || new Set(links.map(v => v.official_url)).size !== links.length) throw new Error('Empty or duplicate locator; preserve existing feed');
  const omitted = priorUrls.filter(url => !links.some(v => v.official_url === url));
  if (omitted.length) throw new Error(`Locator omitted previous branches; review status before replacing feed: ${omitted.join(', ')}`);
}
