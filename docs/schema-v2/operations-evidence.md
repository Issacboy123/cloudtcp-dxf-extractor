# CloudTCP IF v2.0.0 operations, evidence and completeness

Implementation status: active data-contract, standalone validation and producer work is delivered. See [implemented interfaces and limits](implementation.md) and [release-gate evidence](release-checklist.md). Verifier behavior remains deferred; source-policy and engineering dependencies in this chapter remain unresolved.

Active scope defines stored facts, provenance and completeness records plus their structural/reference consistency. Whether evidence is sufficient, authoritative, current for a rule or establishes nonapplicability is deferred verifier behavior. No readiness engine or compliance reporting is required by this chapter.

This chapter defines records in the document envelope, not additional entity kinds. Each record has a globally unique required `id`. All timestamps use RFC 3339 with an explicit offset; comparison uses instants rather than local clock strings. Unknown intervals remain omitted. Local operating conditions require evidence; a time bin alone does not establish nighttime work.

## Operating phases

| Phase field | Type | Required | Meaning |
|---|---|---|---|
| `name` | string | yes | Human phase description |
| `phase_type` | installation/work/removal/idle | yes | Operation category |
| `start_at`, `end_at` | timestamps | no | Planned/actual interval qualified by assertions |
| `duration` | quantity duration | no | Authored duration where exact clock times are unavailable |
| `mobility` | stationary/mobile/intermittent | no | Operational mobility |
| `light_condition` | daylight/night/mixed | no | Verified coverage of the entire operation, not inferred from snapshot bins |
| `predecessor_refs` | phase refs | no | Dependency DAG; does not assert a precise clock schedule |
| `actions` | ordered array of action objects | no | Declared installation/removal sequence |

Action fields are required `action` (install/remove/activate/deactivate/open/close/cover/uncover), required `subject_refs` (nonempty refs→entity), and optional `at` timestamp and `evidence_refs`. Array order is declared sequence; same-time actions may be grouped in one action record. A phase may include an interval spanning multiple light conditions; rules requiring daytime-only conditions are then not ready unless a narrower phase supplies adequate evidence.

When duration and timestamps coexist, their declared derivation must agree after unit conversion, or be marked disputed if they refer to different evidence. Distinguish a planned schedule from a witnessed operation using assertion method and evidence, not separate guessable booleans. Contradictory ordered timestamps are invalid supplied semantics.

## Evidence records

| Evidence field | Type | Required | Meaning |
|---|---|---|---|
| `source_type` | cad/survey/manual_inspection/plan_document/publication/agency_record/sensor/model/legacy_import | yes | Source category |
| `locator` | object | yes | At least one of `uri`, `file_name`, `record_key`; optional page/section/layer/handle strings |
| `recorded_at` | timestamp | no | Time record was made, distinct from measurement time |
| `author` | string | no | Person/organization identified by source |
| `edition` | string | no | Source version or publication edition |
| `content_hash` | string | no | SHA-256 as 64 lowercase hexadecimal characters |
| `authority` | string | no | Claimed source authority, subject to consumer verification |
| `limitations` | string array | no | Explicit uncertainty or acquisition restrictions |

A locator preserves traceability; consumers do not fetch it automatically. A model source cannot satisfy a source-policy or approval prerequisite merely because `authority` contains a persuasive string. Consumer policy defines allowed evidence and authority requirements per rule. External evidence availability and verification status are reported by the consumer, not silently asserted by structural validation.

## Decisions, exceptions and coordination

| Decision field | Type | Required | Meaning |
|---|---|---|---|
| `decision_type` | engineering_assessment/exception/approval/policy_selection/coordination/conflict_resolution | yes | Why a human/agency record exists |
| `subject_refs` | nonempty refs→entity/phase/observation/assertion | yes | Objects affected |
| `rule_refs` | source/canonical identifier strings | no | Source-scoped applicability; required before a rule treats this as its exception |
| `outcome` | approved/rejected/conditional/information | yes | Recorded disposition, not automatic verifier authorization |
| `authority`, `rationale` | strings | yes | Responsible authority and reasoning |
| `evidence_refs` | nonempty refs→evidence | yes | Basis and signed/recorded decision |
| `phase_refs` | phase refs | no | Affected operating phases |
| `valid_from`, `valid_to` | timestamps | no | Effective period |
| `conditions` | string array | no | Conditions needing review before the decision is applied |
| `parameters` | array of `{name,value,unit,source_locator}` | no | Source-selected numeric quantities or named tiers; value is number/string; unit required for numeric quantities |
| `notified_parties`, `acknowledgements` | string arrays | no | Coordination participants and documented responses |

`source_locator` is a string identifying the relevant source provision. A numeric parameter's unit must be from the core vocabulary. `conditions` are review text, not executable predicates: an unresolved condition leaves readiness blocked. An OPTION does not require a decision merely to record that a permitted treatment was not used. Source clauses that require approval or engineering justification do require corresponding evidence.

Policy selection can record an interpolation/tolerance policy only after the source and authority are resolved. No generic “approved=true” overrides all clauses. Coordination records bind required notifications to the affected closure and phase; assertions/evidence establish whether they preceded closure.

## Observation and design measurements

