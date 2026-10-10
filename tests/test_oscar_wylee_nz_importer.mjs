import assert from 'node:assert/strict';
import { businessPoint, resolveBusinessPoint, branchStatus, validateLocator } from '../scripts/operator_business_map.mjs';
import { collectStore } from '../scripts/fetch_oscar_wylee_nz_stores.mjs';
const identity = '0x0:0xe6d401472aa51665';
const url = `https://www.google.com/maps/embed?pb=!1m18!2d174.707488!3d-36.728246!1s${identity.replace(':', '%3A')}!2sOscar`;
const point = [-36.7282464, 174.7096769];
const feature = () => {
  const f = Array(18).fill(null); f[0] = ['0x6d0d3bcba6fc8ad9:0xe6d401472aa51665', 'Oscar Wylee', point];
  f[1] = 'Oscar Wylee Albany'; f[13] = 'Shop S229, Westfield Albany, Auckland 0632'; return f;
};
const payload = (...features) => `initEmbed(${JSON.stringify([features, [[174.707488, -36.728246]]])});`;
let checks = 0;
async function test(name, fn) { await fn(); checks++; }
await test('actual feature differs from camera and zero-prefix CID works', async () => {
  const r = await resolveBusinessPoint(url, async requested => { assert.equal(requested, url); return payload(feature()); });
  assert.deepEqual([r.latitude, r.longitude], point);
});
await test('feature IDs retain precision beyond Number range', () => {
  assert.throws(() => businessPoint(payload(feature()), '0x0:0xe6d401472aa51666'));
});
await test('ambiguous/missing features fail', () => {
  for (const p of [payload(), payload(feature(), feature()), 'initEmbed([', 'html only']) assert.throws(() => businessPoint(p, identity));
});
await test('text punctuation cannot truncate JSON', () => {
  const f = feature(); f[1] = 'Oscar ); [Wylee] "Albany"'; assert.equal(businessPoint(payload(f), identity).name, f[1]);
});
await test('invalid/non-NZ points fail', () => {
  for (const v of [[true,174],[-37,'174'],[-33,174],[-40,150],[Infinity,174],[-37],null]) {
    const f = feature(); f[0][2] = v; assert.throws(() => businessPoint(payload(f), identity));
  }
});
await test('closure flags need explicit operator closure', () => {
  const f = feature(); f[17] = 1; assert.throws(() => businessPoint(payload(f), identity));
  assert.equal(businessPoint(payload(f), identity, {allowClosed:true}).closure_flag, 1);
  f[17] = 2; assert.throws(() => businessPoint(payload(f), identity, {allowClosed:true}));
});
await test('camera-only/untrusted/ambiguous URLs never fetch', async () => {
  for (const bad of [url.replace('www.google.com','untrusted.example'),url.split('!1s')[0],url+'!1s0x1:0x2',url+'&pb=another',url.replace('https:','http:')]) {
    await assert.rejects(() => resolveBusinessPoint(bad, async () => assert.fail('Must not fetch untrusted map')));
  }
});
await test('explicit closure beats old normal hours', () => {
  assert.equal(branchStatus({main_text:'Our Oscar Wylee St Lukes store has closed, but this is not the end. Monday 9-6; Sunday closed'}),'Closed');
  assert.equal(branchStatus({main_text:'Monday 9-6; Sunday closed'}),'Active');
  assert.equal(branchStatus({status_headings:'Opening in Early October'}),'Opening Soon');
  assert.equal(branchStatus({status_headings:'Temporarily Closed'}),'Temporarily Closed');
});
await test('locator has no fixed desired count but cannot silently drop existing branches', () => {
  assert.throws(() => validateLocator([])); assert.throws(() => validateLocator([{official_url:'a'},{official_url:'a'}]));
  assert.throws(() => validateLocator([{official_url:'b'}],['a']));
  validateLocator(Array.from({length:30},(_,i)=>({official_url:`branch-${i}`})), ['branch-0']);
});
const link = {list_name:'Westfield Albany',official_url:'https://www.oscarwylee.co.nz/locations/optometrist-albany.html'};
function page(details, result = payload(feature()), ok = true) {
  return {goto:async()=>{}, locator:()=>({first:()=>({waitFor:async()=>{}})}),evaluate:async()=>details,
    request:{get:async()=>({ok:()=>ok,status:()=>429,text:async()=>result})}};
}
const details = {address:'Westfield Albany\nShop S229, 219 Don McKinnon Drive\nAlbany Auckland 0632',phone:'09 281 0674',map_url:url,status_headings:'Optometrist Albany',main_text:'Current branch'};
await test('actual collector records coordinate provenance', async () => {
  const result=await collectStore(page(details),link); assert.equal(result.store.id,'optometrist-albany');
  assert.equal(result.store.longitude,point[1]); assert.equal(result.source.coordinate_evidence.feature_id,feature()[0][0]);
});
await test('collector cannot fall back to hard-coded point on missing map or failed fetch', async () => {
  await assert.rejects(()=>collectStore(page({...details,map_url:''}),link));
  await assert.rejects(()=>collectStore(page(details,payload(feature()),false),link));
});
console.log(`Oscar Wylee NZ importer: ${checks} checks passed`);
