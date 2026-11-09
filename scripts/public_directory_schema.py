"""Closed public directory schemas, shared by admission, projection and scanning.

Schemas select every emitted field, including nested receipts and native IDs.
Dates retain publisher precision and representation; validation never refreshes them.
URL checks are offline syntax/address checks, not proof of publisher ownership.
"""
from datetime import date, datetime, timezone
import ipaddress
import json
import math
import re
from urllib.parse import unquote, urlsplit


PRIVATE_REFERENCE = re.compile(
    r"(?:(?:^|[\s\"'=])/(?:Users|home)/|file://|[A-Za-z]:\\Users\\|"
    r"\b(?:bn-target|private-research|private-corridor|private-place)-)", re.I
)


def decode_json(source):
    """Do not let a later duplicate key hide content in a published raw file."""
    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"Duplicate public JSON key: {key}")
            result[key] = value
        return result
    return json.loads(source, object_pairs_hook=unique_object)


def public_text(value):
    if not isinstance(value, str):
        raise ValueError("Expected public text")
    # Decode URL-encoded paths/identifiers as well, without changing the evidence.
    decoded = value
    for _ in range(3):
        decoded = unquote(decoded)
    if PRIVATE_REFERENCE.search(decoded):
        raise ValueError("Private source identifier or local path in public evidence")
    return value


def text(value):
    public_text(value)
    if not value.strip():
        raise ValueError("Required public text is empty")
    return value


def source_url(value):
    text(value)
    if re.search(r"[\x00-\x20\x7f\\]", value):
        raise ValueError("Invalid public source URL")
    try:
        p = urlsplit(value)
        host = (p.hostname or "").rstrip(".").encode("idna").decode("ascii").lower()
        port = p.port
        if p.scheme != "https" or not host or "%" in host or p.username is not None or p.password is not None:
            raise ValueError("Public evidence requires an attributed HTTPS source")
        if port is not None and port != 443:
            raise ValueError("Public evidence requires the standard HTTPS port")
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            # Exclude local names and browser-interpreted numeric IP aliases.
            labels = host.split(".")
            if (len(labels) < 2 or labels[-1] in {"localhost", "local", "localdomain", "internal", "intranet", "lan", "home", "test", "invalid"}
                    or host.endswith(".home.arpa")
                    or any(not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label) for label in labels)
                    or re.fullmatch(r"(?:0x[0-9a-f]+|[0-9]+)", labels[-1])):
                raise ValueError("Source host must be public")
        else:
            mapped = getattr(address, "ipv4_mapped", None)
            if (not address.is_global or address.is_multicast or address.is_reserved
                    or (mapped is not None and not mapped.is_global)):
                raise ValueError("Non-public IP address in public source URL")
    except (UnicodeError, ValueError) as error:
        raise ValueError("Invalid or non-public HTTPS source") from error
    return value


def iso_date(value, partial=False):
    text(value)
    try:
        if partial and re.fullmatch(r"\d{4}-\d{2}", value):
            date.fromisoformat(value + "-01")
        elif re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            date.fromisoformat(value)
        elif re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?", value):
            datetime.fromisoformat(value.replace("Z", "+00:00"))
        else:
            raise ValueError("Expected ISO date or timestamp")
    except ValueError as error:
        raise ValueError("Invalid evidence date") from error
    return value


def publication_date(value):
    return iso_date(value, partial=True)


def publisher_updated(value):
    # Some publisher APIs expose native Unix milliseconds. Preserve them as-is.
    if type(value) is int:
        try:
            if value < 0:
                raise ValueError("Negative publisher timestamp")
            datetime.fromtimestamp(value / 1000, timezone.utc)
        except (ValueError, OverflowError, OSError) as error:
            raise ValueError("Invalid publisher timestamp") from error
        return value
    return iso_date(value)


def count(value):
    if type(value) is not int or value < 0:
        raise ValueError("Expected non-negative integer count")
    return value


def boolean(value):
    if type(value) is not bool:
        raise ValueError("Expected boolean")
    return value


def number(value):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError("Expected finite coordinate")
    return value


