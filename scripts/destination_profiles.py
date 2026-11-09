"""Compile public destination profiles; geography and optical membership stay distinct."""
from __future__ import annotations
import csv
import hashlib
import html
import json
import math
from pathlib import Path


def load(path):
    return json.loads(path.read_text())


def distance_km(lat, lon, other_lat, other_lon):
    lat, lon, other_lat, other_lon = map(math.radians, map(float, (lat, lon, other_lat, other_lon)))
    a = math.sin((other_lat-lat)/2)**2 + math.cos(lat)*math.cos(other_lat)*math.sin((other_lon-lon)/2)**2
    return 6371.0088 * 2 * math.asin(min(1, math.sqrt(a)))


def validated_market(fact, place, markets):
    geo = fact['demographic_boundary_evidence']
    if (geo['match_status'] != 'Unique' or geo['match_count'] != 1
            or any(abs(float(geo[k])-float(place[k])) > 0.00000005 for k in ('latitude','longitude'))):
        raise ValueError('Demographic receipt is not unique and bound to the current place point')
    if not geo['source_url'].startswith('https://geo.abs.gov.au/'):
        raise ValueError('Missing authoritative boundary evidence')
    props = markets[geo['sa2_code']]
    return {**props, 'interpretation':'Resident SA2 context, not a centre trade area or customer catchment.',
            'boundary_evidence':geo}


def compile_profiles(data, summaries):
    facts = load(data/'destination_profile_facts.json')['profiles']
    places = {r['place_id']:r for r in load(data/'retail_places.json')['places']}
    markets = {r['properties']['sa2_code']:r['properties'] for r in load(data/'sa2_market.geojson')['features']}
    def read_csv(name):
        with (data/name).open(newline='') as f:return list(csv.DictReader(f))
    stores = {r['store_id']:r for r in read_csv('optical_stores.csv')}
    certificates = {r['store_id']:r for r in read_csv('store_certification.csv')}
    memberships = read_csv('store_place_memberships.csv')
    directory = load(data/'destination_directory.json')['records']
    def store_summary(sid):
        r=stores[sid]; c=certificates[sid]
        return {k:r.get(k) for k in ('store_id','retailer','name','business_type','status','full_address','latitude','longitude','source_url','fetched_at','status_evidence_url','status_verified_at')} | {
            'stale_source_warning':c.get('current_source') != 'true',
            'quality_notes':c.get('issues','')}
    result=[]
    for fact in facts:
        pid=fact['place_id'];place=places[pid]
        market=validated_market(fact,place,markets)
        accepted=[]
        for m in memberships:
            if (m['place_id']==pid and m['review_status']=='Accepted'
                    and certificates.get(m['store_id'], {}).get('eligible_for_place_analytics')=='true'):
                accepted.append(store_summary(m['store_id']) | {'membership_evidence':{k:m[k] for k in ('evidence_basis','evidence_url','verified_at','mapping_confidence')}})
        nearby=[]
        for sid,r in stores.items():
            if r['country']!=place['country'] or r['retailer']=='Bailey Nelson' or certificates.get(sid, {}).get('eligible_for_analytics')!='true':continue
            d=distance_km(place['latitude'],place['longitude'],r['latitude'],r['longitude'])
            if d<=5:nearby.append(store_summary(sid) | {'distance_km':d,'accepted_destination_member':any(x['store_id']==sid for x in accepted)})
        nearby.sort(key=lambda r:(r['distance_km'],r['store_id']))
        summary=next(s for s in summaries if s['place_id']==pid)
        result.append({**fact,'identity':{k:place[k] for k in ('place_id','name','country','state','location_setting','address','latitude','longitude','source_url','source_date')},
                       'population_context':market,
                       'optical_competition':{'accepted_current_members':accepted,'accepted_member_count':len(accepted),'nearby_current_non_bn':nearby,'within_2km':sum(r['distance_km']<=2 for r in nearby),'within_5km':len(nearby),
                           'method':'Current non-BN competitors at <=2/5 km straight-line distance from the recorded point. All settings eligible. Radius does not establish membership or customer catchment; observed counts may be incomplete. Stale-source warnings remain separate.'},
                       'directory_summary':summary,
                       'directory_record_ids':[r['record_id'] for r in directory if r['place_id']==pid],
                       'directory_database':'destination_directory.json'})
    return result


