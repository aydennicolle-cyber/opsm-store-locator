"""Apply dated property reference points without creating or renewing memberships."""
from datetime import date
import math
from urllib.parse import urlsplit

METHODS={'Named property map','Operator map marker','Operator-linked property map','Accepted tenant reference'}

def apply_place_point_reviews(places, stores, memberships, reviews):
    by_id={r['place_id']:r for r in places};by_store={r['store_id']:r for r in stores}
    by_member={r['store_id']:r for r in memberships};patches=[];seen=set()
    for row in reviews:
        key=row.get('place_id','');place=by_id.get(key)
        if not place or key in seen:raise ValueError(f'Unknown or duplicate place coordinate review: {key}')
        seen.add(key)
        try:
            if any(isinstance(row[k],bool) for k in ('latitude','longitude')):raise ValueError('Boolean point')
            lat,lon=(float(row[k]) for k in ('latitude','longitude'))
            bounds={'Australia':(-44.5,-9,112,154.5),'New Zealand':(-48,-33.5,165,179.5)}[place['country']]
            assert math.isfinite(lat) and math.isfinite(lon) and bounds[0]<=lat<=bounds[1] and bounds[2]<=lon<=bounds[3]
            date.fromisoformat(row['verified_at'])
            url=urlsplit(row['evidence_url']);assert url.scheme=='https' and url.hostname and '.' in url.hostname and not url.username and not url.password
            method=row['method'];confidence=row['confidence'];reason=row['reason'].strip()
            assert method in METHODS and confidence in {'High','Medium','Low'} and reason
        except (KeyError,TypeError,ValueError,AssertionError) as exc:
            raise ValueError(f'Invalid place coordinate evidence: {key}') from exc
        reference=row.get('reference_store_id','')
        if method=='Accepted tenant reference':
            member=by_member.get(reference);store=by_store.get(reference)
            if (confidence!='Low' or not store or not member or member['place_id']!=key
                    or member['review_status']!='Accepted' or (lat,lon)!=(float(store['latitude']),float(store['longitude']))):
                raise ValueError(f'Tenant reference requires an accepted member and its exact point: {key}')
        elif reference:raise ValueError(f'Unexpected tenant reference for property point: {key}')
        patches.append((place,dict(latitude=lat,longitude=lon,coordinate_source_url=row['evidence_url'],coordinate_verified_at=row['verified_at'],coordinate_confidence=confidence,coordinate_method=method,coordinate_reason=reason,coordinate_reference_store_id=reference)))
    for place,patch in patches:place.update(patch)