def native_id(value):
    if type(value) is int:
        return count(value)
    return public_text(value)


def nullable(check):
    return lambda value: None if value is None else check(value)


def array(check, nonempty=False):
    def validate(value):
        if not isinstance(value, list) or (nonempty and not value):
            raise ValueError("Expected evidence list")
        return [check(item) for item in value]
    return validate


def object_schema(fields, required=()):
    def project(value):
        if not isinstance(value, dict):
            raise ValueError("Expected evidence object")
        unexpected = set(value) - fields.keys()
        missing = set(required) - value.keys()
        if unexpected or missing:
            raise ValueError(f"Invalid public evidence fields: unexpected={sorted(unexpected)}, missing={sorted(missing)}")
        result = {}
        # Iterate schema fields, never copy an input object wholesale.
        for field, check in fields.items():
            if field in value:
                try:
                    result[field] = check(value[field])
                except ValueError as error:
                    raise ValueError(f"{field}: {error}") from error
        return result
    return project


IDENTITY_SOURCE_FIELDS = {
    "url": source_url, "observed_at": iso_date,
    "source_date": nullable(publication_date), "reviewed_at": iso_date,
}
identity_source = object_schema(IDENTITY_SOURCE_FIELDS, ("url", "observed_at"))
PREVIOUS_RECORD_FIELDS = {
    **{k: public_text for k in ("name", "address", "listing_status", "scope_status")},
    "source_id": text, "source_url": source_url,
}
previous_record = object_schema(PREVIOUS_RECORD_FIELDS)
HISTORY_FIELDS = {
    **{k: public_text for k in ("address", "basis", "displayed_address", "displayed_name", "listing_status", "name", "scope_status")},
    "observed_at": iso_date, "source_url": source_url, "previous_record": previous_record,
}
history = object_schema(HISTORY_FIELDS, ("observed_at",))
CATEGORY_SOURCE_FIELDS = {
    "category": text, "url": source_url, "source_url": source_url, "observed_at": iso_date,
    "crawler_age": public_text, "crawler_age_at_retrieval": public_text,
}


def category_source(value):
    result = object_schema(CATEGORY_SOURCE_FIELDS)(value)
    if not (result.get("url") or result.get("source_url")):
        raise ValueError("Category receipt requires a source URL")
    return result


native_source_object = object_schema({"page_id": native_id, "toggle_id": native_id}, ("page_id", "toggle_id"))
native_sources = object_schema({
    **{k: nullable(native_id) for k in ("table_id", "row_id", "storedetail_id")},
    "map_level_ids": array(native_id), "map_shape_ids": array(native_id),
})
RECORD_FIELDS = {
    **{k: public_text for k in (
        "role", "category_basis", "address", "listing_status_basis", "identity_review_basis",
        "ownership_evidence", "ownership_status", "independence_source_phrase", "source_id_basis",
        "source_brand", "source_type", "publisher_status", "publisher_location_reference")},
    **{k: text for k in ("source_id", "name", "scope_basis", "scope_status", "listing_status")},
    **{k: source_url for k in ("source_url", "boundary_source_url", "frontage_evidence_url")},
    "source_categories": array(public_text),
    **{k: array(text) for k in ("categories", "previous_source_ids",
                               "source_ids", "resolved_address_lead_ids")},
    **{k: text for k in ("canonical_observation_source_id", "resolved_to_source_id")},
    **{k: nullable(native_id) for k in (
        "native_store_id", "native_wordpress_id", "raw_source_external_id", "raw_source_id",
        "raw_source_slug", "raw_source_store_id", "raw_source_unit_key", "raw_source_uuid", "source_native_id")},
    "native_source_id": nullable(lambda v: native_source_object(v) if isinstance(v, dict) else native_id(v)),
    "source_native_ids": native_sources,
    "additional_source_urls": array(source_url),
    "observed_at": iso_date, "source_date": nullable(publication_date),
    "source_checked_at": nullable(iso_date), "source_updated_at": publisher_updated,
    "frontage_imagery_date": publication_date, "source_version": count,
    "current_trading_verified": boolean,
    "verification_history": array(history), "category_sources": array(category_source),
}
REQUIRED_RECORD_FIELDS = ("source_id", "name", "source_url", "observed_at", "scope_basis",
                          "scope_status", "listing_status", "categories")
