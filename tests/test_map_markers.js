const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('assets/app.js', 'utf8');
const helpers = source.slice(source.indexOf('  const CENTRE_BAG_SVG'), source.indexOf('  let BRAND_CONFIG'));
const {placeClusterPresentation, mapClusterLabel} = vm.runInNewContext(`(() => {${helpers}; return {placeClusterPresentation, mapClusterLabel};})()`);
const place = (id, kind) => ({options: {placeId: id, placeKind: kind}});
const store = {options: {storeId: 'store'}};
const corridors = [place('a', 'corridor'), place('b', 'corridor')];
const centres = [place('a', 'centre'), place('b', 'centre')];
const mixed = [centres[0], corridors[1]];
assert.equal(placeClusterPresentation(corridors).label, '2 high-street corridors');
assert.equal(placeClusterPresentation(centres).label, '2 shopping centres');
assert.equal(placeClusterPresentation(mixed).label, '1 shopping centre and 1 high-street corridor');
assert.notEqual(placeClusterPresentation(corridors).icon, placeClusterPresentation(centres).icon);
assert.notEqual(placeClusterPresentation(mixed).icon, placeClusterPresentation(centres).icon);
assert.notEqual(placeClusterPresentation(mixed).icon, placeClusterPresentation(corridors).icon);
assert.equal(placeClusterPresentation([...corridors, store]).count, 2);
assert.equal(placeClusterPresentation([...corridors, store]).icon, placeClusterPresentation(corridors).icon);
assert.match(mapClusterLabel([...mixed, store]), /^1 shopping centre and 1 high-street corridor and 1 store nearby/);
assert.equal(placeClusterPresentation([place('x', 'other')]).label, '1 other place');
console.log('Map marker type and count tests passed');

// Detached cluster groups may retain stale child trees. Joined clusters must
// reflect the applied data selection, including an empty store selection.
const refreshSource = source.slice(source.indexOf('  function refreshOverviewClusters()'), source.indexOf('  const selectionLayer'));
let selectedMarkers = [{options:{storeId:'selected',baseLatitude:-33,baseLongitude:151},getTooltip:()=>null}];
const selectedPlace = {options:{placeId:'place',baseLatitude:-33,baseLongitude:151},getTooltip:()=>null};
let rendered = [];
const staleGroup = {getLayers(){throw new Error('Stale detached cluster tree was read');}};
const refresh = vm.runInNewContext(`(() => {${refreshSource}; return refreshOverviewClusters;})()`, {
  map:{getZoom:()=>5,hasLayer:()=>true,removeLayer:()=>{}},
  state:{activeLayers:new Set(['stores','centres'])},
  mixedOverviewLayer:{clearLayers:()=>{rendered=[];},addLayers:markers=>{rendered=markers;}},
  storeClusters:staleGroup,centreLayer:staleGroup,
  storeMarkersForActiveMapView:()=>selectedMarkers,
  centreMarkersForActiveMapView:()=>[selectedPlace],
  L:{marker:(_point,options)=>({options,on:()=>{}})},refreshIcons:()=>{},
});
refresh();
assert.deepEqual(Array.from(rendered,marker=>marker.options.storeId || marker.options.placeId), ['selected','place']);
selectedMarkers=[];
refresh();
assert.deepEqual(Array.from(rendered,marker=>marker.options.placeId), ['place']);
console.log('Joined clusters use applied filters, including empty results');
