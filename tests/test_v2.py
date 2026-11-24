"""Active contract acceptance; regulatory and readiness expectations are excluded."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker

from cloudtcp_dxf.v2_validation import (
    V2ValidationError,
    convert_quantity,
    structural_diagnostics,
    v2_validator,
    validate_v2_document,
)

ROOT = Path(__file__).resolve().parents[1]


def partial():
    return dict(
        format_version="2.0.0",
        document_id="doc",
        project_id="project",
        revision="a",
        created_at="2026-11-19T20:00:00Z",
        site={"name": "Synthetic partial"},
        reference_frames=[],
        phases=[],
        entities=[],
        evidence=[],
        assertions=[],
        completeness=[],
    )


def network():
    d = partial()
    d["reference_frames"] = [
        {"id": "station", "kind": "station", "units": "feet"},
        {"id": "plan", "kind": "planar", "units": "feet"},
    ]
    d["phases"] = [
        {"id": "work", "name": "Work", "phase_type": "work", "light_condition": "mixed"}
    ]
    d["entities"] = [
        {"id": "road", "kind": "road"},
        {
            "id": "north",
            "kind": "approach",
            "road_ref": "road",
            "frame_ref": "station",
            "travel_sign": 1,
        },
        {
            "id": "south",
            "kind": "approach",
            "road_ref": "road",
            "frame_ref": "station",
            "travel_sign": -1,
        },
        {"id": "lane-a", "kind": "lane", "road_ref": "road", "approach_ref": "north"},
        {"id": "lane-b", "kind": "lane", "road_ref": "road", "approach_ref": "north"},
        {
            "id": "path",
            "kind": "path",
            "approach_ref": "north",
            "lane_refs": ["lane-a"],
        },
        {
            "id": "closure",
            "kind": "closure",
            "closure_type": "lane",
            "lane_refs": ["lane-a", "lane-b"],
        },
        {
            "id": "zone-n",
            "kind": "zone",
            "zone_type": "work",
            "approach_ref": "north",
            "extent": {"frame_ref": "station", "start_station": 0, "end_station": 100},
        },
        {
            "id": "zone-s",
            "kind": "zone",
            "zone_type": "work",
            "approach_ref": "south",
            "extent": {"frame_ref": "station", "start_station": 0, "end_station": 100},
        },
        {
            "id": "taper",
            "kind": "taper",
            "taper_type": "one_lane_two_way",
            "approach_ref": "north",
            "device_run_refs": ["run"],
            "from_path_refs": ["path"],
            "length": {"value": 0, "unit": "ft"},
        },
        {
            "id": "run",
            "kind": "device_run",
            "device_type": "cone",
            "segment_role": "taper",
            "taper_ref": "taper",
            "path_refs": ["path"],
            "spacing": {"value": 60, "unit": "ft"},
        },
        {
            "id": "control",
            "kind": "control",
            "control_type": "alternating",
            "controlled_path_refs": ["path"],
        },
        {
            "id": "board-a",
            "kind": "device",
            "device_type": "arrow_board",
            "lane_refs": ["lane-a"],
            "specification": {"mode": "arrow"},
        },
        {
            "id": "board-b",
            "kind": "device",
            "device_type": "arrow_board",
            "lane_refs": ["lane-b"],
            "specification": {"mode": "caution"},
        },
    ]
    d["evidence"] = [
        {
            "id": "source",
            "source_type": "manual_inspection",
            "locator": {"record_key": "inspection"},
        }
    ]
    return d


def fail(d, code, path=None):
    with pytest.raises(V2ValidationError) as caught:
        validate_v2_document(d)
    diagnostics = caught.value.diagnostics
    assert any(
        e["code"] == code and (path is None or e["path"] == path) for e in diagnostics
    ), diagnostics
    assert all(
        set(("layer", "code", "path", "message", "severity")) <= e.keys()
        for e in diagnostics
    )


def point(x, y):
    return {"frame_ref": "plan", "x": x, "y": y}


def test_a01_minimal_partial_is_unchanged_and_never_creates_absence():
    d = partial()
    before = deepcopy(d)
    assert validate_v2_document(d) is d
    assert d == before
    assert d["completeness"] == []


@pytest.mark.parametrize(
    "field,value",
    [
        ("format_version", "3.0.0"),
        ("created_at", "2026-99-99T00:00:00Z"),
        ("site", None),
        ("revision", " x "),
        ("extra", 1),
    ],
)
def test_a02_closed_envelope(field, value):
    d = partial()
    d[field] = value
    assert structural_diagnostics(d)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_a02_nonfinite_even_in_legacy_data(value):
    d = partial()
    d["legacy_records"] = [
        {
            "id": "raw",
            "source_path": "",
            "value": {"nested": value},
            "reason": "raw",
            "source_evidence_ref": "e",
        }
    ]
    fail(d, "non_finite", "/legacy_records/0/value/nested")


def test_a02_unknown_kind_and_null_optional():
    d = network()
    d["entities"][0]["kind"] = "new_kind"
    assert structural_diagnostics(d)
    d = network()
    d["entities"][0]["road_name"] = None
    fail(d, "schema_type", "/entities/0/road_name")


@pytest.mark.parametrize(
    "change,code",
    [
        ("duplicate", "duplicate_id"),
        ("dangling", "dangling_reference"),
        ("wrong", "wrong_target_kind"),
    ],
)
def test_a03_references(change, code):
    d = network()
    if change == "duplicate":
        d["evidence"][0]["id"] = "road"
    elif change == "dangling":
        d["entities"][1]["road_ref"] = "unknown"
    else:
        d["entities"][1]["road_ref"] = "source"
    fail(d, code)


def test_a04_a05_a06_a12_a23_a27_shared_relationships():
    d = network()
    validate_v2_document(d)
    assert d["entities"][7]["extent"] == d["entities"][8]["extent"]
    # Membership is an authored relationship; changing one board's lane is representable.
    d["entities"][-1]["lane_refs"] = ["lane-a"]
    validate_v2_document(d)
    d["entities"][10].pop("taper_ref")
    d["entities"][10]["segment_role"] = "tangent"
    d["entities"][9].pop("device_run_refs")
    validate_v2_document(d)
    assert not any(e["kind"] == "buffer" for e in d["entities"])


def test_a07_equivalent_quantities_and_dimension_rejection():
    assert convert_quantity({"value": 10, "unit": "ft"}, "m") == pytest.approx(3.048)
    assert convert_quantity({"value": 12, "unit": "in"}, "ft") == pytest.approx(1)
    assert convert_quantity(
        {"value": 60, "unit": "flashes/min"}, "Hz"
    ) == pytest.approx(1)
    assert convert_quantity({"value": 100, "unit": "%"}, "ratio") == pytest.approx(1)
    assert convert_quantity({"value": 1, "unit": "ft2"}, "in2") == pytest.approx(144)
    with pytest.raises(ValueError):
        convert_quantity({"value": 1, "unit": "ft"}, "mph")
    d = network()
    d["entities"][10]["spacing"]["unit"] = "mph"
    assert structural_diagnostics(d)


def test_a10_speed_bases_modes_and_target_metrics():
    d = network()
    d["observations"] = [
        {
            "id": "speed",
            "subject_refs": ["north"],
            "metric": "calculation_speed",
            "basis": "prework_offpeak_85th_percentile",
            "mode": "motor",
            "value": {"value": 42, "unit": "mph"},
        }
    ]
    d["entities"][1]["calculation_speed_ref"] = "speed"
    validate_v2_document(d)
    d["observations"][0]["mode"] = "bicycle"
    validate_v2_document(d)
    d["observations"][0]["metric"] = "posted_speed"
    fail(d, "wrong_target_kind")


def test_a13_geometry_and_frame_errors():
    d = network()
    d["entities"].append(
        {
            "id": "work-area",
            "kind": "work_area",
            "activity": "storage",
            "extent": {
                "rings": [
                    [point(0, 0), point(4, 4), point(0, 4), point(4, 0), point(0, 0)]
                ]
            },
        }
    )
    fail(d, "self_intersection")
    d = network()
    d["entities"][7]["extent"]["end_station"] = -1
    fail(d, "reversed_range")
    d = network()
    d["entities"].append(
        {
            "id": "f",
            "kind": "facility",
            "facility_type": "landing",
            "geometry": {
                "rings": [[point(0, 0), point(4, 0), point(4, 4), point(0, 0)]]
            },
        }
    )
    validate_v2_document(d)
    d["entities"][-1]["geometry"]["rings"][0][-1] = point(0, 1)
    fail(d, "unclosed_ring")


def test_a13_polygon_holes_and_mixed_frames():
    d = network()
    d["entities"].append(
        {
            "id": "f",
            "kind": "facility",
            "facility_type": "landing",
            "geometry": {
                "rings": [
                    [
                        point(0, 0),
                        point(10, 0),
                        point(10, 10),
                        point(0, 10),
                        point(0, 0),
                    ],
                    [point(2, 2), point(3, 2), point(3, 3), point(2, 2)],
                ]
            },
        }
    )
    validate_v2_document(d)
    d["entities"][-1]["geometry"]["rings"][1] = [
        point(20, 20),
        point(30, 20),
        point(30, 30),
        point(20, 20),
    ]
    fail(d, "invalid_hole")
    d["reference_frames"].append({"id": "other", "kind": "planar", "units": "meters"})
    d["entities"][-1]["geometry"]["rings"][0][1]["frame_ref"] = "other"
    fail(d, "mixed_frames")


def test_a15_a17_a18_decisions_scopes_and_conflicts():
    d = network()
    d["entities"][0]["road_name"] = "Selected"
    d["assertions"] = [
        {
            "id": "assert",
            "subject_ref": "road",
            "path": "/road_name",
            "status": "disputed",
            "method": "authored",
            "scope": {"phase_refs": ["work"]},
            "evidence_refs": ["source"],
            "alternatives": [{"value": "Other", "evidence_refs": ["source"]}],
        }
    ]
    d["completeness"] = [
        {
            "id": "inventory",
            "scope": {
                "subject_refs": ["north"],
                "phase_refs": ["work"],
                "entity_kinds": ["device"],
                "device_types": ["sign"],
            },
            "state": "partial",
            "method": "manual_inventory",
            "evidence_refs": ["source"],
        }
    ]
    validate_v2_document(d)
    d["assertions"][0]["status"] = "supported"
    fail(d, "unresolved_alternatives")
    d["decisions"] = [
        {
            "id": "resolution",
            "decision_type": "conflict_resolution",
            "subject_refs": ["assert"],
            "outcome": "approved",
            "authority": "Authored reviewer",
            "rationale": "Selected recorded value",
            "evidence_refs": ["source"],
            "phase_refs": ["work"],
        }
    ]
    d["assertions"][0]["decision_ref"] = "resolution"
    validate_v2_document(d)
    d["assertions"][0]["alternatives"][0]["value"] = 42
    fail(d, "alternative_type")
    d["assertions"][0]["path"] = "/missing"
    fail(d, "invalid_pointer")


def test_a16_complete_scope_cannot_have_known_skips():
    d = network()
    d["completeness"] = [
        {
            "id": "inventory",
            "scope": {"subject_refs": ["north"], "phase_refs": ["work"]},
            "state": "complete",
            "method": "configured_extraction",
            "evidence_refs": ["source"],
            "excluded_source_refs": ["source"],
        }
    ]
    fail(d, "incomplete_acquisition")


def test_a19_timestamps_compare_instants_and_phase_order():
    d = network()
    d["phases"][0].update(
        start_at="2026-11-19T12:00:00-08:00",
        end_at="2026-11-19T21:00:00Z",
        duration={"value": 1, "unit": "h"},
    )
    validate_v2_document(d)
    d["phases"][0]["end_at"] = "2026-11-19T19:00:00Z"
    fail(d, "reversed_interval")
    d = network()
    d["phases"][0]["predecessor_refs"] = ["work"]
    fail(d, "cycle")


def test_phase_duration_and_ordered_actions():
    d = network()
    d["phases"][0].update(
        start_at="2026-11-19T20:00:00Z",
        end_at="2026-11-19T21:00:00Z",
        duration={"value": 2, "unit": "h"},
    )
    fail(d, "duration_mismatch")
    d["phases"][0]["duration"]["value"] = 1
    d["phases"][0]["actions"] = [
        {
            "action": "install",
            "subject_refs": ["board-a"],
            "at": "2026-11-19T20:30:00Z",
        },
        {"action": "remove", "subject_refs": ["board-a"], "at": "2026-11-19T20:15:00Z"},
    ]
    fail(d, "action_order")


def test_a26_subtypes_and_caution_mode():
    d = network()
    d["entities"][-1]["specification"]["arrow_direction"] = "left"
    fail(d, "caution_direction")
    d = network()
    d["entities"][-1]["specification"]["height"] = {"value": 1, "unit": "ft"}
    fail(d, "schema_additionalProperties")


def test_reciprocal_membership_and_acyclic_assemblies():
    d = network()
    d["entities"][9]["device_run_refs"] = []
    fail(d, "membership_mismatch")
    d = network()
    d["entities"] += [
        {
            "id": "s1",
            "kind": "device",
            "device_type": "sign",
            "specification": {"assembly_parent_ref": "s2"},
        },
        {
            "id": "s2",
            "kind": "device",
            "device_type": "sign",
            "specification": {"assembly_parent_ref": "s1"},
        },
    ]
    fail(d, "cycle")


def test_alignment_profile_mapping_and_path_frame():
    d = network()
    d["reference_frames"][0]["alignment_ref"] = "alignment"
    d["entities"].append(
        {
            "id": "alignment",
            "kind": "alignment",
            "frame_ref": "station",
            "plan_geometry": {"points": [point(0, 0), point(100, 0)]},
            "profile": [
                {"station": 0, "elevation": 0},
                {"station": 100, "elevation": 3},
            ],
            "station_mapping": [
                {"station": 0, "point_index": 0, "distance_along_segment": 0},
                {"station": 100, "point_index": 0, "distance_along_segment": 100},
            ],
        }
    )
    d["entities"][5]["geometry"] = {"points": [point(0, 0), point(100, 0)]}
    validate_v2_document(d)
    d["entities"][-1]["station_mapping"][1]["distance_along_segment"] = 101
    fail(d, "mapping_distance")
    d["entities"][-1]["profile"][1]["station"] = 0
    fail(d, "unordered_stations")


def test_declared_arithmetic_not_regulatory_evaluation():
    d = network()
    d["observations"] = [
        {
            "id": "distance",
            "subject_refs": ["north"],
            "metric": "stopping_sight_distance",
            "value": {"value": 3.048, "unit": "m"},
            "derivation": "station_difference",
            "reference_locations": [
                {"frame_ref": "station", "station": 0, "offset": 0},
                {"frame_ref": "station", "station": 10, "offset": 0},
            ],
        }
    ]
    validate_v2_document(d)
    d["observations"][0]["value"]["value"] = 4
    fail(d, "derivation_mismatch")
    d["observations"][0]["derivation"] = "surveyed using optical equipment"
    validate_v2_document(d)


def test_schema_is_authoritative_synchronized_and_standalone():
    authoritative = (ROOT / "schemas/2.0.0/schema.json").read_bytes()
    assert (
        authoritative
        == (ROOT / "src/cloudtcp_dxf/schemas/2.0.0/schema.json").read_bytes()
    )
    schema = json.loads(authoritative)
    Draft202012Validator.check_schema(schema)
    standalone = Draft202012Validator(schema, format_checker=FormatChecker())
    standalone.validate(network())
    assert len(v2_validator().schema["$defs"]["entity"]["oneOf"]) == 24


def test_traceability_inventory_is_preserved():
    import re

    text = (ROOT / "docs/schema-v2/rule-traceability.md").read_text()
    clauses = re.findall(r"^\| \[(Full|W1) ([^]]+)\]", text, re.M)
    assert len(clauses) == len(set(clauses)) == 504
    assert len(re.findall(r"^\| G\d+ \|", text, re.M)) == 37


def test_representative_fixture_is_valid():
    for file in (ROOT / "examples/v2").glob("*.document.json"):
        validate_v2_document(json.loads(file.read_text()))


def specialist():
    return json.loads((ROOT / "examples/v2/specialist.document.json").read_text())


def test_a09_a14_a20_a28_safety_facts_remain_facts():
    d = specialist()
    validate_v2_document(d)
    sight = next(o for o in d["observations"] if o["id"] == "sight")
    assert sight["metric"] == "stopping_sight_distance" and sight["reference_locations"]
    facility = next(e for e in d["entities"] if e["kind"] == "facility")
    assert facility["surface"]["slip_resistant"] is False
    assert facility["running_slope"]["value"] < 0
    cone = next(
        e
        for e in d["entities"]
        if e.get("device_type") == "cone" and e["kind"] == "device"
    )
    assert cone["specification"]["height"] == {"value": 1, "unit": "in"}
    assert (
        next(o for o in d["observations"] if o["id"] == "occupancy")["value"] is False
    )
    assert (
        next(o for o in d["observations"] if o["id"] == "queue")["metric"]
        == "queue_length"
    )
    cone["specification"]["height"]["value"] = -1
    fail(d, "schema_minimum")


@pytest.mark.parametrize(
    "subtype",
    [
        "sign",
        "cone",
        "drum",
        "vertical_panel",
        "tubular_marker",
        "barrier",
        "barricade",
        "arrow_board",
        "message_sign",
        "afad",
        "signal",
        "audible_device",
        "warning_light",
    ],
)
def test_r3_each_subtype_accepts_its_specification_and_rejects_other_variant_fields(
    subtype,
):
    d = specialist()
    device = next(e for e in d["entities"] if e["id"] == subtype)
    validate_v2_document(d)
    device["specification"]["undeclared_variant_field"] = True
    fail(d, "schema_additionalProperties")


@pytest.mark.parametrize(
    "change,code",
    [
        ("operator_is_device", "wrong_target_kind"),
        ("sign_parent_is_barrier", "wrong_target_kind"),
        ("stop_line_is_crosswalk", "wrong_target_kind"),
        ("mount_surface_is_road", "wrong_target_kind"),
        ("negative_support_count", "schema_minimum"),
        ("bad_frequency", "schema_enum"),
        ("mount_top_below_bottom", "mount_heights"),
        ("facility_cycle", "cycle"),
        ("slope_wrong_unit", "schema_const"),
        ("circle_missing_diameter", "schema_required"),
    ],
)
def test_r2_r3_integrity(change, code):
    d = specialist()
    entities = {e["id"]: e for e in d["entities"]}
    if change == "operator_is_device":
        entities["afad"]["specification"]["operator_actor_refs"] = ["sign"]
    elif change == "sign_parent_is_barrier":
        entities["sign"]["specification"]["assembly_parent_ref"] = "barrier"
    elif change == "stop_line_is_crosswalk":
        entities["stop"]["marking_type"] = "crosswalk"
    elif change == "mount_surface_is_road":
        entities["warning_light"]["mount"]["reference_surface_ref"] = "road"
    elif change == "negative_support_count":
        entities["barricade"]["specification"]["support_count"] = -1
    elif change == "bad_frequency":
        entities["warning_light"]["specification"]["flash_rate"]["unit"] = "mph"
    elif change == "mount_top_below_bottom":
        entities["warning_light"]["mount"]["top_height"]["value"] = 0
    elif change == "facility_cycle":
        entities["facility"]["parent_facility_ref"] = "facility"
    elif change == "slope_wrong_unit":
        entities["facility"]["running_slope"]["unit"] = "%"
    elif change == "circle_missing_diameter":
        entities["sign"]["specification"]["shape"] = "circle"
    fail(d, code)


def test_phase_order_evidence_intervals_and_assertion_pointer_escaping():
    d = network()
    d["phases"][0].update(
        start_at="2026-11-19T20:00:00Z", end_at="2026-11-19T21:00:00Z"
    )
    d["phases"].append(
        {
            "id": "remove",
            "name": "Removal",
            "phase_type": "removal",
            "predecessor_refs": ["work"],
            "start_at": "2026-11-19T20:30:00Z",
        }
    )
    fail(d, "phase_order")
    d["phases"][1]["start_at"] = "2026-11-19T21:00:00Z"
    validate_v2_document(d)
    d["assertions"] = [
        {
            "id": "a",
            "subject_ref": "run",
            "path": "/spacing/value",
            "status": "withdrawn",
            "method": "measured",
            "evidence_refs": ["source"],
            "scope": {"phase_refs": ["work"]},
            "valid_from": "2026-11-19T20:00:00Z",
            "valid_to": "2026-11-19T19:00:00Z",
        }
    ]
    fail(d, "reversed_interval")
    d["assertions"][0].pop("valid_to")
    d["assertions"][0]["path"] = "/spacing/~2"
    fail(d, "schema_pattern")
    d["assertions"][0]["path"] = "/spacing/missing"
    fail(d, "invalid_pointer")


def test_observation_derivation_cycle_and_alternative_quantity_dimensions():
    d = network()
    d["observations"] = [
        {
            "id": "a",
            "subject_refs": ["road"],
            "metric": "queue_length",
            "value": {"value": 1, "unit": "ft"},
            "input_refs": ["b"],
        },
        {
            "id": "b",
            "subject_refs": ["road"],
            "metric": "queue_length",
            "value": {"value": 1, "unit": "ft"},
            "input_refs": ["a"],
        },
    ]
    fail(d, "cycle")
    d["observations"][1].pop("input_refs")
    d["assertions"] = [
        {
            "id": "assert",
            "subject_ref": "a",
            "path": "/value",
            "status": "disputed",
            "method": "measured",
            "evidence_refs": ["source"],
            "scope": {"phase_independent": True},
            "alternatives": [
                {"value": {"value": 2, "unit": "mph"}, "evidence_refs": ["source"]}
            ],
        }
    ]
    fail(d, "alternative_type")


def test_no_trailing_newline_ids_or_unbounded_complete_scope():
    d = network()
    d["entities"][0]["id"] = "road\n"
    fail(d, "schema_pattern")
    d = network()
    d["completeness"] = [
        {
            "id": "c",
            "scope": {"subject_refs": [], "phase_refs": ["work"]},
            "state": "complete",
            "evidence_refs": ["source"],
            "method": "manual_inventory",
        }
    ]
    fail(d, "schema_minItems")


def test_evidence_and_inventory_cannot_expand_explicit_phase_scope():
    d = network()
    d["phases"].append({"id": "other", "name": "Other", "phase_type": "idle"})
    d["entities"][1]["phase_refs"] = ["work"]
    d["observations"] = [
        {
            "id": "o",
            "subject_refs": ["north"],
            "phase_refs": ["other"],
            "metric": "observed_speed",
            "value": {"value": 10, "unit": "mph"},
        }
    ]
    fail(d, "observation_phase_scope")
    d.pop("observations")
    d["completeness"] = [
        {
            "id": "c",
            "scope": {"subject_refs": ["north"], "phase_refs": ["other"]},
            "state": "partial",
            "method": "manual_inventory",
            "evidence_refs": ["source"],
        }
    ]
    fail(d, "completeness_phase_scope")


def test_run_subtype_gap_membership_and_legitimate_network_cycles():
    d = network()
    d["entities"].append({"id": "cone", "kind": "device", "device_type": "cone"})
    run = d["entities"][10]
    run["individual_device_refs"] = ["cone"]
    run["specification"] = {"height": {"value": 1, "unit": "in"}}
    d["entities"][5]["successor_refs"] = ["path"]
    validate_v2_document(d)
    run["specification"]["barricade_type"] = "III"
    fail(d, "schema_additionalProperties")
    run["specification"].pop("barricade_type")
    run["gap_measurements"] = [
        {
            "from_device_ref": "cone",
            "to_device_ref": "cone",
            "gap": {"value": 1, "unit": "ft"},
        }
    ]
    fail(d, "self_link")
