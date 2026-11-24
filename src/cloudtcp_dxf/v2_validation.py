"""Independent CloudTCP 2.0.0 validation. No rule execution or evidence ranking."""

import json
from copy import deepcopy
from datetime import datetime
from functools import lru_cache
from importlib.resources import files
from math import hypot, isclose, isfinite

from jsonschema import Draft202012Validator, FormatChecker

from .validation import ConversionError


def pointer(parts):
    return "".join("/" + str(p).replace("~", "~0").replace("/", "~1") for p in parts)


def diagnostic(layer, code, path, message, related_refs=None, severity="error"):
    result = dict(layer=layer, code=code, path=path, message=message, severity=severity)
    if related_refs:
        result["related_refs"] = list(related_refs)
    return result


class V2ValidationError(ConversionError):
    """Machine-readable diagnostics, also compatible with existing conversion callers."""

    def __init__(self, diagnostics):
        self.diagnostics = diagnostics
        first = diagnostics[0]
        super().__init__(
            f"V2 validation failed at {first['path']}: {first['message']}",
            {
                "diagnostics": diagnostics,
                "issues": [{**d, "reason": d["message"]} for d in diagnostics],
            },
        )


@lru_cache(maxsize=1)
def v2_validator():
    schema = json.loads(
        files("cloudtcp_dxf").joinpath("schemas/2.0.0/schema.json").read_text()
    )
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def json_diagnostics(value, path=()):
    if isinstance(value, float) and not isfinite(value):
        yield diagnostic("json", "non_finite", pointer(path), "Numbers must be finite")
    elif isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str):
                yield diagnostic(
                    "json",
                    "invalid_key",
                    pointer(path),
                    "JSON object keys must be strings",
                )
            yield from json_diagnostics(child, (*path, key))
    elif isinstance(value, list):
        for i, child in enumerate(value):
            yield from json_diagnostics(child, (*path, i))
    elif value is not None and not isinstance(value, (str, int, float, bool)):
        yield diagnostic(
            "json", "invalid_type", pointer(path), "Value is not a JSON value"
        )


def resolve(schema):
    while "$ref" in schema:
        schema = {
            **v2_validator().schema["$defs"][schema["$ref"].split("/")[-1]],
            **{k: v for k, v in schema.items() if k != "$ref"},
        }
    return schema


def schema_nodes(value, schema, path=()):
    """Visit the active schema branches, including reference target annotations."""
    schema = resolve(schema)
    yield value, schema, path
    for keyword in ("oneOf", "anyOf", "allOf"):
        for branch in schema.get(keyword, []):
            if keyword == "allOf" or v2_validator().evolve(schema=branch).is_valid(
                value
            ):
                yield from schema_nodes(value, branch, path)
    if "if" in schema:
        branch = (
            "then"
            if v2_validator().evolve(schema=schema["if"]).is_valid(value)
            else "else"
        )
        yield from schema_nodes(value, schema.get(branch, {}), path)
    if isinstance(value, dict):
        for key, child in value.items():
            if key in schema.get("properties", {}):
                yield from schema_nodes(child, schema["properties"][key], (*path, key))
    if isinstance(value, list) and "items" in schema:
        for i, child in enumerate(value):
            yield from schema_nodes(child, schema["items"], (*path, i))


def _structural_errors(error):
    # Show errors within the supplied discriminated variant rather than every other kind.
    if error.validator == "oneOf" and isinstance(error.instance, dict):
        choices = error.schema["oneOf"]
        matching = []
        for i, choice in enumerate(choices):
            props = resolve(choice).get("properties", {})
            discriminators = {k: p["const"] for k, p in props.items() if "const" in p}
            if discriminators and all(
                error.instance.get(k) == v for k, v in discriminators.items()
            ):
                matching.append(i)
        if len(matching) == 1:
            for child in error.context:
                if child.schema_path[0] == matching[0]:
                    yield from _structural_errors(child)
            return
    yield diagnostic(
        "structure",
        "schema_" + str(error.validator),
        pointer(error.absolute_path),
        error.message,
    )


