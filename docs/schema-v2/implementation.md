# CloudTCP IF v2.0.0 implementation and usage

The active contract is implemented in this repository: a closed Draft 2020-12
schema, standalone structural/semantic validation, conservative v1 migration and
named-block extraction with v2 as the default CLI IF export. The original chapters
describe the data model; this guide specifies executable interfaces, producer
limits and resolved details.
The [release checklist](release-checklist.md) links evidence to each active gate.
No rule-verifier interface, evaluator, readiness state or exit-code change is delivered.

## Validate supplied data

```python
from cloudtcp_dxf import validate_v2_document, V2ValidationError

try:
    validate_v2_document(document)  # returns the very same object; does not mutate it
except V2ValidationError as exc:
    diagnostics = exc.diagnostics
```

`cloudtcp-validate-v2 document.json` prints `{valid, diagnostics}`. Diagnostics have
`layer`, `code`, RFC 6901 `path`, `message`, `severity` and optionally `related_refs`.
Layers are `json`, `structure`, `reference` and `semantic`. Errors raise
`V2ValidationError`, also a `ConversionError`; existing library error handling can
read `exc.report`. The separate utility commands use the existing success/failure
convention (0/1); the extractor's exit behavior is unchanged.

The authoritative contract is `schemas/2.0.0/schema.json`; the installed resource
is `cloudtcp_dxf/schemas/2.0.0/schema.json`. `tools/sync_schemas.py --check` and a
regression test compare their bytes. The original root and packaged v1 schemas
are unchanged. Generic Draft 2020-12 validators must enable date-format checking;
JSON Schema alone does not perform cross-record or computational geometry checks.
The schema's `x-targets` annotations describe target categories/subtypes used by
the semantic validator; they are not JSON Schema assertion keywords.

Checks include globally unique record IDs, existence and types of every supplied
reference (including equipment subtypes and observation metrics), pointer targets,
quantity dimensions and finite values, closed variants, geometry frame agreement,
ordered ranges and intervals, polygon closure/self-intersections/holes, increasing
alignment profiles and bounded station mappings. Phase dependencies, sign assemblies,
facility parent hierarchies and observation derivations are acyclic. Network path
successor cycles are allowed. Reciprocal taper/run links must agree when both are
supplied. Phase-scoped assertions, measurements and inventory declarations cannot
expand an explicitly declared subject phase set. Unknown optional facts remain omitted.

Evidence records, expired/disputed/withdrawn assertions, observations, predictions
and authored approvals remain distinct stored data. Validation checks integrity;
it does not fetch sources, verify authority, infer completeness or decide whether
an inventory proves physical absence. A complete inventory with explicit excluded
source portions is contradictory and rejected. Extraction declarations stay partial.
Unsupported source content is recorded in acquisition diagnostics.

## Numerical and schema details resolved during implementation

- Coordinates use their declared frame units. `convert_quantity(quantity, unit)`
  in `v2_validation` performs dimension-safe mathematical conversions. Slopes use
  signed rise/run `ratio`; actual dimensions are nonnegative and usable widths
  are positive. No regulatory minima or maxima are embedded.
- Dimension groups require width and height, or diameter. Supplied rectangle/diamond
  sign dimensions require width/height; circle dimensions require diameter. Shape
  can remain unknown, including when migration safely parses width × height.
- Station geometry on an approach/path uses the approach's station frame. A planar
  path uses the planar frame of that station frame's explicit alignment. No
  cross-frame transform or station/curve correspondence is inferred. Explicit
  measurements across discontinuities may retain endpoints in distinct frames;
  arithmetic derivations require compatible frames.
- Five exact arithmetic derivation names are recognized: `sum`, `difference`
  (first input minus second), `maximum` over observation `input_refs`, and
  `station_difference` / `planar_distance` over two `reference_locations`.
  Values must agree after unit conversion. Numerical comparisons allow only
  floating-point roundoff (`1e-12` relative/absolute), not engineering tolerances.
  Other derivation text is retained as a description and is never executed or
  treated as a verified calculation. No arbitrary expression interpreter is included.
- Supplied phase duration and clock interval must agree, or a disputed/withdrawn
  assertion must retain the differing duration evidence. Action timestamps agree
  with declared sequence and the supplied phase interval. No phase is inferred
  from a timestamp, light condition from a time bin or travel sign from a compass label.
- A supported assertion retaining alternatives needs a decision link affecting
  that assertion or its subject. Alternatives must fit the selected field's
  structural contract. Withdrawn alternatives may retain historical conflicts.
  Resolution and authority remain authored facts; no evidence-ranking engine runs.

## CloudTCP IF v2.0.0 extraction

Configured CLI conversion defaults to v2.0.0:

```bash
cloudtcp-dxf plan.dxf --if-config v2-config.json
```

The Python conversion APIs remain version-specific; use these functions for v2:

```python
from cloudtcp_dxf.v2_conversion import convert_v2_dxf, convert_v2_extraction

document, acquisition_report = convert_v2_dxf("plan.dxf", config)
```

`config` contains `document` (a valid authored v2 partial snapshot), `stationing`
with exactly `frame_ref`, `origin` and `endpoint`, optional `source_units` and
`block_mappings`. The frame must already exist as a station frame. Drawing-space
origin/endpoint define a straight reference line; stations/offsets are normalized
to frame units. Units and assumptions use the same resolution as v1 and remain in
the report. The configured `document_id`, `revision` and creation timestamp identify
the submitted snapshot; authors must revise these when changing its input facts.

