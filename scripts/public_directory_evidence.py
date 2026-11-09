"""Validated public-source place definitions and reusable tenant captures.

This adapter never opens a private workspace or imports commercial selections.
A source directory's completeness is separate from current occupancy/trading.
"""
from pathlib import Path
try:
    from . import public_directory_schema as schema
except ImportError:
    import public_directory_schema as schema

FILE = 'public_directory_captures.json'
source_url = schema.source_url


def load(data):
    path = Path(data)/FILE
    if not path.exists():
        return {'places': [], 'captures': []}
    return schema.document(schema.decode_json(path.read_text()))


def reviewed_reference(store, override, definitions):
    """Resolve an explicit store link without recreating a directory identity."""
    identity = definitions.get(override.get('canonical_place_id'))
    if identity is None:
        return None
    if (identity['country'] != store['country']
            or identity['state'] != store['state']
            or identity['format'] != override['location_setting']):
        raise ValueError('Store reference conflicts with public directory identity')
    return identity['place_id']


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
            source_url=r['sources'][0]['url'],source_date=r['sources'][0].get('source_date'),
            sources=[schema.identity_source(src) for src in r['sources']], reviewed_at=r['reviewed_at'],
            coordinate_source_url=r['coordinate_source_url'],status='Mapped',confidence='Medium' if r['latitude'] is not None else 'Uncertain',
            source_basis=r['scope'],retailers=[],optical_store_count=0,old_centre_ids=[],catchment_radius_m=800,
            coordinate_confidence='Medium' if r['latitude'] is not None else 'Uncertain',
            coordinate_reason='Approximate publicly sourced road reference; not a shopfront or surveyed boundary.' if r['latitude'] is not None else 'Named property identity is evidenced; map point remains unresolved. No coordinate or demographic assignment inferred.')
        places.append(p);by_id[p['place_id']]=p


def apply(payload, data):
    from retail_directory_overlay import apply_captures
    from reconcile_environment_optics import reconcile
    x=load(data)
    if not x['captures']: return payload
    from directory_category_crosswalk import supplement
    output=apply_captures(payload,supplement(x['captures']))
    captures={c['place_id']:c for c in x['captures']}
    reconcile(output,set(captures))
    for p in output['places']:
        if p['place_id'] not in captures: continue
        p['public_directory_evidence']=True
        p['limitations']=[v for v in p['limitations'] if 'unknown reporting-period' not in v]
        if captures[p['place_id']].get('anonymous_counts'):
            p['anonymous_counts']=schema.anonymous_counts(captures[p['place_id']]['anonymous_counts'])
            samples=[p['anonymous_counts'],*p['anonymous_counts'].get('additional_samples',[])]
            positive=[(i,s) for i,s in enumerate(samples) if (s.get('hospitality_venues') or 0)>0]
            if positive:
                from build_retail_environments import key
                fid='category:'+key('Food and dining')
                receipts=[]
                for index,sample in positive:
                    ref='anonymous-dining:'+p['place_id']+(f':sample-{index}' if index else '')
                    p['features'].setdefault(fid,[]).append(ref)
                    receipts.append(dict(source_id=ref,source_urls=sample.get('source_urls') or captures[p['place_id']]['source_urls'],observed_at=sample.get('as_of') or sample.get('observed_at'),category='Food and dining',count=sample['hospitality_venues'],basis='Anonymous source-attributed street dining observations; samples may overlap and are not added. No occupancy or absence inference.'))
                p['anonymous_counts']['evidence']=receipts
                if not any(f['id']==fid for f in output['features']):output['features'].append(dict(id=fid,label='Food and dining',kind='Category'))
                if 'Food and dining' not in p['shopping_purpose']:p['shopping_purpose'].append('Food and dining')
        schema.validate_generated_place(p)
    output['metadata']['public_directory_capture_count']=len(captures)
    output['metadata']['directory_trading_note']='Complete capture means all available publisher records, not independently verified current trading or occupied premises.'
    return output