def structural_diagnostics(document):
    errors = list(json_diagnostics(document))
    if errors:
        return errors
    for error in v2_validator().iter_errors(document):
        errors.extend(_structural_errors(error))
    return errors


def at_pointer(value, path):
    """Resolve RFC 6901; array indices have their canonical decimal spelling."""
    if path == "":
        return value
    if not path.startswith("/"):
        raise KeyError(path)
    import re

    if re.search(r"~(?![01])", path):
        raise KeyError(path)
    for token in path[1:].split("/"):
        token = token.replace("~1", "/").replace("~0", "~")
        if isinstance(value, list):
            if (
                not token.isascii()
                or not token.isdigit()
                or (len(token) > 1 and token[0] == "0")
            ):
                raise KeyError(token)
            value = value[int(token)]
        elif isinstance(value, dict):
            value = value[token]
        else:
            raise KeyError(token)
    return value


# SI conversion constants; these are mathematics, not policy tolerances.
UNITS = {
    "m": ("length", 1),
    "ft": ("length", 0.3048),
    "in": ("length", 0.0254),
    "m2": ("area", 1),
    "ft2": ("area", 0.09290304),
    "in2": ("area", 0.00064516),
    "mph": ("speed", 0.44704),
    "km/h": ("speed", 1 / 3.6),
    "m/s": ("speed", 1),
    "s": ("duration", 1),
    "min": ("duration", 60),
    "h": ("duration", 3600),
    "deg": ("angle", 1),
    "ratio": ("ratio", 1),
    "%": ("ratio", 0.01),
    "veh/h": ("flow", 1),
    "Hz": ("frequency", 1),
    "flashes/min": ("frequency", 1 / 60),
}


def convert_quantity(quantity, unit):
    dimension, factor = UNITS[quantity["unit"]]
    target_dimension, target_factor = UNITS[unit]
    if dimension != target_dimension:
        raise ValueError("Cannot convert quantities of different dimensions")
    return quantity["value"] * factor / target_factor


def _instant(value):
    return datetime.fromisoformat(value.upper().replace("Z", "+00:00"))


def _cycles(graph):
    visited, active = set(), set()
    for start in graph:
        stack = [(start, False)]
        while stack:
            node, leaving = stack.pop()
            if leaving:
                active.discard(node)
                visited.add(node)
            elif node in active:
                yield node
            elif node not in visited:
                active.add(node)
                stack.append((node, True))
                stack.extend((child, False) for child in graph.get(node, []))


def _cross(a, b, c):
    return (b["x"] - a["x"]) * (c["y"] - a["y"]) - (b["y"] - a["y"]) * (c["x"] - a["x"])


def _on(a, b, c):
    return (
        _cross(a, b, c) == 0
        and min(a["x"], b["x"]) <= c["x"] <= max(a["x"], b["x"])
        and min(a["y"], b["y"]) <= c["y"] <= max(a["y"], b["y"])
    )


def _intersects(a, b, c, d):
    p, q, r, s = _cross(a, b, c), _cross(a, b, d), _cross(c, d, a), _cross(c, d, b)
    return (p * q < 0 and r * s < 0) or any(
        (_on(a, b, c), _on(a, b, d), _on(c, d, a), _on(c, d, b))
    )


def _inside(point, ring):
    odd = False
    for a, b in zip(ring, ring[1:]):
        if _on(a, b, point):
            return False
        if (a["y"] > point["y"]) != (b["y"] > point["y"]):
            if (
                point["x"]
                < (b["x"] - a["x"]) * (point["y"] - a["y"]) / (b["y"] - a["y"]) + a["x"]
            ):
                odd = not odd
    return odd