record = object_schema(RECORD_FIELDS, REQUIRED_RECORD_FIELDS)
observation = object_schema({**RECORD_FIELDS, "features": array(text)}, REQUIRED_RECORD_FIELDS + ("features",))
IDENTITY_REVIEW_FIELDS = {
    **{k: public_text for k in ("place_id", "source_id", "store_id", "decision", "basis")},
    "review_date": iso_date, "source_url": source_url,
}
identity_review = object_schema(IDENTITY_REVIEW_FIELDS, IDENTITY_REVIEW_FIELDS)
GENERATED_RECORD_FIELDS = {
    **RECORD_FIELDS, "original_scope_status": public_text, "identity_review": identity_review,
    "original_role": public_text,
    "role_review": object_schema({"date": iso_date, "basis": text, "source_url": source_url},
                                ("date", "basis", "source_url")),
}
generated_record = object_schema(GENERATED_RECORD_FIELDS, REQUIRED_RECORD_FIELDS)
generated_observation = object_schema({**GENERATED_RECORD_FIELDS, "features": array(text)},
                                      REQUIRED_RECORD_FIELDS + ("features",))
ABSENCE_FIELDS = {
    **{k: text for k in ("feature_id", "label", "kind", "basis")},
    "observed_at": iso_date, "reviewed_at": iso_date, "source_url": source_url,
}
absence_review = object_schema(ABSENCE_FIELDS, ("feature_id", "label", "kind", "basis", "observed_at", "source_url"))
SAMPLE_FIELDS = {
    **{k: nullable(count) for k in ("hospitality_venues", "office_businesses", "hours_known", "hours_unknown", "activity_unresolved")},
    **{k: public_text for k in ("source", "scope", "overlap_with_other_sources")},
    **{k: nullable(iso_date) for k in ("as_of", "observed_at", "source_timestamp")},
    "source_urls": array(source_url), "source_record_refs": array(text),
    "hours": object_schema({k: count for k in ("daytime_only", "evening_only", "daytime_and_evening", "unknown")}),
}
def sample(value):
    result = object_schema(SAMPLE_FIELDS)(value)
    if (result.get("hospitality_venues") or 0) > 0 and not (result.get("as_of") or result.get("observed_at")):
        raise ValueError("Positive anonymous presence requires an observation date")
    return result


ANONYMOUS_FIELDS = {**SAMPLE_FIELDS, "additional_samples": array(sample)}


def anonymous_counts(value):
    result = object_schema(ANONYMOUS_FIELDS)(value)
    sample({k: v for k, v in result.items() if k in SAMPLE_FIELDS})
    return result
ANONYMOUS_RECEIPT_FIELDS = {
    "source_id": text, "source_urls": array(source_url, nonempty=True),
    "observed_at": iso_date, "category": text, "count": count, "basis": text,
}
generated_anonymous = object_schema({
    **ANONYMOUS_FIELDS, "evidence": array(object_schema(ANONYMOUS_RECEIPT_FIELDS, ANONYMOUS_RECEIPT_FIELDS)),
})
COVERAGE_FIELDS = {
    'research_status_label': public_text, 'trading_verification_label': public_text,
    **{k: public_text for k in ("status", "format_scope", "directory_note", "capture_method", "ownership_coverage")},
    **{k: boolean for k in ("complete", "directory_complete", "absence_eligible", "trading_verified")},
    **{k: count for k in ("captured_listings", "anonymous_records", "usable_listings", "observations", "distinct_names")},
    "source_total": nullable(count), "observed_dates": array(iso_date),
    "held_scope_records": array(text), "duplicate_source_ids": array(text),
    "source_urls": array(source_url, nonempty=True),
    "non_present_listings": array(object_schema({"name": text, "status": text}, ("name", "status"))),
}
coverage = object_schema(COVERAGE_FIELDS)


