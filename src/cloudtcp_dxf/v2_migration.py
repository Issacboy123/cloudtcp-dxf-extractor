"""Conservative, loss-preserving v1 import. Input objects remain untouched."""

import json
import re
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
from math import isfinite
from urllib.parse import quote

from .v2_validation import (
    V2ValidationError,
    at_pointer,
    diagnostic,
    json_diagnostics,
    structural_diagnostics,
    validate_v2_document,
)
from .validation import document_issues, if_validator


def canonical_hash(value):
    return sha256(
        json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        ).encode()
    ).hexdigest()


def _leaves(value, path=""):
    if isinstance(value, dict) and value:
        for key, child in value.items():
            escaped = key.replace("~", "~0").replace("/", "~1")
            yield from _leaves(child, path + "/" + escaped)
    elif isinstance(value, list) and value:
        for i, child in enumerate(value):
            yield from _leaves(child, path + "/" + str(i))
    else:
        yield path, value


def migrate_v1_document(document, context=None):
    """Return {document, migration_report}; validate before conversion and after merge.

    Authored context never changes the original or silently overwrites a target binding.
    Full source JSON is retained as a legacy record as well as by the caller/input file.
    """
    json_errors = list(json_diagnostics(document))
    if json_errors:
        raise V2ValidationError(json_errors)
    structure_errors = list(if_validator().iter_errors(document))
    issues = document_issues(document)
    if any(i["severity"] == "error" for i in issues):
        raise V2ValidationError(
            [
                diagnostic(
                    "structure"
                    if structure_errors
                    else "reference"
                    if i["reason"].startswith(("Unknown ", "Duplicate "))
                    else "semantic",
                    "invalid_v1",
                    i["path"],
                    i["reason"],
                )
                for i in issues
                if i["severity"] == "error"
            ]
        )
    context = deepcopy(context) if context is not None else {}
    allowed = {
        "project_id",
        "reference_frames",
        "phases",
        "entities",
        "evidence",
        "assertions",
        "completeness",
        "decisions",
        "bindings",
    }
    if not isinstance(context, dict) or set(context) - allowed:
        raise V2ValidationError(
            [
                diagnostic(
                    "structure",
                    "migration_context",
                    "/context",
                    "Unknown migration context fields or invalid context",
                )
            ]
        )
    source_hash = canonical_hash(document)
    context_hash = canonical_hash(context)
    namespace = context.get("project_id", "legacy-import:" + source_hash)
    if (
        not isinstance(namespace, str)
        or not namespace.strip()
        or namespace != namespace.strip()
    ):
        raise V2ValidationError(
            [
                diagnostic(
                    "structure",
                    "migration_context",
                    "/context/project_id",
                    "Project ID must be a nonempty trimmed string",
                )
            ]
        )
    prefix = "legacy:" + quote(namespace, safe="") + ":"

    def rid(collection, key):
        return prefix + collection + ":" + quote(str(key), safe="")

    source_id, frame_id, road_id, closure_id = (
        rid(k, "source") for k in ("evidence", "frame", "road", "closure")
    )
    converted_at = datetime.now(timezone.utc).isoformat()
    output = dict(
        format_version="2.0.0",
        document_id=rid(
            "document", source_hash + ":" + context_hash + ":" + converted_at
        ),
        project_id=namespace,
        revision="import-" + source_hash[:12] + "-" + context_hash[:12],
        created_at=converted_at,
        site={"name": document["site"]["name"]},
        reference_frames=[],
        phases=[],
        entities=[],
        evidence=[],
        assertions=[],
        completeness=[],
        observations=[],
        legacy_records=[],
    )
    entries = {
        path: dict(
            source_path=path,
            disposition="preserved",
            reason="Retained in immutable legacy source record",
        )
        for path, _ in _leaves(document)
    }
    id_map = {}

    def mark(source_path, disposition, reason, target_ref=None, target_path=None):
        matches = [
            p for p in entries if p == source_path or p.startswith(source_path + "/")
        ]
        for p in matches:
            entries[p] = dict(source_path=p, disposition=disposition, reason=reason)
            if target_ref:
                entries[p]["target_ref"] = target_ref
            if target_path is not None:
                entries[p]["target_path"] = target_path
        if not matches:
            entries[source_path] = dict(
                source_path=source_path, disposition=disposition, reason=reason
            )

    def converted(source_path, target, target_path):
        mark(
            source_path,
            "converted",
            "Explicit legacy value converted without inferring additional facts",
            target,
            target_path,
        )

    converted("/format_version", output["document_id"], "/format_version")
    for field in ("city", "county", "created_date"):
        if field in document["site"]:
            mark(
                "/site/" + field,
                "preserved",
                "Legacy geographic/project-date context has no equivalent typed v2 field; no classification or timestamp inferred",
            )
    if "temporal_context" in document:
        mark(
            "/temporal_context",
            "preserved",
            "Legacy snapshot context retained without inferring phase, lighting or sight-distance facts",
        )
    source = document["site"]
    output["evidence"].append(
        {
            "id": source_id,
            "source_type": "legacy_import",
            "locator": {
                "record_key": "v1:" + source_hash,
                **(
                    {"file_name": source["source_file"]}
                    if "source_file" in source
                    else {}
                ),
            },
            "content_hash": source_hash,
            "limitations": [
                "Original v1 JSON; not evidence of complete inventory, phase applicability or engineering approval.",
                "Source format: " + source.get("source_format", "unspecified"),
                "Hash identifies canonical parsed v1 JSON, not the named CAD file bytes.",
                "Weather visibility, counts, compass directions and predictions retain their original semantics.",
            ],
        }
    )
    output["legacy_records"].append(
        {
            "id": rid("raw", "document"),
            "source_path": "",
            "value": deepcopy(document),
            "reason": "Immutable complete v1 source; includes every unmapped or ambiguous field",
            "source_evidence_ref": source_id,
        }
    )
    output["reference_frames"].append(
        {
            "id": frame_id,
            "kind": "station",
            "units": source["units"],
            "datum_description": source["coordinate_system"],
            "increasing_direction_description": "Original legacy station domain; no compass travel direction or planar transform inferred.",
        }
    )
    road = {
        "id": road_id,
        "kind": "road",
        "road_name": source["road_name"],
        "jurisdiction": {"state": source["state"]},
        "source_evidence_refs": [source_id],
    }
    output["entities"].append(road)
    for name, target in [
        ("highway_number", "route_number"),
        ("location_description", "description"),
    ]:
        if name in source:
            road[target] = source[name]
            converted("/site/" + name, road_id, "/" + target)
    converted("/site/road_name", road_id, "/road_name")
    converted("/site/state", road_id, "/jurisdiction/state")
    converted("/site/name", output["document_id"], "/site/name")
    if "project_number" in source:
        output["site"]["project_number"] = source["project_number"]
        converted("/site/project_number", output["document_id"], "/site/project_number")
    converted("/site/units", frame_id, "/units")
    converted("/site/coordinate_system", frame_id, "/datum_description")
    traffic = document["typical_application"]
    closure_type = {
        "lane_closure": "lane",
        "multi_lane_closure": "lane",
        "shoulder_closure": "shoulder",
        "road_closure": "road",
        "intersection_closure": "intersection",
        "median_crossover": "median_crossover",
        "ramp_closure": "ramp",
        "other": "other",
    }[traffic["type"]]
    closure = {
        "id": closure_id,
        "kind": "closure",
        "closure_type": closure_type,
        "source_evidence_refs": [source_id],
    }
    if "description" in traffic:
        closure["description"] = traffic["description"]
        converted("/typical_application/description", closure_id, "/description")
    output["entities"].append(closure)
    converted("/typical_application/type", closure_id, "/closure_type")
    for name, metric, basis in [
        ("posted_speed_mph", "posted_speed", "posted"),
        ("work_zone_speed_mph", "work_zone_speed", "work_zone_posted"),
    ]:
        if name in traffic:
            oid = rid("speed", metric)
            output["observations"].append(
                {
                    "id": oid,
                    "subject_refs": [road_id],
                    "metric": metric,
                    "value": {"value": traffic[name], "unit": "mph"},
                    "basis": basis,
                    "evidence_refs": [source_id],
                }
            )
            road[metric + "_ref"] = oid
            converted("/typical_application/" + name, oid, "/value")
    for field in ("lanes_total", "lanes_closed"):
        if field in traffic:
            mark(
                "/typical_application/" + field,
                "ambiguous",
                "Counts do not identify physical lanes, adjacency or membership",
            )
    mark(
        "/typical_application/direction",
        "ambiguous",
        "Compass/BOTH does not establish signed travel or alternating operation",
    )
    snapshot = document.get("temporal_context", {})
    for collection, key in [("zones", "zone_id"), ("elements", "element_id")]:
        for item in document[collection]:
            id_map[collection + "/" + item[key]] = rid(collection, item[key])
    for i, zone in enumerate(document["zones"]):
        zid = id_map["zones/" + zone["zone_id"]]
        path = f"/zones/{i}"
        entity = {
            "id": zid,
            "kind": "zone",
            "zone_type": zone["type"],
            "source_evidence_refs": [source_id],
            "extent": {
                "frame_ref": frame_id,
                "start_station": zone["start_station"],
                "end_station": zone["end_station"],
            },
        }
        if "description" in zone:
            entity["description"] = zone["description"]
        output["entities"].append(entity)
        for k in zone:
            converted(
                path + "/" + k,
                zid,
                {
                    "zone_id": "/id",
                    "type": "/zone_type",
                    "start_station": "/extent/start_station",
                    "end_station": "/extent/end_station",
                    "description": "/description",
                }[k],
            )

    def position(value):
        if value["offset"] < 0 or (value["side"] == "center" and value["offset"] != 0):
            return None
        return {
            "frame_ref": frame_id,
            "station": value["station"],
            "offset": value["offset"] * (-1 if value["side"] == "right" else 1),
        }

    for i, element in enumerate(document["elements"]):
        eid = id_map["elements/" + element["element_id"]]
        path = f"/elements/{i}"
        kind = element["type"]
        entity = {"id": eid, "source_evidence_refs": [source_id]}
        if kind in ("sign", "arrow_board"):
            entity.update(kind="device", device_type=kind)
        elif kind == "flagger":
            entity.update(kind="actor", role="flagger")
        elif kind == "device_line":
            entity.update(kind="device_run", device_type=element["device"])
        else:
            entity.update(kind="taper", taper_type=element["taper_type"])
        converted(path + "/element_id", eid, "/id")
        converted(path + "/type", eid, "/kind")
        if "zone_id" in element:
            if kind == "flagger":
                mark(
                    path + "/zone_id",
                    "ambiguous",
                    "Actor has no zone relationship; preserved without inventing a control assignment",
                )
            else:
                entity["zone_ref"] = id_map["zones/" + element["zone_id"]]
                converted(path + "/zone_id", eid, "/zone_ref")
        if "source" in element:
            raw = element["source"]
            evidence_id = rid("cad-evidence", element["element_id"])
            locator = {"record_key": raw.get("entity", "legacy-element")}
            for k in ("layer", "handle"):
                if k in raw:
                    locator[k] = raw[k]
            if "block" in raw:
                locator["section"] = raw["block"]
            output["evidence"].append(
                {
                    "id": evidence_id,
                    "source_type": "cad",
                    "locator": locator,
                    "limitations": [
                        "Imported CAD locator; block name is not independently verified physical identity."
                    ],
                }
            )
            entity["source_evidence_refs"].append(evidence_id)
            converted(path + "/source", evidence_id, "/locator")
        if "position" in element:
            location = position(element["position"])
            if location is None:
                mark(
                    path + "/position",
                    "ambiguous",
                    "Negative magnitude or contradictory center offset; no location emitted",
                )
            else:
                entity["location"] = location
                converted(path + "/position", eid, "/location")
        if kind == "sign":
            entity["specification"] = {
                k: element[k] for k in ("mutcd_code", "legend") if k in element
            }
            for k in entity["specification"]:
                converted(path + "/" + k, eid, "/specification/" + k)
            if "size_inches" in element:
                match = re.fullmatch(
                    r"\s*(\d+(?:\.\d+)?)\s*[x×]\s*(\d+(?:\.\d+)?)\s*",
                    element["size_inches"],
                )
                if match and all(isfinite(float(v)) for v in match.groups()):
                    entity["specification"]["dimensions"] = {
                        k: {"value": float(v), "unit": "in"}
                        for k, v in zip(("width", "height"), match.groups())
                    }
                    converted(path + "/size_inches", eid, "/specification/dimensions")
                else:
                    mark(
                        path + "/size_inches",
                        "ambiguous",
                        "Only finite numeric width x height encoding is parsed; shape remains unknown",
                    )
            if "face_direction" in element:
                mark(
                    path + "/face_direction",
                    "ambiguous",
                    "Compass facing cannot identify a surveyed heading or served approach",
                )
        elif kind == "arrow_board":
            mapped = {
                "sequential_arrow": {"mode": "arrow", "sequence": "sequential"},
                "sequential_chevron": {"mode": "chevron", "sequence": "sequential"},
                "double_arrow": {"mode": "double_arrow"},
            }.get(element["mode"])
            if mapped:
                entity["specification"] = mapped
                converted(path + "/mode", eid, "/specification")
            else:
                mark(
                    path + "/mode",
                    "ambiguous",
                    "Legacy flashing/diamond pattern has no verified caution-mode meaning",
                )
        elif kind == "flagger":
            if "controls" in element:
                mark(
                    path + "/controls",
                    "ambiguous",
                    "Cardinal controls cannot manufacture path/control assignments",
                )
        elif kind == "device_line":
            entity["spacing"] = {"value": element["spacing_ft"], "unit": "ft"}
            converted(path + "/device", eid, "/device_type")
            converted(path + "/spacing_ft", eid, "/spacing")
            for k in (
                "start_station",
                "end_station",
                "start_offset",
                "end_offset",
                "side",
            ):
                if k in element:
                    mark(
                        path + "/" + k,
                        "ambiguous",
                        "Legacy line offset units/sign context are not explicit; no run geometry inferred",
                    )
        elif kind == "taper":
            converted(path + "/taper_type", eid, "/taper_type")
            if (
                element.get("side") in ("left", "right")
                and element["start_offset"] >= 0
                and element["end_offset"] >= 0
                and element["end_station"] >= element["start_station"]
            ):
                scale = 0.3048 if source["units"] == "meters" else 1
                sign = -1 if element["side"] == "right" else 1
                for endpoint in ("start", "end"):
                    entity[endpoint + "_location"] = {
                        "frame_ref": frame_id,
                        "station": element[endpoint + "_station"],
                        "offset": element[endpoint + "_offset"] * scale * sign,
                    }
                    for suffix in ("station", "offset"):
                        converted(
                            path + "/" + endpoint + "_" + suffix,
                            eid,
                            "/" + endpoint + "_location",
                        )
                converted(path + "/side", eid, "/start_location/offset")
            else:
                for k in (
                    "start_station",
                    "end_station",
                    "start_offset",
                    "end_offset",
                    "side",
                ):
                    if k in element:
                        mark(
                            path + "/" + k,
                            "ambiguous",
                            "Taper endpoints need nonnegative magnitudes, ordered stations and an explicit lateral side",
                        )
            if "lane_width_ft" in element:
                mark(
                    path + "/lane_width_ft",
                    "ambiguous",
                    "Lane width is not taper offset width; retained without substitution",
                )
        output["entities"].append(entity)
    metrics = {
        "speed_mph": ("observed_speed", "mph"),
        "volume_vph": ("volume", "veh/h"),
        "occupancy_pct": ("occupancy", "%"),
        "headway_sec": ("headway", "s"),
        "queue_length_ft": ("queue_length", "ft"),
    }
    for i, observation in enumerate(document.get("observations", [])):
        source_path = f"/observations/{i}"
        evidence_id = rid("observation-evidence", observation["obs_id"])
        output["evidence"].append(
            {
                "id": evidence_id,
                "source_type": "legacy_import",
                "locator": {
                    "record_key": observation["source"] + ":" + observation["obs_id"]
                },
                "limitations": [
                    observation.get(
                        "note", "Legacy reading; missing mode/time remains unknown."
                    )
                ],
            }
        )
        subjects = (
            [id_map["zones/" + observation["zone_id"]]]
            if "zone_id" in observation
            else [road_id]
        )
        # No offset is available; a point cannot be manufactured from station alone.
        for field, (metric, unit) in metrics.items():
            if field not in observation:
                continue
            oid = rid("observations", observation["obs_id"] + ":" + metric)
            candidate = {
                "id": oid,
                "subject_refs": subjects,
                "metric": metric,
                "value": {"value": observation[field], "unit": unit},
                "evidence_refs": [source_id, evidence_id],
                "range": {
                    "frame_ref": frame_id,
                    "start_station": observation["station"],
                    "end_station": observation["station"],
                },
            }
            if "timestamp" in snapshot:
                candidate["observed_at"] = snapshot["timestamp"]
            if structural_diagnostics({**output, "observations": [candidate]}):
                mark(
                    source_path + "/" + field,
                    "ambiguous",
                    "Legacy value is outside the v2 physical domain; raw value retained",
                )
            else:
                output["observations"].append(candidate)
                converted(source_path + "/" + field, oid, "/value")
                converted(source_path + "/obs_id", oid, "/id")
                converted(source_path + "/station", oid, "/range")
                if "zone_id" in observation:
                    converted(source_path + "/zone_id", oid, "/subject_refs")
                id_map["observations/" + observation["obs_id"] + ":" + metric] = oid
    if "predictions" in document:
        _migrate_predictions(
            document["predictions"], output, rid, id_map, source_id, mark, converted
        )
    for key in (
        "reference_frames",
        "phases",
        "entities",
        "evidence",
        "assertions",
        "completeness",
        "decisions",
    ):
        if key in context:
            if not isinstance(context[key], list):
                raise V2ValidationError(
                    [
                        diagnostic(
                            "structure",
                            "migration_context",
                            "/context/" + key,
                            "Context records must be arrays",
                        )
                    ]
                )
            output.setdefault(key, []).extend(context[key])
    validate_v2_document(output)
    _apply_bindings(document, output, context.get("bindings", []), source_id, rid, mark)
    validate_v2_document(output)
    counts = Counter(entry["disposition"] for entry in entries.values())
    report = {
        "source_format_version": "1.0.0",
        "target_format_version": "2.0.0",
        "source_document_hash": source_hash,
        "entries": list(entries.values()),
        "id_map": id_map,
        "context_hash": context_hash,
        "summary": {
            "fields": dict(counts),
            "entities": {
                "source": len(document["elements"]),
                "converted": len(document["elements"]),
                "total_output": len(output["entities"]),
            },
        },
        "limitations": [
            "Preserve original v1 file alongside this export.",
            "Import namespace is provisional unless an authored project ID and retained identity map are provided.",
            "No physical lanes, approaches, phases, approvals or completeness were inferred.",
        ],
        "source_validation_warnings": [i for i in issues if i["severity"] == "warning"],
    }
    return {"document": output, "migration_report": report}