def semantic_diagnostics(document):
    """Check supplied consistency; call after structural validation succeeds."""
    errors, index, record_paths, categories = [], {}, {}, {}

    def add(code, path, message, refs=None, layer="semantic"):
        errors.append(diagnostic(layer, code, path, message, refs))

    collections = {
        "reference_frames": "frame",
        "phases": "phase",
        "entities": "entity",
        "evidence": "evidence",
        "assertions": "assertion",
        "completeness": "completeness",
        "decisions": "decision",
        "observations": "observation",
        "predictions": "prediction",
        "legacy_records": "legacy_record",
    }
    for collection, category in collections.items():
        for i, record in enumerate(document.get(collection, [])):
            rid, path = record["id"], pointer((collection, i))
            if rid in index:
                add(
                    "duplicate_id",
                    path + "/id",
                    f"Duplicate ID: {rid}",
                    [rid],
                    "reference",
                )
            else:
                index[rid], record_paths[rid], categories[rid] = record, path, category
    nodes = list(schema_nodes(document, v2_validator().schema))
    for value, schema, path in nodes:
        if "x-targets" not in schema:
            continue
        target = index.get(value)
        if target is None:
            add(
                "dangling_reference",
                pointer(path),
                f"Unknown reference: {value}",
                [value],
                "reference",
            )
            continue
        category = categories[value]
        labels = {category}
        if category == "entity":
            labels.add(target["kind"])
            if target["kind"] == "device":
                labels.add("device:" + target["device_type"])
            if target["kind"] == "marking":
                labels.add("marking:" + target["marking_type"])
        elif category == "frame":
            labels.add("frame:" + target["kind"])
        elif category == "observation":
            labels.add("observation:" + target["metric"])
        if not labels.intersection(schema["x-targets"]):
            add(
                "wrong_target_kind",
                pointer(path),
                f"Expected {' or '.join(schema['x-targets'])}; got {sorted(labels)}",
                [value],
                "reference",
            )
    # Prevent dependent checks from interpreting invalid references as valid typed records.
    if errors:
        return errors

    def same_frames(value, path):
        frames = set()

        def collect(v):
            if isinstance(v, dict):
                if "frame_ref" in v:
                    frames.add(v["frame_ref"])
                for child in v.values():
                    collect(child)
            elif isinstance(v, list):
                for child in v:
                    collect(child)

        collect(value)
        if len(frames) > 1:
            add(
                "mixed_frames",
                path,
                "Geometry primitive must use one frame",
                sorted(frames),
            )
        return frames

    def disputed(rid, path):
        return any(
            a["subject_ref"] == rid
            and a["status"] in ("disputed", "withdrawn")
            and (path == a["path"] or path.startswith(a["path"] + "/"))
            for a in document["assertions"]
        )

    # Walk only typed geometry; arbitrary preserved JSON is never interpreted as plan facts.
    for value, schema, parts in nodes:
        if not isinstance(value, dict) or schema.get("type") != "object":
            continue
        path = pointer(parts)
        if "start_station" in value and "end_station" in value and "frame_ref" in value:
            if value["end_station"] < value["start_station"]:
                add("reversed_range", path, "end_station precedes start_station")
            if (
                value.get("left_offset", 0) < value.get("right_offset", 0)
                and "left_offset" in value
                and "right_offset" in value
            ):
                add(
                    "reversed_offsets",
                    path,
                    "left_offset must be at least right_offset",
                )
        if "points" in value:
            same_frames(value, path)
        if "station_offsets" in value:
            same_frames(value["station_offsets"], path + "/station_offsets")
        if "start_location" in value and "end_location" in value:
            same_frames([value["start_location"], value["end_location"]], path)
        if "rings" in value:
            rings = value["rings"]
            same_frames(value, path)
            for i, ring in enumerate(rings):
                rp = path + "/rings/" + str(i)
                if ring[0] != ring[-1]:
                    add("unclosed_ring", rp, "Ring must be closed")
                segments = list(zip(ring, ring[1:]))
                if any(a == b for a, b in segments):
                    add("degenerate_ring", rp, "Ring has a zero-length edge")
                if sum(a["x"] * b["y"] - b["x"] * a["y"] for a, b in segments) == 0:
                    add("degenerate_ring", rp, "Ring has zero area")
                for j, (a, b) in enumerate(segments):
                    for k, (c, d) in enumerate(segments[:j]):
                        if j == k + 1 or (k == 0 and j == len(segments) - 1):
                            # Adjacent edges may meet only at their common endpoint.
                            if any(
                                _on(u, v, w) and w != u and w != v
                                for u, v, w in (
                                    (a, b, c),
                                    (a, b, d),
                                    (c, d, a),
                                    (c, d, b),
                                )
                            ):
                                add(
                                    "self_intersection",
                                    rp,
                                    "Adjacent ring edges overlap",
                                )
                            continue
                        if _intersects(a, b, c, d):
                            add("self_intersection", rp, "Ring self-intersects")
                if i and not _inside(ring[0], rings[0]):
                    add("invalid_hole", rp, "Hole is outside the exterior ring")
                for prior in rings[:i]:
                    if any(
                        _intersects(a, b, c, d)
                        for a, b in segments
                        for c, d in zip(prior, prior[1:])
                    ):
                        add("ring_intersection", rp, "Polygon rings intersect")
                if i > 1 and any(
                    _inside(ring[0], prior) or _inside(prior[0], ring)
                    for prior in rings[1:i]
                ):
                    add("invalid_hole", rp, "Polygon holes overlap or nest")
        for start, end in [("start_at", "end_at"), ("valid_from", "valid_to")]:
            if (
                start in value
                and end in value
                and _instant(value[end]) < _instant(value[start])
            ):
                add("reversed_interval", path + "/" + end, f"{end} precedes {start}")

    graphs = {"phase": {}, "sign": {}, "facility": {}, "observation": {}}
    for rid, record in index.items():
        path, category = record_paths[rid], categories[rid]
        if (
            category == "frame"
            and record["kind"] == "station"
            and "alignment_ref" in record
        ):
            if index[record["alignment_ref"]]["frame_ref"] != rid:
                add(
                    "alignment_frame",
                    path + "/alignment_ref",
                    "Alignment belongs to a different station frame",
                )
        if category == "phase":
            graphs["phase"][rid] = record.get("predecessor_refs", [])
            for predecessor in record.get("predecessor_refs", []):
                prior = index[predecessor]
                if (
                    "end_at" in prior
                    and "start_at" in record
                    and _instant(prior["end_at"]) > _instant(record["start_at"])
                ):
                    add(
                        "phase_order",
                        path + "/predecessor_refs",
                        "Predecessor ends after this phase starts",
                        [predecessor],
                    )
            times = [_instant(a["at"]) for a in record.get("actions", []) if "at" in a]
            if any(a > b for a, b in zip(times, times[1:])):
                add(
                    "action_order",
                    path + "/actions",
                    "Action timestamps contradict declared order",
                )
            for i, action in enumerate(record.get("actions", [])):
                if "at" in action and (
                    (
                        "start_at" in record
                        and _instant(action["at"]) < _instant(record["start_at"])
                    )
                    or (
                        "end_at" in record
                        and _instant(action["at"]) > _instant(record["end_at"])
                    )
                ):
                    add(
                        "action_interval",
                        path + f"/actions/{i}/at",
                        "Action lies outside the phase interval",
                    )
            if all(k in record for k in ("duration", "start_at", "end_at")):
                actual = (
                    _instant(record["end_at"]) - _instant(record["start_at"])
                ).total_seconds()
                if not isclose(
                    convert_quantity(record["duration"], "s"),
                    actual,
                    rel_tol=1e-12,
                    abs_tol=1e-12,
                ) and not disputed(rid, "/duration"):
                    add(
                        "duration_mismatch",
                        path + "/duration",
                        "Duration differs from supplied timestamps; retain differing evidence as disputed",
                    )
        if category == "assertion":
            subject = index[record["subject_ref"]]
            try:
                at_pointer(subject, record["path"])
            except (KeyError, IndexError, ValueError):
                add(
                    "invalid_pointer",
                    path + "/path",
                    "Assertion pointer does not select an existing field",
                    [record["subject_ref"]],
                    "reference",
                )
                continue
            if (
                record.get("alternatives")
                and record["status"] == "supported"
                and "decision_ref" not in record
            ):
                add(
                    "unresolved_alternatives",
                    path + "/status",
                    "Supported alternatives require an explicit resolution decision",
                )
            if "decision_ref" in record:
                decision = index[record["decision_ref"]]
                if (
                    rid not in decision["subject_refs"]
                    and record["subject_ref"] not in decision["subject_refs"]
                ):
                    add(
                        "decision_scope",
                        path + "/decision_ref",
                        "Resolution decision must identify this assertion or its subject",
                    )
            for i, alternative in enumerate(record.get("alternatives", [])):
                target_collection = next(
                    k
                    for k, v in collections.items()
                    if v == categories[record["subject_ref"]]
                )
                subject_schema = v2_validator().schema["properties"][target_collection][
                    "items"
                ]
                candidate = deepcopy(subject)
                if record["path"] == "":
                    candidate = alternative["value"]
                else:
                    tokens = record["path"].split("/")
                    parent = at_pointer(candidate, "/".join(tokens[:-1]))
                    token = tokens[-1].replace("~1", "/").replace("~0", "~")
                    parent[int(token) if isinstance(parent, list) else token] = (
                        alternative["value"]
                    )
                if not v2_validator().evolve(schema=subject_schema).is_valid(candidate):
                    add(
                        "alternative_type",
                        path + f"/alternatives/{i}/value",
                        "Alternative does not match the selected field contract",
                    )
            scope = record["scope"].get("phase_refs", [])
            if "phase_refs" in subject and any(
                p not in subject["phase_refs"] for p in scope
            ):
                add(
                    "assertion_phase_scope",
                    path + "/scope",
                    "Assertion phases are outside declared subject phases",
                )
        if category == "observation":
            graphs["observation"][rid] = [
                r
                for r in record.get("input_refs", [])
                if categories[r] == "observation"
            ]
            _check_derivation(record, path, index, add)
        if (
            category == "completeness"
            and record["state"] == "complete"
            and record.get("excluded_source_refs")
        ):
            add(
                "incomplete_acquisition",
                path + "/state",
                "Known excluded source portions require partial scope",
            )
        if category == "completeness":
            for subject_ref in record["scope"]["subject_refs"]:
                subject = index[subject_ref]
                if "phase_refs" in subject and any(
                    phase not in subject["phase_refs"]
                    for phase in record["scope"]["phase_refs"]
                ):
                    add(
                        "completeness_phase_scope",
                        path + "/scope/phase_refs",
                        "Inventory phases are outside declared subject phases",
                        [subject_ref],
                    )
        if category == "observation" and "phase_refs" in record:
            for subject_ref in record["subject_refs"]:
                subject = index[subject_ref]
                if "phase_refs" in subject and any(
                    phase not in subject["phase_refs"] for phase in record["phase_refs"]
                ):
                    add(
                        "observation_phase_scope",
                        path + "/phase_refs",
                        "Observation phases are outside declared subject phases",
                        [subject_ref],
                    )
        if category != "entity":
            continue
        kind = record["kind"]
        if kind == "facility":
            graphs["facility"][rid] = (
                [record["parent_facility_ref"]]
                if "parent_facility_ref" in record
                else []
            )
            if record.get("alternate_facility_ref") == rid:
                add(
                    "self_link",
                    path + "/alternate_facility_ref",
                    "Alternate facility cannot be itself",
                )
        if kind == "device" and record["device_type"] == "sign":
            parent = record.get("specification", {}).get("assembly_parent_ref")
            graphs["sign"][rid] = [parent] if parent else []
        if kind == "device" and record["device_type"] == "arrow_board":
            spec = record.get("specification", {})
            if spec.get("mode") == "caution" and "arrow_direction" in spec:
                add(
                    "caution_direction",
                    path + "/specification/arrow_direction",
                    "Caution mode cannot indicate an arrow direction",
                )
        mount = record.get("mount", {})
        if (
            "top_height" in mount
            and "bottom_height" in mount
            and convert_quantity(mount["top_height"], "m")
            < convert_quantity(mount["bottom_height"], "m")
        ):
            add("mount_heights", path + "/mount", "top_height precedes bottom_height")
        if kind == "device_run":
            if record.get("segment_role") == "tangent" and "taper_ref" in record:
                add(
                    "tangent_taper",
                    path + "/taper_ref",
                    "A tangent run cannot declare taper membership",
                )
            for i, target in enumerate(record.get("individual_device_refs", [])):
                if index[target]["device_type"] != record["device_type"]:
                    add(
                        "run_subtype",
                        path + f"/individual_device_refs/{i}",
                        "Run member subtype differs from run",
                        [target],
                    )
            for i, gap in enumerate(record.get("gap_measurements", [])):
                if gap["from_device_ref"] == gap["to_device_ref"]:
                    add(
                        "self_link",
                        path + f"/gap_measurements/{i}",
                        "A device cannot form a gap with itself",
                    )
                for key in ("from_device_ref", "to_device_ref"):
                    if index[gap[key]]["device_type"] != record["device_type"]:
                        add(
                            "run_subtype",
                            path + f"/gap_measurements/{i}/{key}",
                            "Gap device differs from run subtype",
                        )
                    if (
                        "individual_device_refs" in record
                        and gap[key] not in record["individual_device_refs"]
                    ):
                        add(
                            "gap_membership",
                            path + f"/gap_measurements/{i}/{key}",
                            "Gap device is outside declared run members",
                        )
        if kind == "taper":
            for run_ref in record.get("device_run_refs", []):
                run = index[run_ref]
                if "taper_ref" in run and run["taper_ref"] != rid:
                    add(
                        "membership_mismatch",
                        path + "/device_run_refs",
                        "Reciprocal taper/run links disagree",
                        [run_ref],
                    )
        if kind == "device_run" and "taper_ref" in record:
            taper = index[record["taper_ref"]]
            if "device_run_refs" in taper and rid not in taper["device_run_refs"]:
                add(
                    "membership_mismatch",
                    path + "/taper_ref",
                    "Reciprocal taper/run links disagree",
                )
        _check_entity_frames(record, path, index, add)
        if kind == "alignment":
            frame = index[record["frame_ref"]]
            if "alignment_ref" in frame and frame["alignment_ref"] != rid:
                add(
                    "alignment_frame",
                    path + "/frame_ref",
                    "Station frame identifies a different alignment",
                )
            for field in ("profile", "station_mapping"):
                entries = record.get(field, [])
                if any(
                    a["station"] >= b["station"] for a, b in zip(entries, entries[1:])
                ):
                    add(
                        "unordered_stations",
                        path + "/" + field,
                        "Stations must strictly increase",
                    )
            for i, mapping in enumerate(record.get("station_mapping", [])):
                points = record.get("plan_geometry", {}).get("points", [])
                j = mapping["point_index"]
                if j >= len(points) - 1:
                    add(
                        "mapping_segment",
                        path + f"/station_mapping/{i}/point_index",
                        "Station mapping needs an existing plan segment",
                    )
                elif mapping["distance_along_segment"] > hypot(
                    points[j + 1]["x"] - points[j]["x"],
                    points[j + 1]["y"] - points[j]["y"],
                ):
                    add(
                        "mapping_distance",
                        path + f"/station_mapping/{i}/distance_along_segment",
                        "Distance exceeds referenced segment length",
                    )
    for relation, graph in graphs.items():
        for rid in set(_cycles(graph)):
            add(
                "cycle",
                record_paths[rid],
                f"{relation} hierarchy must be acyclic",
                [rid],
            )
    # Preserve stable ordering and remove duplicate messages from union/schema traversal.
    return list({json.dumps(e, sort_keys=True): e for e in errors}.values())


