# Independent full-document schema audit

Pinned verifier commit: `ef5e47459aea9559ae8fad7f0087f376308fe09e`. Input schema: `1.0.0`.

Every one of **381 headings and 384 clauses** in `TCP Rules Document.md` was reconciled to the catalog by complete substantive text, heading and citation. The checked-in extraction is the source boundary; external manuals were not re-audited.

Source accounting is not evaluability: informational: 43, input_blocked: 270, review_required: 24, source_blocked: 32, partial: 13, automated: 2. These are catalog dispositions, retained for comparison.

The companion JSON records a clause-level audit, schema pointers, precise absence statements, existing encodable facts, proposed minimum extensions, residual blockers and confidence. Family membership is overlapping; source duplicates share canonical checks. All schema pointers were checked to exist.

## Facts already representable

- Required posted speed, site units, taper station/offset endpoints and device-line spacing support existing numeric subcases. Missing branch/interpolation/tolerance policy is not a schema defect.
- Optional sign facing and zone references can be absent from valid documents. They are missing input, while persistent approach identity and device-to-lane/taper references are missing schema semantics.
- Upstream and downstream buffer station intervals are expressible. Lateral-buffer width/footprint, buffer occupancy, grade and flow relationships are not.
- `observations` can express point volume/speed/queue readings; it lacks vehicle mix, approach/lane associations and design-assessment provenance. Predictions remain model output.

## Schema extensions with broad reuse

| Family | Candidate related canonical checks in full-document subset | Missing capability |
|---|---:|---|
| `application_layout_identity` | 204 | Numbered typical application/figure/Standard Plan and specific variant/phase selection |
| `device_taper_lane_relationships` | 144 | Device-line membership in a taper/tangent/closure and intended traffic-path geometry |
| `lane_identity_and_flow` | 79 | Directional lane IDs, original/receiving/closed lanes and alternating-flow arrangements |
| `approaches_and_sign_associations` | 75 | Approach identity, travel orientation, restriction references and sign/closure associations |
| `approval_and_review` | 65 | Chosen exception/deviation, responsible authority, approval and documented engineering assessment |
| `shoulder_and_road_edges` | 62 | Paved shoulder dimensions, pavement/traveled-way/curb/median edges, occupation, overhang and structural suitability |
| `buffer_geometry` | 52 | Lateral buffer footprint/width, occupancy and geometric role relative to flows, work and control points |
| `operation_phases` | 46 | Duration, stationary/mobile status, daylight/night operation and closure setup/removal sequence |
| `road_classification` | 42 | Roadway functional/environment classification, divided/access-controlled status, and State-highway ownership |
| `traffic_and_assessment` | 39 | Approach/lane traffic demands, capacity, heavy-vehicle mix, queues and operational feasibility assessment |
| `lane_width_and_encroachment` | 35 | Usable lane width measured to device near-face/pavement edges and work encroachment |
| `ramp_geometry` | 32 | Entrance/exit/temporary ramp identity, access and merging/acceleration/deceleration geometry |
| `work_vehicles_and_occupancy` | 30 | Workers, equipment/material/vehicle footprints, active lighting and work/shadow/transfer vehicle roles |
| `sight_and_stopping` | 26 | Available directional sight distance, intended stop points, sight lines and visibility constraints |
| `alignment` | 25 | Horizontal/vertical alignment, curve/crest endpoints, grade and design-speed criteria |
| `speed_basis_and_provenance` | 25 | Selected calculation speed and provenance: posted, pre-work off-peak 85th-percentile, anticipated operating or bicycle speed |
| `barrier_properties` | 24 | Barrier type, traffic role, crashworthiness, shielding and delineation |
| `pavement_markings` | 24 | Marking identity, geometry, temporary/conflicting/removed status and relation to lane use |
| `intersection_turns` | 19 | Crossroad/driveway/intersection topology, receiving approaches and turning traffic movements |
| `signal_control` | 16 | Signals/stop/yield control, stop lines, control station association and equipment height |
| `flagger_operations` | 16 | Flagger staffing/equipment, duty, escape/recovery areas, visibility and approach control associations |
| `bicycle_geometry_speed` | 14 | Bikeway/path geometry, bicycle-specific speed and sharing/diversion arrangements |
| `device_specifications` | 13 | Individual device dimensions/material/retroreflectivity/light specifications and device groups |
| `pedestrian_accessibility` | 12 | Pedestrian/crosswalk topology, clear width, ramps/landings, slopes, surface and passing spaces |
| `arrow_board_equipment` | 11 | Arrow-board type, stored/deployed status, mounting and lane/taper association |
| `message_signs` | 10 | PCMS identity, dimensions/overhang, active/stored status, facing and protection |
| `sign_design_and_attachments` | 6 | Sign symbol orientation, plaque-parent attachment, sign-size tier and dimensional geometry |
| `mounts_vertical_clearance` | 4 | Mount/support geometry, vertical clearance and device elevation |
| `rail_crossing_queues` | 4 | Track crossing extent, actual queue footprint and crossing-specific controller |
| `barricade_types` | 4 | Barricade type and rail/group geometry |
| `afad_equipment` | 1 | AFAD identity/equipment, traffic stopping point and attendance/staffing |
| `coordination_records` | 1 | Pre-closure coordination with cross-street and emergency officials |

