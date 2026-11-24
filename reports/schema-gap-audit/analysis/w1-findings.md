# Independent W1 clause audit

Audited repository: `Issacboy123/cloudtcp-python-verifier` at `ef5e47459aea9559ae8fad7f0087f376308fe09e`; schema `1.0.0`. The companion `w1-audit.json` covers all 76 source headings and all 120 W1 source-catalog clauses, with unique source-rule/clause keys. Every JSON Pointer in its `schema_support` resolves against the unchanged schema. An `absence:` statement describes the missing capacity; it is not a fabricated pointer.

This is source/implementation analysis. The parent audit owns actual test execution, CLI/API runs and probe artifacts. This file does not claim that reading a test or source branch constitutes a passing execution.

## Counting and attribution

- Catalog dispositions are inherited claims, not independent proof of a schema defect. W1 clauses: 102 input_blocked, 10 partial, 3 review_required, 2 source_blocked, 2 automated, 1 informational.
- Blocker categories overlap. `schema` identifies an unrepresentable fact/relation; `missing_input` identifies an optional existing field or unusable supplied geometry; `implementation` identifies absent or restricted code; `source_policy` identifies unavailable criteria or unresolved interpretation; `engineering_judgment` retains the human decision; `informational` flags permission/explanation rather than a compulsory choice.
- Each OPTION record explicitly says the source permits a choice or constrains its chosen use. It must not be counted as a universally missing mandatory feature. Existing full-catalog `informational` disposition is separate from this normative interpretation.
- A formula that can use required posted_speed_mph is evaluable for that selected basis. Additional permitted pre-work 85th-percentile/anticipated speeds cannot be selected with provenance in this schema. Those are conditional capability gaps, while 40<S<45 is a missing source formula policy.
- The downstream 50–100-ft predicate is executable with existing stations and units. One-lane-two-way identity is a separate missing enum; it does not block ordinary shift/shoulder clauses.

## Findings that change the apparent scope of schema work

