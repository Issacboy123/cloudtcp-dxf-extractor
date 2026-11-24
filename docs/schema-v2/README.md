# CloudTCP IF v2.0.0 schema specification

Status: active schema/validation/producer scope implemented, November 19, 2026. The original specification chapters below define the contract; [implementation and usage](implementation.md) records executable interfaces and limits. The [release checklist](release-checklist.md) links active gates to test evidence. Verifier proposals remain deferred and nonbinding.

Active scope: schema expansion, independent structural/semantic validation, default v2 CLI export and v1 migration. All changes to the rules verifier are deferred to a separately authorized follow-up. The current verifier remains a v1 consumer; delivering this plan does not require it to read v2.

CloudTCP v2 should let a producer describe the facts needed by a rule, identify their source and scope, and distinguish an unknown fact from a confirmed absence. It must preserve useful partial CAD extraction without turning incomplete evidence into a compliance claim. Explicit relationships, roadway context, geometry and measurements come before additional rule automation.

The specification covers all 37 families in the [schema audit](../../reports/schema-gap-audit/report.md), including all 504 source clauses. Audit baseline: verifier `ef5e47459aea9559ae8fad7f0087f376308fe09e`, extractor `67e0def600166301a72e1b2b64e0fa8bdac50a53`, shared schema 1.0.0. It does not replace or independently verify the official manuals referenced by the extracted rules.

## Reading order

| Document | Decisions and implementation detail |
|---|---|
| [Schema handoff](handoff.md) | Delivery artifacts, validator integration, consumer semantics and rules verifier acceptance |
| [Architecture](architecture.md) | Boundaries, entities, versioning, design decisions and dependency order |
| [Core contract](core-contract.md) | Document structure, IDs, units, geometry primitives, assertions and validation layers |
| [Roadway and geometry](roadway-geometry.md) | Network topology, applications, lanes, approaches, tapers, cross-sections and facilities |
| [Devices and road users](devices-road-users.md) | Device variants, physical specifications, runs, actors, vehicles and controls |
| [Operations and evidence](operations-evidence.md) | Phases, calculation bases, approvals, completeness, observations and predictions |
| [Rule traceability](rule-traceability.md) | All gap families and all 504 clauses, including non-schema dependencies |
| [Migration and integration](migration-integration.md) | Active legacy conversion/extractor adoption; separate provisional verifier follow-up |
| [Validation and rollout](validation-rollout.md) | Acceptance scenarios, release gates, metrics and rollback |

## Confirmed product decisions

- Clean redesign with `format_version: "2.0.0"`; Draft 2020-12 is the JSON Schema dialect.
- Plan geometry uses declared feet or meters. Physical and operational measurements carry explicit value/unit pairs.
- Hybrid support for geometry and authored measurements; a full civil model is not required to submit useful partial facts.
- Structurally sound partial inputs are accepted. Rule readiness is separate from document validity.
- CloudTCP IF v2.0.0 is the default CLI format for configured IF conversion. Legacy v1 requires `--format-version 1.0.0`; Python conversion APIs remain version-specific. Migration preserves original v1 data. Verifier APIs, version dispatch, readiness execution, evaluator changes and compliance reporting are deferred.
- Standalone validation checks the data contract and supplied consistency. It does not execute rules, verify engineering authority or compute rule readiness.
- The original specification blocks remain illustrative excerpts. The authoritative JSON Schema, validated runtime fixtures, standalone validator and producer/migration modules are now delivered separately; see the implementation guide.

## Success criteria

Every gap has a documented place in the model, a validation boundary and a delivery phase. Each source clause identifies its needed capabilities and remaining implementation, source-policy or judgment work. Every v1 field has a conversion or explicit preservation disposition. Producers can represent different approaches and device associations without guesswork, independently validate supplied data, and preserve unknown or disputed facts without assigning compliance outcomes.

The active target is increased representability, data integrity and conservative producer adoption. Automated-rule counts, readiness results and compliance findings are not active success measures. The 419 canonical checks remain traceable for future work; candidate impact counts overlap and must not be added or interpreted as guaranteed unlocks.

## Specification conventions

“Required” in an entity table means required when that entity variant is supplied. Optional fields can be omitted when unknown. A rule can require optional data before evaluating its subject. Tables define the implemented contract, with details resolved in the implementation guide; regulatory numeric values must come from resolved source provisions, not these example values.

All examples use synthetic sites. Names such as `taper_type`, `subject_refs` and `calculation_speed` are v2 interfaces. V1 behavior remains separate and unchanged.
