(function (root) {
  'use strict';
  function summarise(stores, places, region = '') {
    const auPlaces = places.filter(p => p.country === 'Australia');
    const auStores = stores.filter(s => s.country === 'Australia' && s.usable_for_network === true && s.status !== 'Closed');
    const scoped = auPlaces.filter(p => !region || p.state === region);
    const network = auStores.filter(s => !region || s.state === region);
    const centres = scoped.filter(p => p.place_type === 'Shopping Centre');
    const corridors = scoped.filter(p => p.place_type === 'High Street Corridor');
    const absent = centres.filter(p => !p.has_bailey);
    const groupCount = p => new Set(p.retailers || []).size;
    const distribution = [0,1,2,3,4].map(n => ({label: n === 4 ? '4+ optical outlets' : `${n} optical ${n === 1 ? 'outlet' : 'outlets'}`, count: centres.filter(p => n === 4 ? Number(p.optical_store_count || 0) >= 4 : Number(p.optical_store_count || 0) === n).length}));
    const regions = ['NSW','VIC','QLD','WA','SA','TAS','ACT','NT'];
    const unrecorded = auStores.filter(s => !regions.includes(s.state)).length;
    const states = regions.map(label => ({label, count: auStores.filter(s => s.state === label).length})).sort((a,b) => b.count-a.count);
    if (unrecorded) states.push({label:'Unrecorded',count:unrecorded});
    const brands = [...new Set(centres.flatMap(p => p.retailers || []).filter(name => name !== 'Independent / Other optical'))].map(label => ({label, count:centres.filter(p => (p.retailers || []).includes(label)).length})).sort((a,b)=>b.count-a.count);
    const metrics = ['gla_sqm','annual_visits','tenancy_count'].map(key => ({key,count:centres.filter(p => Number(p[key]) > 0).length}));
    return {scoped,network,centres,corridors,absent,distribution,states,brands,metrics,withBN:centres.length-absent.length, validatedWhitespace:absent.filter(p => groupCount(p)>=2).length, stale:network.filter(s=>!s.current_source).length};
  }
  const api = {summarise};
  if (typeof module !== 'undefined' && module.exports) module.exports=api;
  else root.LeasingOverview=api;
})(typeof window !== 'undefined' ? window : globalThis);
