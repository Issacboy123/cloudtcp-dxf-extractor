# CloudTCP IF v2.0.0 validation, acceptance and rollout

Implementation status: active data-contract, standalone validation and producer work is delivered. See [implemented interfaces and limits](implementation.md) and [release-gate evidence](release-checklist.md). Verifier behavior remains deferred; source-policy and engineering dependencies in this chapter remain unresolved.

This roadmap covers the schema, standalone structural/semantic validation, default v2 CLI export and v1 migration. Rules-verifier changes are deferred to a separate implementation decision with no automatic start date. The scenarios below retain their acceptance classification; active portions now have executable tests linked in the release checklist. Existing audit results remain evidence about v1 only.

## Active validation responsibilities

Structural validation enforces version/kind discriminators, closed shapes, primitive types, required variant fields, quantity dimensions and date formats. Independent semantic validation enforces unique IDs, references, frame agreement, pointer targets, acyclic hierarchies, ordered intervals and declared derivation consistency. It checks facts supplied by the document, not their regulatory adequacy.

Stored evidence states and scopes remain part of the contract. Validation can reject an invalid assertion reference or an interval ending before its start. It does not decide source authority, whether evidence is fresh enough for a rule, whether an inventory establishes real-world absence, or whether a rule is ready. Those decisions, regulatory calculations and compliance findings are deferred.

Do not embed source-specific minimum device dimensions in structural validation. An actual undersized device remains representable. A negative physical dimension or wrong unit is a data error; a dimension below a regulatory threshold requires later rule evaluation.

## Acceptance classification

Active contract scenarios test representation and data consistency. Active producer scenarios test acquisition, export, conversion and preservation. Deferred verifier scenarios retain their IDs for future integration and are excluded from active release gates. Mixed scenarios have an active data test and a separately deferred behavioral expectation.

| ID | Classification | Active representation/validation or producer outcome | Deferred verifier behavior |
|---|---|---|---|
| A01 | Active contract + deferred | Minimal partial envelope is structurally valid; empty inventory is not labeled confirmed absence | Requested-rule readiness and completeness aggregation |
| A02 | Active contract | Reject wrong version, undeclared field, unsupported kind, null unknown or non-finite number with precise paths | Verifier execution/error handling unchanged |
| A03 | Active contract | Reject duplicate IDs, dangling references and wrong-kind links | None required |
| A04 | Active contract + deferred | Retain distinct approaches sharing station numbers; reject no valid data merely for global overlap | Sign selection and encounter-order evaluation per approach |
| A05 | Active contract + deferred | Represent taper and tangent membership as different typed relationships despite identical run geometry | Select source-specific spacing limits and compare them |
| A06 | Active contract + deferred | Represent two boards assigned to one lane separately from one board assigned to each lane | Determine required board coverage or noncompliance |
| A07 | Active contract | Equivalent feet/meters coordinates and quantities convert to equivalent physical values; no invented engineering tolerance | Readiness/evaluator outcome equivalence is future work |
| A08 | Active producer | Convert legacy taper feet offsets explicitly on meter-station sites or preserve/report ambiguity | No verifier migration or input dispatch change |
| A09 | Active contract + deferred | Store sight-distance metric, reference locations and provenance separately from weather visibility | Determine adequacy for a flagger approach |
| A10 | Active contract + deferred | Keep posted, percentile and bicycle speed bases/modes distinct; validate types and references | Select permitted source basis and formula |
| A11 | Deferred verifier | Store 42-mph values and source-policy decisions without inventing interpolation | Report unresolved branches/table policy during rule evaluation |
| A12 | Active contract + deferred | Preserve a zero-length feature when otherwise consistent; do not invent missing geometry | Determine whether sequence prerequisites are satisfied |
| A13 | Active contract | Reject self-intersecting polygons and end-before-start ranges; allow unknown geometry to be omitted | None required |
| A14 | Active contract + deferred | Preserve accessible-facility dimensions and missing-source limitations | Resolve accessibility criterion and evaluate adequacy |
| A15 | Active contract + deferred | Represent approval/exception records, authority text, scopes and evidence links; check integrity only | Verify authority, conditions and effect on a rule |
| A16 | Active producer + deferred | Preserve scoped inspection/extraction declarations and skipped-content diagnostics; producer cannot claim complete extraction despite known relevant skips | Decide whether trusted evidence establishes absence |
| A17 | Active contract + deferred | Keep completeness declarations bounded to their specific approaches/phases | Aggregate incomplete rule subjects across scopes |
| A18 | Active contract + deferred | Preserve disputed alternatives and explicit authored resolution links without last-write-wins data loss | Decide usable evidence/readiness for a rule |
| A19 | Active contract + deferred | Store mixed lighting, validity intervals and phase scope; reject malformed intervals | Enforce daytime-only/freshness prerequisites |
| A20 | Active contract + deferred | Accept nonnegative actual device dimensions even below a source minimum | Produce regulatory findings from those dimensions |
| A21 | Deferred verifier | No active schema or producer requirement for execution results | Preserve fail plus complete=false for mixed subjects and select verifier exit code |
| A22 | Deferred verifier | Preserve source/jurisdiction identifiers as ordinary data | Federal/California delegation and finding deduplication |
| A23 | Active contract + deferred | Optional buffer can be omitted; store measurements without requiring a regulatory minimum | Evaluate guidance and permission semantics |
| A24 | Active producer + deferred | Keep predictions separate from observations/decisions and preserve model provenance | Decide whether a rule permits a particular evidence source |
| A25 | Active producer | Preserve original v1 data, migration diagnostics and ambiguous fields; invent no lanes, phases, approvals or completeness | No v2 compliance claim from migration |
| A26 | Active contract + deferred | Reject caution-mode board with arrow direction and subtype mismatch; permit unknown optional direction | Direction-dependent readiness and outcomes |
| A27 | Active contract + deferred | Represent one-lane two-way taper and explicit control/path relations | Evaluate applicable source provisions |
| A28 | Active contract + deferred | Store railroad geometry, queue footprint or scalar queue as distinct facts | Determine track occupancy and required controls |
| A29 | Deferred verifier | No active evaluator registry or capability manifest required | Report unsupported evaluator independently of data readiness |
| A30 | Active producer/validation + deferred | Independent validator rejects unsupported versions; producers retain original v1 artifacts for existing tools | Any new verifier version dispatcher or CLI behavior |

