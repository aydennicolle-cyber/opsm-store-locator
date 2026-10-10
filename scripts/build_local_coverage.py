#!/usr/bin/env python3
"""Build the local BN pipeline and Luc review overlay; never a public asset."""
import csv
import json
import re
import math
from collections import Counter
from pathlib import Path
from reconcile_luc_records import normalized, street_key
from store_rules import current_competitor, valid_store_point, meaningful_address

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/coverage-expansion-20260912'
PACK=ROOT/'output/mac-handover/BN-data-pack'


def read(path):
    with path.open(newline='',encoding='utf-8-sig') as f:return list(csv.DictReader(f))


def norm(value):
    value=normalized(value)
    for a,b in [('shopping centre',''),('shopping center',''),('mall',''),('westfield','')]:
        value=value.replace(a,b)
    value=re.sub(r'\b(?:st|rd)\b',lambda m: {'st':'street','rd':'road'}[m.group()],value)
    return ' '.join(value.split())


def pipeline_status(source_status, committed):
    return ("Open — supplier reported" if source_status == "Open" else "Opening Soon — supplier reported" if source_status.lower().startswith("opening") else "Planned — BN opening plan" if committed == "Y" else "Prospective — backup")


def distance_km(a, b):
    lat1, lon1, lat2, lon2 = map(math.radians, [float(a['latitude']), float(a['longitude']), float(b['latitude']), float(b['longitude'])])
    h = math.sin((lat2-lat1)/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin((lon2-lon1)/2)**2
    return 6371 * 2 * math.asin(min(1, math.sqrt(h)))


def point_available(row):
    country = {'AU': 'Australia', 'NZ': 'New Zealand'}.get(row.get('country'))
    return bool(country and valid_store_point({**row, 'country': country}))


def enrich_appraisals(records, stores, places, rankings, properties, tenants):
    """Join public evidence locally; research order is not an investment ranking."""
    place_index = {p['place_id']: p for p in places}
    rank_index = {r['place_id']: r for group in rankings.values() for r in group}
    for row in records:
        opened = row['status'].startswith('Open —')
        row['research_scope'] = 'Existing / reported open' if opened else 'ANZ target' if row['country'] in {'AU', 'NZ'} else 'Outside ANZ scope'
        # Automatic names/localities are reference pins, never accepted membership.
        place = place_index.get(row.get('place_id')) if row.get('location_review_date') else None
        rank = rank_index.get(place['place_id']) if place else None
        appraisal = dict(mapping_accepted=bool(place), public_screen=rank, gaps=[], nearest_current_bn=None, nearest_other_target=None)
        if not place:
            appraisal['gaps'].append('Confirm intended centre or street and record an accepted canonical place mapping')
        else:
            summary = properties.get(place['place_id'], {})
            co_tenants = [t for t in tenants if t['place_id'] == place['place_id'] and t.get('category') != 'Optical' and t.get('status') == 'Active']
            appraisal.update(place_name=place['name'], optical_store_count=place.get('optical_store_count'), retailers=place.get('retailers', []), has_current_bn=place.get('has_bailey', False), key_co_tenant_count=len(co_tenants), property_research=summary.get('research_status', 'Not researched'))
            if place.get('has_bailey'):
                appraisal['gaps'].append('Resolve existing BN presence: additional store, relocation or outdated target')
            if not rank or not rank.get('market_features') or not any(v is not None for v in rank['market_features'].values()):
                appraisal['gaps'].append('Obtain comparable demographic evidence for the intended catchment')
            if not co_tenants:
                appraisal['gaps'].append('Research key co-tenants from public venue sources')
            if summary.get('research_status', 'Not researched') == 'Not researched':
                appraisal['gaps'].append('Research public property and format context')
        if point_available(row):
            country = {'AU': 'Australia', 'NZ': 'New Zealand'}[row['country']]
            current = [s for s in stores if s['retailer'] == 'Bailey Nelson' and s['country'] == country and current_competitor(s) and valid_store_point(s) and meaningful_address(s)]
            if current:
                nearest = min(current, key=lambda s: distance_km(row, s))
                appraisal['nearest_current_bn'] = dict(name=nearest['name'], store_id=nearest['store_id'], status=nearest['status'], distance_km=round(distance_km(row, nearest), 2))
            others = [r for r in records if r['id'] != row['id'] and r['country'] == row['country'] and r.get('source_kind') == 'target' and not r['status'].startswith('Open —') and point_available(r)]
            if others:
                nearest = min(others, key=lambda r: distance_km(row, r))
                appraisal['nearest_other_target'] = dict(id=nearest['id'], name=nearest['name'], status=nearest['status'], distance_km=round(distance_km(row, nearest), 2))
        appraisal['gaps'].append('Confirm site feasibility and commercial terms privately')
        row['appraisal'] = appraisal
        # Opening-soon/current-list discrepancies first, then opening plan, backups.
        row['research_tier'] = 9 if row['research_scope'] != 'ANZ target' else 0 if row['status'].startswith('Opening Soon') or row.get('source_kind') == 'current' else 1 if row.get('committed_fy31') == 'Y' else 2
        row['research_priority'] = {0: 'Verify opening / status', 1: 'Opening plan', 2: 'Backup research', 9: 'Outside target queue'}[row['research_tier']]
    def order(row):
        try: sequence = float(row.get('opening_sequence') or 'inf')
        except ValueError: sequence = float('inf')
        return (row['research_tier'], row['appraisal']['mapping_accepted'], row['country'], sequence, row['id'])
    queue = sorted((r for r in records if r['research_scope'] == 'ANZ target'), key=order)
    for position, row in enumerate(queue, 1): row['research_order'] = position
    return [r['id'] for r in queue]


def locate(row,places,stores):
    country={'AU':'Australia','NZ':'New Zealand','CA':'Canada'}[row['country']]
    area=norm(row['area']);venue=norm(row['venue'])
    matches=[s for s in stores if s['retailer']=='Bailey Nelson' and s['country']==country and area and area in norm(s['name'])]
    if len(matches)==1:
        s=matches[0]
        return dict(latitude=float(s['latitude']),longitude=float(s['longitude']),precision='Existing store reference',location_reason='Matched the same named locality in our Bailey network; check supplier target for relocation/second-store intentions.',canonical_store_id=s['store_id'],public_status=s['status'],public_evidence_url=s.get('status_evidence_url') or s['official_url'])
    candidates=[]
    for p in places:
        if p['country']!=country:continue
        if row.get('region') and country=='Australia' and p.get('state') and p['state']!=row['region']:continue
        names=[norm(p['name'])]+[norm(a) for a in p.get('aliases',[])]
        # A street name embedded in a place ID is not evidence of the suburb:
        # Toorak Road also runs through South Yarra.
        localities={norm(p.get(k,'')) for k in ['suburb','locality']} - {''}
        if venue and any(venue==n for n in names):
            score=2 if area and area in localities else 1
            candidates.append((score,p))
    if candidates:
        best=max(s for s,p in candidates);top=[p for s,p in candidates if s==best]
        if len(top)==1:
            p=top[0]
            return dict(latitude=float(p['latitude']),longitude=float(p['longitude']),precision='Centre / street reference',location_reason='Supplier names this public canonical place. Marker represents the centre or street, not an agreed tenancy or a current BN store.',place_id=p['place_id'],public_evidence_url=p.get('source_url') or p.get('official_url',''))
    return dict(latitude=None,longitude=None,precision='Unlocated',location_reason='No unique existing store or named public centre/street match. Confirm the intended location before assigning a pin.')


def main():
    stores=read(ROOT/'data/optical_stores.csv');places=json.loads((ROOT/'data/retail_places.json').read_text())['places'];records=[]
    for country in ['AU','NZ','CA']:
        for r in read(PACK/f'03-bn-target-sites/bn-target-sites-{country.lower()}.csv'):
            source_status=r.get('Status','').strip()
            status=pipeline_status(source_status,r['committed_fy31'])
            row=dict(id=f"bn-target-{country.lower()}-{r['bn_row']}",kind='BN pipeline',country=country,name=f"Bailey Nelson — {r['Area']}",area=r['Area'],venue=r['Street or Mall name'],region=r.get('State') or r.get('Island') or r.get('Province',''),status=status,supplier_status=source_status,source_date='2026-09-05',timing_note=source_status if source_status else 'No opening date supplied',reason='Supplied BN pipeline classification; planned/backup does not mean publicly announced or currently trading.')
            row.update(locate(row,places,stores));records.append(row)
            row.update(source_kind='target', committed_fy31=r['committed_fy31'], opening_sequence=r.get('Opening Order') or r.get('Opening Rank', ''), supplier_priority=r.get('Priority', ''), market_type=r.get('Infill/New Market', ''), target_format=r.get('Mall/Street', ''))
    # Keep current-list status discrepancies visible without copying financials.
    for r in read(PACK/'04-bn-current-stores/bn-current-stores.csv'):
        if r['status']=='Open':continue
        name=re.sub(r'^\S+\s+','',r['name'])
        row=dict(id=f"bn-current-{r['country'].lower()}-{r['store_code']}",kind='BN pipeline',country=r['country'],name='Bailey Nelson — '+name,area=name,venue='',region=r['state'],status='Opening Soon — supplier reported' if 'soon' in r['status'].lower() else 'Unknown — supplier status blank',supplier_status=r['status'],source_date='2026-09-05',timing_note='No confirmed opening date applied',reason='Current-store source includes an uncertain/opening status. Current public evidence is shown separately where available.')
        row.update(locate(row,places,stores))
        if row['latitude'] is None and r['lat'] and r['lng']:
            row.update(latitude=float(r['lat']),longitude=float(r['lng']),precision='Supplier point — unverified',location_reason='Coordinates supplied in BN current-store file; independent location verification remains outstanding.')
        records.append(row)
        row['source_kind'] = 'current'
    override_path=OUT/'pipeline-location-decisions.json'
    if override_path.exists():
        by_id={r['id']:r for r in records}
        for key,decision in json.loads(override_path.read_text()).items():
            if key not in by_id:raise ValueError(f'Unknown pipeline override {key}')
            by_id[key].update(decision)
    rankings=json.loads((ROOT/'data/lookalike_places.json').read_text())['rankings']
    properties=json.loads((ROOT/'data/property_intelligence.json').read_text())['property_summaries']
    tenants=json.loads((ROOT/'data/place_tenants.json').read_text())['memberships']
    research_queue=enrich_appraisals(records,stores,places,rankings,properties,tenants)
    reconciliation=json.loads((OUT/'reconciliation/all-records.json').read_text())
    summary=dict(pipeline_rows=len(records),target_rows=sum(r["id"].startswith("bn-target-") for r in records),by_country=dict(Counter(r['country'] for r in records)),statuses=dict(Counter(r['status'] for r in records)),mapped_au_nz=sum(r['country']!='CA' and r['latitude'] is not None for r in records),unlocated_au_nz=sum(r['country']!='CA' and r['latitude'] is None for r in records))
    summary.update(anz_research_targets=len(research_queue), accepted_target_place_mappings=sum(r['research_scope']=='ANZ target' and r['appraisal']['mapping_accepted'] for r in records))
    payload=dict(schema_version=2,private_local_only=True,summary=summary,pipeline=records,research_queue=research_queue,reconciliation=reconciliation)
    temporary=OUT/'local-coverage.json.tmp'
    temporary.write_text(json.dumps(payload,indent=2)+'\n')
    temporary.replace(OUT/'local-coverage.json')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
