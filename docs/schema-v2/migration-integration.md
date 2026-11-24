# CloudTCP IF v2.0.0 migration, producer adoption and deferred verifier integration

Implementation status: active data-contract, standalone validation and producer work is delivered. See [implemented interfaces and limits](implementation.md) and [release-gate evidence](release-checklist.md). Verifier behavior remains deferred; source-policy and engineering dependencies in this chapter remain unresolved.

This is the implemented active contract, with deferred notes clearly separated below. Active work is independent v2 validation, default v2 CLI export and migration. The current verifier remains unchanged and receives original v1 documents. All verifier modifications require a separate follow-up decision and are not dependencies of schema or producer delivery. Never pass a v2 document through a permissive v1 override or alter the bundled v1 schema in place.

## Active standalone validation and producer boundaries

| Future interface | Input | Output and behavior |
|---|---|---|
| `validate_v2_document(document)` | Parsed document | Returns unchanged structurally/semantically valid data; raises structured data-validity diagnostics on malformed data. No rule readiness or engineering-authority decisions. |
| `migrate_v1_document(document, context=None)` | Valid v1 document plus optional authored frame/phase/evidence context | `{document, migration_report}`. Never modifies original. Partial output may preserve ambiguous values without making a new semantic claim. Invalid input has no migrated document. |
| Extractor `--format-version 1.0.0\|2.0.0` | Drawing, explicit configuration and requested output version | Configured IF conversion defaults to 2.0.0; legacy v1 requires explicit selection. Without configuration, the default command inspects raw DXF. No implicit migration or configuration fallback. Existing v1 artifacts remain protected. |

The default change applies only to the CLI. Python callers continue using the
version-specific conversion functions; existing v1 functions retain their contract.

The optional migration `context` is an authored bundle with optional `project_id`, `reference_frames`, `phases`, `entities`, `evidence`, `assertions`, `completeness`, `decisions` and `bindings`. Bundle records use the corresponding v2 definitions. Bindings are `{source_path,target_ref,target_path}` records: a legacy source path is associated with an existing authored subject/field, not permitted to overwrite it silently. Conflicts become migration entries and disputed assertions until a recorded decision selects a value. A supplied context must pass its own structural/reference checks after merging; duplicate IDs or unresolved bindings are errors.

Without an authored project ID, migration uses `legacy-import:<source-document-sha256>` as an explicitly provisional import namespace. It is stable for the same input but does not claim identity across changed legacy revisions. Cross-revision entity stability requires an authored project ID and retained identity map. The new document ID incorporates the source hash and migration/context revision; `created_at` records conversion time.

Validation diagnostics have `layer` (json/structure/reference/semantic), `code` string, `path` JSON Pointer, `message` string, `severity` (error/warning) and optional `related_refs`. Hard validation failures contain error diagnostics. Missing optional facts and stored disputed/expired evidence do not become compliance findings or computed readiness results. Infrastructure failures remain operational errors, not malformed-site findings. This interface is independent of the rules verifier.

## Migration report and loss preservation

The migration report has required `source_format_version`, `target_format_version`, `source_document_hash`, `entries` and `summary`. Each entry has `source_path`, optional `target_ref`/`target_path`, `disposition` (preserved/converted/ambiguous/unavailable), `reason` and optional `evidence_refs`. Summary counts report fields and entities separately; neither count is rule coverage.

Preserve the original immutable input outside the conversion output and reference its hash as legacy-import evidence. `legacy_records` entries inside v2 have required `id`, `source_path`, `value`, `reason` and `source_evidence_ref`; `value` preserves an arbitrary JSON subtree. This intentionally open value is a preservation container, not an extensibility mechanism or source of typed compliance facts. All other record objects remain closed. Legacy subtrees do not satisfy typed v2 fields; a future verifier must not treat them as prerequisites implicitly.

Migrated IDs use deterministic namespace-prefixed forms based on collection and escaped v1 ID, keeping an explicit map in the migration report. Generated revision/evidence/frame IDs must not collide with preserved IDs. Do not treat syntactic ID changes as new physical objects. Renamed identity mappings must remain stable across repeated migrations of the same project.

## Complete v1 field disposition

The table groups fields with the same handling; every v1 property and shared definition is included. Optional absent fields stay absent. V1 validation precedes conversion, and valid v1 geometry is not automatically complete v2 geometry.