def _check_entity_frames(record, path, index, add):
    frame_ref = record.get("frame_ref")
    if "approach_ref" in record:
        approach = index[record["approach_ref"]]
        frame_ref = approach["frame_ref"]
        if "road_ref" in record and record["road_ref"] != approach["road_ref"]:
            add(
                "road_mismatch",
                path + "/road_ref",
                "Road differs from supplied approach road",
            )
    for field in ("station_range", "range", "extent", "start_location", "end_location"):
        geom = record.get(field, {})
        if (
            frame_ref
            and "frame_ref" in geom
            and index[geom["frame_ref"]]["kind"] == "station"
            and geom["frame_ref"] != frame_ref
        ):
            add(
                "frame_mismatch",
                path + "/" + field,
                "Station geometry differs from subject frame",
            )
    if record["kind"] == "alignment":
        for i, segment in enumerate(record.get("grade_segments", [])):
            if segment["range"]["frame_ref"] != frame_ref:
                add(
                    "frame_mismatch",
                    path + f"/grade_segments/{i}/range",
                    "Grade range differs from alignment frame",
                )
    if record["kind"] == "path":
        for lane in record.get("lane_refs", []):
            if index[lane]["road_ref"] != index[record["approach_ref"]]["road_ref"]:
                add(
                    "road_mismatch",
                    path + "/lane_refs",
                    "Path lane belongs to a different road",
                    [lane],
                )
        if "geometry" in record:
            frame = index[frame_ref]
            alignment = index.get(frame.get("alignment_ref"), {})
            planar = alignment.get("plan_geometry", {}).get("points", [])
            if (
                not planar
                or record["geometry"]["points"][0]["frame_ref"]
                != planar[0]["frame_ref"]
            ):
                add(
                    "frame_mismatch",
                    path + "/geometry",
                    "Path planar geometry needs the approach station frame alignment in that planar frame",
                )


