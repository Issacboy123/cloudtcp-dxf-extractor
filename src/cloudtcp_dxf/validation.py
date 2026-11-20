"""The packaged IF contract and additional document relationship checks."""
from functools import lru_cache
from importlib.resources import files
import json
from math import isfinite
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker


class ConversionError(ValueError):
    """Conversion failed; ``report`` remains available to library and CLI callers."""

    def __init__(self, message, report):
        super().__init__(message)
        self.report = report


def pointer(parts):
    return "/" + "/".join(str(p).replace("~", "~0").replace("/", "~1") for p in parts)


def issue(reason, path, severity="error", source=None):
    result = {"severity": severity, "reason": reason, "path": path}
    if source is not None:
        result["source"] = source
    return result


@lru_cache(maxsize=1)
def if_validator():
    schema = json.loads(files("cloudtcp_dxf").joinpath("tcp-intermediate-format.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def finite_issues(value, path=()):
    """JSON Schema's number type alone does not exclude Python NaN/infinity."""
    if isinstance(value, float) and not isfinite(value):
        yield issue("Numbers must be finite", pointer(path))
    elif isinstance(value, dict):
        for key, child in value.items():
            yield from finite_issues(child, (*path, key))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from finite_issues(child, (*path, index))


def element_issues(element):
    validator = if_validator()
    variants = validator.schema["properties"]["elements"]["items"]["oneOf"]
    variant = next((v for v in variants if v["properties"]["type"]["const"] == element.get("type")), None)
    if variant is None:
        return [issue("Unsupported mapping type", "/type")]
    return [issue(e.message, pointer(e.absolute_path)) for e in validator.descend(element, variant)] + list(finite_issues(element))


def document_issues(document, schema_path=None):
    validator = if_validator()
    errors = [issue(e.message, pointer(e.absolute_path)) for e in validator.iter_errors(document)]
    errors.extend(finite_issues(document))
    if errors:
        return errors
    errors.extend(relationship_issues(document))
    if schema_path is not None:
        schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        extra = Draft202012Validator(schema, format_checker=FormatChecker())
        errors.extend(issue(e.message, pointer(e.absolute_path)) for e in extra.iter_errors(document))
    return errors


def relationship_issues(document):
    results = []
    zones = document["zones"]
    zone_ids = {z["zone_id"] for z in zones}
    for collection, key in (("zones", "zone_id"), ("elements", "element_id"), ("observations", "obs_id")):
        seen = set()
        for index, entry in enumerate(document.get(collection, [])):
            value = entry[key]
            path = pointer((collection, index))
            if value in seen:
                results.append(issue(f"Duplicate {key}: {value}", f"{path}/{key}"))
            seen.add(value)
            if "zone_id" in entry and collection != "zones" and entry["zone_id"] not in zone_ids:
                results.append(issue(f"Unknown zone_id: {entry['zone_id']}", f"{path}/zone_id"))

    for index, zone in enumerate(zones):
        path = pointer(("zones", index))
        if zone["end_station"] < zone["start_station"]:
            results.append(issue("Zone end_station precedes start_station", path))
        if index and zone["start_station"] < zones[index - 1]["start_station"]:
            results.append(issue("Zones must be in increasing start_station order", path))
        if any(zone["start_station"] < prior["end_station"] and zone["end_station"] > prior["start_station"] for prior in zones[:index]):
            results.append(issue("Zone station ranges overlap", path, "warning"))

    by_id = {z["zone_id"]: z for z in zones}
    for collection in ("elements", "observations"):
        for index, entry in enumerate(document.get(collection, [])):
            zone = by_id.get(entry.get("zone_id"))
            if zone is None:
                continue
            if "position" in entry:
                stations = [entry["position"]["station"]]
            elif "station" in entry:
                stations = [entry["station"]]
            else:
                stations = [entry["start_station"], entry["end_station"]]
            if any(s < zone["start_station"] or s > zone["end_station"] for s in stations):
                results.append(issue("Placement outside assigned zone bounds", pointer((collection, index)), "warning", entry.get("source") if collection == "elements" else None))

    traffic = document["typical_application"]
    if traffic.get("lanes_closed", 0) > traffic["lanes_total"]:
        results.append(issue("lanes_closed exceeds lanes_total", "/typical_application/lanes_closed"))

    predictions = document.get("predictions", {})
    element_ids = {e["element_id"] for e in document["elements"]}
    for collection in ("by_zone", "recommendations"):
        for index, entry in enumerate(predictions.get(collection, [])):
            for key, ids in (("zone_id", zone_ids), ("element_id", element_ids)):
                if key in entry and entry[key] not in ids:
                    results.append(issue(f"Unknown {key}: {entry[key]}", pointer(("predictions", collection, index, key))))
    return results


def validate_if(document, schema_path=None):
    """Validate the bundled contract, relationships, and optional additional schema."""
    issues = document_issues(document, schema_path)
    errors = [i for i in issues if i["severity"] == "error"]
    if errors:
        raise ConversionError(f"IF validation failed at {errors[0]['path']}: {errors[0]['reason']}", {"issues": issues})
