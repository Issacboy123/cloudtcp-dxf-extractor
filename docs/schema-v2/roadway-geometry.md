# CloudTCP IF v2.0.0 roadway and geometry contract

Implementation status: active data-contract, standalone validation and producer work is delivered. See [implemented interfaces and limits](implementation.md) and [release-gate evidence](release-checklist.md). Verifier behavior remains deferred; source-policy and engineering dependencies in this chapter remain unresolved.

This chapter remains active for schema design, independent data validation and producer adoption. Rule applicability, readiness and source comparisons mentioned here are future use cases; implementing those verifier behaviors is deferred.

All records below extend the entity envelope in [core-contract.md](core-contract.md). Fields are optional unless marked required. `ref` and `refs` mean a string reference and a unique reference array, constrained to the target kinds stated. Quantities and geometry use the core primitives. Optional geometry does not imply optional evidence when a rule needs a geometric fact.

## Network and applicability

| Kind | Proposed fields and types | Relationships and semantics |
|---|---|---|
| `road` | `road_name`: string; `route_number`: string; `jurisdiction`: object; `classification`: object; `alignment_refs`: refs→alignment; `posted_speed_ref`, `work_zone_speed_ref`: refs→observation | Jurisdiction fields: `country`, `state`, `agency`, `ownership` strings. Classification fields: `functional_class` string; `environment` urban/rural; `access_control` full/partial/none; `divided` boolean; `facility_class` conventional/freeway/expressway/other. Unknown fields are omitted, not inferred. |
| `alignment` | required `frame_ref`: station frame; `road_ref`: ref→road; `plan_geometry`: line; `profile`: array of `{station,elevation}`; `grade_segments`: array of `{range,grade}` | Profile stations strictly increase. Elevation uses the frame's units and declared vertical datum. A plan line alone does not establish station/curve correspondence. |
| `approach` | required `road_ref`: ref→road; required `frame_ref`: station frame; required `travel_sign`: integer ±1; `travel_heading`: quantity deg; `path_refs`: refs→path; `junction_ref`: ref→junction; `calculation_speed_ref`: ref→observation | Travel sign relates encounter order to increasing station. Heading is measured clockwise from declared north and is optional. Separate approaches for opposing flows, even on the same road. |
| `lane` | required `road_ref`: ref→road; `approach_ref`: ref→approach; `role`: through/turn/shoulder/auxiliary/bicycle/shared; `traffic_mode`: motor/bicycle/mixed; `travel_sign`: ±1; `boundary_refs`: refs→boundary; `clear_width`: quantity length; `width_measurement_refs`: refs→observation | The same stable lane can have different phase-scoped operational paths/closures. A lane object is physical inventory; availability is phase-specific. Width needs measurement endpoints/method before clearance checks. |
| `path` | required `approach_ref`: ref→approach; `lane_refs`: refs→lane; `geometry`: line; `station_range`: range; `use`: normal/temporary/receiving/detour/escape; `traffic_modes`: unique motor/bicycle/pedestrian array; `successor_refs`: refs→path | Lane references are ordered in travel order if a path traverses more than one lane. Geometry must agree with the approach's frame or have an explicit transform outside this release. Shared alternating use is represented through controls and phase/timing facts. |
| `junction` | `junction_type`: intersection/driveway/roundabout; `road_refs`: refs→road; `approach_refs`: refs→approach; `footprint`: polygon; `movements`: array of `{from_path_ref,to_path_ref,movement}` | Movement enum: through/left/right/u_turn. References target path. A turn exists only if explicitly supplied; omitted movements do not prove prohibition. |
| `ramp` | required `road_ref`: ref→road; `ramp_type`: entrance/exit/temporary; `from_path_ref`, `to_path_ref`: refs→path; `acceleration_range`, `deceleration_range`: ranges; `available_length`: quantity length | Source/destination distinguish a ramp from an arbitrary closure category. Length evidence identifies reference endpoints. |
| `boundary` | required `road_ref`: ref→road; required `boundary_type`: pavement_edge/traveled_way_edge/curb_face/median_edge/shoulder_edge/lane_edge; `geometry`: line; `station_offsets`: array of station locations; `surface`: paved/unpaved; `load_suitability_decision_ref`: ref→decision | Geometry identifies which edge is measured. Shoulder strength is a documented assessment, not a consequence of surface category. |
| `application` | required `jurisdiction`: object with required `country` and optional state/agency; required `source_evidence_ref`: ref→evidence; required `layout_id`: string; `edition`: string; `variant`: string; `closure_refs`: refs→closure; `approach_refs`: refs→approach | Layout IDs preserve source nomenclature, e.g. TA identifiers and agency Standard Plan identifiers. Selection is a fact requiring evidence; it does not assert that the layout is appropriate. |

