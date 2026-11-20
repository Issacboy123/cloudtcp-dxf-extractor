import json
from copy import deepcopy
from importlib.resources import files
from pathlib import Path
import ezdxf
import pytest
from cloudtcp_dxf.extract import extract_dxf
from cloudtcp_dxf.if_conversion import convert_dxf, convert_extraction, station_offset, validate_if
from cloudtcp_dxf.cli import main
from cloudtcp_dxf.validation import ConversionError

def config():
    return {
        "site": {"name": "Synthetic", "coordinate_system": "local", "units": "feet", "road_name": "Example Rd", "state": "CA"},
        "typical_application": {"type": "lane_closure", "direction": "NB", "posted_speed_mph": 35, "lanes_total": 2},
        "zones": [{"zone_id": "Z1", "type": "work", "start_station": 0, "end_station": 100}],
        "centerline": {"origin": [0, 0], "endpoint": [100, 0]},
        "block_mappings": {"W20_1": {"type": "sign", "mutcd_code": "W20-1", "zone_id": "Z1"}}
    }

def fixture(tmp_path):
    doc = ezdxf.new()
    doc.units = 2  # Explicitly feet; modern DXF templates otherwise default to meters.
    doc.blocks.new("W20_1")
    doc.blocks.new("OTHER")
    m = doc.modelspace()
    m.add_line((0, 0), (100, 0), dxfattribs={"layer": "Road"})
    m.add_blockref("W20_1", (20, 5), dxfattribs={"layer": "Signs"})
    m.add_blockref("OTHER", (30, 6))
    path = tmp_path / "fixture.dxf"
    doc.saveas(path)
    return path

def test_extract(tmp_path):
    data = extract_dxf(fixture(tmp_path))
    assert data["source"]["extracted_entity_count"] == 3
    assert data["entity_types"]["INSERT"] == 2
    assert data["log"]["audit_errors"] == 0

def test_positions():
    assert station_offset([20, 5], [0, 0], [100, 0])["side"] == "left"
    assert station_offset([20, -5], [0, 0], [100, 0])["side"] == "right"
    with pytest.raises(ValueError):
        station_offset([1, 2], [0, 0], [0, 0])

def test_conversion(tmp_path):
    document, log = convert_dxf(fixture(tmp_path), config())
    assert len(document["elements"]) == 1
    assert document["elements"][0]["mutcd_code"] == "W20-1"
    assert document["elements"][0]["position"]["station"] == 20
    assert log["unmapped_blocks"] == {"OTHER": 1}

def test_missing_facts_not_fabricated(tmp_path):
    with pytest.raises(ValueError, match="centerline"):
        convert_dxf(fixture(tmp_path), {"site": {}, "typical_application": {}, "zones": []})

def test_cli(tmp_path):
    path = fixture(tmp_path)
    output, log = tmp_path / "out.json", tmp_path / "log.json"
    assert main([str(path), "-o", str(output), "--log", str(log)]) == 0
    assert json.loads(output.read_text())["source"]["extracted_entity_count"] == 3


@pytest.fixture
def extraction(tmp_path):
    return extract_dxf(fixture(tmp_path))


def test_packaged_schema_matches_supplied_contract():
    packaged = files("cloudtcp_dxf").joinpath("tcp-intermediate-format.schema.json").read_bytes()
    supplied = Path(__file__).parents[1].joinpath("tcp-intermediate-format.schema.json").read_bytes()
    assert packaged == supplied


def test_all_supported_elements(extraction):
    cfg = config()
    cfg["block_mappings"]["OTHER"] = {"type": "arrow_board", "mode": "sequential_arrow", "zone_id": "Z1"}
    extra = deepcopy(extraction["entities"][1])
    extra.update(handle="FLAG", block_name="FLAGGER")
    extraction["entities"].append(extra)
    cfg["block_mappings"]["FLAGGER"] = {"type": "flagger", "controls": "NB"}
    document, report = convert_extraction(extraction, cfg)
    validate_if(document)
    assert [e["type"] for e in document["elements"]] == ["sign", "arrow_board", "flagger"]
    assert report["converted_elements"] == 3
    assert report["skipped_elements"] == report["unmapped_elements"] == 0


