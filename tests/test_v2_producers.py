import json
from copy import deepcopy

import pytest
from test_pipeline import config, fixture
from test_v2 import network

from cloudtcp_dxf.cli import main
from cloudtcp_dxf.extract import extract_dxf
from cloudtcp_dxf.if_conversion import convert_extraction
from cloudtcp_dxf.v2_cli import migrate_main, validate_main
from cloudtcp_dxf.v2_conversion import convert_v2_extraction
from cloudtcp_dxf.v2_migration import migrate_v1_document
from cloudtcp_dxf.v2_validation import V2ValidationError, validate_v2_document
from cloudtcp_dxf.validation import ConversionError


def legacy(tmp_path):
    document, _ = convert_extraction(extract_dxf(fixture(tmp_path)), config())
    return document


def v2config():
    d = network()
    return {
        "document": d,
        "stationing": {"frame_ref": "station", "origin": [0, 0], "endpoint": [100, 0]},
        "block_mappings": {
            "W20_1": {
                "kind": "device",
                "device_type": "sign",
                "specification": {"mutcd_code": "W20-1"},
                "approach_refs": ["north"],
                "phase_refs": ["work"],
            }
        },
    }


def test_a25_migration_preserves_all_original_fields_and_invents_no_inventory(tmp_path):
    original = legacy(tmp_path)
    before = deepcopy(original)
    original["site"]["city"] = "Example"
    original["site"]["county"] = "Example County"
    original["temporal_context"] = {
        "timestamp": "2026-11-19T20:00:00Z",
        "visibility_mi": 2,
        "weather": "fog",
    }
    before = deepcopy(original)
    result = migrate_v1_document(original)
    d = result["document"]
    validate_v2_document(d)
    assert original == before
    assert d["legacy_records"][0]["value"] == before
    assert d["phases"] == d["completeness"] == []
    assert not any(
        e["kind"] in ("lane", "approach", "control", "application")
        for e in d["entities"]
    )
    assert not any(o["metric"] == "stopping_sight_distance" for o in d["observations"])
    report = result["migration_report"]
    assert report["summary"]["fields"]["ambiguous"] >= 2
    assert d["project_id"] == "legacy-import:" + report["source_document_hash"]
    again = migrate_v1_document(original)
    assert d["document_id"] != again["document"]["document_id"]
    assert report["id_map"] == again["migration_report"]["id_map"]
    assert report["summary"] == again["migration_report"]["summary"]


@pytest.mark.parametrize(
    "units,side,offset",
    [("meters", "left", 3.048), ("meters", "right", -3.048), ("feet", "left", 10)],
)
def test_a08_taper_feet_are_explicitly_converted(tmp_path, units, side, offset):
    d = legacy(tmp_path)
    d["site"]["units"] = units
    d["elements"] = [
        {
            "element_id": "taper/one~",
            "type": "taper",
            "taper_type": "merge",
            "start_station": 0,
            "end_station": 100,
            "start_offset": 0,
            "end_offset": 10,
            "side": side,
            "lane_width_ft": 12,
        }
    ]
    result = migrate_v1_document(d)
    taper = next(e for e in result["document"]["entities"] if e["kind"] == "taper")
    assert taper["end_location"]["offset"] == pytest.approx(offset)
    assert "offset_width" not in taper
    assert "%2F" in taper["id"]
    validate_v2_document(result["document"])


@pytest.mark.parametrize("change", ["no_side", "negative_offset", "reversed_stations"])
def test_a08_ambiguous_tapers_preserve_without_endpoints(tmp_path, change):
    d = legacy(tmp_path)
    e = {
        "element_id": "t",
        "type": "taper",
        "taper_type": "merge",
        "start_station": 0,
        "end_station": 100,
        "start_offset": 0,
        "end_offset": 10,
        "side": "left",
    }
    if change == "no_side":
        e.pop("side")
    elif change == "negative_offset":
        e["end_offset"] = -10
    else:
        e["end_station"] = -1
    d["elements"] = [e]
    result = migrate_v1_document(d)
    taper = next(e for e in result["document"]["entities"] if e["kind"] == "taper")
    assert "start_location" not in taper and "end_location" not in taper
    assert result["document"]["legacy_records"][0]["value"] == d
    assert any(
        e["disposition"] == "ambiguous" and "Taper endpoints" in e["reason"]
        for e in result["migration_report"]["entries"]
    )


