# Focused schema and evaluator probe findings

The unchanged CloudTCP 1.0.0 contract admits documents that cannot distinguish several materially different traffic-control arrangements. The decisive missing capabilities are explicit path/approach and lane associations, exception evidence, road classification, sight-distance geometry, and device specifications. Some incomplete results instead arise from omitted existing fields, unsupported parsing, published-table policy, or degenerate input geometry; extending the schema alone does not resolve those cases.

## Execution evidence

The reproducible harness is [run_probes.py](../evidence/probes/run_probes.py). Run it with the verifier environment:

```sh
/private/tmp/cloudtcp-schema-audit-ef5e474/venv/bin/python \
  reports/schema-gap-audit/evidence/probes/run_probes.py \
  --repo /private/tmp/cloudtcp-schema-audit-ef5e474/cloudtcp-python-verifier
```

The run validated **53 synthetic documents** against the unchanged Draft 2020-12 schema and the verifier's semantic ingestion checks, then executed each against the full and W1 registries: **106 API executions**, producing **92 focused rule-result records**. Every expected status/completeness assertion passed. All **10 full-registry partial evaluator keys** were exercised, as were W1-only `TAPER-03`, `FLAG-02`, `SIGN-20`, `SIGN-31`, and `ARROW-02`. This is behavioral family coverage, not exhaustive execution of every source clause.

Fourteen separately labelled **expected-invalid extension probes** were rejected by the schema and verifier with input exit code `2` and zero rule executions. These payloads demonstrate where additional properties, element discriminators, or enums prohibit expressing the tested fact directly. They are not included among the 53 schema-valid examples.

[summary.json](../evidence/probes/summary.json) records counts, schema hash, evaluator coverage, and assertion failures. [focused-results.json](../evidence/probes/focused-results.json) contains every selected registry result. Each input has a corresponding per-probe result file under `evidence/probes/inputs/` and `evidence/probes/results/`; results retain focused report output, raw evaluator output, overall report exit codes, and all-registry status counts.

Schema SHA-256: `2109f24ef1659389dbfb72da650efe03767cdd9635a145afab86b2dfe000eba6`.

## Missing capabilities with observable consequences

| Capability | Schema-valid probe and result | Minimum missing information | Code evidence |
|---|---|---|---|
| Device-line association with a taper or tangent path | `federal_spacing_60`: at 45 mph, a line with 60-ft spacing and longitudinal taper overlap remains `not_evaluable` in both registries. 20 ft passes and 100 ft fails. | Persistent device-line-to-taper/path association; station overlap alone is not a relation. | `rules/w1_evaluable.py:228–262` |
| California spacing applicability | `ca_spacing_20`: passes; `ca_spacing_20_01` and `ca_spacing_100`: incomplete; `ca_spacing_100_01`: fails at 55 mph. | Taper/tangent association, conflict-spacing applicability, and whether the separate 20-ft taper cap applies. | `rules/full_evaluable.py:161–190` |
| Multiple traffic approaches | `sign_side_multiple_approaches`: complete zone geometry and explicit sign facing still leave placement incomplete in both registries. `BOTH` also remains incomplete. | Explicit approach inventories and sign/zone/path associations, with direction per approach. | `rules/geometry.py:67–84`; `rules/w1_evaluable.py:298–317` |
| Sign-placement exceptions | `sign_side_exception_unmodeled`: explicit left placement and facing remain incomplete. | Applicable exception and its supporting engineering/agency evidence. | `rules/w1_evaluable.py:314–316` |
| Sight-distance geometry | `flagger_sight_distance_unmodeled`: a known flagger position does not enable the W1 sight-distance check. | Available approach sight distance and intended stopping point, rather than flagger-to-zone separation. | `rules/w1_evaluable.py:288–295`; limitations at `:42–45` |
| Road classification and lane identity | `sign_size_road_tier_unmodeled`, `sign_through_lane_applicability_unmodeled`, and `arrow_boards_no_lane_identity` all remain incomplete in W1 despite encoded sign size, sign code, or board counts. | Applicable road tier, through-lane identity, closure classification, and board-to-lane assignments. | `rules/w1_evaluable.py:320–328`, `:383–390`, `:427–435` |
| Traffic pattern and lane-shift intent | `arrow_two_lanes_no_traffic_pattern`: two total lanes plus a declared closure do not resolve the arrow-board rule. The shoulder-work caution-mode case passes and an arrow-mode shoulder case fails. | Explicit one-lane/two-way operation and lane-shift intent. | `rules/w1_evaluable.py:393–424` |

[rejected-extensions.json](../evidence/probes/rejected-extensions.json) contains validation evidence for attempted road classification, operation duration, one-lane/two-way operation, approach inventory, device-to-taper relation, one-lane/two-way taper type, available sight distance, board-to-lane relation, sign mounting height, placement approval, channelizer dimensions, barricade type, AFAD type, and accessible-route width.

