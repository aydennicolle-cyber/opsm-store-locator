const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('assets/app.js', 'utf8');
const fn = source.slice(source.indexOf('  function refreshExcludedContext()'), source.indexOf('  function refreshInspectionMarker()'));
const visible = new Set();
let zoom = 14, enabled = true, mapView = true;
const state = {activeLayers:new Set(['stores','centres']), allStores:[
  {store_id:'match',name:'Match',status:'Active',latitude:1,longitude:1},
  {store_id:'excluded',name:'Excluded',status:'Active',latitude:2,longitude:2},
  {store_id:'closed',name:'Closed',status:'Closed',latitude:2,longitude:2},
  {store_id:'offscreen',name:'Offscreen',status:'Active',latitude:99,longitude:99},
], centres:[{place_id:'place',name:'Place',latitude:3,longitude:3}]};
const point = value => ({distanceTo:()=>100,add:()=>point(value),value});
const sandbox = {state,document:{getElementById:()=>null},isMapView:()=>mapView,
  map:{getZoom:()=>zoom,getBounds:()=>({contains:p=>p[0]<50}),hasLayer:()=>false,latLngToLayerPoint:point,layerPointToLatLng:p=>p.value},
  filteredPlaces:()=>[],storeMatchesFilters:r=>r.store_id==='match',
  markerById:new Map(state.allStores.map(r=>[r.store_id,{}])),centreMarkerById:new Map([['place',{}]]),
  excludedMarkerCache:new Map(),storeMarkersForActiveMapView:()=>[],centreMarkersForActiveMapView:()=>[],
  contextMarker:r=>({id:r.store_id||r.place_id,bindTooltip(){},setLatLng(){}}),
  excludedContextLayer:{hasLayer:m=>visible.has(m.id),addLayer:m=>visible.add(m.id),removeLayer:m=>visible.delete(m.id)},
  escapeHtml:x=>x,recordExclusions:()=>['Place type'],
};
Object.defineProperty(sandbox,'showExcludedNearby',{get:()=>enabled});
const refresh=vm.runInNewContext(`(()=>{${fn};return refreshExcludedContext;})()`,sandbox);
refresh(); assert.deepEqual([...visible],['excluded','place']);
assert.equal(sandbox.excludedMarkerCache.size,2);
refresh(); assert.equal(sandbox.excludedMarkerCache.size,2, 'reuse context markers');
zoom=13; refresh(); assert.equal(visible.size,0);
zoom=14; state.activeLayers.delete('stores'); refresh(); assert.deepEqual([...visible],['place']);
state.activeLayers.add('stores'); enabled=false; refresh(); assert.equal(visible.size,0);
enabled=true; state.selectedStoreId='excluded'; refresh(); assert.deepEqual([...visible],['place']);
state.selectedStoreId=''; mapView=false; refresh(); assert.equal(visible.size,0);
assert.equal(state.allStores.length,4,'context does not mutate the search source');
console.log('Excluded context: zoom, viewport, closed records, selection, layer switches and marker reuse passed');