| Source | Independent finding | Consequence |
|---|---|---|
| SIGN-08 | Existing optional face_direction plus unique warning/transition zones can resolve a restricted single approach; full evaluator has a hardcoded warning-code policy. | Populate missing fields and identify code-policy limits separately from missing multi-approach relationships. |
| SIGN-11 | Right/left is relative to travel direction, but position.side is relative to increasing station. | Explicit approach orientation and placement exceptions are needed; a cardinal direction alone is insufficient. |
| SIGN-12 | Dual-side, roadway-portable and barricade installation is permission. | Stub not_evaluable does not establish a mandatory schema gap. |
| SIGN-16 | A sign offset from centerline exists, but pavement-edge/curb distance does not. | Add road-edge/curb references, rather than another unqualified offset number. |
| SIGN-17.c02 | ADA Sec.307 is not reproduced. | Geometry extension alone cannot establish the external legal/technical criterion. |
| SIGN-18 | Installation duration and mounts are absent; Part2 heights and similar-sign exceptions are not supplied as complete policy. | Keep modeling and source-policy work distinct. |
| SIGN-19.c02 | Existing size_inches can yield sign area when present; supporting-post type/count and ground clearance are absent. | Do not classify every sign dimension as wholly unrepresentable. |
| SIGN-20/22 | Counts, direction=BOTH and lane_closure do not encode adjacent through lanes or a shared alternating lane. | Add lane identities, directions, closure grouping and approach association. |
| SIGN-21.c01 | Explicit face_direction and flagger.controls already exist but are optional. | A single-approach case often needs better input, not a new field. |
| SIGN-21.c02 | Adding W3-4 is optional. | No mandatory chosen=false field is necessary merely to allow a supplementary sign. |
| SIGN-24.c01 | mutcd_code and legend can express allowed variants. | A narrow content evaluator can be implemented now; the freeway sequence still needs road and approach scope. |
| SIGN-25 | Termination endpoints already exist. | Near-end placement is judgment and scope/association, not simply absent termination geometry. |
| SIGN-26.c01/c03 | Zone stations exist, but inventory completeness/authoritative TTC limits and mileage-sign association are unqualified. | Add authoritative extent/association, derive miles; avoid duplicating a computable unit conversion. |
| SIGN-26.c02 | Full parses only recognizable numeric ROAD WORK NEXT legends. | Optional missing legend is input; alternate string formatting is parser support; neither is proof of absent field capacity. |
| SIGN-30 | Codes, legends and optional size strings exist; plaque-parent and agency determination do not. | Add assembly/determination relations and optionally structured dimensions. |
| SIGN-31 | Road-tier-dependent warning sizes are blocked, but fixed regulatory rows can use existing optional size_inches. | Partial evaluator work is possible before a schema extension. |
| TAPER-02.c04 | Enum permits merge, shift, shoulder and downstream, not one-lane-two-way. | Add a distinct type; do not disguise it as downstream or BOTH. |
| TAPER-03 | About20ft lacks approved acceptance tolerance as well as device/taper association. | Additional geometry must not invent a numeric pass/fail band. |
| BUFFER-01 | OPTIONAL short buffer still passes; table has discrete speed rows. | Unlisted speed is table policy, not missing schema field; binary report scores override old graded-score comments. |
| BUFFER-02 | Station-only buffers cannot express lateral footprint or work/storage occupancy. | Add footprints and occupancy, retaining human lateral-width selection. |
| CHAN-01 | device enum excludes barricades; barrier is a different kind. | Add barricade representation and explicit taper/tangent relation; never relabel barriers. |
| CHAN-03/04, FLAG-04, ARROW-07 | A snapshot timestamp/time bin does not prove planned operation lighting conditions. | Record work-period light context and actual equipment/activation facts. |
| PED-01–05 | Routes, crossings, passing spaces, ramps, detectable devices and signal state are absent. | Add pedestrian topology and physical specifications, not flattened text. |
| ARROW-02/05 | Board count cannot establish board per closed lane or ordered taper/lane positioning. | Add lane, stage, board and taper identities/relationships. |
| FLAG-02 | visibility_mi is weather/context; a flagger/work-boundary gap is not approach stopping sight distance. | Add measured sight distance and intended stop point with provenance. |
| FLAG-08/09 | Human flagger and AFAD equipment are distinct entities. | Add equipment/operator/stop-point/attendance relationships and physical AFAD attributes. |
| FLAG-10 | One timestamp cannot establish planned <=20-minute daytime closure or LEO alternative. | Add planned duration/light context and personnel roles. |

## Full registry versus historical W1 behavior

| Behavior | Full/default | Historical W1 | Source evidence |
|---|---|---|---|
| Overall coverage | Both source documents; canonical shared checks and California guards | 76 W1 headings with evaluator/stub mixture | rules/full_registry.py:65; rules/w1_registry.py:206 |
| Warning order SIGN-08 | Partial executable comparison | Unconditional stub | rules/full_evaluable.py:193; rules/w1_registry.py:31 |
| Whole-mile inscription SIGN-26 | c02 numeric-whole-mile comparison; c03 actual-length relationship remains blocked | Whole SIGN-26 stub | rules/full_evaluable.py:261; rules/w1_registry.py:77 |
| Zero offset W with lane_width_ft | Removes lane_width_ft fallback before formula delegation | Uses lane_width_ft as fallback | rules/full_evaluable.py:94; rules/w1_evaluable.py:114 |
| California 12-ft taper rows | Exact listed-speed printed lookup under CA-007 | Generic formula | rules/full_evaluable.py:80; rules/full_evaluable.py:132 |
| Downstream taper | Evaluated once under T-013, overlaps cited | Evaluated under TAPER-02 | rules/full_evaluable.py:85; rules/w1_evaluable.py:195 |
| California device spacing | CA-008 considers unknown table column/conflict and CA-008-B20ft cap | Federal S/2S bounds | rules/full_evaluable.py:124; rules/full_evaluable.py:161; rules/w1_evaluable.py:228 |
| TAPER-03 | Unsupported canonical check returns incomplete regardless of subjects | No downstream taper returns not_applicable; otherwise incomplete | rules/full_registry.py:95; rules/w1_evaluable.py:217 |
| FLAG-02, SIGN-31 | Unsupported canonical check normally remains not_evaluable | Can return not_applicable when no flaggers/signs | rules/full_registry.py:95; rules/w1_evaluable.py:288; rules/w1_evaluable.py:383 |
| SIGN-20, ARROW-02 | Blocked canonical stubs | Shoulder closure or explicitly zero closed lanes can return not_applicable | rules/full_registry.py:95; rules/w1_evaluable.py:320; rules/w1_evaluable.py:427 |
| California replacements | Z-025/B-009/Z-026/D-014 marked not_applicable; CA replacement can remain blocked | No full-source CA replacement accounting | rules/full_registry.py:15; rules/full_registry.py:48 |

