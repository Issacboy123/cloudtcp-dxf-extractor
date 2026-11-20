"""Conservative DXF to CloudTCP IF v1 conversion with explicit metadata and mappings."""
from collections import Counter
from copy import deepcopy
from math import hypot, isfinite

from ezdxf import units

from .extract import extract_dxf
from .validation import ConversionError, document_issues, element_issues, if_validator, issue, pointer, validate_if


SOURCE_UNITS = {"inches": 1, "feet": 2, "millimeters": 4, "centimeters": 5, "meters": 6, "yards": 10, "us_survey_feet": 21}
SUPPORTED_TYPES = {"sign", "arrow_board", "flagger"}


def _point(value):
    if not isinstance(value, (list, tuple)) or len(value) not in (2, 3):
        raise ValueError("Coordinates must contain two or three finite numbers")
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not isfinite(v) for v in value):
        raise ValueError("Coordinates must contain two or three finite numbers")
    return value


def station_offset(point, origin, endpoint, *, scale=1.0):
    point, origin, endpoint = _point(point), _point(origin), _point(endpoint)
    if not isfinite(scale) or scale <= 0:
        raise ValueError("Coordinate scale must be finite and positive")
    dx, dy = endpoint[0] - origin[0], endpoint[1] - origin[1]
    length = hypot(dx, dy)
    if length == 0:
        raise ValueError("centerline endpoints must differ")
    if not isfinite(length):
        raise ValueError("Centerline length must be finite")
    ux, uy = dx / length, dy / length
    vx, vy = point[0] - origin[0], point[1] - origin[1]
    along = (vx * ux + vy * uy) * scale
    signed = (ux * vy - uy * vx) * scale
    if not isfinite(along) or not isfinite(signed):
        raise ValueError("Projected coordinates must be finite")
    return {"station": round(along, 4), "offset": round(abs(signed), 4), "side": "left" if signed > 1e-9 else "right" if signed < -1e-9 else "center"}


def _record(report, issues):
    report["issues"].extend(issues)
    report["warnings"].extend(i["reason"] for i in issues if i["severity"] == "warning")


def _fail_if_errors(report):
    errors = [i for i in report["issues"] if i["severity"] == "error"]
    if errors:
        first = errors[0]
        raise ConversionError(f"Conversion failed at {first['path']}: {first['reason']}", report)


def _resolve_units(extraction, config, report):
    target = config["site"]["units"]
    code = extraction["source"].get("drawing_units_code", 0)
    override = config.get("source_units")
    if "source_units" in config:
        if not isinstance(override, str) or override not in SOURCE_UNITS:
            _record(report, [issue(f"source_units must be one of: {', '.join(SOURCE_UNITS)}", "/source_units")])
            _fail_if_errors(report)
        code = SOURCE_UNITS[override]
    factor = None
    if isinstance(code, int) and not isinstance(code, bool) and 21 <= code <= 24:
        # ezdxf has no conversion factors for the DXF US survey unit codes.
        survey_foot_meters = 1200 / 3937
        meters = survey_foot_meters * {21: 1, 22: 1 / 12, 23: 3, 24: 5280}[code]
        factor = meters / (0.3048 if target == "feet" else 1)
    elif isinstance(code, int) and not isinstance(code, bool) and 1 <= code <= 20:
        try:
            factor = units.conversion_factor(code, SOURCE_UNITS[target])
        except (ValueError, TypeError, IndexError, ZeroDivisionError):
            pass
    assumed = factor is None or not isfinite(factor) or factor <= 0
    report["units"] = {
        "drawing_units_code": extraction["source"].get("drawing_units_code", 0),
        "source_units_override": override,
        "resolved_source_units_code": None if assumed else code,
        "target_units": target,
        "scale": 1.0 if assumed else factor,
        "assumed": assumed,
    }
    if assumed:
        _record(report, [issue(f"Source units unavailable or unsupported; assuming source coordinates use site.units ({target}) with scale 1", "/source/drawing_units_code", "warning")])
    return report["units"]["scale"]


def _mapping_issues(mapping, zone_ids):
    if not isinstance(mapping, dict):
        return [issue("Mapping must be an object", "")]
    if not isinstance(mapping.get("type"), str) or mapping["type"] not in SUPPORTED_TYPES:
        return [issue(f"Unsupported mapping type: {mapping.get('type')}", "/type")]
    variants = if_validator().schema["properties"]["elements"]["items"]["oneOf"]
    variant = next(v for v in variants if v["properties"]["type"]["const"] == mapping["type"])
    allowed = set(variant["properties"]) - {"element_id", "position", "source"}
    issues = [issue(f"Field is not configurable for {mapping['type']}: {key}", pointer((key,))) for key in mapping if key not in allowed]
    probe = {**mapping, "element_id": "mapping", "position": {"station": 0, "offset": 0, "side": "center"}}
    issues.extend(element_issues(probe))
    if isinstance(mapping.get("zone_id"), str) and mapping["zone_id"] not in zone_ids:
        issues.append(issue(f"Unknown zone_id: {mapping['zone_id']}", "/zone_id"))
    return issues


