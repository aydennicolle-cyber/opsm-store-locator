const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const context = {window:{}};
vm.runInNewContext(fs.readFileSync(require.resolve('../assets/environment-explorer.js'), 'utf8'), context);
const render = context.window.EnvironmentExplorer.metricEvidenceHtml;
const html = render({metric_conflicts:{gla_sqm:'Different reported values'}, metric_observations:{gla_sqm:[
  {value:100,unit:'m²',source_url:'https://example.org/a',source_date:'2024-01-01',last_verified_at:'2026-10-25'},
  {value:120,unit:'m²',source_url:'https://example.org/b',source_period:'2025',last_verified_at:''},
]}});
assert.ok(html.includes('Different reported values'));
assert.ok(html.includes('100 m²') && html.includes('120 m²'));
assert.ok(html.includes('Source date: 2024-01-01'));
assert.ok(html.includes('reporting period: 2025'));
assert.ok(html.includes('checked: not recorded'));
assert.ok(!html.includes('Source date: 2026-10-25'), 'check date cannot become publication date');
const escaped = render({metric_observations:{tenancy_count:[{value:0,unit:'<script>',source_url:'javascript:alert(1)'}]}});
assert.ok(escaped.includes('0 &lt;script&gt;'));
assert.ok(!escaped.includes('href="javascript:'));
console.log('Metric profile sources: differing values, dates, zero and escaping passed');

const addressHtml = context.window.EnvironmentExplorer.addressEvidenceHtml({address:'52 Soldiers Parade', address_evidence:{basis:'Supported destination-profile address',source_url:'https://example.org/about',source_date:null,checked_at:'2026-10-08'}});
assert.ok(addressHtml.includes('52 Soldiers Parade'));
assert.ok(addressHtml.includes('Source date: unknown'));
assert.ok(addressHtml.includes('address checked: 2026-10-08'));
assert.ok(!addressHtml.includes('Shop AG26'));

const pointHtml = context.window.EnvironmentExplorer.pointEvidenceHtml({coordinate_reason:'Average of storefront points; not a boundary.',coordinate_source_url:'https://example.org/map'});
assert.ok(pointHtml.includes('not a boundary'));
assert.ok(!pointHtml.includes('reviewed'), 'derived point explanations cannot invent a review date');
const unsafePoint = context.window.EnvironmentExplorer.pointEvidenceHtml({coordinate_reason:'<script>',coordinate_source_url:'javascript:alert(1)'});
assert.ok(unsafePoint.includes('&lt;script&gt;'));
assert.ok(!unsafePoint.includes('href="javascript:'));