For active cases, future fixture authors identify exact record IDs, expected preserved values and validation/conversion diagnostics. Source clause IDs provide context but do not require a rule engine or findings. Physical values are examples until reconciled with authoritative source criteria. Do not repurpose v1 audit probe outcomes as proof of v2 validation.

## Active release stages and gates

| Stage | Delivered future data capability | Exit gate and dependency |
|---|---|---|
| D0 specification review | All chapters, 37-family mapping and 504-clause inventory | Every family/legacy-field disposition preserved; medium-confidence mappings and external dependencies visible; verifier work separated |
| R0 standalone validation foundation | Envelope, quantities, IDs, frames, assertions/evidence containers, structural and supplied-data semantic validation | Active portions of A01–A03, A07, A13, A18, A30; independent validator without readiness, report-version or evaluator changes |
| R1 shared relationships and evidence | Roads/applications/approaches/lanes/paths/closures, phases, speed facts, basic devices/runs/tapers and scoped completeness records | Active portions of A04–A06, A10, A12, A15–A19, A23, A26–A27; facts and relationships are representable and internally consistent |
| R2 safety geometry | Boundaries, widths, buffers, alignment/sight measurements, facilities and crossings | Active portions of A09, A14, A20, A28; measured facts remain distinct from resolved regulatory criteria |
| R3 specialist equipment | Mounts/physical subtypes, vehicles, AFAD/control, markings, ramps/intersections, parking/mileage and coordination | Data-contract examples and integrity checks for each relevant family; no activated-rule or external-policy-resolution gate |
| R4 producer and migration adoption | Default v2 CLI export, independent validation, loss-preserving migration, archived v1/v2 data | Active A08, A24–A25, A30; conversion/preservation reviewed; explicit v1 output remains available for unchanged verifier |

R4 starts incrementally after R0 and pilots the R1 contract before broad R2/R3 production. In this roadmap R4 is an adoption workstream, not a mandate to wait for all specialist entities. No active stage requires verifier readiness results, findings, changes to the 407 placeholders or a v2 consumer in the existing verifier.

## Deferred verifier follow-up

Verifier input-version dispatch, canonical adapters, prerequisite/capability manifests, evidence-authority decisions, readiness execution, evaluator changes, compliance reporting, exit-code design and all deferred portions above require a separately authorized implementation plan. Their provisional notes are in [migration and integration](migration-integration.md#deferred-verifier-workstream-provisional-notes). Retaining them preserves design context without committing active APIs or release dependencies.

When that follow-up is requested, select its schema revision, actual evaluator scope, source policies, authoritative evidence rules and tests afresh. No automatic activation follows R4 completion.

## Ownership and review

- Schema maintainer owns contract naming, units, cross-record integrity, independent validation and authoritative schema/resource synchronization.
- Extractor maintainer owns conservative factual acquisition, source handles, export selection, migration and loss diagnostics.
- Domain reviewer supplies context for data meaning and unresolved source requirements; engineering authority is not automatically verified by the active validator.
- Verifier maintainer participates in the deferred workstream only; no active schema/producer milestone requires delivery from that role.

These are responsibility roles, not staffing commitments. Avoid calendar or automation-benefit promises without implementation evidence.

## Active progress measures

Track represented facts/relationships, structurally valid documents, supplied-data consistency, field preservation, migration ambiguity, producer limitations and the scope of recorded completeness. Pin the source corpus and contract revision. Count all 504 source clauses and 37 families for documentation coverage; overlapping candidate counts are not benefit estimates.

Compare data representation and preservation on the same source plans before/after producer adoption. Active success does not include improved automated-rule counts, computed readiness percentages, completed compliance checks or fewer findings. Those measures belong to a future verifier evaluation with its own sources and implementation scope.

## Rollout and rollback

1. Retain original v1 schemas, inputs and Python producer behavior. Select `--format-version 1.0.0` for legacy CLI conversion. Preserve existing verifier behavior; it continues receiving original v1 documents.
2. Validate default v2 CLI exports alongside preserved v1 artifacts. Distinguish data-validity diagnostics from compliance results.
3. Review explicit relationships, unit conversions, loss preservation and incomplete acquisition on representative drawings; do not seek matching verifier outcomes for v2.
4. Use CloudTCP IF v2.0.0 as the default configured CLI export without switching the existing verifier's input. Document which producer features and independent validation checks are supported. Keep raw inspection without configuration available.
5. If the v2 export/migration path is faulty, explicitly select `--format-version 1.0.0` with legacy configuration. Preserve v2 artifacts for diagnosis; do not overwrite them with lossy projections.

V2-to-v1 projection is not an active implementation requirement or an assumed bridge into the existing verifier. Any later lossy projection must preserve originals, report lost facts and avoid claims of equivalent rule evaluation.

No running service or monitoring platform is assumed. Initial observability consists of independent validation results, conversion diagnostics and retained source data. Readiness/compliance telemetry is deferred.