def convert_extraction(extraction, config):
    report = {
        "source": extraction["source"], "converted_elements": 0,
        "unmapped_blocks": {}, "skipped_mappings": {},
        "skipped_elements": 0, "unmapped_elements": 0,
        "unsupported_geometry_counts": extraction["log"]["unsupported_geometry_counts"],
        "warnings": list(extraction["log"].get("warnings", [])), "issues": [],
        "limitations": [
            "Only named block INSERTs mapped as sign, arrow_board or flagger are converted; flattened symbols are not detected.",
            "Stationing uses a configured straight reference line, not a curved road centerline.",
            "Cone sequences, road/basemap geometry, references and CAD round-trip are not implemented.",
            "Site traffic facts and zone boundaries are supplied by configuration rather than guessed."
        ]
    }
    if not isinstance(config, dict):
        _record(report, [issue("Configuration must be an object", "/")])
        _fail_if_errors(report)
    for key in ("site", "typical_application", "zones", "centerline"):
        if key not in config:
            _record(report, [issue(f"Missing required configuration: {key}", pointer((key,)))])
    if "predictions" in config:
        _record(report, [issue("predictions are model-owned and cannot be authored by this converter", "/predictions")])
    _fail_if_errors(report)
    document = {"format_version": "1.0.0", **{k: deepcopy(config[k]) for k in ("site", "typical_application", "zones")}, "elements": []}
    if isinstance(document["site"], dict):
        document["site"].setdefault("source_file", extraction["source"]["filename"])
        document["site"].setdefault("source_format", "DXF")
    for key in ("temporal_context", "observations"):
        if key in config:
            document[key] = deepcopy(config[key])
    _record(report, document_issues(document))
    _fail_if_errors(report)
    line = config["centerline"]
    try:
        if not isinstance(line, dict) or "origin" not in line or "endpoint" not in line:
            raise ValueError("centerline requires origin and endpoint")
        station_offset(line["origin"], line["origin"], line["endpoint"])
    except ValueError as exc:
        _record(report, [issue(str(exc), "/centerline")])
        _fail_if_errors(report)
    scale = _resolve_units(extraction, config, report)
    mappings = config.get("block_mappings", {})
    if not isinstance(mappings, dict):
        _record(report, [issue("block_mappings must be an object", "/block_mappings")])
        _fail_if_errors(report)
    if any(not isinstance(key, str) for key in mappings):
        _record(report, [issue("Block mapping names must be strings", "/block_mappings")])
        _fail_if_errors(report)
    names = [key.casefold() for key in mappings]
    if len(set(names)) != len(names):
        _record(report, [issue("Block mapping names must be unique ignoring case", "/block_mappings")])
        _fail_if_errors(report)
    zone_ids = {z["zone_id"] for z in document["zones"]}
    prepared = {}
    for name, mapping in mappings.items():
        issues = _mapping_issues(mapping, zone_ids)
        path = pointer(("block_mappings", name))
        prepared[name.casefold()] = (mapping, path, issues)
        _record(report, [{**i, "severity": "warning", "path": path + i["path"]} for i in issues])

    unmapped, skipped = Counter(), Counter()
    for index, entity in enumerate(extraction["entities"]):
        if entity["type"] != "INSERT":
            continue
        block = entity.get("block_name", "")
        match = prepared.get(block.casefold())
        if match is None:
            unmapped[block] += 1
            continue
        mapping, mapping_path, mapping_errors = match
        source = {"layer": entity["layer"], "entity": "INSERT", "handle": entity["handle"], "block": block}
        if mapping_errors:
            report["skipped_elements"] += 1
            skipped[mapping_errors[0]["reason"]] += 1
            _record(report, [{**i, "severity": "warning", "path": mapping_path + i["path"], "source": source} for i in mapping_errors])
            continue
        try:
            position = station_offset(entity["geometry"]["insert"], line["origin"], line["endpoint"], scale=scale)
            data = {**deepcopy(mapping), "element_id": f"CAD_{entity['handle']}", "position": position, "source": source}
            issues = element_issues(data)
        except (ValueError, KeyError, TypeError) as exc:
            issues = [issue(str(exc), "/geometry/insert")]
        if issues:
            report["skipped_elements"] += 1
            skipped[issues[0]["reason"]] += 1
            _record(report, [{**i, "severity": "warning", "path": pointer(("entities", index)) + i["path"], "source": source} for i in issues])
        else:
            document["elements"].append(data)
    report["converted_elements"] = len(document["elements"])
    report["unmapped_blocks"] = dict(sorted(unmapped.items()))
    report["unmapped_elements"] = sum(unmapped.values())
    report["skipped_mappings"] = dict(sorted(skipped.items()))
    # Metadata was checked before mapping; append only newly discovered issues.
    _record(report, [i for i in document_issues(document) if i not in report["issues"]])
    if unmapped:
        _record(report, [issue("Unmapped block inserts detected", "/entities", "warning")])
    if not document["elements"]:
        _record(report, [issue("No elements were converted", "/elements", "warning")])
    _fail_if_errors(report)
    return document, report


def convert_dxf(path, config):
    return convert_extraction(extract_dxf(path), config)