| Observation field | Type | Required | Meaning |
|---|---|---|---|
| `subject_refs` | nonempty refs→entity | yes | Network/device/facility subjects measured |
| `metric` | enumerated metric below | yes | Physical or operational meaning |
| `value` | quantity or boolean | yes | Type/dimension depends on metric |
| `observed_at` | timestamp | no | Observation instant |
| `interval` | `{start_at,end_at}` | no | Sample/planned interval; both timestamps required |
| `phase_refs` | phase refs | no | Applicable phases |
| `location` / `range` | location/range | no | Measurement scope |
| `reference_locations` | location array | no | Width endpoints, sight observer/target or stopping points |
| `footprint` | footprint | no | Queue or occupancy geometry |
| `basis` | string enum below | no | Selected calculation-speed or measurement basis |
| `mode` | motor/bicycle/pedestrian/mixed | no | User mode |
| `input_refs` | refs→observation/entity | no | Derivation inputs; graph must be acyclic for derived observations |
| `derivation` | string | no | Named method and expression description; not executable code |
| `evidence_refs` | evidence refs | no | Convenience source links; assertions qualify the selected fact |

Metrics: `posted_speed`, `work_zone_speed`, `design_speed`, `calculation_speed`, `observed_speed` (speed); `volume`, `capacity` (flow); `occupancy`, `heavy_vehicle_share` (ratio); `headway`, `delay` (duration); `queue_length`, `clear_width`, `shoulder_width`, `stopping_sight_distance`, `passing_sight_distance`, `curve_radius`, `maximum_device_gap` (length); `grade`, `cross_slope` (ratio); `queue_occupancy` (boolean).

Speed basis enum: `posted`, `work_zone_posted`, `prework_offpeak_85th_percentile`, `anticipated_operating`, `measured_snapshot`, `design_criterion`. Calculation speed requires mode and basis before evaluating a source branch that distinguishes them. Pre-work percentile evidence includes the sampling interval, method and affected approach; generic instantaneous speed cannot be relabeled as a percentile.

A road may carry `posted_speed_ref` and `work_zone_speed_ref` pointing to the respective observation metrics. An approach may carry `calculation_speed_ref`; a taper's explicit selection overrides it only when source applicability and selection evidence permit. Otherwise conflicting selections remain unresolved. No automatic “highest available speed” policy is introduced.

For metrics requiring endpoint/reference geometry, structural validity does not require all inputs; readiness does. A ratio in `%` is converted to `ratio` only mathematically. A volume observation cannot satisfy capacity, and a predicted queue cannot satisfy observed railroad occupancy without an explicitly permitted source policy.

## Prediction records

Required fields are `model_version` string, `predicted_at` timestamp, `horizon` quantity duration and nonempty `subject_refs`→entity. Optional fields: `metrics` array of `{metric,value}` using compatible observation metric/dimension pairs; `confidence` from 0 to 1; `risk_level` low/moderate/high/critical; and `recommendations` array of `{action,priority,subject_refs,reason}` with required action/priority and priority info/low/medium/high/urgent.

Predictions are model-owned outputs. Extraction must not manufacture them from configuration. Input validation can verify their references and types without granting compliance authority. Unsupported legacy metrics are preserved in legacy records rather than silently renamed to a different quantity.

## Scoped inventory completeness

| Completeness field | Type | Required | Meaning |
|---|---|---|---|
| `scope` | selector object | yes | Declares exactly what was inspected |
| `state` | complete/partial/unknown | yes | Collection completeness, distinct from compliant installation |
| `evidence_refs` | nonempty evidence refs | yes | Acquisition/inventory evidence |
| `method` | exhaustive_inspection/configured_extraction/manual_inventory/legacy_import | yes | How inventory was collected |
| `limitations` | string array | no | Missing coverage, unsupported classes and uncertain portions |
| `excluded_source_refs` | evidence refs | no | Known skipped/unprocessed source portions |
| `recorded_at` | timestamp | no | Declaration time |

Scope requires nonempty `subject_refs`→road/approach/path/closure/zone/facility and nonempty `phase_refs`. Optional selectors: `entity_kinds`, `device_types`, `range`. Selectors intersect. They identify a bounded inventory, not the entire project by default. Device-type selectors are valid only when devices/runs are included. An unbounded “everything complete” declaration is not supported in 2.0.0.

Known unsupported or skipped relevant content makes that scope partial. Mere successful export, a configured block map, a count of converted objects or a confidence score cannot establish exhaustive inventory. A narrower, independently inspected subset can be complete even if other areas remain partial. The verifier must not extend a subset declaration to the whole drawing.

Conflicting declarations resolve conservatively: overlapping partial/unknown coverage prevents a complete absence claim for that overlap until the conflict is explicitly resolved. Uncovered areas remain unknown. A complete declaration becomes usable only if its evidence meets the rule's evidence policy.

## Deferred interpretation and readiness

Keep unknown information, reported completeness and assertion states distinct in the data contract. Standalone validation checks supplied shapes, IDs, references, scopes and explicit contradictions; it does not decide which evidence makes a rule evaluable. The provisional readiness interface and aggregation notes are retained in the [deferred verifier workstream](migration-integration.md#deferred-verifier-workstream-provisional-notes), requiring a separate implementation decision.
