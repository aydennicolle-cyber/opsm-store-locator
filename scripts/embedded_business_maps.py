"""Resolve a named business in an operator map; never use its camera centre."""
from __future__ import annotations

import json
import math
import re
from html.parser import HTMLParser
from urllib.parse import parse_qs, unquote, urlsplit


class MapEvidenceError(ValueError):
    pass


class OperatorMaps(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = set()

    def handle_starttag(self, tag, attrs):
        if tag != "iframe":
            return
        url = dict(attrs).get("src") or ""
        parsed = urlsplit(url)
        if (parsed.scheme == "https" and parsed.hostname in {"www.google.com", "maps.google.com"}
                and parsed.path == "/maps/embed" and not parsed.username and not parsed.password):
            self.urls.add(url)


def feature_cid(feature_id):
    # Google sometimes writes the same business as 0x0:CID in an embed URL.
    if not isinstance(feature_id, str) or not re.fullmatch(r"0x[0-9a-f]+:0x[0-9a-f]+", feature_id, re.I):
        raise MapEvidenceError("Missing or invalid named business identity")
    return int(feature_id.split(":")[-1], 16)


def business_feature(page, expected_id):
    marker = re.search(r"\binitEmbed\s*\(", page)
    if not marker:
        raise MapEvidenceError("Map response has no named business payload")
    try:
        payload, _ = json.JSONDecoder().raw_decode(page[marker.end():].lstrip())
    except ValueError as exc:
        raise MapEvidenceError("Map response has an invalid business payload") from exc
    features = []

    def visit(value):
        if not isinstance(value, list):
            return
        if (len(value) > 17 and isinstance(value[0], list) and len(value[0]) > 2
                and isinstance(value[0][0], str) and value[0][0].startswith("0x")
                and isinstance(value[1], str)):
            features.append(value)
        for child in value:
            visit(child)

    visit(payload)
    if len(features) != 1:
        raise MapEvidenceError("Map must resolve exactly one named business")
    feature = features[0]
    if feature_cid(feature[0][0]) != feature_cid(expected_id):
        raise MapEvidenceError("Resolved business differs from the operator's map identity")
    if feature[17] is not None:
        raise MapEvidenceError("Map carries a closure/status flag requiring review")
    point = feature[0][2]
    if not isinstance(point, list) or len(point) != 2 or any(isinstance(v, bool) for v in point):
        raise MapEvidenceError("Named business has no unambiguous point")
    try:
        lat, lon = map(float, point)
    except (ValueError, TypeError) as exc:
        raise MapEvidenceError("Invalid named business point") from exc
    if not (math.isfinite(lat) and math.isfinite(lon)
            and -44.5 <= lat <= -9 and 112 <= lon <= 154.5):
        raise MapEvidenceError("Named business point is outside Australian bounds")
    if not feature[1].strip() or not isinstance(feature[13], str) or not feature[13].strip():
        raise MapEvidenceError("Named business lacks a name or written address")
    return dict(feature_id=feature[0][0], name=feature[1], address=feature[13],
                latitude=lat, longitude=lon)


def resolve_operator_map(profile, fetch):
    parser = OperatorMaps()
    parser.feed(profile)
    if len(parser.urls) != 1:
        raise MapEvidenceError("Operator must identify exactly one supported business map")
    url = next(iter(parser.urls))
    payload = parse_qs(urlsplit(url).query).get("pb", [])
    identities = set(re.findall(r"!1s(0x[0-9a-f]+:0x[0-9a-f]+)(?=!|$)",
                               unquote(payload[0]) if len(payload) == 1 else "", re.I))
    if len(identities) != 1:
        raise MapEvidenceError("Operator map has no unique named business identity")
    result = business_feature(fetch(url), next(iter(identities)))
    return dict(result, map_url=url, method="Operator-linked named business feature; approximate premises point")
