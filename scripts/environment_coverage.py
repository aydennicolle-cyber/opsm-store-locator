"""Coverage of assembled evidence, separately from directory and trading checks."""


def label_coverage(payload):
    for place in payload['places']:
        c = place['coverage']
        if c.get('directory_complete'):
            c['research_status_label'] = 'Complete source capture within the stated research scope'
        elif c.get('observations') or c.get('source_urls') or c.get('held_scope_records'):
            c['research_status_label'] = 'Partly researched'
        else:
            c['research_status_label'] = 'Not researched for tenant mix'
        # Capture completeness and current trading verification remain independent.
        c['trading_verification_label'] = ('Independent trading verification recorded'
            if c.get('trading_verified') is True else 'Current trading not independently verified')
    return payload


def summarize(payload, bailey_corridor_ids=()):
    places = payload['places']
    listing_ids = {p['place_id'] for p in places if p['observations']}
    non_optical_ids = {p['place_id'] for p in places
                       if any(r.get('role') != 'Optical' for r in p['observations'])}
    captured_ids = {p['place_id'] for p in places if p['coverage'].get('directory_complete')}
    centres = {p['place_id'] for p in places if p.get('place_type') == 'Shopping Centre'}
    centre_captures = {p['place_id'] for p in places if p['place_id'] in centres & captured_ids
                       and p['coverage'].get('format_scope') == 'canonical centre'}
    streets = set(bailey_corridor_ids) & {p['place_id'] for p in places}
    return {
        'coverage_statement': 'Counts use the assembled environment evidence, including captured directories and curated observations. A source capture is not a complete census of trading businesses. Missing listings do not establish absence.',
        'counts': {
            'places': len(places), 'places_with_listing_evidence': len(listing_ids),
            'places_without_listing_evidence': len(places) - len(listing_ids),
            'places_with_non_optical_listing_evidence': len(non_optical_ids),
            'complete_source_captures': len(captured_ids), 'shopping_centres': len(centres),
            'complete_centre_source_captures': len(centre_captures),
            'independently_trading_verified_places': sum(p['coverage'].get('trading_verified') is True for p in places),
            'bailey_corridors': len(streets), 'bailey_corridors_with_non_optical_listing_evidence': len(streets & non_optical_ids),
        },
        'bailey_corridor_retail_mix_coverage': round(100 * len(streets & non_optical_ids) / len(streets), 1) if streets else 0,
    }
