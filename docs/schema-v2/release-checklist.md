# CloudTCP IF v2.0.0 release-gate checklist

Initial implementation evidence, November 19, 2026. These checks establish data capabilities
and producer preservation; they do not establish regulatory adequacy or successful
rule evaluation. The authoritative contract is `schemas/2.0.0/schema.json`.

The D0–R4 checklist and initial verification record below describe the historical
release that defaulted to v1. Current CLI conversion defaults to v2.0.0; see the
[v2-default verification record](#v2-default-verification-record--november-23-2026).

## D0 — specification review

- [x] Read the eight specification chapters and index before implementation. No
  `AGENTS.md` exists in this repository or its ancestor path; no extra repository
  instructions could be read.
- [x] Preserve all 37 capability families and 504 unique clauses (384 Full / 120 W1),
  457 headings and 419 canonical checks in `rule-traceability.md`. Documentation
  counts were independently counted from the retained table; `test_traceability_inventory_is_preserved`
  guards the family/unique-clause inventory.
- [x] Preserve the audit confidence split (229 high, 275 medium), external manual,
  missing-figure, erratum, source-policy and engineering dependencies. No candidate
  mapping was promoted into a rule evaluator or a regulatory threshold.
- [x] Preserve the complete legacy-field disposition table. Migration reports cover
  every input leaf, with the full immutable JSON retained even when values convert.
- [x] Keep verifier proposals separate and nonbinding. Resolve routine details in
  `implementation.md`: dimension axes, frame agreement, arithmetic vocabulary,
  immutable conversion IDs and historical withdrawn alternatives. No material
  conflict blocked the active data contract.

## R0 — validation foundation

- [x] Draft 2020-12 envelope, dimensioned quantities, IDs, frames, closed variants,
  evidence/assertions and JSON/date checks. Authoritative and packaged resources
  are byte-identical (`test_schema_is_authoritative_synchronized_and_standalone`).
- [x] A01–A03: minimal partial input, unchanged return value, unknown inventory,
  unsupported version/kind/null/undeclared fields/nonfinite values, duplicate IDs,
  missing references and wrong target kinds. See `tests/test_v2.py`.
- [x] A07/A13: dimension-safe conversion, ordered ranges, frame agreement, polygon
  closure/intersections/holes. Equivalent producer coordinates in feet/meters are
  tested in `test_v2_acquisition_coordinates_convert_to_equivalent_physical_values`.
- [x] A18: disputed alternatives, explicit resolution references, correct pointer
  targets and alternative types. No arrival-order or authority policy is computed.
- [x] A30: independent validator rejects unsupported versions; unchanged v1
  validation remains available. No verifier dispatch or report change.

## R1 — shared relationships and scoped evidence

- [x] A04–A06/A12/A23/A27: separate approaches sharing stations, taper/tangent
  associations, per-lane board assignments, zero-length features, omitted buffers,
  one-lane two-way taper identity and explicit alternating controls.
- [x] A10/A15/A17–A19/A26: speed metric/basis/mode distinctions; authored approvals
  and decisions; bounded inventory and phase scopes; conflicts and intervals;
  caution-board consistency; subtype and reciprocal relationship checks.
- [x] A16: acquisition limitations and excluded sources retained; known excluded
  portions cannot coexist with complete acquisition declarations.
- [x] Pilot opt-in R1 extraction before broad specialist adoption. Synthetic
  DXF tests exercise mapped signs, scoped provenance, source handles, partial
  acquisition, unmapped/unsupported blocks and v1/v2 output separation.

Evidence: shared-network, scoped-evidence, phase and producer tests in
`tests/test_v2.py` and `tests/test_v2_producers.py`.

## R2 — safety geometry and facilities

- [x] A09/A14/A20/A28: sight metrics with reference locations distinct from weather;
  measured accessible-facility geometry with missing source criteria retained;
  actual undersized equipment accepted as data; railroad footprints, scalar queue
  lengths and observed occupancy remain different facts.
- [x] Boundary/frame links, usable widths, signed slopes, alignment profiles,
  station-mapping indices/distances, buffers and polygon integrity are checked.
  Exact declared derivations are checked without regulatory comparisons.

Evidence: `specialist.document.json`, `test_a09_a14_a20_a28_safety_facts_remain_facts`,
`test_alignment_profile_mapping_and_path_frame`, geometry/derivation tests and the
R2/R3 integrity parametrization.

## R3 — specialist facts

- [x] The validated specialist fixture contains all 24 entity kinds and 13 device
  subtypes. It includes vehicles, actors/AFADs, controls, mounts, markings,
  junctions/ramps, mileage/parking relationships and coordination decisions.
- [x] Each physical subtype accepts its own supplied fields and rejects undeclared
  fields. Wrong-kind operator, sign-parent, stop-line and mount-surface references,
  wrong units, invalid counts/heights, assembly/facility/derivation cycles and
  run/gap consistency have negative tests.
- [x] No external accessibility/design criterion, approved hardware designation,
  speed tier or engineering tolerance was invented.

Evidence: `test_r3_each_subtype_accepts_its_specification_and_rejects_other_variant_fields`,
`test_r2_r3_integrity`, run/assembly tests and the specialist fixture. This gate
means facts can be authored and validated; CAD discovery of these specialist
features is not claimed.

## R4 — producer and migration adoption

- [x] A08/A25: offset conversion on meter-station imports; missing side, negative
  magnitude, contradictory center offset, reversed taper and ambiguous line units
  preserve original values with structured field diagnostics. Counts do not create
  lanes; lane width does not substitute for offset width.
- [x] A24: observations, predictions and authored decisions remain distinct.
  Incomplete model metadata, unsupported metrics and missing prediction scopes
  remain preserved; extraction cannot author predictions.
- [x] A25: source/context objects unchanged; invalid source/context/bindings produce
  no migrated document; every source leaf has a disposition; conflicts retain
  authored values and disputed assertions; stable project/escaped identity maps
  coexist with new immutable conversion documents.
- [x] A30: explicit opt-in v2 CLI and separate config; unchanged default v1 export;
  retained original files, raw extraction and reports; path/alias protection;
  v2 validation cannot be disabled with an additional schema.
- [x] Synthetic fixture, migration/producer library and CLI tests are delivered;
  [usage and concrete limitations](implementation.md) distinguish implemented
  capabilities from proposals.

## Initial verification record — November 19, 2026

- `python -m pytest -q`: **149 passed**, including all **61 existing v1 tests**.
  Test interpreter: `/private/tmp/cloudtcp-dxf-tests-venv/bin/python` (Python 3.14).
- `python tools/sync_schemas.py --check`: passed.
- Ruff on changed Python files, new tests and schema-sync tool, with isolated
  `E4,E7,E9,F,I` selection: passed. Formatting checked on those files. This does not
  claim the repository's pre-existing files satisfy unrelated global Ruff rules.
- `git diff --check`: passed for tracked changes; newly added Python files also
  pass Ruff formatting checks.
- Wheel construction, installation into a separate target and five installed-CLI
  smoke commands passed outside the source import path. Both packaged schemas match
  their authoritative sources, and every packaged Python module matches the final
  source. The smoke converted three explicitly mapped INSERTs, retained one unmapped
  INSERT diagnostic, validated exported/migrated v2 data and preserved the original
  v1 file byte-for-byte. [Recorded evidence](evidence/package-smoke.json), wheel
  SHA-256 `0e88116f56790733f4d164a4488fd5815efb9abdbad31cb0cc53196a545470b6`.
  Reproduce with `tools/check_v2_wheel.py WHEEL INSTALLED_TARGET --report REPORT`
  using the installed target on `PYTHONPATH` and a Python with the declared runtime
  dependencies. The script retains its synthetic source, outputs and reports in
  a temporary directory for inspection.

## V2-default verification record — November 23, 2026

- CloudTCP IF v2.0.0 is the default configured CLI export. Legacy conversion
  requires `--format-version 1.0.0`; raw DXF inspection and version-specific
  Python conversion APIs retain their behavior. The schema title changed; its
  version identifier, URLs, fields and validation constraints did not.
- `PYTHONPATH=src /private/tmp/cloudtcp-v2-default-venv/bin/python -m pytest -q`:
  **158 passed** (Python 3.14). Coverage includes default/explicit v2 export,
  explicit v1 preservation, configuration/version mismatch diagnostics without
  fallback, raw inspection, configuration-required errors, additional schema
  enforcement and output/sidecar protection.
- `python3 tools/sync_schemas.py --check` and `git diff --check`: passed.
  Ruff `E4,E7,E9,F,I` and formatting checks passed for `cli.py`, `v2_conversion.py`,
  `test_v2_producers.py` and `check_v2_wheel.py`.
- A fresh wheel was built without isolation, installed into a separate target,
  and checked outside the source import path. All five installed CLI smoke
  commands passed: explicit v1 export, default v2 export, v2 validation, v1
  migration and migrated-document validation. The v1 artifact stayed byte-identical;
  three mapped INSERTs converted, one unmapped INSERT was reported, and v2 raw
  extraction/report sidecars were retained. Both packaged schemas and every
  packaged Python module match the source.
  [Recorded evidence](evidence/v2-default-package-smoke.json), wheel SHA-256
  `b106f01fc439b6b050333ca4757c09fcc14a26af737f842fb5798cbf4858e92a`.
  The earlier evidence file and verification record above remain historical.

## Remaining boundaries

Only configured named sign/arrow-board/flagger INSERT acquisition and straight-line
stationing are supported automatically. Other supplied v2 facts can be authored and
validated. Arbitrary derivation descriptions remain opaque; only the documented
five arithmetic names have computational checks. No real-plan exhaustive-inventory,
source-authority, regulatory-criterion or engineering signoff claim is made.

A11, A21, A22 and A29, plus every deferred portion of the mixed scenarios, remain
outside acceptance. No verifier readiness, evaluator, compliance-report, exit-code
or v2-to-v1 projection work was activated. The unchanged verifier continues to
consume original v1 files.