def test_line_offsets_are_not_given_taper_units(tmp_path):
    d = legacy(tmp_path)
    d["elements"] = [
        {
            "element_id": "barrier",
            "type": "device_line",
            "device": "barrier",
            "start_station": 0,
            "end_station": 100,
            "start_offset": 2,
            "end_offset": 2,
            "side": "left",
            "spacing_ft": 10,
        }
    ]
    result = migrate_v1_document(d)
    run = next(e for e in result["document"]["entities"] if e["kind"] == "device_run")
    assert (
        run["device_type"] == "barrier"
        and "geometry" not in run
        and "taper_ref" not in run
    )
    assert run["spacing"] == {"value": 10, "unit": "ft"}


@pytest.mark.parametrize("offset,side", [(-1, "left"), (5, "center")])
def test_invalid_legacy_magnitude_is_preserved_not_repaired(tmp_path, offset, side):
    d = legacy(tmp_path)
    d["elements"][0]["position"].update(offset=offset, side=side)
    result = migrate_v1_document(d)
    sign = next(
        e for e in result["document"]["entities"] if e.get("device_type") == "sign"
    )
    assert "location" not in sign
    assert result["document"]["legacy_records"][0]["value"] == d


def test_zero_length_features_sizes_and_ambiguous_boards(tmp_path):
    d = legacy(tmp_path)
    d["zones"][0]["end_station"] = 0
    d["elements"][0]["size_inches"] = "36 x 48"
    d["elements"][0]["face_direction"] = "NB"
    d["elements"].append(
        {
            "element_id": "b",
            "type": "arrow_board",
            "mode": "diamond",
            "position": {"station": 0, "offset": 0, "side": "center"},
        }
    )
    result = migrate_v1_document(d)
    entities = result["document"]["entities"]
    assert next(e for e in entities if e.get("device_type") == "sign")["specification"][
        "dimensions"
    ]["width"] == {"value": 36, "unit": "in"}
    assert "specification" not in next(
        e for e in entities if e.get("device_type") == "arrow_board"
    )
    assert all("shape" not in e.get("specification", {}) for e in entities)


def test_a24_observations_and_predictions_remain_distinct(tmp_path):
    d = legacy(tmp_path)
    d["observations"] = [
        {
            "obs_id": "o",
            "source": "radar",
            "station": 10,
            "zone_id": "Z1",
            "speed_mph": 20,
            "queue_length_ft": 30,
            "volume_vph": -1,
            "note": "Reading",
        }
    ]
    d["predictions"] = {
        "model_version": "demo",
        "predicted_at": "2026-11-19T20:00:00Z",
        "horizon_minutes": 15,
        "by_zone": [
            {
                "zone_id": "Z1",
                "queue_length_ft": 40,
                "delay_sec": 20,
                "throughput_vph": 30,
                "congestion_index": 0.5,
            }
        ],
        "recommendations": [
            {
                "action": "Review",
                "priority": "info",
                "zone_id": "Z1",
                "element_id": d["elements"][0]["element_id"],
            }
        ],
    }
    result = migrate_v1_document(d)
    v2 = result["document"]
    validate_v2_document(v2)
    assert (
        next(o for o in v2["observations"] if o["metric"] == "queue_length")["value"][
            "value"
        ]
        == 30
    )
    assert v2["predictions"][0]["metrics"][0]["value"]["value"] == 40
    assert not any(o["metric"] == "volume" for o in v2["observations"])
    assert not v2.get("decisions")
    d["predictions"].pop("model_version")
    result = migrate_v1_document(d)
    assert not result["document"].get("predictions")
    assert any(
        e["source_path"].startswith("/predictions/") and e["disposition"] == "ambiguous"
        for e in result["migration_report"]["entries"]
    )


def test_authored_bindings_conflict_without_overwriting(tmp_path):
    d = legacy(tmp_path)
    context = {
        "project_id": "authored-project",
        "entities": [{"id": "authored-road", "kind": "road", "road_name": "Different"}],
        "bindings": [
            {
                "source_path": "/site/road_name",
                "target_ref": "authored-road",
                "target_path": "/road_name",
            }
        ],
    }
    before = deepcopy(context)
    result = migrate_v1_document(d, context)
    assert context == before
    assert result["document"]["project_id"] == "authored-project"
    assert (
        next(e for e in result["document"]["entities"] if e["id"] == "authored-road")[
            "road_name"
        ]
        == "Different"
    )
    a = result["document"]["assertions"][0]
    assert (
        a["status"] == "disputed"
        and a["alternatives"][0]["value"] == d["site"]["road_name"]
    )
    validate_v2_document(result["document"])
    context["bindings"][0]["target_ref"] = "missing"
    with pytest.raises(V2ValidationError):
        migrate_v1_document(d, context)