These differences mean a status from one registry must not be presented as the inherent capacity of the schema. Subject absence, delegation, code restrictions and jurisdiction guards need separate explanation.

## Cross-cutting interpretation and evidence risks

1. `RuleResult.status=fail` can have `complete=False`; retain both its finding and unresolved subjects. The independent audit must include every incomplete result, not merely not_evaluable. Evidence: rules/w1_evaluable.py:92 and rules/full_evaluable.py:68.
2. `implemented_rule_ids` is a registration list, not an executed-comparison list. Full code advertises only T-013 and SIGN-26.c02 as wholly automated. Evidence: rules/full_evaluable.py:288; rules/full_registry.py:150; tests/test_full_registry.py:29.
3. Reports project scores to1 only for pass and0 for other statuses, erasing evaluator graded scores. A zero must not mean a regulatory violation. Evidence: reporting.py (_reported_result).
4. Historical compliant/violating fixture labels are not ground truth; many are identical. tests/test_w1_rules.py:17 explicitly warns of intended labels; six evaluator families remain incomplete even in both labeled examples. There are155 bundled JSON files:152 W1 examples plus three top-level files.
5. The schema permits empty elements with no independent extraction-completeness record. Absence of supported subjects often yields not_applicable. An extractor may omit unsupported entities while producing valid JSON; that is an evidence-completeness concern, not proof that no physical device exists.
6. Sign size and legend are unconstrained strings. Adding structured dimensions can improve future data quality, but existing strings still represent known dimensions/text and missing parser support must not be mislabeled as complete inability to encode.
7. Taper start/end offsets use feet by field-reference documentation even when station units are meters. Preserve this established contract in reproductions. Evidence: tcp-field-reference.md:140; rules/full_evaluable.py:50; tests/test_full_evaluable.py:53.
8. observations are point snapshot measurements without verified approach/lane/design-basis provenance, and predictions are model output. Neither automatically proves work-period operation, design speed, sight distance, inventory completeness or approval.

## Family vocabulary

W1 uses descriptive slugs; the parent synthesis can normalize these to its full-document families without losing required facts. In particular retain TTC extent and mileage association, legal/local-only closure scope, parking restriction geometry, audible equipment, missing one-lane taper kind and verified operation light condition, even if they are absent from a broad family list. `optional_direction`, `sign_text`, `warning_policy`, `speed_policy`, `geometric_validity` and `acceptance_policy` can identify input/code/policy blockers and are not always new schema requirements.

## Candidate discriminating probes

The parent owns execution and final evidence. Useful cases are: identical represented lane counts but differing unrepresentable directions/adjacency; identical device-line/taper overlap but differing real membership; two closed lanes/two boards with different lane assignments; a size-fixed regulatory sign versus road-tier-dependent warning sign; same station model with two distinct pedestrian/curb contexts; explicit facing/controls populated versus omitted; shoulder board versus unknown roadside/two-way case; actual stopping sight versus equal flagger/work distance; same timestamp but different planned night coverage; and zero-W/lane-width fallback across registries. Schema-rejected additions must be reported as representation probes rather than verifier runs on valid v1 documents.