No road-class enum substitutes for agency-defined speed tiers. Store selected source-specific tiers in a decision's `parameters` with a source locator. A future controlled vocabulary can formalize them once the source definitions are resolved. This prevents an invented “urban high speed” boundary.

### Alignment correspondence

An alignment may additionally carry `station_mapping`: an array of `{station, point_index, distance_along_segment}` records tying station to its `plan_geometry` vertices/segments. `point_index` is a zero-based segment-start index; `distance_along_segment` is a nonnegative number in the planar frame's units, bounded by that segment's length. Mapping stations strictly increase. `station_equations` are not supported in 2.0.0; use distinct station frames and explicit measurements across discontinuities. Consumers must not derive station distance from line length without a supplied correspondence.

Curved geometry is represented as a surveyed polyline with stated acquisition/approximation evidence. Rule checks requiring true curve parameters instead use an observation with measured radius/design criterion. This hybrid release does not invent a CAD curve kernel or claim a coarse polyline meets design tolerances.

## Closures, zones and construction geometry

| Kind | Proposed fields and types | Relationships and semantics |
|---|---|---|
| `closure` | required `closure_type`: lane/shoulder/road/intersection/ramp/median_crossover/other; `lane_refs`: refs→lane; `path_refs`: refs→path; `approach_refs`: refs→approach; `extent`: footprint; `access_policy`: none/local_only/controlled; `receiving_path_refs`: refs→path | Scope and access are independent of device counts. Closed-lane counts are derived only from complete scoped inventory. |
| `zone` | required `zone_type`: advance_warning/transition/upstream_buffer/work/downstream_buffer/termination; `approach_ref`: ref→approach; `path_refs`: refs→path; `extent`: footprint; `closure_refs`: refs→closure | A station interval is not a lane/path membership assertion. Separate zones can occupy the same stations on different approaches or phases. |
| `taper` | required `taper_type`: merge/shift/shoulder/downstream/one_lane_two_way; `approach_ref`: ref→approach; `from_path_refs`, `to_path_refs`: refs→path; `start_location`, `end_location`: locations; `length`, `offset_width`: quantities length; `zone_ref`: ref→zone; `closure_ref`: ref→closure; `device_run_refs`: refs→device_run; `calculation_speed_ref`: ref→observation | Length and width may be measured or derived; retain provenance and endpoints. A supplied lane width is never substituted for offset width. Control is needed to establish alternating operation. |
| `buffer` | required `buffer_role`: longitudinal_upstream/longitudinal_downstream/lateral; `extent`: footprint; `width`, `length`: quantities length; `protected_path_refs`, `opposing_path_refs`: refs→path; `work_area_refs`: refs→work_area; `occupant_refs`: refs→actor/vehicle/device/work_area; `zone_ref`: ref→zone | Occupants describe known presence. An empty occupant list cannot prove no work/storage intrusion without scoped completeness. Lateral and longitudinal roles remain distinct. |
| `work_area` | required `activity`: active_work/storage/staging/idle; `extent`: footprint; `closure_ref`: ref→closure; `occupant_refs`: refs→actor/vehicle/device | Store material/equipment footprints as work areas when no detailed asset inventory exists; do not label them as empty roadway. |
| `ttc_extent` | required `definition`: first_warning_to_last_device/agency_project_limits; `path_ref`: ref→path; `start_location`, `end_location`: locations; `length`: quantity length; `boundary_device_refs`: refs→device/device_run; `mileage_sign_refs`: refs→device | Authoritative extent must identify its selected definition, phase and evidence. Neither min/max zone stations nor a model queue proves complete TTC limits. |

V2 permits explicit independent measurements because available survey data may support a length without all endpoints. If both are supplied, a derivation observation identifies which inputs and method establish the comparison value. Disagreement outside stated measurement uncertainty is disputed evidence, not silently resolved in favor of geometry or a scalar. A wrong declared derivation, such as a reported difference inconsistent with its exact inputs, is a semantic error.

Positive taper/buffer lengths are readiness prerequisites for the corresponding subject. Merely defining a zero-length station feature is not universally invalid. Any directional relation needed for a check must resolve from the approach and path, not from sorting all project zones globally.