def readable(profiles):
    out=['DESTINATION RESEARCH PROFILES — SOURCE DATES RETAINED','Public evidence; three explicitly partial profiles. No commercial forecast.','The detailed directory database preserves every source row, including held/out-of-scope listings.','']
    for p in profiles:
        i=p['identity']; m=p['population_context'];c=p['optical_competition'];d=p['directory_summary']
        out.extend([i['name'].upper(),p['profile_status'],f"Canonical identity: {i['place_id']}; {i['location_setting']}; {i['latitude']}, {i['longitude']}",
                    'EXTENT: '+p['extent'],'Extent source: '+p['extent_evidence']['source_url'],
                    f"OPTICAL: {c['accepted_member_count']} accepted current members; {c['within_2km']} current non-BN competitors within 2 km; {c['within_5km']} within 5 km.",c['method']])
        for r in c['accepted_current_members']:
            out.append(f"  {r['name']} [{r['store_id']}] — {r['full_address']}; type: {r['business_type'] or 'unclassified'}; membership evidence: {r['membership_evidence']['evidence_url']}; checked {r['membership_evidence']['verified_at']}; stale source: {r['stale_source_warning']}")
        out.extend([p['material_optical_note'],f"DIRECTORY: {d['source_listing_count']} source listings; {d['in_scope_non_optical_listings']} in-scope directory-listed non-optical records; {d['coming_soon_listings']} coming soon; {d['held_scope_listings']} held; {d['outside_or_unresolved_address_listings']} outside scope/unresolved address; {d['unclassified_listings']} unclassified.",d['scope'],'Categories (overlap possible): '+', '.join(f"{x['name']} {x['listing_count']}" for x in d['categories']),d['share_unavailable_reason'],
                    f"RESIDENT CONTEXT: {m['sa2_name']} (SA2 {m['sa2_code']}); 2025 population {m['population_2025']:,}; 2021 population {int(m['population_2021']):,}; change {m['population_growth_2021_2025_number']:,} ({m['population_growth_2021_2025_pct']}%). Density {m['population_density_2025']:,}/km² (2025). Age 45+ {m['age_45_plus_pct_2021']}%; median equivalised household income AUD {m['median_equivalised_household_income_weekly_2021']:,}/week (2021).",m['interpretation'],f"ABS release {m['source_release_date']}: {m['source_url']}",f"Coordinate-bound SA2 receipt checked {m['boundary_evidence']['checked_at']}: {m['boundary_evidence']['source_url']}"])
        for label,key in [('ACCESS','access'),('PUBLIC PROPERTY FACTS','property_facts'),('LEASING','leasing_evidence'),('PUBLISHED TRADE AREA','trade_area_evidence'),('CENSUS CONTEXT','census_context')]:
            out.append(label)
            for f in p.get(key,[]):out.append(f"  {f['label']}: {f['value']} Source: {f['source_url']}; source date/period: {f.get('source_date') or f.get('source_period') or 'not stated'}; checked {f['checked_at']}")
        out.extend(['DECISION USE: '+p['decision_use'],'LIMITATIONS: '+' '.join(p['limitations']+d['coverage_limitations']),'NEXT QUESTIONS:']+['  '+q for q in p['next_questions']]+['',''])
    return '\n'.join(out)


def build_profiles(data, summaries):
    if not (data/'destination_profile_facts.json').exists():return
    profiles=compile_profiles(data,summaries)
    names=['destination_profile_facts.json','destination_directory.json','optical_stores.csv','store_certification.csv','store_place_memberships.csv','sa2_market.geojson','retail_places.json']
    metadata={'as_of':max(p['checked_at'][:10] for p in profiles),'baseline':'Validated census batch78; no census admissions in this pilot','input_sha256':{n:hashlib.sha256((data/n).read_bytes()).hexdigest() for n in names},'limitations':'Partial profiles, preserving source vintages. No inferred tenancy shares, customer catchment or predicted store performance.'}
    (data/'destination_profiles.json').write_text(json.dumps({'metadata':metadata,'profiles':profiles},indent=2,ensure_ascii=False)+'\n')
    (data/'destination_profiles.txt').write_text(readable(profiles))
    report_html = '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Destination research pilot</title><style>body{font:16px/1.6 system-ui,sans-serif;max-width:960px;margin:40px auto;padding:0 24px;color:#19362f;background:#f8faf9}pre{font:inherit;white-space:pre-wrap;overflow-wrap:anywhere}nav{padding:16px;background:#e8f0ec}a{color:#165d48}h1{line-height:1.15}</style><h1>Destination research pilot</h1><nav><a href="destination_directory.json" download>Full directory database</a> · <a href="destination_profile_comparisons.csv" download>Comparison CSV</a> · <a href="destination_profiles.json" download>Structured profiles</a></nav><pre>'+html.escape(readable(profiles))+'</pre></html>'
    (data/'destination_profiles.html').write_text(report_html)
    rows=[]
    for p in profiles:
        c=p['optical_competition'];m=p['population_context'];d=p['directory_summary']
        rows.append({'place_id':p['place_id'],'name':p['identity']['name'],'profile_status':p['profile_status'],'accepted_optical_members':c['accepted_member_count'],'nearby_2km':c['within_2km'],'nearby_5km':c['within_5km'],'directory_listings_in_scope':d['in_scope_non_optical_listings'],'sa2_code':m['sa2_code'],'resident_population_2025':m['population_2025'],'resident_growth_2021_2025_pct':m['population_growth_2021_2025_pct'],'resident_density_2025':m['population_density_2025'],'income_2021_equivalised_weekly':m['median_equivalised_household_income_weekly_2021'],'decision_use':p['decision_use'],'remaining_questions':' | '.join(p['next_questions'])})
    with (data/'destination_profile_comparisons.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
