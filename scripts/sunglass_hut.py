"""Deterministic Sunglass Hut public snapshot normalisation and canonical refresh."""
import csv
import json
import re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / 'retailers/sunglass-hut'
# Locator uses sales territories (NZ North/NZ South), not administrative regions.
# Normalise only these unambiguous named cities; unknown cities fail closed.
NZ_CITY_REGIONS = {'Auckland': 'Auckland', 'Hamilton': 'Waikato', 'New Plymouth': 'Taranaki',
                   'Christchurch': 'Canterbury', 'Dunedin': 'Otago'}

def rows():
    snapshot = json.loads((FOLDER / 'source_snapshot.json').read_text())
    result = []
    for doc in snapshot['stores']:
        address = doc['address']; nz = address['countryCode'] == 'NZ'
        region = address.get('localizedRegionName', '') if nz else address['region']
        if nz and region in ('', 'NZ North', 'NZ South'):
            region = NZ_CITY_REGIONS[address['city']]
        point = doc.get('yextDisplayCoordinate') or doc['geocodedCoordinate']
        closed = bool(doc.get('closed')) or bool(re.search(r'\bclosed\b', doc['name'], re.I))
        services = doc.get('c_dServicesSection', {}).get('serviceName', [])
        result.append(dict(id=doc['id'], name=doc['name'], country='New Zealand' if nz else 'Australia',
            state=region, city=address.get('sublocality') or address['city'], postal_code=address.get('postalCode',''),
            full_address=', '.join(dict.fromkeys(filter(None,[address.get('line1'), address.get('line2'), address.get('extraDescription'), address['city'], region, address.get('postalCode')]))),
            phone=doc.get('mainPhone',''), latitude=point['latitude'], longitude=point['longitude'],
            official_url=doc['source_url'], website_url=doc['source_url'], source_url=doc['source_url'],
            services='; '.join(['Sunglasses retail']+services), status='Closed' if closed else 'Active' if doc.get('hours') else 'Unknown',
            business_type='Sunglasses retail', fetched_at=snapshot['fetched_at'], verified_at=snapshot['fetched_at'][:10],
            identity_reviewed='true', coordinates_reviewed='true', status_evidence_url=doc['source_url'],
            coordinate_evidence_url=doc['source_url'], coordinate_confidence='Medium — operator display point; exact frontage unverified',
            evidence_notes='Official branch listing and trading hours; explicitly closed names override hours. Services describe sunglasses retail; no optometry service established.'))
    return result

def refresh_canonical(stores, remaps):
    by_id = {s['store_id']:s for s in stores}
    for row in rows():
        source = 'sunglass-hut-'+row['id']
        target = remaps.get(source, source)
        if target not in by_id:
            continue
        store = by_id[target]
        # Existing accepted place mappings and reviewed coordinates remain intact.
        store.update(retailer='Sunglass Hut', business_type=row['business_type'], services=row['services'],
                     status=row['status'], source_url=row['source_url'], official_url=row['official_url'],
                     fetched_at=row['fetched_at'], status_verified_at=row['verified_at'],
                     status_evidence_url=row['source_url'], status_reason=row['evidence_notes'])

def main():
    data = rows()
    with (FOLDER / 'stores.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(data[0]),lineterminator='\n');writer.writeheader();writer.writerows(data)
    print(f'Normalised {len(data)} official records')
if __name__ == '__main__': main()