| V1 fields | Proposed v2 destination | Conditions and preservation |
|---|---|---|
| `format_version` | `format_version=2.0.0` | Original version retained in migration report/evidence |
| `site.name`, `project_number` | `site.name`, `site.project_number` | Preserve text |
| `site.source_file`, `source_format` | Legacy-import evidence locator/type | Original format retained in evidence limitations; DXF does not imply exhaustive extraction |
| `site.coordinate_system`, `units` | Reference frame | Preserve unit declaration; identify whether CRS is usable or merely a local description. Do not create a transform from a label. |
| `site.road_name`, `highway_number` | Road `road_name`, `route_number` | Names do not establish roadway class/ownership |
| `site.state`, `city`, `county` | Road jurisdiction state; legacy record for city/county | Preserve geographic text without converting it to urban/rural or agency ownership |
| `site.location_description` | Road description | Preserve narrative |
| `site.created_date` | Legacy record/evidence locator | Date-only project creation is not document `created_at`; migration uses actual conversion time |
| `typical_application.type` | Closure `closure_type` | Map lane_closure/multi_lane_closure→lane, shoulder_closure→shoulder, road_closure→road, intersection_closure→intersection, median_crossover→median_crossover, ramp_closure→ramp, other→other. Preserve original subtype in legacy evidence. No lane identities inferred. |
| `typical_application.direction` | Legacy record; optional authored approach context | Compass label/BOTH cannot establish frame travel_sign or alternating operation |
| `typical_application.posted_speed_mph`, `work_zone_speed_mph` | Posted/work-zone speed observations, unit mph | Link to road; qualify only as legacy-import facts. Do not identify an alternate calculation basis. |
| `typical_application.lanes_total`, `lanes_closed` | Legacy records plus comparison diagnostics | Counts cannot identify physical lanes, adjacency or closure membership. Do not generate fictitious lanes to match counts. |
| `typical_application.description` | Closure description | No extraction of structured facts from prose |
| `temporal_context.timestamp`, `day_of_week`, `time_of_day_bin` | Legacy snapshot record | Timestamp may qualify corresponding legacy observations; bins/day are preserved, not phase/light declarations |
| `temporal_context.weather`, `visibility_mi` | Legacy snapshot record | Weather visibility is not stopping sight distance; no metric substitution |
| `temporal_context.nearby_event`, `nearby_event_note`, `school_in_session` | Legacy snapshot record | Retained model context; no invented compliance use |
| `zones[].zone_id`, `type`, `description` | Zone ID mapping, zone_type, description | Upstream/downstream buffer zones may also produce linked buffer entities of the corresponding role, with no inferred width/occupancy |
| `zones[].start_station`, `end_station` | Zone extent range in the migrated station frame | Need frame meaning; no global sorting/association across inferred approaches. Zero/reversed semantics are diagnosed before creating an invalid v2 extent. |
| Every element's `element_id`, `type`, `zone_id` | Entity ID/kind/subtype and zone reference | Preserve explicit links; do not upgrade zone membership into taper/path membership |
| Every `source.layer`, `entity`, `handle`, `block` | CAD evidence locator layer/record_key/handle; block retained in locator section | Entity and block names remain traceability, not trusted physical classification |
| Point `position.station`, `offset`, `side` | Station location | Station uses site.units; nonnegative magnitude offset becomes signed by left/right. Center requires zero offset. Negative magnitude or contradictory center/offset is ambiguous, not silently repaired. |
| Sign `mutcd_code`, `legend` | Sign specification | Preserve strings; parser limits remain implementation limits |
| Sign `size_inches` | Structured dimensions where safely parseable | Only a documented unambiguous width×height encoding can become inches. Preserve original string and unknown shape; other strings remain legacy data. Do not assume every sign is rectangular. |
| Sign `face_direction` | Legacy value; optional authored heading mapping | A compass-facing label does not identify a served approach or a surveyed angle |
| Taper `taper_type`, `lane_width_ft`, `side` | Taper subtype; lane width/side retained as legacy data unless authored geometry justifies a mapping | No width substitution for offset W; subtype maps merge/shift/shoulder/downstream unchanged. No one-lane subtype inferred. |
| Taper `start_station`, `end_station`, `start_offset`, `end_offset` | Taper endpoints/measurements when resolvable | Stations use site.units; offsets use documented feet. Convert offsets to frame units exactly. Establish side/sign from verified context; missing/ambiguous sign preserves raw offsets without asserting endpoints. |
| Device line `device`, `spacing_ft` | Device_run device_type, spacing in ft | Barrier remains barrier. No barricade alias. Legacy uniform design spacing does not prove as-built maximum gap. |
| Device line `start_station`, `end_station`, `start_offset`, `end_offset`, `side` | Run geometry only with verified lateral-unit/sign context | V1 line offsets lack an explicit field-level unit declaration. Preserve ambiguous values; do not silently borrow taper feet semantics. |
| Arrow board `mode` | Board specification where unambiguous | sequential_arrow→arrow+sequential with unknown direction; sequential_chevron→chevron+sequential; double_arrow→double_arrow with original pattern retained. flashing/diamond remain ambiguous pattern records until caution semantics are verified. |
| Flagger `position`, `controls` | Actor position; controls retained as legacy scope | Cardinal controls cannot manufacture a path/control assignment |
| Observation `obs_id`, `source`, `station`, `zone_id`, `note` | Observation ID and source evidence, location/scope, legacy note | Split multi-metric readings into separate metric records with shared acquisition evidence. Preserve note in evidence limitations. Do not assign an approach from station alone. |
| Observation `speed_mph`, `volume_vph`, `occupancy_pct`, `headway_sec`, `queue_length_ft` | observed_speed/volume/occupancy/headway/queue_length observations | Explicit units mph/veh/h/%/s/ft; retain source station and zone scope. Missing time/mode stays unknown. |
| Prediction `model_version`, `predicted_at`, `horizon_minutes`, `risk_level` | Prediction fields, horizon in min | Remain model output; missing required v2 prediction metadata preserves the original subtree until enriched |
| Prediction `total_delay_sec`, `max_queue_ft` | delay/queue_length metrics | Corridor/max aggregation meaning retained in evidence; bind to an authored scope before using generic metrics |
| Prediction `by_zone[].zone_id`, `queue_length_ft`, `delay_sec`, `throughput_vph`, `confidence` | Per-zone prediction records and metrics | Map throughput to volume only when clearly labeled as predicted output and preserve throughput semantics; otherwise preserve subtree. Missing identity/time/horizon prevents fabricated records. |
| Prediction `by_zone[].congestion_index` | Legacy prediction record | No v2 observation metric claims equivalence |
| Recommendation `action`, `priority`, `zone_id`, `element_id`, `reason` | Prediction recommendation action/priority/subject refs/reason | Retain explicit ID mappings; never treat a model recommendation as an approved decision |

