# CloudTCP DXF Extractor

Reusable Python DXF modelspace extraction and **conservative** mapping of named block references to CloudTCP IF v2.0.0, the default IF export format, with explicit legacy v1 support.

## Features

- Reads DXF modelspace using `ezdxf` and inventories layers and entity types.
- Extracts lines, polylines, arcs, circles, text, ellipses and named block inserts with DXF handles.
- Logs unsupported entities rather than silently treating them as converted.
- IF JSON conversion for *explicitly mapped* sign, arrow-board and flagger blocks.
- Converts insert coordinates to station/offset relative to a **user-provided straight reference line**, normalized to declared units.
- Validates exports against the selected bundled contract and checks supplied relationships.
- Provides independent v2 structural/semantic validation, typed plan facts and loss-preserving v1 migration.
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

## CloudTCP IF v2.0.0

IF conversion defaults to `2.0.0`. Edit [the synthetic v2 configuration](examples/v2/if-config.example.json)
with authored IDs, frames, phases and relationships before use.

```bash
cloudtcp-dxf input.dxf --if-config v2-config.json
cloudtcp-validate-v2 input.v2.if.json
```

`--format-version 2.0.0` also selects v2 explicitly. Without `--if-config`, the
command inspects raw DXF data as shown above; explicitly requesting v2 requires
configuration. V2 extraction defaults to `input.v2.if.json`, with
`input.v2.if.extracted.json` (raw acquisition) and `input.v2.if.report.json`
(diagnostics). Original drawings, configurations and v1 exports remain separate.
Existing v1 artifacts cannot be overwritten by v2 output or sidecars.

Python callers use the version-specific v2 functions:

```python
from cloudtcp_dxf.v2_conversion import convert_v2_dxf, convert_v2_extraction

document, report = convert_v2_dxf("input.dxf", config)
```

Start with the [schema handoff](docs/schema-v2/handoff.md) when delivering the
contract to another team. See [v2 usage and limitations](docs/schema-v2/implementation.md) and the
[release-gate evidence checklist](docs/schema-v2/release-checklist.md). The authoritative
Draft 2020-12 contract is [schemas/2.0.0/schema.json](schemas/2.0.0/schema.json).
Run `python tools/sync_schemas.py` after editing it; `--check` verifies the packaged
copy. A JSON Schema validator with date-format checking handles structure; use the
standalone validator for typed references, geometry and supplied-data consistency.
Validation reports data integrity only and never produces compliance or readiness results.

## Legacy IF v1 conversion and migration

Copy and **edit** `examples/if-config.example.json`, replacing every illustrative site, traffic, zone and centerline value with verified facts specific to the drawing.

```bash
cloudtcp-dxf input.dxf --format-version 1.0.0 --if-config site-config.json -o output.if.json --log conversion-log.json
cloudtcp-migrate-v1 output.if.json -o imported.v2.json
```

Legacy configurations require `--format-version 1.0.0`; they are not automatically
converted to v2 configurations. Migration retains the original v1 document, embeds
its entire JSON in a loss-preservation record and writes a structured migration report.

The supplied v1 `tcp-intermediate-format.schema.json` is bundled in the installed package. V1 library and CLI conversions always validate against it, including date/time formats. `--schema extra-constraints.json` adds constraints to the selected bundled contract; it cannot disable that contract. `validate_if(document, schema_path=None)` checks existing v1 IF documents, including references in model-owned predictions.

## V1 configuration and units

- `site`, `typical_application`, `zones`, and `centerline` are required. Project metadata must conform to the supplied schema; zones must have unique IDs, increasing start stations, and ends at or after their starts. Closed lanes cannot exceed total lanes.
- `centerline.origin` and `centerline.endpoint` use the drawing's coordinates and units. Computed stations and offsets use `site.units` (`feet` or `meters`). Left/right face increasing station; point offsets are magnitudes.
- Source units come from DXF `$INSUNITS`. An optional `source_units` override accepts `inches`, `feet`, `millimeters`, `centimeters`, `meters`, `yards`, or `us_survey_feet`. Use verified source units when overriding drawing metadata.
- If drawing units are missing or unsupported, conversion continues with scale 1, assumes the coordinates already use `site.units`, and records this uncertainty in `units.assumed` and the warning log. An invalid explicit override is a configuration error.
- Configured zone bounds and observation stations already use `site.units` and are not rescaled. Explicitly suffixed fields, such as `queue_length_ft`, keep their stated units.
- `block_mappings` names match inserts without regard to case and must be unique ignoring case. Each mapping accepts `type`, optional `zone_id`, and the fields for that element: signs accept `mutcd_code` (required), `legend`, `size_inches`, and `face_direction`; arrow boards require `mode`; flaggers optionally accept `controls`. Position, ID, and source are generated from CAD.
- Optional `temporal_context` and `observations` are preserved and validated. Observation IDs must be unique and zone references must exist. The converter rejects `predictions` in configuration because predictions are authored by the model.

## V1 partial conversion and diagnostics

Invalid mappings and insert coordinates are skipped; other valid entities are exported. Unrecognized block names remain unmapped. A schema-valid export may contain no elements, in which case the report includes a warning. Invalid project metadata, duplicate generated IDs, or document validation failures stop export. Zone overlap and placements outside assigned zones produce advisory warnings rather than blocking export.

Use `--log conversion-log.json` to retain diagnostics on success or failure. The report retains `converted_elements`, `unmapped_blocks`, and `skipped_mappings` and adds `skipped_elements`, `unmapped_elements`, a `units` summary, and structured `issues`. Each issue contains `severity`, `reason`, and a JSON-pointer-style `path`; entity issues also contain CAD `source` details. Mapping paths refer to configuration, entity geometry paths to the extraction, and document paths to the IF document. Skipped entities are warnings; errors prevent export.

Failed validation leaves an existing output untouched. JSON writes use temporary files followed by atomic replacement. Output and diagnostic paths must differ from each other and from the input, configuration, and schema paths.

The existing `cloudtcp_dxf.if_conversion.convert_dxf` and `convert_extraction` Python functions continue to produce v1 and return `(document, report)`. Failed conversion raises `ConversionError` (a `ValueError`) with its diagnostics available as `exc.report`.

After updating the supplied root schema, synchronize the package resource at `src/cloudtcp_dxf/tcp-intermediate-format.schema.json`; a test checks byte-for-byte equality.

## Important limitations

- **No native DGN support**. The reader only accepts DXF. A separate DGN adapter or carefully validated DGN-to-DXF export is needed.
- **No reliable classification of flattened signs or cones**. The supplied Alameda DXF has no `INSERT` entities; conversion from that file will yield no identified signs.
- No automatic road centerline discovery, curved-line stationing, sign placement/legend disambiguation, cone aggregation, basemap reconstruction, xref resolution, or CAD round-trip yet.
- Required v1 fields such as posted speed, number of lanes and zones are **not inferred**. V2 also requires authored configuration and preserves unknown optional facts.
- The IF v1 schema cannot encode complete basemap/road geometry. Raw extracted CAD data should be preserved separately.
- This project does not certify traffic-control compliance.

The example config is deliberately illustrative, **not real Alameda metadata**. Do not use example values for engineering decisions.