def test_invalid_inputs_and_context_have_no_migrated_document(tmp_path):
    d = legacy(tmp_path)
    d["format_version"] = "2.0.0"
    with pytest.raises(V2ValidationError):
        migrate_v1_document(d)
    d = legacy(tmp_path)
    with pytest.raises(V2ValidationError):
        migrate_v1_document(
            d, {"entities": [{"id": "x", "kind": "road"}, {"id": "x", "kind": "road"}]}
        )
    with pytest.raises(V2ValidationError):
        migrate_v1_document(d, {"invent": True})


def test_v2_extraction_is_explicit_partial_and_keeps_source_handles(tmp_path):
    extraction = extract_dxf(fixture(tmp_path))
    cfg = v2config()
    before = deepcopy(cfg)
    d, report = convert_v2_extraction(extraction, cfg)
    validate_v2_document(d)
    assert cfg == before
    assert report["converted_elements"] == 1 and report["unmapped_elements"] == 1
    sign = next(e for e in d["entities"] if e["id"].startswith("cad-insert:"))
    assert sign["kind"] == "device" and sign["device_type"] == "sign"
    assert sign["location"]["offset"] == 5
    evidence = next(
        e for e in d["evidence"] if e["id"] == sign["source_evidence_refs"][0]
    )
    assert evidence["locator"]["handle"] == extraction["entities"][1]["handle"]
    assert report["issues"][0]["source"]["block"] == "OTHER"
    assert d["completeness"] == []
    assert not d.get("predictions")


def test_bad_v2_mapping_skips_with_handle_and_no_inserts_proves_no_absence(tmp_path):
    extraction = extract_dxf(fixture(tmp_path))
    cfg = v2config()
    cfg["block_mappings"]["W20_1"]["device_type"] = "afad"
    d, report = convert_v2_extraction(extraction, cfg)
    assert report["skipped_elements"] == 1 and report["issues"][-1]["source"]["handle"]
    extraction["entities"] = []
    d, report = convert_v2_extraction(extraction, v2config())
    assert report["converted_elements"] == 0 and d["completeness"] == []


def test_v2_extractor_rejects_predictions_and_v1_config(tmp_path):
    extraction = extract_dxf(fixture(tmp_path))
    with pytest.raises(ConversionError):
        convert_v2_extraction(extraction, config())
    cfg = v2config()
    cfg["document"]["predictions"] = []
    with pytest.raises(ConversionError, match="model-owned"):
        convert_v2_extraction(extraction, cfg)


@pytest.mark.parametrize("version_args", [[], ["--format-version", "2.0.0"]])
def test_cli_defaults_to_v2_and_preserves_explicit_v1(tmp_path, version_args):
    source = fixture(tmp_path)
    v1cfg = tmp_path / "v1.json"
    v2cfg = tmp_path / "v2.json"
    v1cfg.write_text(json.dumps(config()))
    v2cfg.write_text(json.dumps(v2config()))
    assert (
        main([str(source), "--format-version", "1.0.0", "--if-config", str(v1cfg)]) == 0
    )
    original = source.with_suffix(".if.json").read_bytes()
    assert json.loads(original)["format_version"] == "1.0.0"
    assert main([str(source), "--if-config", str(v2cfg), *version_args]) == 0
    output = source.with_suffix(".v2.if.json")
    assert json.loads(output.read_text())["format_version"] == "2.0.0"
    assert (
        output.with_suffix(".extracted.json").exists()
        and output.with_suffix(".report.json").exists()
    )
    assert source.with_suffix(".if.json").read_bytes() == original
    assert (
        main(
            [
                str(source),
                "--if-config",
                str(v2cfg),
                *version_args,
                "-o",
                str(source.with_suffix(".if.json")),
            ]
        )
        == 1
    )
    assert source.with_suffix(".if.json").read_bytes() == original
    assert validate_main([str(output)]) == 0


@pytest.mark.parametrize(
    "make_config,version_args,message",
    [
        (config, [], "Use --format-version 1.0.0"),
        (config, ["--format-version", "2.0.0"], "Use --format-version 1.0.0"),
        (v2config, ["--format-version", "1.0.0"], "Omit --format-version"),
    ],
)
def test_cli_config_version_mismatch_does_not_fallback(
    tmp_path, capsys, make_config, version_args, message
):
    source = fixture(tmp_path)
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps(make_config()))
    output = tmp_path / "existing.if.json"
    output.write_text("previous export")
    log = tmp_path / "diagnostics.json"
    assert (
        main(
            [
                str(source),
                "--if-config",
                str(cfg),
                *version_args,
                "-o",
                str(output),
                "--log",
                str(log),
            ]
        )
        == 1
    )
    assert message in capsys.readouterr().err
    assert output.read_text() == "previous export"
    assert not output.with_suffix(".extracted.json").exists()
    assert message in json.loads(log.read_text())["issues"][0]["reason"]