@pytest.mark.parametrize("mapping, reason", [
    ({"type": "sign"}, "mutcd_code"),
    ({"type": "sign", "mutcd_code": 12}, "string"),
    ({"type": "sign", "mutcd_code": "W20-1", "mode": "flashing"}, "mode"),
    ({"type": "arrow_board", "mode": "not-a-mode"}, "not-a-mode"),
    ({"type": "arrow_board", "mode": "flashing", "legend": "AHEAD"}, "legend"),
    ({"type": "flagger", "controls": "north"}, "north"),
    ({"type": "flagger", "position": {"station": 5}}, "position"),
    ({"type": "sign", "mutcd_code": "W20-1", "zone_id": "missing"}, "Unknown zone_id"),
    ({"type": "device_line"}, "Unsupported mapping type"),
    ({"type": []}, "Unsupported mapping type"),
    (None, "Mapping must be an object"),
])
def test_bad_mappings_skip_and_identify_every_affected_handle(extraction, mapping, reason):
    cfg = config()
    cfg["block_mappings"]["W20_1"] = mapping
    cfg["block_mappings"]["OTHER"] = {"type": "flagger"}
    document, report = convert_extraction(extraction, cfg)
    assert [e["type"] for e in document["elements"]] == ["flagger"]
    assert report["skipped_elements"] == 1
    assert sum(report["skipped_mappings"].values()) == 1
    affected = [i for i in report["issues"] if i.get("source", {}).get("block") == "W20_1"]
    assert affected and all(i["severity"] == "warning" for i in affected)
    assert any(reason in i["reason"] for i in affected)
    assert all(i["path"].startswith("/block_mappings/W20_1") for i in affected)
    assert all(i["source"]["handle"] == extraction["entities"][1]["handle"] for i in affected)
    validate_if(document)


def test_unused_invalid_mapping_is_reported(extraction):
    cfg = config()
    cfg["block_mappings"]["UNUSED"] = {"type": "sign"}
    _, report = convert_extraction(extraction, cfg)
    assert any(i["path"] == "/block_mappings/UNUSED/" for i in report["issues"])
    assert report["skipped_elements"] == 0


@pytest.mark.parametrize("code,target,station,offset", [
    (2, "feet", 20, 5),
    (6, "feet", 65.6168, 16.4042),
    (2, "meters", 6.096, 1.524),
    (1, "feet", 1.6667, 0.4167),
    (4, "meters", 0.02, 0.005),
])
def test_units(extraction, code, target, station, offset):
    extraction["source"]["drawing_units_code"] = code
    cfg = config()
    cfg["site"]["units"] = target
    original_zones = deepcopy(cfg["zones"])
    document, report = convert_extraction(extraction, cfg)
    assert document["elements"][0]["position"] == {"station": station, "offset": offset, "side": "left"}
    assert document["zones"] == original_zones
    assert report["units"]["assumed"] is False


@pytest.mark.parametrize("code", [0, 99, None])
def test_unknown_units_continue_with_explicit_assumption(extraction, code):
    extraction["source"]["drawing_units_code"] = code
    document, report = convert_extraction(extraction, config())
    assert document["elements"][0]["position"]["station"] == 20
    assert report["units"]["assumed"] is True
    assert report["units"]["scale"] == 1
    assert any("assuming source coordinates" in warning for warning in report["warnings"])


def test_source_units_override(extraction):
    cfg = config()
    cfg["source_units"] = "inches"
    document, report = convert_extraction(extraction, cfg)
    assert document["elements"][0]["position"]["station"] == 1.6667
    assert report["units"]["source_units_override"] == "inches"
    assert report["units"]["resolved_source_units_code"] == 1


def test_survey_feet_remain_distinct_from_international_feet(extraction):
    cfg = config()
    cfg["source_units"] = "us_survey_feet"
    _, report = convert_extraction(extraction, cfg)
    assert report["units"]["assumed"] is False
    assert report["units"]["scale"] == pytest.approx((1200 / 3937) / 0.3048)
    assert report["units"]["scale"] > 1


