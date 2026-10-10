#!/usr/bin/env python3
"""Account for every supplied AU/NZ listing without treating suggestions as stores."""
import argparse
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from difflib import SequenceMatcher
from audit_store_identities import normalized, distance_metres
from stage_independent_candidates import valid_point, public_url, candidate_rows, apply_decisions
from luc_record_reviews import apply_record_reviews

ROOT=Path(__file__).resolve().parents[1]


def read(path):
    with path.open(newline='',encoding='utf-8-sig') as f:return list(csv.DictReader(f))


def street_key(address):
    address=re.sub(r'\b(?:shop|unit|suite|ste|level)\s+[A-Za-z]?[-\s]?\d+[A-Za-z]?\s*[,/]?\s*', '', address, flags=re.I)
    text=normalized(address)
    substitutions={'st':'street','rd':'road','ave':'avenue','dr':'drive','pde':'parade','hwy':'highway','ln':'lane','pl':'place','ctr':'centre','center':'centre'}
    text=' '.join(substitutions.get(t,t) for t in text.split())
    match=re.search(r'\b(\d+[a-z]?(?: \d+)? (?:[a-z]+ ){0,5}(?:street|road|avenue|drive|parade|highway|lane|place|terrace|way|boulevard))\b',text)
    return match.group(1) if match else ''


def unit_key(address):
    match=re.search(r'\b(?:shop|unit|suite|level)\s*([a-z]?\d+[a-z]?)\b',normalized(address))
    return match.group(0) if match else ''


def exact_identity(source,store):
    a,b=street_key(source['address']),street_key(store['full_address'])
    if not a or a!=b:return False
    ua,ub=unit_key(source['address']),unit_key(store['full_address'])
    if ua and ub and ua!=ub:return False
    same_name=normalized(source['name'])==normalized(store['name'])
    same_tenancy=bool(ua and ua==ub and source.get('chain')==store['retailer'])
    return (same_name or same_tenancy) and distance_metres(source,store)<=300


def apply_branch_reviews(output, stores, directory):
    """Reuse the explicit handover branch review only for unchanged identities."""
    path = directory/'bailey_nelson_oscar_wylee_branch_review.csv'
    if not path.exists(): return
    current = {r['source_id']: r for r in output}
    canonical = {r['store_id']: r for r in stores}
    for review in read(path):
        row = current.get(review['luc_key'])
        target = canonical.get(review.get('reviewed_identity_ours_key'))
        if not row or not target: continue
        unchanged = (row['name'] == review['luc_name'] and row['address'] == review['luc_address']
                     and float(row['latitude']) == float(review['luc_lat']) and float(row['longitude']) == float(review['luc_lng'])
                     and target['full_address'] == review['ours_address'])
        if not unchanged: continue
        row.update(outcome='Linked existing', canonical_store_id=target['store_id'], evidence_url=target['official_url'],
                   reason='Previously reviewed branch identity and source address are unchanged. '+review['review_basis']+'. Trading status and coordinate discrepancies remain separate checks; this is not fresh verification of every branch.')
    groups_path = directory/'luc_same_brand_coordinate_groups.csv'
    if not groups_path.exists(): return
    groups = defaultdict(list)
    for r in read(groups_path):
        if r['classification'] != 'Repeated Oscar Wylee branch/address listings': continue
        row = current.get(r['record_key'])
        if row and row['address'] == r['address'] and row['name'] == r['name']:
            groups[r['group_id']].append(row)
    for group in groups.values():
        ids = {r['canonical_store_id'] for r in group if r['canonical_store_id']}
        if len(group) < 2 or len(ids) != 1: continue
        group.sort(key=lambda r: int(r['source_id'].split(':')[1]))
        for row in group[1:]:
            row.update(outcome='Duplicate source listing', related_source_id=group[0]['source_id'], canonical_store_id=next(iter(ids)),
                       reason='Previously reviewed repeated Oscar Wylee branch alias: same branch, tenancy and source point; retained as a source row, not another store.')