def _migrate_predictions(predictions, output, rid, id_map, source_id, mark, converted):
    required = {"model_version", "predicted_at", "horizon_minutes"}
    if not required <= predictions.keys() or predictions.get("horizon_minutes", -1) < 0:
        mark(
            "/predictions",
            "ambiguous",
            "V2 prediction identity/time/horizon metadata are incomplete; entire original subtree retained",
        )
        return
    for field in ("total_delay_sec", "max_queue_ft", "risk_level"):
        if field in predictions:
            mark(
                "/predictions/" + field,
                "ambiguous",
                "Legacy corridor aggregation has no authored v2 subject scope; original retained",
            )
    if "recommendations" in predictions:
        mark(
            "/predictions/recommendations",
            "preserved",
            "Only recommendations attached to a converted explicit zone prediction are converted; all originals retained",
        )
    # Corridor aggregates have no authored scope; only explicit legacy zone scopes are converted.
    for i, zone in enumerate(predictions.get("by_zone", [])):
        path = f"/predictions/by_zone/{i}"
        if "zone_id" not in zone:
            mark(path, "ambiguous", "Prediction has no authored subject scope")
            continue
        pid = rid("prediction", str(i) + ":" + zone["zone_id"])
        record = {
            "id": pid,
            "model_version": predictions["model_version"],
            "predicted_at": predictions["predicted_at"],
            "horizon": {"value": predictions["horizon_minutes"], "unit": "min"},
            "subject_refs": [id_map["zones/" + zone["zone_id"]]],
            "metrics": [],
        }
        if "confidence" in zone:
            record["confidence"] = zone["confidence"]
        for field, metric, unit in [
            ("queue_length_ft", "queue_length", "ft"),
            ("delay_sec", "delay", "s"),
        ]:
            if field in zone and zone[field] >= 0:
                record["metrics"].append(
                    {"metric": metric, "value": {"value": zone[field], "unit": unit}}
                )
                converted(path + "/" + field, pid, "/metrics")
        if "throughput_vph" in zone:
            mark(
                path + "/throughput_vph",
                "ambiguous",
                "Throughput aggregation is retained without equating it to generic volume",
            )
        if "congestion_index" in zone:
            mark(
                path + "/congestion_index",
                "preserved",
                "No equivalent v2 observation metric",
            )
        record["recommendations"] = []
        for j, recommendation in enumerate(predictions.get("recommendations", [])):
            if recommendation.get("zone_id") != zone["zone_id"]:
                continue
            rec = {
                k: recommendation[k]
                for k in ("action", "priority", "reason")
                if k in recommendation
            }
            rec["subject_refs"] = [id_map["zones/" + zone["zone_id"]]]
            if "element_id" in recommendation:
                rec["subject_refs"].append(
                    id_map["elements/" + recommendation["element_id"]]
                )
            record["recommendations"].append(rec)
            converted(f"/predictions/recommendations/{j}", pid, "/recommendations")
        output.setdefault("predictions", []).append(record)
        converted(path + "/zone_id", pid, "/subject_refs")
        for field in ("model_version", "predicted_at", "horizon_minutes"):
            converted(
                "/predictions/" + field,
                pid,
                {"horizon_minutes": "/horizon"}.get(field, "/" + field),
            )


