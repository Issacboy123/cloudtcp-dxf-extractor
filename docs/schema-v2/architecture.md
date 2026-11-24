# CloudTCP IF v2.0.0 architecture and decisions

Implementation status: active data-contract, standalone validation and producer work is delivered. See [implemented interfaces and limits](implementation.md) and [release-gate evidence](release-checklist.md). Verifier behavior remains deferred; source-policy and engineering dependencies in this chapter remain unresolved.

## Goal and boundaries

The v2 contract joins explicit network identities, physical plan objects, operating phases and traceable evidence. Active work covers the schema, standalone data validation, extractor export and migration. Rules-verifier changes are deferred. A future verifier must not infer freeway class from a road name, taper membership from station overlap, an alternating lane from `BOTH`, or authority from a model prediction.

Data acquisition may involve configured CAD extraction, a survey, authored measurements, a published plan or a documented engineering decision. A producer records what it knows. The model supports those sources without implying that the present extractor can acquire every field automatically.

No native DGN reader, image recognition, complete civil geometry kernel, external evidence downloader, regulatory threshold invention or 407-evaluator implementation is included in this documentation project. Future implementation packages must declare their narrower capabilities.

## Chosen model

The document contains versioned metadata, reference frames, phases, typed entities, field-level assertions, evidence records, completeness declarations, decisions, observations and predictions. An entity inventory replaces v1's mixture of project-wide counts and five device variants. IDs remain stable within a project across revisions; a document is a complete snapshot of its submitted partial knowledge, not a patch protocol.

| Concern | Decision | Consequence |
|---|---|---|
| Version | New `2.0.0` contract with independent validation; preserve v1 tooling | Current verifier continues receiving original v1 documents; no v2 verifier dispatch is required |
| Shape | Typed entities in one `entities` array, with common ID/kind/phase fields | Concrete relationships reference entities instead of array positions |
| Reference targets | Globally unique IDs with target-kind restrictions | Semantic validator catches dangling or wrong-kind links |
| Geometry | Declared frames; optional explicit alignments and profiles; measurements also supported | Readiness can use measured facts without reconstructing every surface |
| Direction | Signed lateral offset relative to increasing station; explicit approach travel sign | Compass headings do not determine encounter order |
| Units | Frame units for coordinates; value/unit quantities for physical facts | No hidden `_ft` assumptions in new fields |
| Partial data | Omission is unknown, never implied false | Validity and readiness remain separate |
| Evidence | Assertions bind subject fields to evidence and a phase/time scope | Unqualified or disputed values cannot satisfy evidence-dependent checks |
| Absence | Scoped inventory declaration plus adequate collection evidence | Empty arrays alone cannot establish physical absence |
| Application | Explicit jurisdiction, source edition, layout and variant | A closure label no longer selects a whole rule family by implication |
| Judgment | Scoped decisions with authority and rationale | Recording an approval supports review; it does not automate authority |

## Entity ownership

| Group | Entity kinds | Authoritative chapter |
|---|---|---|
| Road network | `road`, `alignment`, `approach`, `lane`, `path`, `junction`, `ramp`, `boundary` | [Roadway](roadway-geometry.md) |
| Plan scope and geometry | `application`, `closure`, `zone`, `taper`, `buffer`, `work_area`, `facility`, `crossing`, `marking`, `restriction`, `ttc_extent` | [Roadway](roadway-geometry.md) |
| Equipment and people | `device`, `device_run`, `vehicle`, `actor`, `control` | [Devices](devices-road-users.md) |
| Evidence containers | Reference frames, phases, assertions, evidence, decisions, completeness, observations, predictions | [Core](core-contract.md) and [operations](operations-evidence.md) |

There is one definition for each shared concept. A temporary barrier is a `device` subtype, not a new road-boundary synonym; an AFAD is equipment, not an `actor`. A `device_run` supplies placement/spacing for homogeneous devices without asserting every device was individually surveyed. A `control` links equipment and actors to the paths and stopping points they control.

## Dependency and implementation order

1. Define envelope, units, references, assertions and unknown-information semantics. Implement independent structural and semantic validation without rule execution or readiness computation.
2. Add applications, roads, approaches, lanes, paths and closures; then zones, tapers and explicit device associations. Include operation phases and selected speed evidence.
3. Add road-edge/cross-section geometry, buffers, sight-distance measurements and pedestrian/bicycle facilities.
4. Add detailed equipment, work vehicles, markings, specialist facilities and coordination requirements.

Evidence and decisions are foundational structures even when specialist uses arrive later. Each stage delivers documented data capabilities and standalone validation scenarios. Extractor adoption and migration begin incrementally once the relevant contract is stable; they do not wait for verifier changes. Configured CLI conversion defaults to v2.0.0, with explicit legacy v1 selection. Unsupported producer features generate preservation/limitation diagnostics rather than silent data loss.

## Deferred verifier workstream

Verifier version dispatch, internal adapters, rule prerequisite manifests, readiness execution, evaluator changes, evidence-authority decisions, compliance report changes and exit-code behavior require a separate implementation decision. They are not release gates or dependencies of the active schema/producer milestones. Provisional notes are retained in [migration and integration](migration-integration.md#deferred-verifier-workstream-provisional-notes).

This follow-up has no automatic activation date. Before it starts, re-review the selected schema revision and source requirements, then finalize verifier interfaces and acceptance criteria independently. Schema validation or successful extraction must not be presented as a rule evaluation.

## Source authority and unresolved inputs

The pinned extracted documents define the traceability inventory. Referenced manuals, missing figures, authorized tolerances and table interpretation remain tracked external dependencies. The documentation does not choose an interpolation policy between published rows or an acceptance band for “about 20 ft.” A future resolved policy must identify its source/version, applicability and approving authority.

Before implementing an affected clause, review its source context and audit confidence. Its listed schema capability is a candidate prerequisite, not a certification that every source exception is resolved.
