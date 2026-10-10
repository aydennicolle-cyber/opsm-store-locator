#!/usr/bin/env python3
"""Verify public place boundary gaps and BN branch points against the ABS service.

No private targets are read. Cache keys bind evidence to the queried coordinate;
moving a point cannot reuse its previous assignment. Ambiguity stays unresolved.
"""
import csv
import json
import urllib.request
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from market_points import contains, point_key

ROOT = Path(__file__).resolve().parents[1]
SERVICE = 'https://geo.abs.gov.au/arcgis/rest/services/ASGS2021/SA2/FeatureServer/0/query'
OUTPUT = ROOT / 'data/market_point_links.json'


def query(point):
    params = dict(where='1=1', geometry=f"{point['longitude']},{point['latitude']}",
                  geometryType='esriGeometryPoint', inSR='4326', spatialRel='esriSpatialRelIntersects',
                  outFields='sa2_code_2021,sa2_name_2021', returnGeometry='false', f='json')
    url = SERVICE + '?' + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=30) as response:
        payload = json.load(response)
    if payload.get('error') or 'features' not in payload:
        raise ValueError('Invalid ABS boundary response')
    matches = payload['features']
    unique = matches[0]['attributes'] if len(matches) == 1 else {}
    return dict(latitude=float(point['latitude']), longitude=float(point['longitude']),
                match_status='Unique' if len(matches)==1 else 'Ambiguous' if matches else 'Unmatched',
                sa2_code=unique.get('sa2_code_2021'), sa2_name=unique.get('sa2_name_2021'),
                match_count=len(matches), source_url=url,
                checked_at=datetime.now(timezone.utc).isoformat())


def main():
    features = json.loads((ROOT/'data/sa2_market.geojson').read_text())['features']
    places = json.loads((ROOT/'data/retail_places.json').read_text())['places']
    stores = list(csv.DictReader((ROOT/'data/optical_stores.csv').open()))
    selected = {}
    for p in places:
        if p['country']=='Australia' and sum(contains(p, f['geometry']) for f in features)!=1:
            selected[point_key(p)] = p
    for p in stores:
        if p['country']=='Australia' and p['retailer']=='Bailey Nelson':
            selected[point_key(p)] = p
    links = json.loads(OUTPUT.read_text()).get('links', {}) if OUTPUT.exists() else {}
    todo = {k:p for k,p in selected.items() if k not in links}
    print(f'{len(selected)} selected public points; {len(todo)} uncached', flush=True)
    failures = []
    def save():
        OUTPUT.write_text(json.dumps(dict(metadata=dict(source='ABS ASGS2021 SA2 authoritative point intersections',
            source_url=SERVICE, geography_vintage='2021', generated_at=datetime.now(timezone.utc).isoformat(),
            scope='Public retail places with missing or overlapping generalised polygons, plus all AU Bailey Nelson branch points',
            method='Unique authoritative intersection only. Never nearest area. Coordinate-bound cache; not a store identity or place-membership rule.',
            failed_point_keys=failures), links=dict(sorted(links.items()))),indent=2)+'\n')
    with ThreadPoolExecutor(max_workers=4) as pool:
        pending={pool.submit(query,p):k for k,p in todo.items()}
        for i,f in enumerate(as_completed(pending),1):
            k=pending[f]
            try: links[k]=f.result()
            except Exception as e: failures.append(k);print(k,type(e).__name__,flush=True)
            if i%25==0:save();print(f'{i}/{len(todo)} checked',flush=True)
    save()
    store_path = ROOT / 'data/store_market_links.json'
    if store_path.exists():
        store_payload = json.loads(store_path.read_text())
        reviewed = 0
        changed_codes = []
        for store in stores:
            if store['country'] != 'Australia':
                continue
            result = links.get(point_key(store))
            if result is None:
                continue
            unique = result['match_status'] == 'Unique'
            previous = store_payload['links'].get(store['store_id'], {})
            code = result['sa2_code'] if unique else ''
            if previous.get('sa2_code') != code:
                changed_codes.append(dict(store_id=store['store_id'], previous_sa2_code=previous.get('sa2_code'), sa2_code=code))
            store_payload['links'][store['store_id']] = dict(sa2_code=code,
                sa2_name=result['sa2_name'] if unique else '', match_confidence='High' if unique else 'Unmatched',
                match_method='Point in SA2' if unique else 'Authoritative boundary match unresolved',
                boundary_distance_km=None, boundary_source='ABS authoritative point query',
                source_url=result['source_url'], checked_at=result['checked_at'],
                queried_latitude=result['latitude'], queried_longitude=result['longitude'])
            reviewed += 1
        store_payload['metadata']['authoritative_point_review'] = dict(reviewed_store_count=reviewed, changed_codes=changed_codes, checked_at=datetime.now(timezone.utc).isoformat())
        store_payload['metadata']['matched_count'] = sum(bool(v.get('sa2_code')) for v in store_payload['links'].values())
        store_path.write_text(json.dumps(store_payload,indent=2)+'\n')
        print(f'Applied {reviewed} coordinate-bound store matches; {len(changed_codes)} SA2 codes changed',flush=True)
    print(f'Saved {len(links)} point results; {len(failures)} request failures',flush=True)


if __name__=='__main__':main()
