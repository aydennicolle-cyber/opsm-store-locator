#!/usr/bin/env python3
"""Inventory readiness work without making research or membership decisions."""
import csv
import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'


def rows(name):
    with (DATA / name).open(newline='') as stream:
        return list(csv.DictReader(stream))


def point(record):
    try:
        lat, lon = float(record['latitude']), float(record['longitude'])
        return (lat, lon) if math.isfinite(lat) and math.isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180 else None
    except (KeyError, ValueError, TypeError):
        return None


def distance(a, b):
    lat1, lon1, lat2, lon2 = map(math.radians, (*a, *b))
    term = math.sin((lat2-lat1)/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin((lon2-lon1)/2)**2
    return 6371 * 2 * math.asin(min(1, math.sqrt(term)))


def build():
    inputs = ['retail_places.json', 'retail_environments.json', 'optical_stores.csv',
              'store_place_memberships.csv', 'place_review.csv', 'data_health.json',
              'optical_evidence_reviews.csv', 'place_id_remaps.csv', 'centre_recognition_review.csv',
              'unresolved_place_reviews.csv', 'centre_recognition_decisions.csv']
    places = json.loads((DATA/'retail_places.json').read_text())['places']
    environments = {p['place_id']: p for p in json.loads((DATA/'retail_environments.json').read_text())['places']}
    stores = {s['store_id']: s for s in rows('optical_stores.csv')}
    memberships = {m['store_id']: m for m in rows('store_place_memberships.csv')}
    health = json.loads((DATA/'data_health.json').read_text())
    cert = health['store_certification']
    by_place = defaultdict(list)
    for m in memberships.values():
        if m['place_id']:
            by_place[m['place_id']].append(stores[m['store_id']])
    issues = []

    def add(kind, identifier, priority, reasons, **context):
        issues.append(dict(issue_id=f'{kind}:{identifier}', kind=kind, subject_id=identifier,
                           priority=priority, reasons=reasons, disposition='Needs investigation', **context))

    for p in places:
        pid = p['place_id']; reasons = []
        address = environments.get(pid, {}).get('address', '')
        street = p.get('location_setting') == 'High Street'
        # Named streets need an explained reference, not a fabricated building number.
        if not address:
            reasons.append('No usable displayed place address')
        elif not street and not re.search(r'\d', address):
            reasons.append('Address lacks a street number; may be valid named premises and needs checking')
        if not address and re.search(r'\b(shop|tenancy|unit|kiosk|level)\b', p.get('address', ''), re.I):
            reasons.append('Raw place address includes a tenant/unit label; check available property evidence')
        pos = point(p)
        if not pos:
            reasons.append('Missing or invalid map point')
        elif not p.get('coordinate_reason'):
            reasons.append('Point meaning not explicitly described in the place record')
        named = [s['store_id'] for s in by_place[pid] if s['retailer'] != 'Independent / Other optical']
        if reasons:
            add('place', pid, 'High' if named or not pos else 'Standard', reasons,
                name=p['name'], country=p['country'], state=p.get('state'),
                raw_address=p.get('address'), display_address=address,
                named_member_ids=named, member_count=len(by_place[pid]),
                source_url=p.get('source_url'), point=pos,
                existing_point_note=p.get('coordinate_reason') or p.get('source_basis'))

    for r in rows('place_review.csv'):
        sid=r['store_id']; c=cert.get(sid, {})
        unsafe=c.get('eligible_for_place_analytics') in [True, 'true']
        add('membership', sid, 'Critical' if unsafe else 'High' if r['retailer'] != 'Independent / Other optical' else 'Standard',
            [r['reason']] + (['Unresolved record is enabled for place-specific analysis'] if unsafe else []),
            original_queue_priority=r['priority'], retailer=r['retailer'], name=r['store_name'],
            address=r['address'], current_place_id=memberships.get(sid, {}).get('place_id'),
            evidence_url=r['evidence_url'], excluded_from_place_analysis=not unsafe)

    place_map={p['place_id']: p for p in places}
    # Recognition also challenges already accepted mappings. Those cases do not
    # appear in place_review.csv, so omitting this audit hides material conflicts.
    recognition = rows('centre_recognition_review.csv')
    for r in recognition:
        sid = r['store_id']
        add('recognition', sid, 'High' if r['priority'] == 'High' else 'Standard',
            [r['review_reason'], r['evidence']],
            name=r['name'], retailer=r['retailer'], address=r['full_address'],
            original_queue_priority=r['priority'],
            current_place_id=memberships.get(sid, {}).get('place_id'),
            candidate_venue_id=r['candidate_venue_id'],
            candidate_venue_name=r['candidate_venue_name'],
            research_review_status=r['review_status'],
            candidate_only=True,
            evidence_limit='Review candidate only; name or distance matching does not establish membership.')
    for sid, s in stores.items():
        c = cert.get(sid, {})
        if not s.get('full_address', '').strip() or 'record lacks a meaningful public storefront address' in c.get('issues', ''):
            unsafe = c.get('eligible_for_analytics') in (True, 'true')
            add('store_address', sid,
                'Critical' if unsafe else 'High' if s['retailer'] != 'Independent / Other optical' else 'Standard',
                ['Missing or insufficient storefront address; a nonempty country or unit label is not a usable address'],
                name=s['name'], retailer=s['retailer'], address=s.get('full_address'),
                source_url=s.get('official_url') or s.get('source_url'),
                excluded_from_network_analysis=not unsafe)
        a=point(s); m=memberships.get(sid, {}); p=place_map.get(m.get('place_id'))
        if not a:
            add('store_point', sid, 'High', ['Missing or invalid store point'], name=s['name'], source_url=s.get('official_url'))
        elif p and p.get('location_setting') == 'Shopping Centre' and point(p):
            km=distance(a,point(p))
            if km > 2:
                add('distance_candidate', sid, 'High', ['Accepted centre membership has distant reference points; distance alone does not invalidate membership'],
                    name=s['name'], place_id=p['place_id'], distance_km=round(km,3), source_url=s.get('official_url'))

    remaps={r['previous_place_id']:r['canonical_place_id'] for r in rows('place_id_remaps.csv')}
    for r in rows('optical_evidence_reviews.csv'):
        sid=r['store_id']; target=r['place_id']; visited=set()
        while target in remaps and target not in visited:
            visited.add(target); target=remaps[target]
        if r['decision']=='pair' and sid in memberships and memberships[sid]['place_id'] != target:
            add('evidence_conflict', sid+'@'+target, 'High', ['Retained explicit directory pairing differs from current accepted membership; investigate supersession or scope'],
                store_id=sid, current_place_id=memberships[sid]['place_id'], evidence_place_id=target,
                source_url=r['source_url'], basis=r['basis'], review_date=r['review_date'])

    for source in health['sources']:
        if source['category']=='named_network' and source['status']!='current':
            add('source', source['id'], 'High', ['Named-network source is stale, missing or incomplete'],
                source_status=source['status'], snapshot=source['snapshot'], last_success=source.get('last_success'),
                affected_store_count=sum(c.get('source_id')==source['id'] for c in rows('store_certification.csv')))

    decision_path=ROOT/'docs/OPTICAL_READINESS_DECISIONS.json'
    decisions=json.loads(decision_path.read_text()) if decision_path.exists() else {}
    decision_map={d['issue_id']:d for d in decisions.get('decisions', [])}
    for issue in issues:
        if issue['issue_id'] in decision_map:
            issue['review']=decision_map[issue['issue_id']]
            issue['disposition']=issue['review']['disposition']
    payload={'purpose':'Full-inventory readiness triage; flags are candidates for investigation, not corrections or proof of error.',
             'scope_counts':{'places_evaluated':len(places),'stores_evaluated':len(stores),
                             'membership_reviews_evaluated':len(rows('place_review.csv')),
                             'recognition_candidates_evaluated':len(recognition),
                             'background_discovery_leads_not_promoted':health['informational_counts']['background_discovery_leads']},
             'issue_counts':dict(Counter(i['kind'] for i in issues)),
             'priority_counts':dict(Counter(i['priority'] for i in issues)),
             'reviewed_decisions':decisions.get('decisions', []),
             'source_refresh_attempts':decisions.get('source_attempts', []),
             'input_hashes':{n:hashlib.sha256((DATA/n).read_bytes()).hexdigest() for n in inputs},
             'issues':sorted(issues,key=lambda i:({'Critical':0,'High':1,'Standard':2}[i['priority']],i['kind'],i['subject_id']))}
    out=ROOT/'docs/OPTICAL_READINESS_REGISTER.json';out.write_text(json.dumps(payload,indent=2)+'\n')
    print(json.dumps({k:payload[k] for k in ['scope_counts','issue_counts','priority_counts']},indent=2))


if __name__=='__main__':
    build()
