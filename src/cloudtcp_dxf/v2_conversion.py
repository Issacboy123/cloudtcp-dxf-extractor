"""Acquisition of explicitly mapped CAD INSERTs into CloudTCP IF v2.0.0."""

import json
from collections import Counter
from copy import deepcopy
from hashlib import sha256
from urllib.parse import quote

from .extract import extract_dxf
from .if_conversion import _resolve_units, station_offset
from .v2_validation import (
    V2ValidationError,
    v2_document_diagnostics,
    validate_v2_document,
)
from .validation import ConversionError, issue


def convert_v2_extraction(extraction, config):
    """Return (document, acquisition report); the authored document is never mutated.

    Config: {document, stationing:{frame_ref,origin,endpoint}, block_mappings, source_units?}.
    Mappings are v2 entity templates without id/location/source_evidence_refs.
    """
    report = dict(
        source=deepcopy(extraction["source"]),
        converted_elements=0,
        unmapped_blocks={},
        skipped_mappings={},
        skipped_elements=0,
        unmapped_elements=0,
        unsupported_geometry_counts=deepcopy(
            extraction["log"]["unsupported_geometry_counts"]
        ),
        warnings=list(extraction["log"].get("warnings", [])),
        issues=[],
        limitations=[
            "Only explicitly mapped named modelspace INSERTs become signs, arrow boards or flaggers.",
            "Stationing projects onto a configured straight line; no curved alignment or roadway discovery.",
            "Configured inventory and extraction are partial; no absence or approval is inferred.",
            extraction["log"]["scope"],
        ],
    )

    def bad(message, path):
        report["issues"].append(issue(message, path))
        raise ConversionError(message, report)

    if not isinstance(config, dict):
        bad("V2 configuration must be an object", "/")
    if set(config) - {"document", "stationing", "block_mappings", "source_units"}:
        bad("Unknown v2 configuration fields", "/")
    if "document" not in config or "stationing" not in config:
        bad("V2 configuration requires document and stationing", "/")
    document = deepcopy(config["document"])
    if isinstance(document, dict) and "predictions" in document:
        bad(
            "predictions are model-owned and cannot be supplied to the extractor",
            "/document/predictions",
        )
    validate_v2_document(document)
    stationing = config["stationing"]
    if not isinstance(stationing, dict) or set(stationing) != {
        "frame_ref",
        "origin",
        "endpoint",
    }:
        bad("stationing requires only frame_ref, origin and endpoint", "/stationing")
    frame = next(
        (f for f in document["reference_frames"] if f["id"] == stationing["frame_ref"]),
        None,
    )
    if frame is None or frame["kind"] != "station":
        bad("stationing.frame_ref must name a station frame", "/stationing/frame_ref")
    try:
        station_offset(
            stationing["origin"], stationing["origin"], stationing["endpoint"]
        )
    except (ValueError, TypeError) as exc:
        bad(str(exc), "/stationing")
    unit_config = {"site": {"units": frame["units"]}}
    if "source_units" in config:
        unit_config["source_units"] = config["source_units"]
    scale = _resolve_units(extraction, unit_config, report)
    mappings = config.get("block_mappings", {})
    if not isinstance(mappings, dict) or any(not isinstance(k, str) for k in mappings):
        bad("block_mappings must be an object with string keys", "/block_mappings")
    if len({k.casefold() for k in mappings}) != len(mappings):
        bad("Block mapping names must be unique ignoring case", "/block_mappings")
    prepared = {}
    for name, mapping in mappings.items():
        message = None
        if not isinstance(mapping, dict):
            message = "Mapping must be an entity object"
        elif set(mapping).intersection({"id", "location", "source_evidence_refs"}):
            message = "IDs, locations and source evidence are acquired, not configurable in mappings"
        elif not (
            (
                mapping.get("kind") == "device"
                and mapping.get("device_type") in ("sign", "arrow_board")
            )
            or (mapping.get("kind") == "actor" and mapping.get("role") == "flagger")
        ):
            message = "Only device(sign/arrow_board) and actor(flagger) mappings are supported"
        else:
            probe = deepcopy(document)
            probe["entities"].append({**deepcopy(mapping), "id": "__mapping_probe__"})
            errors = v2_document_diagnostics(probe)
            if errors:
                message = errors[0]["message"]
        prepared[name.casefold()] = (mapping, message)
        if message:
            report["issues"].append(
                issue(message, "/block_mappings/" + name, "warning")
            )

    # Source/configuration artifacts remain separately serializable and hash-addressed.
    source_hash = sha256(
        json.dumps(
            extraction, sort_keys=True, allow_nan=False, separators=(",", ":")
        ).encode()
    ).hexdigest()
    config_hash = sha256(
        json.dumps(
            config, sort_keys=True, allow_nan=False, separators=(",", ":")
        ).encode()
    ).hexdigest()
    source_id, config_id = "cad-source:" + source_hash, "cad-config:" + config_hash
    document["evidence"].extend(
        [
            {
                "id": source_id,
                "source_type": "cad",
                "locator": {"file_name": extraction["source"]["filename"]},
                "content_hash": source_hash,
                "limitations": [
                    *report["limitations"],
                    "Hash identifies the canonical raw extraction JSON, not DXF file bytes.",
                ],
            },
            {
                "id": config_id,
                "source_type": "plan_document",
                "locator": {"record_key": "extractor-configuration"},
                "content_hash": config_hash,
                "limitations": [
                    "Authored straight reference line and explicit block mappings."
                ],
            },
        ]
    )
    # Frame provenance covers only the configured station definition, without inventing phase scope.
    document["assertions"].append(
        {
            "id": "cad-stationing:" + config_hash,
            "subject_ref": frame["id"],
            "path": "",
            "status": "supported",
            "evidence_refs": [config_id],
            "method": "authored",
            "scope": {"phase_independent": True},
        }
    )
    unmapped, skipped = Counter(), Counter()
    for entity in extraction["entities"]:
        if entity["type"] != "INSERT":
            continue
        block = entity.get("block_name", "")
        match = prepared.get(block.casefold())
        source = {k: entity.get(k) for k in ("handle", "layer")}
        source["block"] = block
        if match is None:
            unmapped[block] += 1
            report["issues"].append(
                issue("Unmapped INSERT", "/entities", "warning", source)
            )
            continue
        mapping, message = match
        if message is None:
            try:
                position = station_offset(
                    entity["geometry"]["insert"],
                    stationing["origin"],
                    stationing["endpoint"],
                    scale=scale,
                )
                offset = position["offset"] * (-1 if position["side"] == "right" else 1)
                eid = "cad-insert:" + quote(str(entity["handle"]), safe="")
                evidence_id = "cad-record:" + quote(str(entity["handle"]), safe="")
                record = {
                    **deepcopy(mapping),
                    "id": eid,
                    "location": {
                        "frame_ref": frame["id"],
                        "station": position["station"],
                        "offset": offset,
                    },
                    "source_evidence_refs": [evidence_id],
                }
                evidence = {
                    "id": evidence_id,
                    "source_type": "cad",
                    "locator": {
                        "file_name": extraction["source"]["filename"],
                        "record_key": "INSERT",
                        "layer": entity["layer"],
                        "handle": str(entity["handle"]),
                        "section": block,
                    },
                    "limitations": [
                        "Block classification is configured; it does not verify physical identity or condition."
                    ],
                }
                probe = deepcopy(document)
                probe["entities"].append(record)
                probe["evidence"].append(evidence)
                validate_v2_document(probe)
            except V2ValidationError:
                raise  # Supplied duplicate identities/references must not be silently skipped.
            except (KeyError, ValueError, TypeError) as exc:
                message = str(exc)
        if message is not None:
            report["skipped_elements"] += 1
            skipped[message] += 1
            report["issues"].append(issue(message, "/entities", "warning", source))
            continue
        document["entities"].append(record)
        document["evidence"].append(evidence)
        # Phase applicability comes only from an explicit mapping; unscoped facts retain source links.
        if record.get("phase_refs"):
            document["assertions"].append(
                {
                    "id": "cad-assertion:" + quote(str(entity["handle"]), safe=""),
                    "subject_ref": eid,
                    "path": "/location",
                    "status": "supported",
                    "method": "extracted",
                    "scope": {"phase_refs": record["phase_refs"]},
                    "evidence_refs": [evidence_id, config_id],
                }
            )
        report["converted_elements"] += 1
    report["unmapped_blocks"] = dict(sorted(unmapped.items()))
    report["unmapped_elements"] = sum(unmapped.values())
    report["skipped_mappings"] = dict(sorted(skipped.items()))
    for declaration in document["completeness"]:
        if declaration["method"] == "configured_extraction":
            declaration["state"] = "partial"
            declaration.setdefault("limitations", []).extend(report["limitations"])
            declaration["evidence_refs"] = list(
                dict.fromkeys([*declaration["evidence_refs"], source_id])
            )
    report["document_id"] = document["document_id"]
    report["source_extraction_hash"] = source_hash
    validate_v2_document(document)
    return document, report


def convert_v2_dxf(path, config):
    return convert_v2_extraction(extract_dxf(path), config)