The attempted property names are illustrative proposals, not claims that a particular future wire format has been approved. Existing `description` and `note` strings can carry human-readable annotations but do not provide typed, interoperable facts or relationships for these checks. CAD `source` references provide traceability rather than those relationships.

## Distinct real-world arrangements sharing a payload

[counterexamples.json](../evidence/probes/counterexamples.json) records five explicitly hypothetical pairs, each linked to a single validated payload by SHA-256:

1. A 60-ft-spaced line serves a 45-mph merging taper versus a separate tangent path at overlapping stations. The applicable S versus 2S requirement differs, while the representable document is identical.
2. A left-side sign has an applicable authorized exception versus the same placement without that exception.
3. A flagger approach has adequate sight distance versus an obstruction or crest restricting sight distance below the requirement, with identical modeled flagger coordinates.
4. Two arrow boards serve two distinct closed lanes versus both serving only one closed lane, with identical board and lane counts.
5. A sign serves one roadway tier versus another with a different applicable size row, with identical sign dimensions and station geometry.

These are information-loss witnesses. They do not assert actual site compliance or invent missing regulatory thresholds. Pairs involving agency exceptions or applicability can retain engineering/source blockers even after the missing fact is modeled.

## Incomplete results that are not absent schema capability

- **Existing optional fields:** removing sign `face_direction` turns `SIGN-11` and `SIGN-21` incomplete; removing flagger `controls` also turns `SIGN-21` incomplete. Supplying these fields makes the supported scenarios pass. These are instance completeness gaps, supported by schema pointers `/properties/elements/items/oneOf/0/properties/face_direction` and `/properties/elements/items/oneOf/4/properties/controls`.
- **Speed-policy gaps:** `merge_formula_speed_gap` and `shift_formula_speed_gap` use schema-valid 42 mph and remain incomplete because neither formula branch applies between 40 and 45 mph. `buffer_unlisted_speed`, `ca_taper_no_exact_speed_row`, and `ca_spacing_no_exact_speed_row` expose exact-row table restrictions. Speed is already encoded; a schema addition cannot author an interpolation policy. See `rules/geometry.py:144–155`, `rules/w1_evaluable.py:275–278`, and `rules/full_evaluable.py:148–150`, `:172–174`.
- **Approximate spacing:** `downstream_approximate_spacing` remains incomplete despite a downstream taper and 20-ft device spacing. W1 requires both a reliable association and an authorized acceptance tolerance for approximate wording. Adding a numeric field cannot supply authority for a tolerance. See `rules/w1_evaluable.py:213–224`.
- **Parser scope:** `warning_sequence_unknown_code` remains incomplete because the evaluator supports a defined code set, although the schema already accepts the code. `mileage_words` remains incomplete for `ROAD WORK NEXT TWO MILES`, while numeric `2 MILES` passes and `2.5 MILES` fails. An absent legend is a missing-input case; unsupported wording is a parser limitation. See `rules/full_evaluable.py:208–229`, `:261–285`.
- **Input quality and validation constraints:** zero-length and overlapping warning zones pass the schema and semantic ingestion but make `SIGN-11` incomplete. The geometry is expressible; these cases concern approach prerequisites and contract validation, unlike missing approach identity. See `sign_side_warning_zone_zero_length`, `sign_side_warning_zone_overlap`, and `rules/geometry.py:75–83`.

## Reporting and compatibility behavior

`federal_spacing_failure_plus_unknown` and `flagger_warning_failure_plus_unknown` return **`fail` with `complete=False`** in both registries. `known_taper_failure_plus_unknown_taper` does so in the full registry. An audit restricted to `not_evaluable` statuses would miss these unresolved subjects.

The zero-offset-width taper with `lane_width_ft=12` passes historical W1 but is incomplete in the full registry. W1 substitutes lane width for W; the full registry removes that fallback when offset width is zero. Both fields already exist, making this a deliberate registry/interpretation difference, not proof of a missing field. See `rules/w1_evaluable.py:113–127` and `rules/full_evaluable.py:80–101`.

Equivalent 540-ft and 164.592-m merge-taper station geometry produces the same passing result in both registries. The probe converts longitudinal stations and preserves taper offsets and fields explicitly documented in feet. Unit conversion is therefore supported for this case; no general claim about all future geometry models follows.

A short optional buffer still returns `pass`; its raw evaluator score is approximately `0.27778`, while the public report projects the passing result to binary score `1`. Raw graded scores and projected scores must not be read as schema coverage or a compliance percentage. See `buffer_short_optional_buffer`, `rules/w1_evaluable.py:265–285`, and `reporting.py:94–126`.
