# CloudTCP IF v2.0.0 schema handoff

Prepared November 23, 2026 for teams producing or consuming CloudTCP Intermediate
Format documents, including the rules verifier team.

CloudTCP IF v2.0.0 represents partial traffic-control plan facts, roadway
relationships, geometry, operating phases, measurements and their evidence.
The delivered contract includes the JSON Schema, semantic validator,
documentation, examples and conformance tests. Together they establish whether
supplied data is internally valid. Rule applicability, evidence authority,
readiness and compliance evaluation belong to the consuming verifier.

## Contract identity and delivery status

| Item | Value |
|---|---|
| Contract name | CloudTCP IF v2.0.0 |
| Document discriminator | `format_version: "2.0.0"` |
| JSON Schema dialect | Draft 2020-12 |
| Schema identifier | `https://cloudtcp.io/schemas/tcp-intermediate-format/v2.0.0/schema.json` |
| Authoritative schema | [`schemas/2.0.0/schema.json`](../../schemas/2.0.0/schema.json) |
| Installed schema resource | `cloudtcp_dxf/schemas/2.0.0/schema.json` |
| Current Python distribution | `cloudtcp-dxf-extractor`, version `0.2.0` |
| Python requirement | Python 3.10 or later |
| Implemented | Structural and semantic validation, configured CAD acquisition, v1 migration |
| Verifier integration | Deferred; proposed interfaces are not implemented APIs |

The distribution version and document format version are independent. Identify
each delivered build by its artifact checksum and source revision as well as its
package version. The schema identifier identifies the contract; consumers can
validate entirely from the bundled schema without retrieving that URL.

Configured CLI conversion defaults to v2.0.0. Legacy CLI conversion requires
`--format-version 1.0.0`. Python conversion functions remain version-specific.

## Required delivery artifacts

Supply the following together, preserving repository-relative paths so the
documentation links continue to work.

| Artifact | Purpose |
|---|---|
| [`schemas/2.0.0/schema.json`](../../schemas/2.0.0/schema.json) | Machine-readable fields, variants, enums, units and structural constraints |
| Python wheel or complete source distribution | Executable validator and bundled schema; the wheel includes both v1 and v2 resources |
| [`docs/schema-v2/`](README.md) | Contract meaning, implemented behavior, migration boundaries and this handoff |
| [`examples/v2/`](../../examples/v2/) | Minimal partial document, specialist document and producer configuration |
| [`tests/`](../../tests/) | Conformance and producer tests, including shared fixtures imported between test modules |
| [`pyproject.toml`](../../pyproject.toml) | Package metadata, runtime dependencies and CLI entry points |
| [`tools/sync_schemas.py`](../../tools/sync_schemas.py) and [`tools/check_v2_wheel.py`](../../tools/check_v2_wheel.py) | Resource synchronization and installed-package verification |
| [`release-checklist.md`](release-checklist.md) and its linked evidence | Recorded validation results and package checksums |

A wheel installation supplies the runtime package and schema resources. Attach
the documentation, examples and tests separately; they are not installed as
package resources by the wheel.

For the specific artifact being transferred, the sender records its filename,
SHA-256 checksum, source revision, dependency versions, test results and any
changes since the previous delivery. Include a source snapshot or patch when the
build includes uncommitted changes. Do not reuse a historical checksum for a
rebuilt artifact. The [November 23 verification evidence](evidence/v2-default-package-smoke.json)
identifies the build checked when v2 became the CLI default.

DXF drawings and extractor configurations are needed only when reproducing
acquisition. A verifier consuming existing IF documents needs the documents and
access to any supporting evidence required by its source policies.

## Document structure and field meaning

Every document requires the following fields:

```json
{
  "format_version": "2.0.0",
  "document_id": "doc",
  "project_id": "project",
  "revision": "a",
  "created_at": "2026-11-19T20:00:00Z",
  "site": {"name": "Synthetic partial"},
  "reference_frames": [],
  "phases": [],
  "entities": [],
  "evidence": [],
  "assertions": [],
  "completeness": []
}
```

This minimal document is valid and contains no claim that devices are physically
absent. Optional top-level fields are `previous_document_id`, `decisions`,
`observations`, `predictions` and `legacy_records`.

`document_id` identifies a document revision; `project_id` identifies the project
across revisions. Addressable records have globally unique, case-sensitive IDs.
References resolve by ID rather than array position and must target the declared
record kind or subtype. Every entity requires `id` and `kind`; optional common
fields are `name`, `description`, `phase_refs` and `source_evidence_refs`.

The contract defines 24 entity kinds and 13 device subtypes:

