# CloudTCP DXF Extractor

Reusable Python DXF modelspace extraction and **conservative** mapping of named block references to CloudTCP IF v1.

## Features

- Reads DXF modelspace using `ezdxf` and inventories layers and entity types.
- Extracts lines, polylines, arcs, circles, text, ellipses and named block inserts with DXF handles.
- Logs unsupported entities rather than silently treating them as converted.
- Optional IF v1 JSON conversion for *explicitly mapped* sign, arrow-board and flagger blocks.
- Converts insert coordinates to station/offset relative to a **user-provided straight centerline**, normalized to site units.
- Validates every IF export against the bundled CloudTCP v1 schema and checks document relationships.
- Writes per-file diagnostics, including skipped entities, CAD handles, and unit assumptions.

## Install and test

```bash
python -m pip install -e ".[dev]"
python -m pytest
```

## Inspect a DXF

```bash
cloudtcp-dxf input.dxf -o extracted.json --log extraction-log.json
```

## Map recognized named blocks to IF v1

Copy and **edit** `examples/if-config.example.json`, replacing every illustrative site, traffic, zone and centerline value with verified facts specific to the drawing.

```bash
cloudtcp-dxf input.dxf --if-config site-config.json -o output.if.json --log conversion-log.json
```

The supplied `tcp-intermediate-format.schema.json` is bundled in the installed package. Both library and CLI conversions always validate against it, including date/time formats. `--schema extra-constraints.json` adds constraints to the bundled contract; it cannot disable that contract. `validate_if(document, schema_path=None)` also checks existing IF documents, including references in model-owned predictions.

## Configuration and units

- `site`, `typical_application`, `zones`, and `centerline` are required. Project metadata must conform to the supplied schema; zones must have unique IDs, increasing start stations, and ends at or after their starts. Closed lanes cannot exceed total lanes.
- `centerline.origin` and `centerline.endpoint` use the drawing's coordinates and units. Computed stations and offsets use `site.units` (`feet` or `meters`). Left/right face increasing station; point offsets are magnitudes.
- Source units come from DXF `$INSUNITS`. An optional `source_units` override accepts `inches`, `feet`, `millimeters`, `centimeters`, `meters`, `yards`, or `us_survey_feet`. Use verified source units when overriding drawing metadata.
- If drawing units are missing or unsupported, conversion continues with scale 1, assumes the coordinates already use `site.units`, and records this uncertainty in `units.assumed` and the warning log. An invalid explicit override is a configuration error.
- Configured zone bounds and observation stations already use `site.units` and are not rescaled. Explicitly suffixed fields, such as `queue_length_ft`, keep their stated units.
- `block_mappings` names match inserts without regard to case and must be unique ignoring case. Each mapping accepts `type`, optional `zone_id`, and the fields for that element: signs accept `mutcd_code` (required), `legend`, `size_inches`, and `face_direction`; arrow boards require `mode`; flaggers optionally accept `controls`. Position, ID, and source are generated from CAD.
- Optional `temporal_context` and `observations` are preserved and validated. Observation IDs must be unique and zone references must exist. The converter rejects `predictions` in configuration because predictions are authored by the model.

## Partial conversion and diagnostics

Invalid mappings and insert coordinates are skipped; other valid entities are exported. Unrecognized block names remain unmapped. A schema-valid export may contain no elements, in which case the report includes a warning. Invalid project metadata, duplicate generated IDs, or document validation failures stop export. Zone overlap and placements outside assigned zones produce advisory warnings rather than blocking export.

Use `--log conversion-log.json` to retain diagnostics on success or failure. The report retains `converted_elements`, `unmapped_blocks`, and `skipped_mappings` and adds `skipped_elements`, `unmapped_elements`, a `units` summary, and structured `issues`. Each issue contains `severity`, `reason`, and a JSON-pointer-style `path`; entity issues also contain CAD `source` details. Mapping paths refer to configuration, entity geometry paths to the extraction, and document paths to the IF document. Skipped entities are warnings; errors prevent export.

Failed validation leaves an existing output untouched. JSON writes use temporary files followed by atomic replacement. Output and diagnostic paths must differ from each other and from the input, configuration, and schema paths.

Library callers still receive `(document, report)` from `convert_dxf` or `convert_extraction`. Failed conversion raises `ConversionError` (a `ValueError`) with its diagnostics available as `exc.report`.

After updating the supplied root schema, synchronize the package resource at `src/cloudtcp_dxf/tcp-intermediate-format.schema.json`; a test checks byte-for-byte equality.

## Important limitations

- **No native DGN support**. The reader only accepts DXF. A separate DGN adapter or carefully validated DGN-to-DXF export is needed.
- **No reliable classification of flattened signs or cones**. The supplied Alameda DXF has no `INSERT` entities; conversion from that file will yield no identified signs.
- No automatic road centerline discovery, curved-line stationing, sign placement/legend disambiguation, cone aggregation, basemap reconstruction, xref resolution, or CAD round-trip yet.
- Required IF fields such as posted speed, number of lanes and zones are **not inferred**. Explicit configuration is necessary.
- The IF v1 schema cannot encode complete basemap/road geometry. Raw extracted CAD data should be preserved separately.
- This project does not certify traffic-control compliance.

The example config is deliberately illustrative, **not real Alameda metadata**. Do not use example values for engineering decisions.
