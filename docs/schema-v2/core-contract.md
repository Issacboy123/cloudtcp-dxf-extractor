# CloudTCP IF v2.0.0 core data contract

Implementation status: active data-contract, standalone validation and producer work is delivered. See [implemented interfaces and limits](implementation.md) and [release-gate evidence](release-checklist.md). Verifier behavior remains deferred; source-policy and engineering dependencies in this chapter remain unresolved.

Active scope is the data contract and independent structural/semantic validation. Rule readiness, evidence-authority qualification and compliance execution are deferred. References to those concepts describe future uses of the stored data, not active validator obligations.

## Document envelope

Use JSON Schema Draft 2020-12 for structural validation. Object variants are closed to undeclared properties. Each proposed kind is enumerated in the versioned contract; adding a new kind requires a subsequent contract version. Human notes do not bypass typed prerequisites.

| Field | Type | Required | Semantics |
|---|---|---|---|
| `format_version` | string constant `2.0.0` | yes | Selects the v2 contract |
| `document_id` | nonempty string | yes | ID of this immutable document revision |
| `project_id` | nonempty string | yes | Stable project namespace across revisions |
| `revision` | nonempty string | yes | Producer revision label; no lexical ordering assumed |
| `created_at` | RFC 3339 timestamp | yes | Document creation, separate from observation time |
| `site` | object | yes | `name` required; optional project number, description and contact reference |
| `reference_frames` | array of reference-frame records | yes | May be empty if no geometry is submitted |
| `phases` | array of phase records | yes | May be empty in a metadata-only partial document |
| `entities` | array of entity variants | yes | Explicitly partial inventory; may be empty |
| `evidence` | array of evidence records | yes | Evidence inventory, possibly empty |
| `assertions` | array of field assertion records | yes | Provenance and qualification, possibly empty |
| `completeness` | array of scoped declarations | yes | No declaration means unknown completeness |
| `decisions` | array of decision records | no | Human/agency judgments; never generated implicitly |
| `observations` | array of observation records | no | Source measurements, distinct from design facts |
| `predictions` | array of prediction records | no | Model-owned outputs; no implicit compliance authority |
| `previous_document_id` | nonempty string | no | Revision lineage only; not a reference requiring the old document in this snapshot |
| `legacy_records` | array | no | Loss-preservation records defined in migration chapter |

`site` optional fields are `project_number`, `description`, `contact_evidence_ref`. Road names, ownership and classification belong to `road`, allowing multiple roads in one project. Required arrays are transport containers, not declarations that inventory is complete.

## IDs and entity envelope

IDs are nonempty, case-sensitive strings without leading/trailing whitespace, globally unique across all addressable records in the document. References are string IDs. The semantic validator checks target existence and the target kinds specified by field tables. References never depend on array order. A subject's field pointer is relative to its own record.

Every entity has required `id` and `kind`. Optional common fields are `name`, `description`, `phase_refs` and `source_evidence_refs`. `phase_refs` is a nonempty unique list when present; absence means the author has not declared phase applicability, not applicability to every phase. A phase-independent assertion uses the explicit assertion scope described below. Cross-phase borrowing is prohibited unless the supporting assertion explicitly covers both phases.

Use the chapter-specific fields in addition to this envelope. Lists of references cannot contain duplicates. Self-links and cycles are rejected only for relations that are defined as acyclic, such as sign-parent assembly and path composition. Road-network connectivity may contain legitimate cycles.

## Reference frames and geometry primitives

| Record/field | Type and requiredness | Meaning |
|---|---|---|
| Frame `id`, `kind`, `units` | required; `kind=planar` or `station`; `units=feet` or `meters` | Geometry uses exactly the declared frame's length units |
| Planar frame `crs` | optional string | Published CRS identifier; local frames may omit it |
| Planar frame `origin_description`, `axis_description` | optional strings | Human definition; insufficient for numeric transformations alone |
| Station frame `alignment_ref` | optional alignment reference | Alignment with this station domain |
| Station frame `datum_description`, `increasing_direction_description` | optional strings | Station origin/orientation documentation |
| Frame `vertical_datum` | optional string | Required by readiness when elevations from different sources are compared |
| Planar point | `{frame_ref, x, y}` required; optional `z` | Frame must be planar; z shares frame length units |
| Station location | `{frame_ref, station, offset}` required | Frame must be station; signed offset positive left looking toward increasing station |
| Line | `{points: [point, ...]}` | At least two points in one planar frame |
| Polygon | `{rings: [[point, ...], ...]}` | Closed exterior ring then holes; at least four points per ring including closure |
| Station range | `{frame_ref, start_station, end_station}` | Start ≤ end; positive extent required by applicable readiness, not for every point feature |
| Footprint | polygon or station range with optional left/right offsets | A ranged footprint uses `left_offset` and `right_offset`, left ≥ right |

V2 station offsets use frame units; v1 taper offsets' documented feet convention is handled only in migration. Coordinates from different frames cannot be compared without a documented transform. A frame's station direction is a physical convention, not NB/SB/EB/WB.