Mapping values are v2 templates for `device(sign)`, `device(arrow_board)` or
`actor(flagger)`. IDs, locations and source evidence are acquired from INSERTs.
Other geometry/equipment discovery is unsupported, while authored v2 entities can
already describe all chapter-listed kinds. No predictions can be supplied to the
extractor, even as an empty array. A prediction engine can later author a separate
validated snapshot. Explicit phase mappings produce scoped location assertions;
unscoped extractions retain source evidence without inventing phase applicability.

The CLI requires `--if-config` for IF conversion; `--format-version 2.0.0` is
optional because v2 is the default. Without configuration, the command performs
raw DXF inspection; explicitly selecting v2 without configuration is an error.
Legacy configuration requires `--format-version 1.0.0`. Incompatible configurations
are rejected with version-selection guidance, without automatic fallback or migration.
The existing `if_conversion.convert_dxf` and `convert_extraction` Python functions
continue producing v1. The CLI stores raw
extraction and diagnostics beside the versioned output by default. `--log` selects
a different report path. `--schema` adds constraints without bypassing bundled
validation. Failed validation preserves existing output; source/config/schema,
raw-extraction, output and report paths cannot alias one another. CAD evidence
retains handles, layers and block names. Its content hash names canonical extraction
JSON, not the original DXF bytes; retain the drawing and raw JSON separately.

Invalid/unsupported mappings and unmapped blocks have source-handle diagnostics.
Duplicate IDs or inconsistent document relationships stop export. With no INSERTs,
a valid partial document can have no acquired devices; absence is unknown.
`configured_extraction` declarations are downgraded to partial and carry acquisition
limits. Independently authored inspection declarations retain their own bounded scope.

## Conservative v1 import

```python
from cloudtcp_dxf import migrate_v1_document

result = migrate_v1_document(v1_document, context=None)
v2_document = result["document"]
migration_report = result["migration_report"]
```

V1 structure and relationships are validated first. Invalid source/context/bindings
raise structured errors and produce no migrated document. The caller's source and
context are never mutated. A full original JSON subtree is stored in `legacy_records`
and hash-referenced by legacy-import evidence. The CLI leaves the original file in
place and defaults to a separate `.v2.json` plus `.v2.migration.json` report.

Source hashes identify canonical parsed JSON (sorted keys, compact UTF-8 encoding),
not the CAD file named inside the legacy metadata. Every source leaf has a disposition (`converted`, `preserved`, `ambiguous` or
`unavailable`) with a reason and optional target reference/path. Field counts and
source/output entity counts are separate. `id_map` retains deterministic escaped,
namespace-prefixed identities. An unprovided project ID becomes the explicitly
provisional `legacy-import:<source-hash>` namespace. Authored project IDs preserve
entity identities across revisions when original IDs and the retained identity map
remain stable; no physical identity reconciliation is attempted. Each conversion
gets a new immutable document ID incorporating source hash, context hash and
conversion time, while entity IDs remain stable.

Road text, closure type, zones, explicit zone links, safe positions, sign code/legend,
unambiguous numeric width × height strings, homogeneous run type/spacing and
separate measurement metrics convert directly. A known left/right taper with
nonnegative offset magnitudes and ordered stations converts feet offsets to its
station units. Missing side, negative magnitudes, contradictory center offsets,
reversed taper stations and unspecified run-offset units remain preserved and
reported. Lane width is never used as taper offset width. Counts create no lanes;
compass labels create no approaches. Flagger directions create no control assignments.

Legacy observations retain station scope as a zero-length range when offset is
unknown. Negative legacy physical values remain raw with ambiguity diagnostics.
Complete, explicitly zone-scoped predictions can convert queue/delay metrics and
linked recommendations as predictions. Missing required model/time/horizon or
subject metadata preserves the subtree. Throughput, congestion index and corridor
aggregates remain raw rather than acquiring invented metric/scope meanings.
Weather visibility never becomes sight distance. No import creates phases,
approvals or completeness declarations.

Optional `context` accepts authored `project_id`, frames, phases, entities, evidence,
assertions, completeness, decisions and `bindings`. A binding has exactly
`source_path`, `target_ref`, `target_path`; both pointers must resolve. An agreeing
value is associated with the target. Conflicts retain the authored target and create
a disputed assertion, with a type-compatible alternative when possible. Incompatible
raw values remain in the legacy record. Unscoped conflict assertions explicitly
remain disputed; they cannot provide supported phase applicability. Authored
resolution must retain the original and supply a decision. Cross-record duplicates
and dangling context references are errors.

## Fixtures and remaining boundaries

[Minimal partial](../../examples/v2/minimal.document.json),
[specialist facts](../../examples/v2/specialist.document.json) and
[producer configuration](../../examples/v2/if-config.example.json) are synthetic.
The specialist fixture exercises all 24 entity kinds and 13 equipment subtypes,
sight measurements, accessibility geometry, railroad/queue facts, coordination,
scoped evidence and separate prediction output. Numeric values demonstrate data
representation and may be below real source requirements.

Acquisition remains limited to configured named blocks and straight stationing.
Curved/civil reconstruction, automatic lane identification, external-source fetching,
source-policy resolution, physical/engineering approval checks and arbitrary
calculation execution are outside these capabilities. The preserved 504-clause
inventory still tracks source dependencies and medium-confidence mappings. Its
clauses are not implemented evaluators. Verifier dispatch, readiness, compliance
reporting and v2-to-v1 projection remain deferred without automatic activation.
