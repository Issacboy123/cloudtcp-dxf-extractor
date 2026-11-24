# CloudTCP schema gaps that prevent rule evaluation

Audit date: November 19, 2026, America/Los_Angeles. Verifier revision: [`ef5e47459aea9559ae8fad7f0087f376308fe09e`](https://github.com/Issacboy123/cloudtcp-python-verifier/tree/ef5e47459aea9559ae8fad7f0087f376308fe09e). Input format: CloudTCP `1.0.0`.

## Findings

CloudTCP 1.0.0 can express useful device locations and a small set of numeric checks, but it cannot describe enough roadway context, relationships, operating conditions, or physical equipment to evaluate most provisions in the bundled rule documents. The largest reusable needs are explicit approaches and lanes; associations among devices, tapers, paths and closures; numbered application selection; roadway classification; cross-section and sight-distance geometry; and operation-specific evidence.

Schema expansion alone will not make the verifier comprehensive. The default registry contains **419 canonical checks**, but only **12 evaluator keys** have rule-specific functions; **407 checks use an explicit unresolved placeholder**. Of the 12, two are declared wholly automated and ten are partial. The two automated capabilities are the downstream taper length range and the numeric whole-mile inscription on a ROAD WORK NEXT sign. Partial functions can resolve supported cases; “two automated” does not mean every other check always fails to run. [Evaluator inventory](evidence/manifest.json), [registry construction](https://github.com/Issacboy123/cloudtcp-python-verifier/blob/ef5e47459aea9559ae8fad7f0087f376308fe09e/rules/full_registry.py#L95-L105).

The audit also found schema-gap overstatements in existing metadata. For example, `T-001` taper placement and `B-004` upstream-buffer permission already fit existing fields; they need appropriate evaluator/interpretation work. Some missing facts are optional fields already supported by the schema. Other blockers require referenced source material, policy decisions, or engineering judgment. Treating all unresolved checks as missing schema fields would produce an oversized schema and leave substantial work unfinished.

The complete clause-level record is [rule-gap-matrix.csv](rule-gap-matrix.csv). [gap-families.md](gap-families.md) details **36 clause-linked capability families and one cross-cutting inventory-evidence concern**, with current schema support, minimum additions, related clauses, and residual blockers. Those mappings are static source/schema assessments; candidate related-check counts are not a forecast of checks automatically unlocked by a change.

## Scope and verified baseline

Both bundled documents are included: **381 entries** in `TCP Rules Document.md` and **76 entries** in `TCP-W1-1 Rules.md`. Their **457 entries** split into **504 clauses**, which map to **419 distinct canonical checks** plus informational clauses. Every heading, citation and complete substantive section body reconciled with the catalog. W1 `SIGN-26` intentionally reuses the same source sentence for inscription and actual-length rounding; reconciliation accounts for that split. [Reconciliation evidence](evidence/source-reconciliation.json).

| Catalog declaration | Source clauses | Interpretation |
|---|---:|---|
| `input_blocked` | 372 | Declared missing facts; independently inspect whether the schema or the instance is responsible |
| `partial` | 23 | A supported subset can run; applicability, exceptions or other subcases remain unresolved |
| `source_blocked` | 34 | Missing or unresolved source/design policy; sometimes additional schema gaps coexist |
| `review_required` | 27 | A decision or assessment requires engineering review |
| `informational` | 44 | No independent canonical violation check |
| `automated` | 4 | Four source clauses share two canonical automated capabilities |

These are the verifier's declared dispositions, preserved for comparison rather than adopted as independent proof. The clause matrix contains the audit's separate blocker categories. Normative strengths are retained at clause level: 95 STANDARD, 287 GUIDANCE, 88 OPTION and 34 SUPPORT clauses. An OPTION permits a treatment; omission of that treatment is not automatically a defect. Mixed-strength source headings are not flattened into one classification. [Catalog snapshot](evidence/source-catalog.json).

The verifier schema, extractor root schema and packaged extractor schema are byte-for-byte identical, with SHA-256 `2109f24ef1659389dbfb72da650efe03767cdd9635a145afab86b2dfe000eba6`. This report therefore addresses the actual shared contract rather than schema drift. [Environment and hash manifest](evidence/manifest.json).

| Execution | Result |
|---|---|
| Existing test suite | **648 passed** |
| Existing Ruff check | Passed |
| Bundled examples | **155 files × 2 registries = 310 API runs** |
| CLI/API smoke comparisons | **24/24** exact output and exit-code agreements across default, all, W1 and legacy registries, JSON and text |
| Focused synthetic inputs | **53 schema-valid documents × 2 registries = 106 executions**; 92 selected rule-result records, all expectations passed |
| Rejected capability extensions | **14/14** rejected as expected, exit `2`, no rules executed |
| Information-loss witnesses | Five explicitly hypothetical pairs of arrangements sharing one validated payload |

The run used Python 3.14.10 on macOS arm64. [Test output](evidence/pytest.stdout.txt), [Ruff output](evidence/ruff.stdout.txt), [example summary](evidence/example-summary.json), [CLI comparisons](evidence/cli-smoke-summary.json), [focused summary](evidence/probes/summary.json).

For **each** example registry, the invalid file exited `2`; nine valid files exited `1` with findings; and 145 valid files exited `3` without findings but with incomplete evaluation. No valid bundled example completed the whole selected registry. These are properties of the supplied fixtures, not estimated frequencies for real plans. Default-registry outcomes across valid fixtures included 55,407 `not_evaluable`, 9,098 `not_applicable`, 10 `fail`, and 11 `pass` rule results. The W1 totals were 10,445, 1,240, nine, and ten respectively. [Run summary](evidence/run-summary.json).

## Schema capabilities that need expansion

### Identity, applicability and relationships

The current `typical_application.type` is a coarse closure category, not a numbered TA, figure, Caltrans Standard Plan, edition, variant or phase. It cannot select layout-specific rules or distinguish optional figure devices. Similarly, lane counts do not identify which lanes close, their directions, the receiving lane, or alternating one-lane/two-way operation. `direction=BOTH` does not supply those facts.

Zones provide station intervals and elements can reference one `zone_id`; neither expresses a traffic approach, a lane, a directed path, a closure, or membership in a taper. Signs have optional cardinal facing but no served-approach identity. A device line may overlap a taper in station without serving it. Two arrow boards and two closed lanes do not prove one board serves each lane. Add explicit identities and relationships, with jurisdiction/application context, before attempting more geometric inference.

Road names, highway numbers, city strings and posted speeds cannot reliably establish freeway/expressway status, urban/rural context, access control, divided-road status, through-lane function, or State-highway ownership. These select provisions and sign-size tiers. Add explicit classifications with evidence rather than parsing names or treating counts as classification.

### Geometry, operation and speed basis

Station/offset locations lack the reference centerline geometry, horizontal curves, vertical profile, grades, road edges, shoulder cross-sections, remaining clear lane widths, turning paths, ramps and intersection connections needed by many clauses. A coordinate-system name does not define that geometry. `lane_width_ft` on a taper is not the remaining traveled lane width or a universal substitute for lateral offset W.

Upstream/downstream buffer lengths are representable. Lateral buffer role, width, footprint, occupancy, relationship to opposing flows, and work/storage intrusion are absent. Flagger coordinates and weather `visibility_mi` cannot establish available stopping sight distance to an intended stopping point. Add measurements tied to the relevant approach, facility and reference points.

`temporal_context` describes snapshot conditions, not installation duration, stationary/mobile work, daylight/night operation, ordered setup/removal actions, or phase-specific lane states. These need operation and phase records. Timestamp-derived guesses are insufficient where the rule needs actual operating or lighting conditions.

The required speed is not always the posted limit. The bundled text also uses pre-work off-peak 85th-percentile, anticipated operating and bicycle speeds. Optional `work_zone_speed_mph` and generic point observations do not record these distinct bases, selection authority, time or applicable mode. Preserve posted speed and add qualified calculation-speed evidence. This limitation was underrepresented in existing formula metadata.

### Equipment, other road users and decision evidence

The five element variants—sign, taper, device line, arrow board and flagger—omit many required entities and properties. Gaps include individual channelizer dimensions and reflective/light properties; barricade types; barrier crashworthiness and protection relationships; arrow-board equipment and deployment state; portable message signs; mounting heights/supports; work/shadow vehicles, lighting and attenuators; AFADs; signals and stop lines; and pavement-marking placement/removal state.

Pedestrian routes, accessible clear widths, ramps, landings, slopes, surfaces, passing spaces and crosswalk states are absent. Bicycle facility geometry, operating mode and speed evidence are absent. Railroad crossing geometry and queue occupancy, crossroad/driveway topology, traffic movement demand, capacity, vehicle mix and required coordination records also need structured support where their clauses apply.

Exceptions, engineering studies, agency approvals and review decisions need rule-scoped authority, rationale, evidence, applicability and effective time. Recording these facts would support verification workflows; it would not make judgment automatic. Observations can carry point readings, and predictions can carry model outputs, but neither is automatically approved compliance evidence.

Free-text `description`, `note` and sign `legend` fields can preserve narrative. They do not establish typed interoperable relationships or the authority behind a decision. CAD `source` fields establish traceability. Strict `additionalProperties: false` at modeled objects and the finite element/taper discriminators prevent consumers from simply appending these missing facts to a valid v1 document. [Rejected-extension diagnostics](evidence/probes/rejected-extensions.json).

There is also an inventory-evidence gap: `elements` may be empty, with no indication that all relevant drawing/site content was successfully examined. A valid synthetic input with an empty element list makes all 12 rule-specific evaluators return `not_applicable`; the full report still remains incomplete because of its other placeholders. That does not prove the physical site has no devices. Carry scoped extraction/inventory evidence into the verification workflow rather than requiring an arbitrary minimum device count. The extractor already emits separate skipped/unmapped diagnostics that can contribute to this evidence. [Sparse-input results](evidence/inventory-completeness.json).

## Demonstrated consequences and non-schema causes

| Case | Observed behavior | Root cause |
|---|---|---|
| 45-mph line at 60-ft spacing beside a taper | Incomplete in both registries; 20 ft passes and 100 ft fails in the focused scenario | No line-to-taper/tangent association to select the S versus 2S bound |
| California 55-mph spacing | 20 ft passes; 20.01 and 100 ft remain incomplete; 100.01 ft fails | Column, conflict and separate taper-cap applicability are unmodeled |
| Multiple warning/transition approaches | Sign placement remains incomplete despite explicit facing | No persistent served-approach relation |
| Missing sign facing or flagger controls | Supported scenarios become complete after supplying the existing fields | Missing input, not absent schema capability |
| 42-mph taper formulas or unlisted table speed | Incomplete despite encoded speed | No supplied branch/interpolation policy |
| Unknown warning code or spelled-out mileage | Incomplete although strings fit the schema | Evaluator/code-set or parser limitation |
| Zero-length or overlapping warning zone | Schema and ingestion accept it; placement evaluator rejects the geometry | Input quality and validation prerequisites |
| Zero-offset taper with `lane_width_ft=12` | Historical W1 passes; full registry remains incomplete | Registry interpretation differs on substituting lane width for W |

At 45 mph, a 60-ft-spaced line serving a merging taper and the same modeled line serving an overlapping tangent path have different applicable bounds. The v1 payload cannot distinguish them. Four further hypothetical pairs demonstrate the same information loss for sign exceptions, flagger sight distance, board-to-lane assignment and roadway size tier. These are explicit information-loss witnesses, not findings about real sites. [Counterexamples](evidence/probes/counterexamples.json), [focused results](evidence/probes/focused-results.json).

Missing source material remains distinct from missing facts: referenced Standard Plans, external design/accessibility criteria, extraction uncertainties and figure issues need authoritative resolution. Approximate 20-ft wording needs an authorized interpretation/tolerance; speed tables need an explicit policy for unlisted rows. The audit does not invent these. A schema extension can record a selected policy and evidence after it exists.

Two permissive cases illustrate why catalog labels need review: `T-001` can associate an existing taper with a transition/termination zone; `B-004` can represent upstream buffer/work intervals. W1 `SIGN-24.c01` legend/code content and fixed-size subcases of `SIGN-31` likewise have existing representable inputs. Authoring evaluators and preserving permission semantics can improve these without inventing a new object model. The separate reviews retain the exact scope and residual conditions. [Full-document corrections](analysis/full-document-findings.md), [W1 review](analysis/w1-findings.md).

## Reporting behavior that affects interpretation

Incomplete work is not limited to `not_evaluable`. Focused mixed-subject probes produce **`fail` with `complete=False`** for channelizer spacing, flagger warning and full-registry taper length. Capture both status and completeness; a finding does not establish that all subjects were evaluated. None of the bundled examples exhibited that mixed case, which is why the additional probes matter.

`not_applicable` can mean a federal check delegates to a California replacement. Inspect the replacement before declaring coverage resolved. `implemented_rule_ids` is a deprecated list of registered checks, including placeholders. Scores are binary report projections: pass is `1`, everything else is `0`. A short optional buffer's raw graded score becomes public pass/score `1`. These values cannot measure schema coverage or regulatory compliance. [Reporting implementation](https://github.com/Issacboy123/cloudtcp-python-verifier/blob/ef5e47459aea9559ae8fad7f0087f376308fe09e/reporting.py#L94-L126), [probe review](analysis/probe_findings.md).

Historical `compliant.json`/`violating.json` names describe fixture intent. Many pairs are identical or lack facts required by today's evaluator; names were not used as expected pass/fail results. Equivalent feet/meter longitudinal taper geometry passed the focused boundary test. Explicit feet fields and the documented taper-offset feet convention were retained, rather than indiscriminately rescaling all numbers. Taper-offset units are specified in the field reference but omitted from those fields' JSON schema descriptions; future geometry contracts should make each field's units explicit.

## Recommended sequence

1. **Improve existing-input coverage first.** Correct misleading blocker metadata, implement representable content/fixed-dimension subcases, distinguish permissions and definitions, and require existing optional evidence when selecting checks. Preserve unknown states and complete/incomplete reporting.
2. **Establish shared identity and applicability.** Add explicit layout/version selection, roadway classification, directed approaches, lane/closure identities, device-to-taper/path relationships, operating phases and qualified speed bases. This foundation supports multiple families; adding unassociated scalar fields will not resolve their ambiguity.
3. **Add safety geometry and evidence.** Build road cross-sections, remaining clear widths, shoulders, alignment, buffers, sight/stopping measurements and pedestrian/bicycle facilities. Tie measurements and evidence to identified facilities and phases. Obtain referenced criteria and preserve engineering decisions separately.
4. **Extend equipment and specialized operations.** Add required physical specifications, work vehicles, markings, controls, AFADs, barriers/barricades, message signs, ramp/intersection/railroad relationships and coordination evidence. Implement consumers alongside each approved capability.

Prioritize STANDARD applicability and measurements first within each group, followed by GUIDANCE and explicitly selected optional treatments. Candidate related-check counts in the appendix estimate reuse, not implementation effort or guaranteed benefit. Geometry/topology and evidence design are larger changes than a new enumerated subtype; adding one-lane/two-way taper support is small in isolation but still requires flow/association data and an evaluator.

A future extension needs an explicit format-version and verifier compatibility decision: v1 fixes `format_version` to `1.0.0` and rejects extra fields. Ship new validation and evaluators with the new contract; preserve the original input and source evidence during any migration. This audit changes no public API, schema, evaluator or exporter behavior.

## Evidence boundaries

The report accounts for every clause in the two checked-in extractions at the pinned commit. It does not establish that those extractions contain every provision of an official manual or current external law. Exact source reconciliation proves accounting; it does not prove implementation or legal interpretation.

Implemented families have runtime probes. Placeholder families have source/schema analysis and observed placeholder outcomes, not fabricated execution of missing logic. Clause-level confidence and evidence basis are retained, including medium-confidence static family mappings requiring source-specific review before field design. Engineering judgment, permissions and informational text remain distinct from enforceable numeric tests.

All raw reports, logs and synthetic inputs are retained in [evidence/](evidence/). Use [README.md](README.md) to reproduce the tests/runs and rebuild the matrix.