The geometry union permits planar or station geometry, never an unexplained mixture inside a primitive. An entity may carry both measured facts and geometry. Geometry-derived measurements identify method/evidence, source frame and input revision. No implicit exact equality or engineering tolerance is inferred from decimal precision. Self-intersecting polygons and invalid profiles are semantic errors when supplied.

## Quantities and physical values

`quantity = {"value": finite number, "unit": enumerated string}`. Supported units by dimension are: length `m`, `ft`, `in`; area `m2`, `ft2`, `in2`; speed `mph`, `km/h`, `m/s`; duration `s`, `min`, `h`; angle `deg`; ratio `ratio`, `%`; flow `veh/h`; frequency `Hz`, `flashes/min`. Unknown unit strings are invalid. Definitions constrain units by dimension; a speed cannot use `ft`. Counts are nonnegative integers, not quantities. Temperatures and other unsupported dimensions require a later contract change.

Optional quantity metadata is `uncertainty` as a nonnegative number in the same unit and `measurement_method` as a descriptive string. Evidence qualification still belongs to assertions. A slope uses signed rise/run `ratio`; cross-slope limits generally compare its magnitude. Physical widths, distances and durations are nonnegative; a supplied usable width must be positive. Positions and elevation changes can be negative. Angular values must define the referenced direction in their containing record.

Units enable mathematically valid conversions; they do not supply policy rounding or engineering tolerances. Non-finite numbers are invalid, including values accepted by permissive JSON decoders.

## Assertions and evidence qualification

| Assertion field | Type | Required | Meaning |
|---|---|---|---|
| `id` | ID | yes | Globally unique assertion |
| `subject_ref` | reference | yes | Addressable entity, phase, frame, observation or decision |
| `path` | JSON Pointer | yes | Existing field within subject; empty pointer covers the whole subject |
| `status` | `supported`, `disputed`, `withdrawn` | yes | Whether the selected value can support evaluation |
| `evidence_refs` | nonempty evidence-ref array | yes | Traceable basis; structural existence does not prove authority |
| `method` | `authored`, `measured`, `extracted`, `derived` | yes | Acquisition method, not confidence |
| `scope` | object | yes | Either `{phase_refs:[...]}` or `{phase_independent:true}` |
| `valid_from`, `valid_to` | timestamps | no | Evidence validity interval; end ≥ start |
| `decision_ref` | decision reference | no | Decision qualifying a selected basis or resolving a conflict |
| `alternatives` | array of `{value,evidence_refs}` | no | Conflicting candidate values; each value matches the target field's type |
| `confidence` | number from 0 to 1 | no | Producer uncertainty indicator; never proof of authority |

An omitted field has no assertion and remains unknown. Null is not a generic unknown marker. `false` means a known negative fact and requires appropriate evidence before a rule relies on it. A supported assertion for a parent object may cover its descendants when the referenced evidence actually supports those fields; a child assertion overrides the qualification of that child. At equal specificity, disputed or withdrawn assertions block use until an explicit decision resolves the conflict. Arrival order is never a conflict policy.

An assertion with unresolved alternatives is `disputed`. Resolution retains alternatives and attaches a decision; only the explicitly selected entity value becomes supported. A consumer must explain unsupported, expired, disputed or out-of-phase evidence. Unsupported values can remain in a valid partial document but cannot satisfy an evidence-qualified rule prerequisite.

## Partial input and validation boundary

| Layer | Reject document? | Examples |
|---|---|---|
| JSON and structure | yes | Non-finite value, unsupported version/kind/unit, wrong type, invalid date, unknown field |
| Referential integrity | yes | Duplicate IDs, dangling supplied reference, wrong target kind, assertion pointer not found |
| Supplied semantic consistency | yes | End before start, contradictory phase ordering, impossible dimensions, parent cycle |
| Evidence qualification — deferred | no active evaluation | Stored assertion states/scopes remain representable; judging source authority, freshness or rule sufficiency is future verifier work |
| Rule readiness — deferred | no active evaluation | Future check prerequisites; not computed by standalone validation |
| Compliance evaluation — deferred | no active evaluation | Future findings; not produced by schema validation |

Do not use dummy IDs or zero values to satisfy absent facts. Omit unknown relations. Incompleteness cannot excuse an explicit dangling reference. Spatial overlap between unrelated approaches/phases is permitted; a global v1-style station-order restriction would be invalid for a multi-road document.

## Minimal partial document example

```json
{
  "format_version": "2.0.0",
  "document_id": "doc-002",
  "project_id": "project-demo",
  "revision": "proposal-a",
  "created_at": "2026-11-19T20:00:00Z",
  "site": {"name": "Synthetic intersection works"},
  "reference_frames": [],
  "phases": [],
  "entities": [],
  "evidence": [],
  "assertions": [],
  "completeness": []
}
```

This is structurally valid under the proposed design and provides no basis to assert that traffic-control devices are absent. Standalone validation reports data validity only; it does not produce an all-rules-complete result.