## Pedestrian, bicycle and specialized facilities

| Kind | Proposed fields and types | Semantics |
|---|---|---|
| `facility` | required `facility_type`: sidewalk/pedestrian_route/bikeway/shared_path/curb_ramp/landing/passing_space; `path_ref`: ref→path; `geometry`: line or polygon; `clear_width`: quantity length; `running_slope`, `cross_slope`: quantities ratio; `surface`: object; `parent_facility_ref`: ref→facility; `obstruction_refs`: refs→device/vehicle/work_area; `alternate_facility_ref`: ref→facility | Surface optional booleans: `firm`, `stable`, `slip_resistant`. Known booleans need assertions. Parent/alternate links cannot self-reference; parent hierarchy is acyclic. |
| `crossing` | required `crossing_type`: crosswalk/railroad; `geometry`: line or polygon; `path_refs`: refs→path; `state`: open/closed/diverted; `control_ref`: ref→control; `rail_clearance_extent`: footprint; `audible_device_refs`: refs→device; `diversion_facility_ref`: ref→facility | Crossing closure is phase scoped. Railroad occupancy requires queue geometry or a sourced intersection/occupancy assessment; scalar queue length is insufficient. |
| `marking` | required `marking_type`: centerline/edge_line/lane_line/stop_line/yield_line/crosswalk/other; `geometry`: line or polygon; `lane_refs`: refs→lane; `state`: existing/temporary/covered/removed; `conflict_refs`: refs→marking/path | Distinguish not-yet-observed from removed. Removal sequence belongs to phase actions. |
| `restriction` | required `restriction_type`: parking/access; `extent`: footprint; `approach_ref`: ref→approach; `boundary_ref`: ref→boundary; `crossing_ref`: ref→crossing; `sign_refs`: refs→device; `state`: active/inactive | Parking restrictions identify curb, approach and extent rather than only a NO PARKING legend. |

Hybrid geometry does not waive source criteria. Surface compliance, detectable edges, accessible communication and unusual-site exceptions can require equipment facts, authoritative standards and engineering decisions as well as dimensions.

## Cross-section, sight and traffic measurements

Use observation records for measured/design quantities linked to subjects. The [operations chapter](operations-evidence.md) specifies their common shape.

| Observation metric | Subjects/context required for readiness | Result type |
|---|---|---|
| `clear_width` | Lane/facility/buffer; reference boundary/device faces; phase; method | quantity length |
| `shoulder_width` | Road/boundaries; station range; paved width distinction | quantity length |
| `grade` / `cross_slope` | Alignment/lane/facility and range; direction/reference | quantity ratio |
| `stopping_sight_distance` / `passing_sight_distance` | Approach/path, observer/target locations or intended stopping point; method and selected design criterion | quantity length |
| `curve_radius` | Alignment/range; acquisition method | quantity length |
| `design_speed` / `calculation_speed` | Mode, basis, phase and applicability; source selection evidence | quantity speed |
| `queue_occupancy` | Crossing/path and observed queue footprint | boolean plus optional footprint |

For a complete cross-section, use a set of boundary entities and width observations scoped to the same station range and phase. Per-lane width may vary by range; do not force one global width. The entity's `clear_width` is a convenience selected value with an assertion; individual observations retain the measurements and conflicts.

## Association example

The following excerpt separates physical overlap from declared membership. All referenced records must be supplied in a complete transported document; this block is not independently valid.

```json
{
  "entities": [
    {"id":"approach-n","kind":"approach","road_ref":"road-main","frame_ref":"station-main","travel_sign":1,"phase_refs":["phase-work"]},
    {"id":"taper-1","kind":"taper","taper_type":"merge","approach_ref":"approach-n","from_path_refs":["path-closed"],"to_path_refs":["path-receiving"],"device_run_refs":["run-1"],"phase_refs":["phase-work"]},
    {"id":"run-1","kind":"device_run","device_type":"cone","segment_role":"taper","taper_ref":"taper-1","path_refs":["path-receiving"],"spacing":{"value":60,"unit":"ft"},"phase_refs":["phase-work"]}
  ]
}
```

Changing `run-1` to a tangent run removes its taper reference and changes `segment_role` to `tangent`. That distinction is representable even if the two candidate runs share identical station geometry. Whether 60 ft is permitted remains a source-specific evaluation using the selected speed and applicability.