| Group | Entity kinds |
|---|---|
| Road network | `road`, `alignment`, `approach`, `lane`, `path`, `junction`, `ramp`, `boundary` |
| Plan scope and geometry | `application`, `closure`, `zone`, `taper`, `buffer`, `work_area`, `ttc_extent` |
| Facilities and markings | `facility`, `crossing`, `marking`, `restriction` |
| Equipment and operations | `device`, `device_run`, `actor`, `vehicle`, `control` |

Device subtypes are `sign`, `cone`, `drum`, `vertical_panel`, `tubular_marker`,
`barrier`, `barricade`, `arrow_board`, `message_sign`, `afad`, `signal`,
`audible_device` and `warning_light`. Their specification fields depend on subtype.

Consumers must preserve these meanings:

- **Unknown facts:** Omit unknown optional fields. `null` is not a general unknown
  value, and a missing field is not equivalent to `false`, zero or an empty inventory.
- **Coordinates:** Planar and station frames declare feet or meters. Station
  offsets are signed, positive left while looking toward increasing station.
  Approach `travel_sign` specifies travel relative to increasing station. Do not
  derive travel direction from an offset sign or compass label.
- **Measurements:** Quantities carry explicit `value` and `unit`. Geometry uses
  frame units. Preserve measurement dimensions and apply only compatible unit
  conversions; do not invent coordinate transformations or engineering tolerances.
- **Phases:** Missing `phase_refs` leaves applicability undeclared. It does not
  mean every phase. Assertions explicitly identify their phases or declare
  phase independence.
- **Evidence:** Source records, supported/disputed/withdrawn assertions, decisions,
  observations and model predictions are separate records. Their presence alone
  establishes neither engineering authority nor suitability for a rule.
- **Completeness:** Declarations apply to bounded subjects and phases, with optional
  kind, device and range selectors. Empty arrays or successful CAD conversion do
  not establish complete coverage or physical absence.

Use the [core contract](core-contract.md), [roadway definitions](roadway-geometry.md),
[device definitions](devices-road-users.md) and [operations and evidence definitions](operations-evidence.md)
for field-level semantics. The JSON Schema and [implementation guide](implementation.md)
resolve executable shapes and checks; illustrative chapter snippets are not substitutes
for the authoritative schema.

## Installing and calling the validator

Install the supplied wheel in the receiving team's environment, substituting its
actual path:

```bash
python -m pip install /path/to/cloudtcp_dxf_extractor-0.2.0-py3-none-any.whl
cloudtcp-validate-v2 examples/v2/minimal.document.json
cloudtcp-validate-v2 examples/v2/specialist.document.json
```

The package declares `ezdxf>=1.3,<2`, `jsonschema>=4.18` and
`rfc3339-validator>=0.1.4`. These dependencies apply to the current distribution,
even when the receiving application only uses validation.

Applications that need the machine-readable definitions can load the installed
resource directly:

```python
import json
from importlib.resources import files

schema = json.loads(
    files("cloudtcp_dxf")
    .joinpath("schemas/2.0.0/schema.json")
    .read_text(encoding="utf-8")
)
```

The supported Python entry point is:

```python
import json
from pathlib import Path

from cloudtcp_dxf import V2ValidationError, validate_v2_document

document = json.loads(Path("plan.v2.if.json").read_text(encoding="utf-8"))
try:
    validated = validate_v2_document(document)
except V2ValidationError as exc:
    diagnostics = exc.diagnostics
else:
    assert validated is document
```

Successful validation returns the same object without mutation. Invalid supplied
data raises `V2ValidationError`, a subclass of `ConversionError` and `ValueError`.
File and JSON parsing errors occur outside this call and remain the caller's
responsibility.

Diagnostics contain `layer`, `code`, RFC 6901 `path`, `message` and `severity`,
with optional `related_refs`. Layers are `json`, `structure`, `reference` and
`semantic`. The standalone validator reports JSON `{valid, diagnostics}` for
validation outcomes, with exit code 0 for valid data and 1 for failure. File or
JSON parsing failures are written to stderr and also return 1; callers must not
assume every failure produces the JSON validation envelope.

## Validation responsibilities

| Layer | Enforced behavior |
|---|---|
| JSON and structure | JSON-compatible values, finite numbers, exact format version, closed variants, required fields, quantity dimensions and date formats |
| References | Globally unique record IDs, target existence and kinds/subtypes, existing assertion pointer targets |
| Supplied semantics | Consistent frames, ordered ranges and intervals, valid polygons and holes, bounded alignment mappings, phase scope, declared arithmetic and equipment relationships |