def reconcile(pack,out,stores_path,manual_path):
    out.resolve().relative_to((ROOT/'output').resolve());out.mkdir(parents=True,exist_ok=True)
    stores=read(stores_path);source=[]
    for layer,file in [('independent','bn-independents-au-nz-ALL-with-verified-flag.csv'),('chain','bn-optical-chains-au-nz.csv')]:
        for row in read(pack/'01-locations'/file):
            if row['country'] not in {'AU','NZ'}:continue
            source.append(dict(source_id=f'{layer}:{row["id"]}',layer=layer,country=row['country'],name=row.get('name') or row.get('store_name',''),chain=row.get('chain',''),address=row['address'],suburb=row.get('suburb',''),postcode=row.get('postcode',''),latitude=row['lat'],longitude=row['lng'],supplier_verified=row.get('verified_optometry','not supplied'),source_method=row.get('source','')))
    manual = {}
    if manual_path.exists():
        candidates = candidate_rows(read(pack/'01-locations/bn-independents-au-nz-ALL-with-verified-flag.csv'), 'luc-independent')
        decisions = read(manual_path)
        checked = apply_decisions(candidates, decisions, {s['store_id'] for s in stores})
        decided_ids = {r['candidate_id'] for r in decisions}
        manual = {r['candidate_id'].replace('luc-independent:', 'independent:'): dict(decision=r['review_status'], canonical_store_id=r['canonical_store_id'], evidence_url=r['evidence_url'], reason=r['reason']) for r in checked if r['candidate_id'] in decided_ids}
    bycountry=defaultdict(list)
    for store in stores:bycountry['AU' if store['country']=='Australia' else 'NZ'].append(store)
    output=[]
    for row in source:
        record={**row,'outcome':'Needs verification','canonical_store_id':'','related_source_id':'','evidence_url':'','reason':'No supported existing identity found. Official practice identity, retail services, current trading and premises coordinates need verification.','checked_at':'2026-09-12'}
        if row['source_id'] in manual:
            decision=manual[row['source_id']]
            record.update(outcome=decision['decision'],canonical_store_id=decision['canonical_store_id'],evidence_url=decision['evidence_url'],reason=decision['reason'])
        elif row['supplier_verified']=='false':
            record.update(outcome='Supplier rejected; not reverified',reason='Supplier supplied no row-specific rejection reason or raw verification evidence. Retained for audit, not counted as an accepted competitor.')
        elif not valid_point(row):
            record.update(outcome='Location unresolved',reason='Coordinates are missing, invalid or outside the stated country. Cannot place an accurate map pin.')
        else:
            nearby=[s for s in bycountry[row['country']] if abs(float(s['latitude'])-float(row['latitude']))<.01 and abs(float(s['longitude'])-float(row['longitude']))<.015]
            matches=[s for s in nearby if exact_identity(row,s)]
            if len(matches)==1:
                match=matches[0]
                record.update(outcome='Linked existing',canonical_store_id=match['store_id'],evidence_url=match['official_url'] or match['source_url'],reason='Same practice name and numbered street address, or same chain with matching street address and tenancy; coordinates corroborate within 300m. Identity link only: existing trading-status evidence retains its own date.')
            elif len(matches)>1:
                record.update(reason='Multiple existing records satisfy the identity/address checks. Resolve tenancy identities before linking or counting an addition.')
            elif not row['address'].strip():
                record.update(reason='Supplier address is blank. Name and map coordinates alone do not establish the physical premises or current trading.')
            elif nearby:
                names=[s for s in nearby if normalized(row['name'])==normalized(s['name'])]
                if names:record.update(reason='A nearby existing record has the same name, but the numbered address/tenancy does not match sufficiently. Verify relocation, address correction or distinct premises.',evidence_url=names[0]['official_url'] or names[0]['source_url'])
        record['source_record_hash']=hashlib.sha256(json.dumps(row,sort_keys=True).encode()).hexdigest()
        record['possible_store_ids']=''
        if record['outcome']=='Needs verification' and valid_point(row):
            possible=[s for s in bycountry[row['country']]
                      if abs(float(s['latitude'])-float(row['latitude']))<.012
                      and abs(float(s['longitude'])-float(row['longitude']))<.018
                      and ((row['chain'] and s['retailer']==row['chain']) or SequenceMatcher(None,normalized(s['name']),normalized(row['name'])).ratio()>=.68)]
            if possible:
                record.update(outcome='Possible existing identity — review', possible_store_ids='|'.join(s['store_id'] for s in possible),
                              reason='Nearby records share a brand or similar practice name, but exact identity/address/tenancy checks have not passed. Review possible aliases, relocations and coordinate errors before counting this as missing or adding another store.')
        output.append(record)
    apply_branch_reviews(output, stores, ROOT/'output/mac-handover/reconciliation')
    # Exact repeated source identity/address/point records are retained as aliases.
    # No nearest-neighbour or shared-centre collapse is permitted.
    groups=defaultdict(list)
    for row in output:
        if valid_point(row) and row['address'].strip():groups[(row['country'],row['chain'] or normalized(row['name']),normalized(row['address']),round(float(row['latitude']),5),round(float(row['longitude']),5))].append(row)
    for group in groups.values():
        if len(group)<2:continue
        group.sort(key=lambda r:(not bool(r['canonical_store_id']),r['source_id']))
        for row in group[1:]:
            if row['outcome']=='Supplier rejected; not reverified':continue
            row.update(outcome='Duplicate source listing',related_source_id=group[0]['source_id'],canonical_store_id=group[0]['canonical_store_id'],evidence_url=group[0]['evidence_url'],reason='Repeated source entry for the same business/chain, identical tenancy address and matching coordinates. Retained as an alias; not a separate store. Representative identity/trading review may still be pending.')
    apply_record_reviews(output, stores, out/'decisions.csv')
    summary=dict(source_rows=len(output),by_layer=dict(Counter(r['layer'] for r in output)),by_country=dict(Counter(r['country'] for r in output)),outcomes=dict(Counter(r['outcome'] for r in output)),method='Every supplied AU/NZ chain and independent row accounted for. Strict identity/address links, explicit public-evidence reviews with source/canonical identity hashes, exact duplicate aliases, otherwise a specific evidence gap. This is not individual web verification of every row.')
    with (out/'all-records.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(output[0]),lineterminator='\n');writer.writeheader();writer.writerows(output)
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    (out/'all-records.json').write_text(json.dumps(dict(summary=summary,records=output),indent=2)+'\n')
    return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pack',type=Path,required=True);parser.add_argument('--output-dir',type=Path,required=True)
    parser.add_argument('--stores',type=Path,default=ROOT/'data/optical_stores.csv')
    parser.add_argument('--decisions',type=Path,default=ROOT/'output/mac-handover/reconciliation/independent-expansion/intake/decisions.csv')
    args=parser.parse_args();print(json.dumps(reconcile(args.pack,args.output_dir,args.stores,args.decisions),indent=2))