No v1 source implies verified phase applicability, complete inventory, approved exceptions, source edition or a complete set of approaches. When optional authored `context` supplies those facts, attach separate evidence and mark them authored rather than legacy-inferred.

## Extractor adoption

Keep the existing `(document, report)` result convention. Add a v2 configuration branch with explicit entities, frames, phases and evidence, separate from existing v1 configuration. Existing named-block mapping creates only device/actor variants it actually supports. A flagger block becomes an actor; an arrow-board block becomes a device. Unsupported geometry and physical details remain absent, with diagnostics.

The conversion report retains converted/unmapped/skipped counts and source handles. A v2 completeness declaration incorporates these limitations and is partial unless independent evidence establishes a complete bounded inventory. A file with no INSERT entities can still yield a valid partial document, but cannot claim all signs absent.

The current straight-centerline projection remains a documented acquisition method. Export it as a station frame with measured/configured provenance. Do not claim curved alignment discovery or generate lanes/road edges from a configured straight line. Preserve raw extraction and diagnostics separately.

## Compatibility and storage

Archive v1 and v2 outputs side by side with immutable source hashes. Use explicit version paths for schema resources, keeping one authoritative schema source per version and synchronized packaged copies. V2-to-v1 projection is opt-in, diagnostic-rich and generally lossy; never overwrite a richer v2 document with it. The unchanged verifier continues reading original v1 data during rollout. V2-to-v1 projection is not an active implementation requirement or a compatibility bridge for v2 rule evaluation; any later projection must document information loss and cannot claim equivalent evaluation capability.

Standalone validation and migration reports describe data validity and conversion only. Do not label v2 outputs as verified or compliant. Preserve the v1 originals, v2 exports and acquisition diagnostics separately.

## Deferred verifier workstream provisional notes

Everything below is deferred, nonbinding design input. No verifier API, report version, readiness state precedence, CLI option, exit-code change, evaluator adapter or capability manifest in this section is part of the active implementation contract. Finalize these choices only in a separately authorized verifier plan; there is no automatic activation after producer rollout.

