# CloudTCP IF v2.0.0 devices and road users

Implementation status: active data-contract, standalone validation and producer work is delivered. See [implemented interfaces and limits](implementation.md) and [release-gate evidence](release-checklist.md). Verifier behavior remains deferred; source-policy and engineering dependencies in this chapter remain unresolved.

Device representations and supplied-data consistency checks remain active. Regulatory comparisons, evidence-authority judgments and rule outcomes are deferred verifier work. A structurally valid device specification does not imply compliance.

Device facts extend the common entity envelope and use core quantities, geometry and assertions. Unknown specifications are omitted. A known noncompliant dimension is valid factual data; it must produce a rule finding rather than be rejected by a schema containing a regulatory minimum.

## Shared equipment contract

| Kind/field | Type | Required | Meaning |
|---|---|---|---|
| `device.device_type` | sign/cone/drum/vertical_panel/tubular_marker/barrier/barricade/arrow_board/message_sign/afad/signal/audible_device/warning_light | yes | Variant discriminator; barrier and barricade are distinct |
| `device.location` | location | no | Planar or station location |
| `device.footprint` | polygon or ranged footprint | no | Physical occupied extent, not only the center point |
| `device.state` | deployed/stored/inactive/removed | no | Equipment state within declared phase |
| `device.approach_refs` | refs→approach | no | Approaches served, not inferred from proximity |
| `device.path_refs`, `lane_refs` | refs→path/lane respectively | no | Explicit served paths/lanes |
| `device.closure_refs` | refs→closure | no | Closures served |
| `device.zone_ref`, `taper_ref` | ref→zone/taper respectively | no | Selected placement relationships |
| `device.vehicle_ref` | ref→vehicle | no | Equipment mounted on a work/shadow vehicle |
| `device.specification` | subtype object | no | Fields allowed only for the declared device type |
| `device.mount` | mount object | no | Shared elevation/support specification |

Common references are typed. A reference can be absent in a valid partial device, but a consumer cannot select lane-specific applicability without it. Shared links must agree: if both a taper and a run declare reciprocal membership, they must reference each other consistently. A common enclosing zone does not establish a missing link.

## Mount and physical dimensions

| Mount field | Type | Meaning |
|---|---|---|
| `mount_type` | ground/portable/overhead/vehicle/barricade | Physical support category |
| `bottom_height`, `top_height` | quantities length | Height above the stated datum, not elevation above an unknown surface |
| `reference_surface_ref` | ref→boundary/facility | Pavement, curb or sidewalk datum |
| `reference_description` | string | Additional datum description; cannot replace a needed measurable reference |
| `support_type` | string | Source-specific hardware designation |
| `support_count` | positive integer | Actual supports |
| `breakaway` | boolean | Known physical characteristic with evidence |
| `support_footprint` | footprint | Used for pedestrian/vehicle clearance |
| `supporting_device_ref` | ref→device | Mounting on barricade or other equipment |

Dimension fields use quantities; dimension groups use `{width,height}` with optional `depth`/`diameter`, each a length quantity. Required axes depend on the measured shape. `shape` is rectangle/diamond/circle/other. Deriving area requires the appropriate shape and dimensions; a diamond's bounding dimensions must not be interpreted as side lengths. Source physical specifications remain evidence references rather than unsupported “certified” booleans.

## Subtype specifications

Each row defines the optional fields of `device.specification` for that variant. These fields are not additional variant discriminators.

| Device type | Specification fields and types | Rule-relevant semantics |
|---|---|---|
| `sign` | `mutcd_code`: string; `legend`: string; `dimensions`: dimension group; `shape`: shape; `face_heading`: quantity deg; `assembly_parent_ref`: ref→device(sign); `assembly_role`: primary/plaque/secondary; `symbol_orientation`: left/right/both; `ttc_extent_ref`: ref→ttc_extent | Code/legend remain distinct. Approach membership controls applicability; facing heading describes orientation. Sign-parent relationships are acyclic. No unsupported assumption that every sign code has one fixed layout/size. |
| `cone` | `height`, `base_width`: quantities length; `color`: string; `reflective_bands`: band array; `lighting_ref`: ref→device(warning_light) | Bands carry width, bottom_height, color and reflective boolean. Lack of a band list does not prove no bands. |
| `drum` | `height`, `diameter`: quantities length; `material`: string; `bands`: band array; `ballast`: string | Flexible/rigid material and band geometry remain source facts. |
| `vertical_panel` | `dimensions`: dimension group; `stripes`: stripe object; `color`: string | Stripe object: optional width, orientation left/right, colors string array and reflective boolean. |
| `tubular_marker` | `height`, `diameter`: quantities length; `color`: string; `bands`: band array | Separate physical marker subtype, not a cone with guessed dimensions. |
| `barrier` | `barrier_type`: temporary/movable/permanent; `height`: quantity length; `crashworthiness_evidence_ref`: ref→evidence; `protected_entity_refs`: refs→entity; `delineator_refs`: refs→device; `deflection_clearance`: quantity length | Crashworthiness evidence requires applicable source/context; line category alone is insufficient. |
| `barricade` | `barricade_type`: I/II/III; `rail_count`: positive integer; `rail_dimensions`: dimension-group array; `rail_area`: quantity area; `covered_area`: quantity area; `stripes`: stripe object; `support_count`: positive integer | Quantities additionally allow area units `m2`, `ft2`, `in2` for area fields. Covered area and mounted-sign area support separate source comparisons. |
| `arrow_board` | `board_class`: string; `mode`: caution/arrow/chevron/double_arrow; `arrow_direction`: left/right/both; `sequence`: flashing/sequential; `dimensions`: dimension group; `display_height`: quantity length; `legibility_distance`: quantity length; `dimming`: boolean; `active`: boolean | Separate mode from sequence and indicated direction. Caution has no arrow_direction. Lane-shift/closure scope comes from referenced paths/closures, not mode alone. |
| `message_sign` | `messages`: ordered string array; `active`: boolean; `dimensions`: dimension group; `lateral_overhang`: quantity length; `legibility_distance`: quantity length; `protective_device_refs`: refs→device | Stored/deployed state is independent of whether a message is active. |
| `afad` | `afad_type`: stop_slow/red_yellow_lens; `display_dimensions`: dimension group; `gate_arm`: boolean; `gate_clearance`: quantity length; `detection`: boolean; `operator_actor_refs`: refs→actor; `warning_light_refs`: refs→device | Staff assignments and stopping geometry are represented through control entities. An AFAD does not imply an attended operator. |
| `signal` | `signal_role`: vehicular/pedestrian; `state`: active/covered/deactivated; `stop_line_ref`: ref→marking; `head_height`: quantity length | Temporal signal timing can be sourced through a control schedule; no timing plan is guessed from a head's presence. |
| `audible_device` | `communication_mode`: audible/tactile/both; `active`: boolean; `message`: string; `crossing_ref`: ref→crossing; `assessment_decision_ref`: ref→decision | An audible-device object does not by itself establish accessible communication adequacy. |
| `warning_light` | `light_type`: string; `color`: string; `active`: boolean; `flash_rate`: quantity frequency; `visibility_distance`: quantity length; `mount_height`: quantity length | Frequency units `Hz` and `flashes/min` are allowed for this dimension. Type nomenclature refers to the selected source edition. |