def _check_derivation(record, path, index, add):
    """Only explicitly named arithmetic is checked; descriptions are never executed."""
    method = record.get("derivation")
    inputs = [index[r] for r in record.get("input_refs", [])]
    if method not in (
        "difference",
        "sum",
        "maximum",
        "station_difference",
        "planar_distance",
    ):
        return
    expected = None
    try:
        if method in ("difference", "sum", "maximum"):
            values = [
                convert_quantity(r["value"], record["value"]["unit"]) for r in inputs
            ]
            if method == "difference" and len(values) == 2:
                expected = values[0] - values[1]
            elif method == "sum" and values:
                expected = sum(values)
            elif method == "maximum" and values:
                expected = max(values)
        else:
            locations = record.get("reference_locations", [])
            if (
                len(locations) == 2
                and locations[0]["frame_ref"] == locations[1]["frame_ref"]
            ):
                a, b = locations
                if method == "station_difference":
                    expected = abs(b["station"] - a["station"])
                else:
                    expected = hypot(b["x"] - a["x"], b["y"] - a["y"])
                unit = "ft" if index[a["frame_ref"]]["units"] == "feet" else "m"
                expected = convert_quantity(
                    {"value": expected, "unit": unit}, record["value"]["unit"]
                )
    except (KeyError, TypeError, ValueError):
        pass
    if expected is None:
        add(
            "derivation_inputs",
            path + "/derivation",
            "Declared arithmetic needs compatible typed inputs or reference locations",
        )
    elif not isclose(record["value"]["value"], expected, rel_tol=1e-12, abs_tol=1e-12):
        add(
            "derivation_mismatch",
            path + "/value",
            "Value disagrees with declared exact derivation",
        )


def v2_document_diagnostics(document):
    errors = structural_diagnostics(document)
    return errors if errors else semantic_diagnostics(document)


def validate_v2_document(document):
    """Return the same document, or raise V2ValidationError with structured diagnostics."""
    diagnostics = v2_document_diagnostics(document)
    if diagnostics:
        raise V2ValidationError(diagnostics)
    return document