### Candidate verifier interfaces

| Future candidate | Input | Provisional behavior |
|---|---|---|
| `assess_readiness(document, selection)` | Valid v2 document plus selected canonical checks and optional subjects/phases | Provisional records from the [candidate readiness interface](#candidate-readiness-result-interface); no invented comparisons or findings. |
| `verify_v2_document(document, selection)` | V2 input and selected capability manifest | Validation diagnostics or readiness plus per-subject results, aggregate findings, completeness and source accounting. Unsupported evaluators remain explicit. |
| Verifier version dispatch | Reads `format_version`; accepts explicit expected version option | Select exact validator. Reject unsupported/option-mismatched versions; keep legacy registry selection independent of input version. |

`selection` contains `rule_ids` and optional `subject_refs`/`phase_refs`. Referenced IDs must exist. Selecting a registered but unsupported check is valid and produces an implementation blocker. Unknown rule IDs are argument errors. Legacy W1/legacy registry behavior is retained only for v1 unless an explicit v2 capability mapping is implemented and tested; a registry name never fabricates data.

Keep existing API/CLI behavior stable for v1. A possible future V2 report version is `3.0.0`, subject to follow-up review; it includes `input_format_version`, `document_id`, registered/executable rule IDs, source clauses, readiness records, subject results, findings, diagnostics and `evaluation_complete`. Do not reuse the deprecated `implemented_rule_ids` as an executable count.


A possible future exit-code design retains current meanings: operational/evaluator error 4; invalid input/arguments 2; any findings 1; otherwise unresolved work 3; otherwise resolved selection 0. Empty requested selection is invalid. A selection containing only informational clauses may be reported as informational with no invented violation. Unsupported evaluators do not count as resolved. Failures can coexist with incomplete work.


### Candidate adapter and evaluator work


Validation occurs before readiness and before any rule execution. Implement typed adapters exposing canonical internal facts and explicit relationships to evaluators; never flatten multiple approaches back to a single global direction/count. Existing numeric calculations may be reused only after the new subject's prerequisite manifest is satisfied.

Readiness accounts for evaluator support independently of representability. A schema change cannot resolve the 407 placeholder checks. Deliver implementation tickets separately for facts already encodable, new evaluator consumers, unresolved sources and human-review workflows. Preserve default/California canonical sharing to avoid duplicate findings.

Do not globally assume right-side travel from signed offset. Encounter order uses approach travel_sign; placement relative to travel can then be calculated. Guard the selected phase and evidence scope before invoking calculations.


### Candidate readiness result interface


Readiness is a consumer result, not a producer-entered `compliant` flag. One record is returned per canonical rule and subject/phase combination:

| Field | Required content |
|---|---|
| `rule_id`, `subject_refs`, `phase_ref` | Canonical check, evaluated subjects and phase; phase may be absent only for phase-independent checks |
| `state` | ready/missing_facts/insufficient_evidence/unresolved_policy/review_required/unsupported_evaluator/confirmed_not_applicable |
| `blockers` | Array of `{category,requirement,subject_refs,paths,evidence_refs,message}`; category includes schema_capability, missing_fact, evidence, source_policy, judgment, implementation |
| `source_clauses` | All selected source aliases, with their normative strengths |
| `input_document_id` | Immutable document evaluated |

When multiple blockers exist, retain all of them. Select the summary state in this order: unsupported_evaluator, unresolved_policy, review_required, insufficient_evidence, missing_facts, ready; confirmed_not_applicable is permitted only after adequate applicability/absence evidence establishes it. This order is a reporting convention, not permission to skip discovery of other blockers.

Readiness profiles are consumer prerequisite manifests, not document admission requirements. They list required subject fields, relationships, phase/evidence conditions, allowed source bases and resolved policy versions. V2 supports partial inputs even when none of the requested checks are ready.

The final evaluator keeps status and completeness separately. Any known finding survives unresolved sibling subjects: `fail` plus `complete=false`. Across a rule, confirmed nonapplicable subjects do not erase unresolved subjects. Registration, source accounting and executable capability remain separate lists.

### Re-entry criteria

A later verifier project must select its schema revision, supported subject kinds and jurisdictions, source policies, evidence authority rules, actual evaluator scope and independent acceptance scenarios. Revisit the candidate interfaces and report version rather than treating them as frozen by this package. No active schema/export milestone requires readiness results, findings, improved evaluation percentages or changes to the 407 placeholder checks.