def _apply_bindings(source, output, bindings, source_id, rid, mark):
    if not isinstance(bindings, list):
        raise V2ValidationError(
            [
                diagnostic(
                    "structure",
                    "migration_binding",
                    "/context/bindings",
                    "Bindings must be an array",
                )
            ]
        )
    index = {
        r["id"]: r
        for key in (
            "entities",
            "phases",
            "reference_frames",
            "observations",
            "decisions",
        )
        for r in output.get(key, [])
    }
    for i, binding in enumerate(bindings):
        path = f"/context/bindings/{i}"
        if (
            not isinstance(binding, dict)
            or set(binding) != {"source_path", "target_ref", "target_path"}
            or any(not isinstance(v, str) for v in binding.values())
        ):
            raise V2ValidationError(
                [
                    diagnostic(
                        "structure",
                        "migration_binding",
                        path,
                        "Binding requires source_path, target_ref and target_path strings",
                    )
                ]
            )
        try:
            value = at_pointer(source, binding["source_path"])
            subject = index[binding["target_ref"]]
            target = at_pointer(subject, binding["target_path"])
        except (KeyError, IndexError, ValueError):
            raise V2ValidationError(
                [
                    diagnostic(
                        "reference",
                        "migration_binding",
                        path,
                        "Unresolved source or target binding",
                    )
                ]
            ) from None
        if value == target:
            mark(
                binding["source_path"],
                "converted",
                "Authored binding agrees with the preserved source",
                subject["id"],
                binding["target_path"],
            )
            continue
        assertion = {
            "id": rid("binding", i),
            "subject_ref": subject["id"],
            "path": binding["target_path"],
            "status": "disputed",
            "evidence_refs": [source_id],
            "method": "extracted",
            "scope": {"phase_refs": subject["phase_refs"]}
            if subject.get("phase_refs")
            else {"phase_independent": True},
        }
        # Retain only type-compatible alternatives. Incompatible raw values remain in legacy_records.
        alternative = {"value": deepcopy(value), "evidence_refs": [source_id]}
        assertion["alternatives"] = [alternative]
        candidate = deepcopy(output)
        candidate["assertions"].append(assertion)
        try:
            validate_v2_document(candidate)
        except V2ValidationError:
            assertion.pop("alternatives")
        output["assertions"].append(assertion)
        mark(
            binding["source_path"],
            "ambiguous",
            "Authored target conflicts with source; target retained and assertion disputed",
            subject["id"],
            binding["target_path"],
        )