Counts are static audit mappings, not measured improvements after a schema change. The JSON retains medium confidence for automatically assigned families. Review a clause before deriving an exact field contract.

## Metadata corrections and overlooked blockers

- **META-11 — T-001, B-004:** The catalog input_blocked labels overstate schema needs for these permissive placements. Taper.zone_id plus transition/termination zone types encode T-001; upstream_buffer/work intervals encode B-004. Neither OPTION requires the optional placement to exist. No schema extension is required for the permission itself. Resolve placeholder/reporting interpretation without inventing a mandatory defect.
- **META-01 — Z-038:** Catalog assigns mounting/support geometry and vertical clearances to a source about lateral clearance via two interior-lane closures. The source requires lane identity, non-access-controlled/undivided classification and traffic capacity; no sign mounting height is stated. Metadata-family imprecision; retain schema blocker but correct the proposed facts.
- **META-02 — Z-041-B:** Catalog assigns mounting/support geometry to an intersection advance-warning trigger above 40 mph; source instead identifies posted/pre-work 85th-percentile/anticipated speeds. Add alternative-speed provenance; do not prioritize mounting height for this clause.
- **META-03 — Z-044:** Catalog assigns work/shadow-vehicle equipment to a significant-turning-traffic mandatory-turn-lane option. Source requires movement counts, intersection/lane identities and permission context. Do not equate generic vehicle mention with work-vehicle equipment.
- **META-04 — Z-045:** Catalog names roadway classification only. Source also requires an expected-queue assessment during design. Prediction fields store model output but carry no approved assessment provenance/roadway association. Roadway class alone will not make the complete clause evaluable.
- **META-05 — T-100, T-101, CA-035, CA-026:** Catalog assigns work/shadow-vehicle equipment to motor-vehicle-speed instructions. These concern calculation speed modality and provenance, not the presence/equipment of work vehicles. Use speed basis/mode and selected layout identity as schema requirements; preserve separate source-classification uncertainty.
- **META-06 — T-009, T-010, T-011, T-012, T-015, T-016, B-012, CA-007:** Catalog partial metadata emphasizes formula branches/rounding but does not fully name the unencodable pre-work off-peak 85th-percentile or anticipated-operating-speed basis. Optional work_zone_speed_mph and unqualified point speed observations do not encode those facts. Supported posted-speed subcases do not prove full source-speed coverage.
- **META-07 — B-012:** Catalog acknowledges upstream_buffer-only implementation. The source permits the optional table for longitudinal buffers generally; downstream_buffer intervals are already expressible. Downstream table selection is an implementation limitation, distinct from missing lateral geometry or speed provenance.
- **META-08 — T-011, T-012:** Shared handler limitations mention absent one-lane/two-way taper types for individual source clauses about shifting and shoulder tapers. That absent subtype is real but is not independently required by these two specific source clauses. Avoid spreading shared-handler limitations onto unrelated source clauses.
- **META-09 — CA-007:c02:** Automated downstream-min/max clause inherits reviewer caveats about 40<S<45 and offset-table rounding. Its 50-to-100-foot numeric downstream range does not depend on speed or offset. Do not count inherited caveats as active schema/source blockers for this automated clause.
- **META-10 — T-019, T-032:** Catalog source_blocked metadata groups the clauses with missing external Green Book/Roadside Design Guide criteria. T-019 itself supplies site-optimization language, and T-032 gives a design-speed comparison with an unusual-site exception; the clause text does not itself cite those missing external publications. External-design dependence may be contextual, but the direct blockers are geometry/design-speed inputs and site engineering judgment; label catalog-derived dependency rather than asserting direct source citation.

## Constraints on interpreting a future schema

- Preserve source strength: an OPTION does not become a requirement; SUPPORT/definitions do not become independent pass/fail checks.
- Adding a decision/evidence object records engineering authority and rationale; it does not automate judgment.
- Model numbered TA/figure/Standard Plan selection and jurisdictional variants explicitly. A coarse closure category cannot select a figure, optional devices, or phase-specific dimensions.
- Distinguish actual traffic/queue evidence, approved design assessments and predicted values. A scalar queue length cannot show that vehicles occupy railroad tracks.
- Define source-specific calculation speed with mode and provenance. Posted speed, anticipated bicycle speed and pre-work percentile speed are different facts.
- Missing publications/errata, unresolved approximate tolerances and unprovided interpolation/rounding policies remain residual blockers.
- No verifier or schema change was made by this audit.