Semantic validation also rejects cycles in phase dependencies, sign assemblies,
facility parents and observation derivations. Path-successor cycles are allowed
because network connectivity can legitimately be cyclic.

Generic JSON Schema validation covers only part of this contract. Enable date
format checking. The `x-targets` annotations describe reference restrictions for
the semantic validator; ordinary JSON Schema validators do not enforce them.
A consumer using another language must reproduce the semantic checks and run
equivalent conformance cases before claiming the same validation coverage.

Validation does not fetch evidence, decide source authority, resolve regulatory
policy, compute rule readiness or issue compliance findings. Only the documented
arithmetic derivation names are checked; arbitrary derivation text is never executed.

## Rules verifier integration responsibilities

The existing verifier is documented as a v1 consumer. Accepting v2 requires a
separate verifier implementation and integration agreement. Complete the following
before enabling v2 rule evaluation:

1. **Version admission:** Dispatch on `format_version`, reject unsupported
   versions and validate against the exact contract before invoking evaluators.
   Preserve an explicit v1 route for existing inputs.
2. **Typed adapters:** Resolve entities, relationships, frames and phases into
   evaluator inputs. Preserve separate approaches, lane identities and device
   associations rather than collapsing them into project-wide counts.
3. **Rule prerequisites:** Define each supported rule's subject kinds, required
   fields, relationships, measurement basis, phase scope and completeness needs.
   Distinguish missing facts from an unsupported evaluator.
4. **Sources and decisions:** Pin regulatory editions and jurisdictions. Specify
   accepted evidence, validity requirements, engineering approvals, calculation
   methods and any authorized tolerances or interpolation policies.
5. **Evaluation reporting:** Agree on result and readiness interfaces, incomplete
   evaluation behavior and exit codes. Preserve known findings when other subjects
   remain unresolved, and trace results to document, subject, phase and rule source.
6. **Acceptance cases:** Test complete and partial inputs, distinct approaches
   sharing station numbers, disputed and out-of-phase assertions, equivalent units,
   missing relationships and unsupported rules.

The [rule traceability map](rule-traceability.md) identifies candidate field and
source dependencies. It is not an executable prerequisite manifest. The
[deferred verifier notes](migration-integration.md#deferred-verifier-workstream-provisional-notes)
contain proposals, including `assess_readiness` and `verify_v2_document`; those
functions and proposed report/exit-code contracts are not supplied by this package.

Schema maintainers own field meaning and validation behavior. Verifier maintainers
own adapters, prerequisites and evaluation results. Domain reviewers resolve source
criteria and authority requirements. These are responsibility roles, not named
approvals or staffing commitments.

## Producer and migration boundaries

The schema can represent more facts than the current CAD producer discovers.
Automatic acquisition handles explicitly mapped named DXF INSERTs for signs,
arrow boards and flaggers, projected onto a configured straight reference line.
Other entities may be authored. Flattened-symbol recognition, curved roadway
reconstruction and exhaustive inventory are not implemented acquisition capabilities.

For legacy inputs, `migrate_v1_document(document, context=None)` returns
`{document, migration_report}` and retains the complete original JSON in
`legacy_records`. The CLI equivalent is:

```bash
cloudtcp-migrate-v1 original.if.json -o imported.v2.json
```

Migration validates v1 first, preserves ambiguous values and reports each source
leaf's disposition. A legacy record is a preservation container, not an implicit
typed v2 fact. Keep the original document and migration report with the migrated
document. No v2-to-v1 projection or automatic verifier upgrade is supplied.

## Receiving team acceptance checklist

- [ ] Record the delivered schema, package identity, source revision and checksums.
- [ ] Install the supplied package and validate both example documents.
- [ ] Reproduce structural, reference and semantic failure diagnostics using the
  conformance tests, including duplicate IDs, wrong reference kinds, invalid
  geometry, wrong units and phase-scope conflicts.
- [ ] Confirm that a valid minimal partial document does not become an absence
  claim or a successful compliance result.
- [ ] Confirm version routing and preservation of existing v1 inputs.
- [ ] Identify the first supported rules and agree on their facts, evidence,
  policy and evaluator requirements before enabling evaluation.

From a source checkout, the delivery checks are:

```bash
python -m pip install -e ".[dev]"
python tools/sync_schemas.py --check
python -m pytest -q
```

The [November 23 release record](release-checklist.md#v2-default-verification-record--november-23-2026)
reports 158 passing tests and five installed CLI smoke checks, including explicit
v1 export, default v2 export and migration. Those results describe that recorded
build; rerun the checks for each newly delivered artifact.
