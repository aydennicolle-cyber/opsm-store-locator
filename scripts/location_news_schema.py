"""Closed public news contract. Private research is never an accepted input format."""
from datetime import date
import re
try:
    from . import public_directory_schema as s
except ImportError:
    import public_directory_schema as s


def enum(*choices):
    def check(value):
        if value not in choices:
            raise ValueError(f"Expected one of {choices}")
        return value
    return check


def partial_date(value):
    if value is None:
        return None
    s.text(value)
    if not re.fullmatch(r"\d{4}(?:-\d{2}(?:-\d{2})?)?", value):
        raise ValueError("Expected year, month or day; unknown dates use null")
    date.fromisoformat(value + {4: '-01-01', 7: '-01', 10: ''}[len(value)])
    return value


def identifier(value):
    s.text(value)
    if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9._-]*', value):
        raise ValueError('Invalid stable news identifier')
    if re.search(r'(?:scope-bn-target|bn-target|unresolved-bailey|private)', value, re.I):
        raise ValueError('Private research identifier is not a public news identifier')
    return value


source = s.object_schema({
    'source_id': identifier, 'url': s.source_url, 'title': s.text,
}, ('source_id', 'url', 'title'))
statement = s.object_schema({
    'text': s.text, 'kind': enum('source_report', 'dataset_observation', 'context'),
    'source_ids': s.array(identifier),
}, ('text', 'kind', 'source_ids'))
metric = s.object_schema({
    'metric_id': identifier, 'name': s.text, 'value': s.number, 'unit': s.text,
    'currency': s.nullable(enum('AUD', 'NZD')), 'period': s.text,
    'definition': s.text, 'source_id': identifier, 'uncertainty': s.public_text,
}, ('metric_id', 'name', 'value', 'unit', 'currency', 'period', 'definition', 'source_id', 'uncertainty'))
version = s.object_schema({
    'revision_id': identifier, 'published_on': partial_date, 'recorded_at': s.iso_date,
    'date_basis': s.public_text, 'title': s.text, 'statements': s.array(statement, nonempty=True),
    'sources': s.array(source, nonempty=True), 'timing': s.public_text,
    'uncertainty': s.public_text, 'metrics': s.array(metric),
}, ('revision_id', 'published_on', 'recorded_at', 'date_basis', 'title', 'statements', 'sources', 'timing', 'uncertainty', 'metrics'))
relation = s.object_schema({
    'kind': enum('direct_place', 'direct_store', 'area_place', 'area_store'),
    'entity_id': identifier, 'label': s.text, 'basis': s.text,
    'source_urls': s.array(s.source_url, nonempty=True),
    'distance_km': s.nullable(s.number),
}, ('kind', 'entity_id', 'label', 'basis', 'source_urls', 'distance_km'))
event = s.object_schema({
    'event_id': identifier, 'aliases': s.array(identifier),
    'parent_event_id': s.nullable(identifier),
    'kind': enum('news', 'background', 'unchanged', 'unresolved'),
    'scope': enum('location', 'market', 'geography_review'),
    'relations': s.array(relation), 'versions': s.array(version, nonempty=True),
}, ('event_id', 'aliases', 'parent_event_id', 'kind', 'scope', 'relations', 'versions'))
check = s.object_schema({
    'source_url': s.source_url, 'attempted_at': s.iso_date,
    'status': enum('retrieved', 'partial', 'blocked', 'not_checked'),
    'last_success_at': s.nullable(s.iso_date), 'note': s.public_text,
}, ('source_url', 'attempted_at', 'status', 'last_success_at', 'note'))
document_shape = s.object_schema({
    'schema_version': enum(1), 'document_type': enum('location_news'),
    'events': s.array(event), 'checks': s.array(check),
}, ('schema_version', 'document_type', 'events', 'checks'))


def document(value, place_ids=None, store_ids=None):
    value = document_shape(value)
    ids, aliases, revisions = set(), set(), set()
    for row in value['events']:
        eid = row['event_id']
        if eid in ids or eid in aliases:
            raise ValueError(f'Duplicate event identity: {eid}')
        ids.add(eid)
        for alias in row['aliases']:
            if alias in ids or alias in aliases:
                raise ValueError(f'Duplicate event alias: {alias}')
            aliases.add(alias)
        for link in row['relations']:
            expected = place_ids if link['kind'].endswith('place') else store_ids
            if expected is not None and link['entity_id'] not in expected:
                raise ValueError(f"Unresolved news relationship: {link['entity_id']}")
            if link['distance_km'] is not None and (link['distance_km'] < 0 or link['kind'] != 'area_store'):
                raise ValueError('Distance belongs only to an area-store relationship')
        if row['scope'] == 'location' and not row['relations']:
            raise ValueError('Location news needs an explicit relationship')
        for revision in row['versions']:
            rid = revision['revision_id']
            if rid in revisions:
                raise ValueError(f'Duplicate revision: {rid}')
            revisions.add(rid)
            source_ids = [x['source_id'] for x in revision['sources']]
            if len(set(source_ids)) != len(source_ids):
                raise ValueError('Duplicate source ID in revision')
            for fact in revision['statements']:
                if not set(fact['source_ids']) <= set(source_ids):
                    raise ValueError('Statement has unknown source')
                if fact['kind'] == 'source_report' and not fact['source_ids']:
                    raise ValueError('Attributed report needs a source')
            for observation in revision['metrics']:
                if observation['source_id'] not in source_ids:
                    raise ValueError('Metric has unknown source')
    for row in value['events']:
        if row['parent_event_id'] and (row['parent_event_id'] not in ids or row['parent_event_id'] == row['event_id']):
            raise ValueError('Invalid parent event')
    parents = {row['event_id']: row['parent_event_id'] for row in value['events']}
    for eid in parents:
        seen, current = set(), eid
        while current:
            if current in seen:
                raise ValueError('Parent event cycle')
            seen.add(current); current = parents[current]
    for attempt in value['checks']:
        if attempt['last_success_at'] and attempt['last_success_at'] > attempt['attempted_at']:
            raise ValueError('Successful check cannot follow the attempt')
        if attempt['status'] != 'retrieved' and attempt['last_success_at'] == attempt['attempted_at']:
            raise ValueError('Failed/partial check cannot mark a source current')
    return value