Band arrays contain objects with optional `width`, `bottom_height` length quantities, `color` string and `reflective` boolean. A stripe object uses the fields defined in the panel row. Area and frequency extend the core quantity vocabulary as dimension-specific units; they cannot appear in length/speed fields.

## Device runs and actual spacing

| Field on `device_run` | Type | Required | Meaning |
|---|---|---|---|
| `device_type` | cone/drum/vertical_panel/tubular_marker/barrier/barricade | yes | Homogeneous run type |
| `segment_role` | taper/tangent/conflict/other | no | Explicit role, not station-overlap inference |
| `taper_ref`, `closure_ref`, `zone_ref` | refs→taper/closure/zone respectively | no | Rule applicability links |
| `path_refs`, `lane_refs` | refs→path/lane | no | Paths/lanes served |
| `geometry` | line or pair of station locations | no | A station pair uses `{start_location,end_location}` in one frame |
| `spacing` | quantity length | no | Uniform declared or measured spacing; acquisition method determines which |
| `individual_device_refs` | ordered refs→device | no | Devices in travel order if individually inventoried |
| `gap_measurements` | array of `{from_device_ref,to_device_ref,gap}` | no | Each gap is a length quantity; references target devices |
| `specification` | corresponding physical subtype fields | no | Shared specification for run members |
| `uniformity` | uniform/variable/unknown | no | Whether a single spacing represents every member gap |

A design spacing is not proof of as-built spacing. A uniformity claim needs evidence scoped to the run. If gaps vary, evaluators use complete measured gaps or a supported maximum-gap observation; they do not interpret an average as the maximum. Taper membership plus a role selects applicable source provisions, but authorized approximate-spacing policy is still a separate dependency.

## Actors, vehicles and controls

| Kind | Fields and types | Meaning |
|---|---|---|
| `actor` | required `role`: flagger/law_enforcement/worker/operator/other; `location`: location; `control_refs`: refs→control; `equipment_refs`: refs→device; `visibility_distance`: quantity length; `escape_path_ref`: ref→path; `communications`: string array | People are explicit inventory. A role is not proof of training, attendance or legal authority; attach source evidence or decisions when a provision needs them. |
| `vehicle` | required `vehicle_role`: work/shadow/transfer/pilot/other; `location`: location; `footprint`: footprint; `lane_refs`: refs→lane; `mounted_device_refs`: refs→device; `lights`: array of `{type,active}`; `attenuator_evidence_ref`: ref→evidence | Vehicle activity and lights are phase scoped. Attenuator approval cannot be inferred from the vehicle role. |
| `control` | required `control_type`: flagger/afad/signal/pilot/yield/stop/alternating; `controlled_path_refs`: refs→path; `actor_refs`: refs→actor; `device_refs`: refs→device; `stopping_locations`: location array; `stop_line_refs`: refs→marking; `communication_method`: string; `mutual_visibility`: boolean; `schedule_evidence_ref`: ref→evidence; `attendance`: attended/unattended | Alternating use identifies the shared path and controlled approaches explicitly. Required staffing is determined by source clauses, not by a universal minimum in the schema. |

Record staffing intervals as phase-scoped assertions or separate actor/control assignments in separate phases. Equipment state, communications and observation time must correspond to the control operation being evaluated. Devices that serve more than one closed lane require explicit lane relationships and source-specific permission; their count alone proves nothing.

## Inventory and assembly checks

- A sign assembly parent must be a sign. Its support may reference another device such as a barricade.
- A caution-mode board with arrow_direction is inconsistent data and fails semantic validation; an arrow-mode board with unknown direction can remain structurally valid but is not ready for directional checks.
- Geometry, datum and boundary relationships must be available before evaluating mounting/near-face clearances.
- A run's subtype specification must agree with its declared device_type.
- Closed-world assumptions require the completeness records in [operations-evidence.md](operations-evidence.md). An empty equipment list is not confirmed absence.