def test_cli_without_config_keeps_raw_inspection(tmp_path):
    source = fixture(tmp_path)
    assert main([str(source)]) == 0
    output = source.with_suffix(".extracted.json")
    assert (
        json.loads(output.read_text())["extraction_format"]
        == "cloudtcp-cad-extraction/0.1.0"
    )
    assert not source.with_suffix(".v2.if.json").exists()
    assert not source.with_suffix(".v2.if.report.json").exists()


def test_cli_explicit_v2_requires_config(tmp_path, capsys):
    source = fixture(tmp_path)
    with pytest.raises(SystemExit) as caught:
        main([str(source), "--format-version", "2.0.0"])
    assert caught.value.code == 2
    assert "--format-version 2.0.0 requires --if-config" in capsys.readouterr().err
    assert not source.with_suffix(".extracted.json").exists()


def test_migration_cli_preserves_original_and_protects_aliases(tmp_path):
    d = legacy(tmp_path)
    source = tmp_path / "legacy.json"
    source.write_text(json.dumps(d))
    before = source.read_bytes()
    assert migrate_main([str(source)]) == 0
    assert source.read_bytes() == before
    assert (
        source.with_suffix(".v2.json").exists()
        and source.with_suffix(".v2.migration.json").exists()
    )
    assert migrate_main([str(source), "-o", str(source)]) == 1
    alias = tmp_path / "alias.json"
    alias.symlink_to(source)
    assert migrate_main([str(source), "-o", str(alias)]) == 1
    assert source.read_bytes() == before


def test_migration_report_covers_every_source_leaf_and_context_types(tmp_path):
    from cloudtcp_dxf.v2_migration import _leaves

    d = legacy(tmp_path)
    d["observations"] = [
        {"obs_id": "x", "source": "radar", "station": 1, "volume_vph": 5}
    ]
    result = migrate_v1_document(d)
    assert {path for path, _ in _leaves(d)} <= {
        entry["source_path"] for entry in result["migration_report"]["entries"]
    }
    context = {
        "entities": [{"id": "road-authored", "kind": "road", "road_name": "Example"}],
        "bindings": [
            {
                "source_path": "/typical_application/lanes_total",
                "target_ref": "road-authored",
                "target_path": "/road_name",
            }
        ],
    }
    bound = migrate_v1_document(d, context)
    assert bound["document"]["assertions"][0]["status"] == "disputed"
    assert "alternatives" not in bound["document"]["assertions"][0]
    assert bound["document"]["legacy_records"][0]["value"] == d
    context["bindings"][0]["source_path"] = "/site/~2"
    with pytest.raises(V2ValidationError):
        migrate_v1_document(d, context)


def test_project_namespace_preserves_entity_ids_across_source_revisions(tmp_path):
    d = legacy(tmp_path)
    context = {"project_id": "stable-project"}
    first = migrate_v1_document(d, context)
    d["site"]["project_number"] = "new revision"
    second = migrate_v1_document(d, context)
    assert first["migration_report"]["id_map"] == second["migration_report"]["id_map"]
    assert first["document"]["document_id"] != second["document"]["document_id"]
    assert (
        first["document"]["project_id"]
        == second["document"]["project_id"]
        == "stable-project"
    )


def test_configured_extraction_declaration_stays_partial(tmp_path):
    extraction = extract_dxf(fixture(tmp_path))
    cfg = v2config()
    cfg["document"]["completeness"] = [
        {
            "id": "inventory",
            "scope": {
                "subject_refs": ["north"],
                "phase_refs": ["work"],
                "entity_kinds": ["device"],
                "device_types": ["sign"],
            },
            "state": "complete",
            "method": "configured_extraction",
            "evidence_refs": ["source"],
        }
    ]
    result, report = convert_v2_extraction(extraction, cfg)
    assert report["unmapped_elements"] == 1
    assert result["completeness"][0]["state"] == "partial"
    assert result["completeness"][0]["limitations"]
    assert cfg["document"]["completeness"][0]["state"] == "complete"


