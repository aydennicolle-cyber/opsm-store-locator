"""Reconcile public place measures without discarding differing source reports."""
import math

UNITS = {
    'gla_sqm': 'm²', 'tenancy_count': 'reported tenancies',
    'annual_visits': 'visits/year', 'trade_area_population': 'people',
}


def observation(field, value, evidence):
    value = float(value)
    if not math.isfinite(value) or value < 0:
        raise ValueError(f'Invalid place metric: {field}')
    if field == 'tenancy_count' and not value.is_integer():
        raise ValueError('Non-integer tenancy count')
    # Explicit public projection: never copy an entire source row into a profile.
    return {
        'value': int(value) if value.is_integer() else value,
        'unit': UNITS[field],
        **{k: evidence.get(k) or '' for k in (
            'portfolio_asset_id', 'source_record_id', 'source_url', 'source_date',
            'source_period', 'last_verified_at', 'confidence',
        )},
    }


def reconcile(observations):
    result = {'metric_observations': {}, 'metric_evidence': {}, 'metric_conflicts': {}}
    for field, rows in observations.items():
        if field not in UNITS or not rows:
            continue
        unique = []
        for row in rows:
            if row not in unique:
                unique.append(row)
        result['metric_observations'][field] = unique
        values = {r['value'] for r in unique}
        if len(values) > 1:
            result[field] = None
            result['metric_conflicts'][field] = (
                'Different reported values; periods or measurement scopes may differ. '
                'No single comparable figure selected. See retained source reports.'
            )
        else:
            result[field] = unique[0]['value']
            result['metric_evidence'][field] = {k: v for k, v in unique[0].items() if k != 'value'}
    return result


def merge_place_metrics(place, property_summary):
    """Combine raw place measures with property evidence, including existing holds."""
    reports = {}
    for source in (place, property_summary):
        for field in UNITS:
            rows = source.get('metric_observations', {}).get(field)
            if rows:
                reports.setdefault(field, []).extend(rows)
            elif source.get(field) not in (None, ''):
                evidence = source.get('metric_evidence', {}).get(field) or {
                    'source_url': source.get('source_url'),
                    'source_date': source.get('source_date'),
                    'last_verified_at': source.get('last_verified_at'),
                }
                reports.setdefault(field, []).append(observation(field, source[field], evidence))
    return reconcile(reports)