def test_invalid_source_units_override_fails(extraction):
    cfg = config()
    cfg["source_units"] = "furlongs"
    with pytest.raises(ConversionError, match="source_units"):
        convert_extraction(extraction, cfg)


def test_reversed_centerline():
    assert station_offset([20, 5], [100, 0], [0, 0]) == {"station": 80, "offset": 5, "side": "right"}


@pytest.mark.parametrize("line", [
    {"origin": [0, 0], "endpoint": [0, 0]},
    {"origin": [0, 0], "endpoint": [float("nan"), 0]},
    {"origin": [0, 0], "endpoint": [100]},
    {"origin": [0, 0], "endpoint": [100, 0, float("inf")]},
    {},
])
def test_centerline_validated_without_inserts(extraction, line):
    cfg = config()
    cfg["centerline"] = line
    extraction["entities"] = []
    with pytest.raises(ConversionError, match="centerline") as raised:
        convert_extraction(extraction, cfg)
    assert raised.value.report["issues"][0]["path"] == "/centerline"


def test_nonfinite_insert_is_skipped(extraction):
    extraction["entities"][1]["geometry"]["insert"][0] = float("nan")
    document, report = convert_extraction(extraction, config())
    assert document["elements"] == []
    assert report["skipped_elements"] == 1
    assert any("finite" in i["reason"] and "source" in i for i in report["issues"])
    json.dumps(report, allow_nan=False)


@pytest.mark.parametrize("change,reason", [
    ("duplicate_zones", "Duplicate zone_id"),
    ("reversed_zone", "end_station precedes"),
    ("unordered_zones", "increasing start_station"),
    ("too_many_closed_lanes", "lanes_closed exceeds"),
    ("empty_zones", "non-empty"),
    ("missing_site_name", "name"),
    ("extra_site_field", "unexpected"),
    ("invalid_date", "date"),
    ("nonfinite_speed", "finite"),
])
def test_invalid_project_metadata_fails(extraction, change, reason):
    cfg = config()
    if change == "duplicate_zones":
        cfg["zones"].append(deepcopy(cfg["zones"][0]))
    elif change == "reversed_zone":
        cfg["zones"][0]["end_station"] = -1
    elif change == "unordered_zones":
        cfg["zones"].append({"zone_id": "Z2", "type": "advance_warning", "start_station": -10, "end_station": 0})
    elif change == "too_many_closed_lanes":
        cfg["typical_application"]["lanes_closed"] = 3
    elif change == "empty_zones":
        cfg["zones"] = []
    elif change == "missing_site_name":
        del cfg["site"]["name"]
    elif change == "extra_site_field":
        cfg["site"]["made_up"] = True
    elif change == "invalid_date":
        cfg["site"]["created_date"] = "2026-99-99"
    elif change == "nonfinite_speed":
        cfg["typical_application"]["posted_speed_mph"] = float("nan")
    with pytest.raises(ConversionError) as raised:
        convert_extraction(extraction, cfg)
    assert any(reason in i["reason"] for i in raised.value.report["issues"])


def test_duplicate_element_ids_fail(extraction):
    extraction["entities"].append(deepcopy(extraction["entities"][1]))
    with pytest.raises(ConversionError, match="Duplicate element_id"):
        convert_extraction(extraction, config())


def test_overlap_and_containment_are_advisory(extraction):
    cfg = config()
    cfg["zones"][0]["end_station"] = 10
    cfg["zones"].append({"zone_id": "Z2", "type": "transition", "start_station": 5, "end_station": 100})
    document, report = convert_extraction(extraction, cfg)
    assert any("overlap" in i["reason"] and i["severity"] == "warning" for i in report["issues"])
    assert any("outside assigned zone" in i["reason"] and i["source"]["block"] == "W20_1" for i in report["issues"])
    validate_if(document)