def test_cli_additional_constraints_cannot_bypass_v2_and_failure_retains_raw(tmp_path):
    path = fixture(tmp_path)
    cfg = v2config()
    config_path = tmp_path / "v2.json"
    config_path.write_text(json.dumps(cfg))
    output = tmp_path / "result.v2.json"
    output.write_text("previous v2")
    additional = tmp_path / "additional.json"
    additional.write_text(json.dumps({"properties": {"entities": {"maxItems": 0}}}))
    assert (
        main(
            [
                str(path),
                "--if-config",
                str(config_path),
                "-o",
                str(output),
                "--schema",
                str(additional),
            ]
        )
        == 1
    )
    assert output.read_text() == "previous v2"
    assert output.with_suffix(".extracted.json").exists()
    assert (
        json.loads(output.with_suffix(".report.json").read_text())["issues"][-1][
            "severity"
        ]
        == "error"
    )
    cfg["document"]["format_version"] = "1.0.0"
    config_path.write_text(json.dumps(cfg))
    additional.write_text("{}")
    assert (
        main(
            [
                str(path),
                "--if-config",
                str(config_path),
                "-o",
                str(output),
                "--schema",
                str(additional),
            ]
        )
        == 1
    )
    assert output.read_text() == "previous v2"


def test_standalone_validator_rejects_unsupported_version(tmp_path, capsys):
    path = tmp_path / "unsupported.json"
    path.write_text('{"format_version":"3.0.0"}')
    assert validate_main([str(path)]) == 1
    result = json.loads(capsys.readouterr().out)
    assert result["valid"] is False
    assert any(e["path"] == "/format_version" for e in result["diagnostics"])


def test_v2_acquisition_coordinates_convert_to_equivalent_physical_values(tmp_path):
    from cloudtcp_dxf.v2_validation import convert_quantity

    extraction = extract_dxf(fixture(tmp_path))
    feet_cfg = v2config()
    feet, _ = convert_v2_extraction(extraction, feet_cfg)
    metric_cfg = v2config()
    metric_cfg["document"]["reference_frames"][0]["units"] = "meters"
    metric, _ = convert_v2_extraction(extraction, metric_cfg)
    feet_location = next(
        e["location"] for e in feet["entities"] if e["id"].startswith("cad-insert:")
    )
    metric_location = next(
        e["location"] for e in metric["entities"] if e["id"].startswith("cad-insert:")
    )
    for coordinate in ("station", "offset"):
        assert convert_quantity(
            {"value": feet_location[coordinate], "unit": "ft"}, "m"
        ) == pytest.approx(metric_location[coordinate])


def test_invalid_migration_diagnostics_identify_json_and_semantic_layers(tmp_path):
    d = legacy(tmp_path)
    d["typical_application"]["posted_speed_mph"] = float("nan")
    with pytest.raises(V2ValidationError) as caught:
        migrate_v1_document(d)
    assert caught.value.diagnostics[0]["layer"] == "json"
    d = legacy(tmp_path)
    d["typical_application"]["lanes_closed"] = 10
    with pytest.raises(V2ValidationError) as caught:
        migrate_v1_document(d)
    assert caught.value.diagnostics[0]["layer"] == "semantic"


@pytest.mark.parametrize("sidecar", ["extracted", "report"])
@pytest.mark.parametrize("version_args", [[], ["--format-version", "2.0.0"]])
def test_sidecars_cannot_overwrite_other_v1_artifacts(tmp_path, sidecar, version_args):
    source = fixture(tmp_path)
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps(v2config()))
    output = tmp_path / "new-v2.json"
    raw = output.with_suffix(f".{sidecar}.json")
    previous = json.dumps(legacy(tmp_path))
    raw.write_text(previous)
    assert (
        main(
            [
                str(source),
                *version_args,
                "--if-config",
                str(cfg),
                "-o",
                str(output),
            ]
        )
        == 1
    )
    assert raw.read_text() == previous and not output.exists()
    original = tmp_path / "original.json"
    original.write_text(previous)
    assert migrate_main([str(original), "-o", str(output), "--report", str(raw)]) == 1
    assert raw.read_text() == previous and not output.exists()


@pytest.mark.parametrize("size", ['36" x 48"', "nonstandard", "9" * 400 + "x48"])
def test_unsupported_size_strings_preserve_instead_of_failing_or_guessing(
    tmp_path, size
):
    d = legacy(tmp_path)
    d["elements"][0]["size_inches"] = size
    result = migrate_v1_document(d)
    sign = next(
        e for e in result["document"]["entities"] if e.get("device_type") == "sign"
    )
    assert "dimensions" not in sign["specification"]
    assert result["document"]["legacy_records"][0]["value"] == d
    entry = next(
        e
        for e in result["migration_report"]["entries"]
        if e["source_path"] == "/elements/0/size_inches"
    )
    assert entry["disposition"] == "ambiguous"