def canonical_centre(value):
    # Environment exports carry the canonical type; older companion payloads
    # carry its format only. Any contradictory canonical classification wins.
    return (value.get("format") == "Shopping Centre"
            and value.get("place_type", "Shopping Centre") == "Shopping Centre"
            and value.get("location_setting", "Shopping Centre") == "Shopping Centre")


def validate_generated_place(value):
    """Validate all directory-derived branches, including held and historical rows."""
    for row in value.get("directory_records", []):
        generated_record(row)
    for row in value.get("observations", []):
        generated_observation(row)
    for row in value.get("absence_reviews", []):
        absence_review(row)
    for reviews in value.get("absent_features", {}).values():
        for review in reviews:
            absence_review(review)
    cov = coverage(value["coverage"])
    eligible = (canonical_centre(value)
                and cov.get("format_scope") == "canonical centre"
                and cov.get("directory_complete") is True)
    if (value.get("absence_reviews") or value.get("absent_features") or cov.get("absence_eligible")) and not eligible:
        raise ValueError("Absence requires complete directory evidence for an actual centre")
    if value.get("anonymous_counts"):
        generated_anonymous(value["anonymous_counts"])
CAPTURE_FIELDS = {
    **{k: text for k in ("place_id", "capture_method", "limitations", "format_scope", "scope")},
    "records": array(record), "source_urls": array(source_url, nonempty=True),
    "source_total": nullable(count), "directory_complete": boolean,
    "absence_reviews": array(absence_review), "anonymous_counts": anonymous_counts,
    "source_record_count": count, "anonymous_record_count": count,
}
_capture = object_schema(CAPTURE_FIELDS, (
    "place_id", "records", "source_urls", "source_total", "directory_complete",
    "capture_method", "limitations", "format_scope", "scope",
))


def capture(value):
    result = _capture(value)
    records = result["records"]
    if len({r["source_id"] for r in records}) != len(records):
        raise ValueError("Duplicate source record identity")
    if result["format_scope"] not in {"canonical centre", "named street", "canonical precinct"}:
        raise ValueError("Unknown directory scope")
    total = result["source_total"]
    source_count = result.get("source_record_count", len(records))
    if source_count != len(records) + result.get("anonymous_record_count", 0):
        raise ValueError("Captured source records must reconcile to named and anonymous records")
    if total is not None and source_count > total:
        raise ValueError("Captured records exceed source total")
    if result["directory_complete"] and total != source_count:
        raise ValueError("Complete extraction must reconcile to source total")
    if result.get("absence_reviews") and (
            not result["directory_complete"] or result["format_scope"] != "canonical centre"):
        raise ValueError("Scoped absence requires an audited complete centre directory")
    return result


PLACE_FIELDS = {
    **{k: text for k in ("place_id", "name", "country", "state", "locality", "format", "scope")},
    "address": public_text, "sources": array(identity_source, nonempty=True),
    "reviewed_at": iso_date, "latitude": nullable(number), "longitude": nullable(number),
    "coordinate_source_url": nullable(source_url),
}
_place = object_schema(PLACE_FIELDS, PLACE_FIELDS)


def place(value):
    result = _place(value)
    if result["format"] not in {"Shopping Centre", "High Street"}:
        raise ValueError("Unknown public place format")
    lat, lon = result["latitude"], result["longitude"]
    if (lat is None) != (lon is None):
        raise ValueError("A map point must have both coordinates or neither")
    if lat is not None:
        try:
            from .store_rules import valid_store_point
        except ImportError:
            from store_rules import valid_store_point
        if not valid_store_point(result) or not result["coordinate_source_url"]:
            raise ValueError("Invalid or unattributed public place coordinates")
    return result


def document(value):
    result = object_schema({
        "schema_version": count, "source_basis": public_text,
        "places": array(place), "captures": array(capture),
    }, ("schema_version", "places", "captures"))(value)
    if result["schema_version"] != 1:
        raise ValueError("Unknown public directory schema")
    for field in ("places", "captures"):
        if len({r["place_id"] for r in result[field]}) != len(result[field]):
            raise ValueError(f"Duplicate public directory {field}")
    return result