def test_optional_context_and_observations_are_preserved(extraction):
    cfg = config()
    cfg["temporal_context"] = {"timestamp": "2026-10-06T17:15:00Z", "weather": "clear"}
    cfg["observations"] = [{"obs_id": "OBS1", "source": "radar", "station": 20, "zone_id": "Z1", "occupancy_pct": 10}]
    original = deepcopy(cfg)
    document, _ = convert_extraction(extraction, cfg)
    assert document["observations"] == cfg["observations"]
    assert document["temporal_context"] == cfg["temporal_context"]
    assert "predictions" not in document
    assert cfg == original
    document["observations"][0]["station"] = 100
    assert cfg == original


@pytest.mark.parametrize("change,reason", [("duplicate", "Duplicate obs_id"), ("zone", "Unknown zone_id"), ("occupancy", "100"), ("timestamp", "date-time")])
def test_invalid_observations_and_context(extraction, change, reason):
    cfg = config()
    cfg["observations"] = [{"obs_id": "OBS1", "source": "radar", "station": 20}]
    if change == "duplicate":
        cfg["observations"] *= 2
    elif change == "zone":
        cfg["observations"][0]["zone_id"] = "missing"
    elif change == "occupancy":
        cfg["observations"][0]["occupancy_pct"] = 101
    else:
        cfg["temporal_context"] = {"timestamp": "yesterday"}
    with pytest.raises(ConversionError) as raised:
        convert_extraction(extraction, cfg)
    assert any(reason in i["reason"] for i in raised.value.report["issues"])


def test_converter_rejects_predictions(extraction):
    cfg = config()
    cfg["predictions"] = {}
    with pytest.raises(ConversionError, match="model-owned"):
        convert_extraction(extraction, cfg)


def test_validator_checks_existing_prediction_references(extraction):
    document, _ = convert_extraction(extraction, config())
    document["predictions"] = {"recommendations": [{"action": "Review", "priority": "info", "element_id": "missing"}]}
    with pytest.raises(ConversionError, match="Unknown element_id"):
        validate_if(document)


def test_additional_schema_cannot_bypass_bundled_contract(extraction, tmp_path):
    document, _ = convert_extraction(extraction, config())
    schema = tmp_path / "loose.json"
    schema.write_text("{}")
    document["site"]["units"] = "furlongs"
    with pytest.raises(ConversionError, match="units"):
        validate_if(document, schema)


def test_cli_if_success_without_schema_flag(tmp_path):
    path = fixture(tmp_path)
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(json.dumps(config()))
    output, log = tmp_path / "out.if.json", tmp_path / "log.json"
    assert main([str(path), "--if-config", str(cfg_path), "-o", str(output), "--log", str(log)]) == 0
    validate_if(json.loads(output.read_text()))
    assert json.loads(log.read_text())["converted_elements"] == 1


@pytest.mark.parametrize("failure", ["metadata", "additional_schema", "bad_config_json"])
def test_cli_failure_keeps_existing_output_and_writes_diagnostics(tmp_path, failure):
    path = fixture(tmp_path)
    cfg = config()
    if failure == "metadata":
        del cfg["site"]["name"]
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text("{" if failure == "bad_config_json" else json.dumps(cfg))
    output, log = tmp_path / "out.if.json", tmp_path / "log.json"
    output.write_text("previous export")
    args = [str(path), "--if-config", str(cfg_path), "-o", str(output), "--log", str(log)]
    if failure == "additional_schema":
        schema = tmp_path / "additional.json"
        schema.write_text(json.dumps({"properties": {"elements": {"maxItems": 0}}}))
        args.extend(["--schema", str(schema)])
    assert main(args) == 1
    assert output.read_text() == "previous export"
    assert any(i["severity"] == "error" for i in json.loads(log.read_text())["issues"])


def test_cli_rejects_log_output_collision(tmp_path):
    path = fixture(tmp_path)
    output = tmp_path / "out.json"
    output.write_text("previous export")
    assert main([str(path), "-o", str(output), "--log", str(output)]) == 1
    assert output.read_text() == "previous export"
