"""Validated public-source place definitions and reusable tenant captures.

This adapter never opens a private workspace or imports commercial selections.
A source directory's completeness is separate from current occupancy/trading.
"""
import copy
import json
from pathlib import Path
from urllib.parse import urlsplit

FILE = 'public_directory_captures.json'
PLACE_FIELDS = {'place_id','name','country','state','locality','format','address','sources','reviewed_at','scope','latitude','longitude','coordinate_source_url'}
CAPTURE_FIELDS = {'place_id','records','source_urls','source_total','directory_complete','capture_method','limitations','format_scope','scope','absence_reviews','anonymous_counts','source_record_count','anonymous_record_count'}
FORBIDDEN = {'bn_sources','current_bn_stores','priority','rank','revenue_group','cohort_membership','supplier_status','committed_fy31','sales_performance','negotiation_notes','source_capture_file'}


def source_url(value):
    p = urlsplit(value or '')
    if p.scheme != 'https' or not p.netloc or p.username or p.hostname in {'localhost','127.0.0.1'}:
        raise ValueError('Public evidence requires an attributed HTTPS source')


def load(data):
    path = Path(data)/FILE
    if not path.exists():
        return {'places': [], 'captures': []}
    x = json.loads(path.read_text())
    if x.get('schema_version') != 1:
        raise ValueError('Unknown public directory schema')
    def inspect(value):
        if isinstance(value,dict):
            if FORBIDDEN & set(value):
                raise ValueError('Private or local fields are not public directory evidence')
            for v in value.values(): inspect(v)
        elif isinstance(value,list):
            for v in value: inspect(v)
        elif isinstance(value,str) and ('/Users/' in value or 'bn-target-' in value or 'private-corridor-' in value or 'private-place-' in value):
            raise ValueError('Private source identifiers or local paths are not public evidence')
    inspect(x)
    ids=set()
    for p in x['places']:
        if set(p)-PLACE_FIELDS or p['place_id'] in ids or not p['sources']:
            raise ValueError('Invalid or duplicate public research place')
        ids.add(p['place_id'])
        if p['format'] not in {'Shopping Centre','High Street'} or not all(p.get(k) for k in ('name','country','state','locality','scope','reviewed_at')):
            raise ValueError('Public place identity requires named geographic scope and dated sources')
        for src in p['sources']: source_url(src['url'])
        point=(p.get('latitude'),p.get('longitude'))
        if any(v is None for v in point):
            if point!=(None,None): raise ValueError('A map point must have both coordinates or neither')
        else:
            from store_rules import valid_store_point
            if not valid_store_point(p): raise ValueError('Invalid public place coordinates')
            source_url(p['coordinate_source_url'])
    captures=set()
    for c in x['captures']:
        if set(c)-CAPTURE_FIELDS or c['place_id'] in captures:
            raise ValueError('Invalid or duplicate public directory capture')
        captures.add(c['place_id'])
        for url in c['source_urls']: source_url(url)
        for r in c['records']: source_url(r['source_url'])
    return x


def add_places(places, data):
    by_id={p['place_id']:p for p in places}
    for r in load(data)['places']:
        if r['place_id'] in by_id:
            raise ValueError('Research identity cannot overwrite an existing public place')
        p=dict(place_id=r['place_id'],centre_id=r['place_id'],name=r['name'],canonical_name=r['name'],aliases=[],
            place_type='High Street Corridor' if r['format']=='High Street' else 'Shopping Centre',location_setting=r['format'],
            country=r['country'],state=r['state'],locality=r['locality'],suburb=r['locality'],postcode='',address=r['address'],
            latitude=r['latitude'],longitude=r['longitude'],owner='',manager='',centre_type='',gla_sqm='',annual_visits='',
            trade_area_population='',anchors=[],tenancy_count='',redevelopment_activity='',official_url=r['sources'][0]['url'],
            source_url=r['sources'][0]['url'],source_date=r['reviewed_at'],status='Mapped',confidence='Medium' if r['latitude'] is not None else 'Uncertain',
            source_basis=r['scope'],retailers=[],optical_store_count=0,old_centre_ids=[],catchment_radius_m=800,
            coordinate_confidence='Medium' if r['latitude'] is not None else 'Uncertain',
            coordinate_reason='Approximate publicly sourced road reference; not a shopfront or surveyed boundary.' if r['latitude'] is not None else 'Named property identity is evidenced; map point remains unresolved. No coordinate or demographic assignment inferred.')
        places.append(p);by_id[p['place_id']]=p


def apply(payload, data):
    from retail_directory_overlay import apply_captures
    from reconcile_environment_optics import reconcile
    x=load(data)
    if not x['captures']: return payload
    output=apply_captures(payload,x['captures'])
    captures={c['place_id']:c for c in x['captures']}
    reconcile(output,set(captures))
    for p in output['places']:
        if p['place_id'] not in captures: continue
        p['public_directory_evidence']=True
        p['limitations']=[v for v in p['limitations'] if 'unknown reporting-period' not in v]
        if captures[p['place_id']].get('anonymous_counts'):
            p['anonymous_counts']=copy.deepcopy(captures[p['place_id']]['anonymous_counts'])
            count=p['anonymous_counts'].get('hospitality_venues')
            if count and count > 0:
                from build_retail_environments import key
                fid='category:'+key('Food and dining')
                ref='anonymous-dining:'+p['place_id']
                p['features'].setdefault(fid,[]).append(ref)
                p['anonymous_counts']['evidence']=[dict(source_id=ref,source_urls=captures[p['place_id']]['source_urls'],observed_at=p['anonymous_counts'].get('as_of'),category='Food and dining',count=count,basis='Anonymous source-attributed street dining observations; no occupancy or absence inference.')]
                if not any(f['id']==fid for f in output['features']):output['features'].append(dict(id=fid,label='Food and dining',kind='Category'))
                if 'Food and dining' not in p['shopping_purpose']:p['shopping_purpose'].append('Food and dining')
        if captures[p['place_id']]['format_scope']=='named street' and captures[p['place_id']]['directory_complete']:
            p['coverage']['status']='Complete publisher capture; partial street coverage'
    output['metadata']['public_directory_capture_count']=len(captures)
    output['metadata']['directory_trading_note']='Complete capture means all available publisher records, not independently verified current trading or occupied premises.'
    return output
