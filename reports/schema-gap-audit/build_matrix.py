"""Validate semantic audit coverage and build clause and capability mappings."""
import csv
import json
import re
from collections import Counter
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent
PIN = "ef5e47459aea9559ae8fad7f0087f376308fe09e"
BASE = f"https://github.com/Issacboy123/cloudtcp-python-verifier/blob/{PIN}/"
ALIASES = {
    "road_class": "road_classification",
    "approach_geometry": "approaches_and_sign_associations",
    "engineering_decisions": "approval_and_review",
    "road_network": "intersection_turns",
    "work_footprint": "work_vehicles_and_occupancy",
    "sign_mount": "mounts_vertical_clearance",
    "pedestrian_geometry": "pedestrian_accessibility",
    "road_edges": "shoulder_and_road_edges",
    "duration": "operation_phases",
    "barricade_geometry": "barricade_types",
    "lane_identity": "lane_identity_and_flow",
    "layout_identity": "application_layout_identity",
    "closure_scope": "lane_identity_and_flow",
    "vehicle_equipment": "work_vehicles_and_occupancy",
    "device_association": "device_taper_lane_relationships",
    "device_kind": "device_specifications",
    "device_attributes": "device_specifications",
    "operating_light": "operation_phases",
    "signal_state": "signal_control",
    "flagger_operation": "flagger_operations",
    "sight_distance": "sight_and_stopping",
}
NON_SCHEMA = {"warning_policy", "optional_direction", "optional_permission", "sign_text",
              "speed_policy", "geometric_validity", "acceptance_policy", "external_standard"}
ADDITIONS = {
    "taper_kind": {
        "required_facts": "Explicit one-lane two-way taper identity, linked to the controlled path",
        "absence": "The taper_type enum has merge, shift, shoulder and downstream, but no one-lane two-way taper.",
        "minimal_extension": "Add an explicit one-lane two-way taper subtype with the relevant flow/path relationships; implement its source-specific checks.",
        "related_schema_pointers": ["/properties/elements/items/oneOf/1/properties/taper_type"],
    },
    "ttc_extent": {
        "required_facts": "Authoritative complete TTC-zone extent, mileage-sign scope and rounding basis",
        "absence": "Zone intervals do not declare complete project/TTC limits or associate a G20-1 inscription with those limits.",
        "minimal_extension": "Add authoritative TTC boundaries and mileage-sign/approach associations; preserve units and authorized rounding policy.",
        "related_schema_pointers": ["/properties/zones", "/properties/elements/items/oneOf/0/properties/legend"],
    },
    "parking_restrictions": {
        "required_facts": "No-parking intervals associated with a closed midblock crossing, curb and approach",
        "absence": "Signs can carry parking legends, but there is no parking-restriction extent or crossing/curb association.",
        "minimal_extension": "Add parking-restriction extents linked to crosswalk closure, curb geometry and served approaches.",
        "related_schema_pointers": ["/properties/elements/items/oneOf/0", "/properties/zones"],
    },
    "accessibility_equipment": {
        "required_facts": "Audible accessibility equipment and its crossing/closure association",
        "absence": "There is no audible-device variant or accessible communication relationship.",
        "minimal_extension": "Add audible or other required accessibility communication equipment linked to the affected crossing, closure and signs, with assessment evidence.",
        "related_schema_pointers": ["/properties/elements/items/oneOf"],
    },
    "inventory_completeness": {
        "required_facts": "Evidence that the relevant drawing/site/device inventory was examined completely",
        "absence": "elements may be empty; the contract has no scoped inventory-completeness or extraction-coverage declaration. Absence can mean no subject or missing evidence.",
        "minimal_extension": "Define a scoped completeness/evidence contract or accompanying trusted ingestion report before treating absent subjects as confirmed absent. Do not impose a universal minimum device count.",
        "related_schema_pointers": ["/properties/elements", "/properties/site/properties/source_file"],
    },
}
FOUNDATION = {"application_layout_identity", "road_classification", "approaches_and_sign_associations",
              "lane_identity_and_flow", "device_taper_lane_relationships", "operation_phases",
              "speed_basis_and_provenance", "inventory_completeness"}
GEOMETRY = {"shoulder_and_road_edges", "lane_width_and_encroachment", "buffer_geometry", "alignment",
            "sight_and_stopping", "pedestrian_accessibility", "bicycle_geometry_speed",
            "intersection_turns", "ramp_geometry", "traffic_and_assessment"}


def read(path):
    return json.loads(path.read_text())


def write(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def sequence(value):
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def key(row):
    return row.get("document", row.get("source_document")), row["source_rule_id"], row["clause_id"]


def render(value):
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return "" if value is None else value


def main():
    full = read(ROOT / "analysis/full-document-audit.json")
    w1 = read(ROOT / "analysis/w1-audit.json")
    reviews = full["clauses"] + (w1 if isinstance(w1, list) else w1["clauses"])
    by_key = {key(r): r for r in reviews}
    catalog = read(ROOT / "evidence/source-catalog.json")
    assert len(by_key) == len(reviews) == len(catalog) == 504
    assert set(by_key) == {key(c) for c in catalog}
    manifest = read(ROOT / "evidence/manifest.json")
    assert manifest["commit"] == full["commit"] == PIN
    evaluators = {"mutcd." + name for name in manifest["evaluator_keys"]}
    runtime = read(ROOT / "evidence/runtime-index.json")
    focused = read(ROOT / "evidence/probes/focused-results.json")
    definitions = {**full["gap_family_definitions"], **ADDITIONS}
    family_ids = {name: f"G{index:02d}" for index, name in enumerate(definitions, 1)}
    schema = read(ROOT.parents[1] / "tcp-intermediate-format.schema.json")

    def check_pointer(pointer):
        current = schema
        for part in pointer.removeprefix("#").split("/")[1:]:
            part = part.replace("~1", "/").replace("~0", "~")
            current = current[int(part)] if isinstance(current, list) else current[part]

    for definition in definitions.values():
        for pointer in definition["related_schema_pointers"]:
            check_pointer(pointer)

    rows = []
    root_adjustments = []
    for clause in catalog:
        review = by_key[key(clause)]
        assert review["source_text"] == clause["text"]
        assert review["classification"] == clause["classification"]
        assert review["canonical_rule_id"] == clause["canonical_rule_id"]
        categories = list(review["blocker_categories"])
        families, themes = [], []
        for name in review["gap_families"]:
            if name in NON_SCHEMA:
                themes.append(name)
            else:
                families.append(ALIASES.get(name, name))
        support = list(sequence(review["schema_support"]))
        facts = list(sequence(review["required_facts"]))
        extensions = list(sequence(review["minimal_extension"]))
        residual = list(sequence(review["residual_blockers"]))
        is_w1 = clause["source_document"] == "TCP-W1-1 Rules.md"
        if is_w1 and ((clause["source_rule_id"] == "TAPER-01") or
                      (clause["source_rule_id"] == "TAPER-02" and clause["clause_id"] in {"c01", "c02", "c03"})):
            families.append("speed_basis_and_provenance")
            categories.append("schema")
            facts.append("Qualified pre-work off-peak 85th-percentile or anticipated operating-speed evidence for permitted alternative speed bases.")
            support.append("absence: generic observations and posted/work-zone speeds do not identify the permitted pre-work percentile/anticipated calculation-speed basis.")
            extensions.append("No extension for the supported posted-speed subset; add qualified speed-basis/provenance evidence to support the permitted alternatives.")
            residual.append("Formula gaps at 40<S<45 remain source policy; posted-speed cases can already evaluate.")
            root_adjustments.append({"source_key": list(key(clause)), "reason": "Cross-document reconciliation of permitted alternative speed bases; conditional schema need, not a blocker to the supported posted-speed subset."})
        if "schema" in categories and re.search(r"one.lane.two.way taper", clause["text"], re.IGNORECASE):
            families.append("taper_kind")
        if "schema" in categories and re.search(r"audible", clause["text"], re.IGNORECASE):
            families.append("accessibility_equipment")
        if "schema" in categories and re.search(r"\bAFAD", clause["text"]):
            families.append("afad_equipment")
        if is_w1 and "schema" in categories and clause["source_rule_id"].startswith("ARROW-"):
            families.append("arrow_board_equipment")
        if is_w1 and "schema" in categories and clause["source_rule_id"] == "SIGN-30":
            families.append("sign_design_and_attachments")
        if "device_kind" in review["gap_families"] and re.search(r"barricade", clause["text"], re.IGNORECASE):
            families.append("barricade_types")
        has_evaluator = clause["canonical_rule_id"] in evaluators
        if clause["canonical_rule_id"] and not has_evaluator:
            categories.append("implementation")
            residual.append("Default registry has no rule-specific evaluator for this canonical check; adding schema fields alone will not execute it.")
        categories = sorted(set(categories))
        families = sorted(set(families)) if "schema" in categories else []
        assert all(name in definitions for name in families), families
        observations = runtime.get(clause["canonical_rule_id"], [])
        probes = [r for r in focused if r["registry"] == "full" and r["rule_id"] == clause["canonical_rule_id"]]
        source_evidence = next((e for e in review["evidence"] if e.startswith(clause["source_document"] + ":")), "")
        source_line = int(source_evidence.rsplit(":", 1)[-1]) if source_evidence else review.get("source_line", "")
        source_url = BASE + quote(clause["source_document"]) + (f"#L{source_line}" if source_line else "")
        normative = review.get("normative_note", review.get("normative_evaluation"))
        if not normative:
            normative = {"OPTION": "Permission or conditional-use provision; omission of the optional treatment is not itself a violation.",
                         "SUPPORT": "Interpretive context; do not invent an independent mandatory requirement.",
                         "GUIDANCE": "Advisory provision; preserve engineering judgment and applicable exceptions.",
                         "STANDARD": "Mandatory provision only when its applicability and exceptions are established."}[clause["classification"]]
        evidence = list(review["evidence"])
        if not has_evaluator and clause["canonical_rule_id"]:
            evidence.append("rules/full_registry.py:95-102")
        rows.append({"document": clause["source_document"], "source_rule_id": clause["source_rule_id"],
                     "clause_id": clause["clause_id"], "heading": clause["heading"], "citation": clause["citation"],
                     "source_url": source_url, "classification": clause["classification"],
                     "normative_evaluation": normative, "canonical_rule_id": clause["canonical_rule_id"],
                     "catalog_disposition": clause["disposition"], "rule_specific_evaluator_available": has_evaluator,
                     "blocker_categories": categories, "gap_ids": [family_ids[f] for f in families],
                     "gap_families": families, "non_schema_themes": themes, "required_facts": facts,
                     "schema_support": support, "minimal_extension": extensions, "residual_blockers": sorted(set(residual)),
                     "confidence": review["confidence"],
                     "evidence_basis": review.get("evidence_basis", "Clause-specific source/schema/evaluator static review; runtime evidence separately attached."),
                     "static_evidence": evidence, "default_observed_statuses": sorted({r["status"] for r in observations}),
                     "runtime_evidence": {"example_index": "evidence/runtime-index.json", "lookup_rule_id": clause["canonical_rule_id"],
                                          "observed_variants": observations,
                                          "focused_probes": [{"probe": r["probe"], "status": r["status"], "complete": r["complete"],
                                                              "reason": r["reason"]} for r in probes]},
                     "source_text": clause["text"]})
    assert len({r["canonical_rule_id"] for r in rows if r["canonical_rule_id"]}) == 419
    with (ROOT / "rule-gap-matrix.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows({k: render(v) for k, v in row.items()} for row in rows)

    family_records = []
    text = ["# CloudTCP schema capability gaps", "",
            "This appendix gives the complete capability-to-clause mapping used by the audit. Read it with [report.md](report.md) and the [clause matrix](rule-gap-matrix.csv).", "",
            "Counts are overlapping static source/schema mappings of candidate related checks. They are not guaranteed unlock counts, actual findings, or a compliance percentage. A permission can need additional context when selected without requiring that treatment on every plan. Medium-confidence mappings require clause-specific review before choosing an exact future field contract.", "",
            "G37 is a cross-cutting evidence-completeness concern, not an extra requirement attributed to a specific source clause. Proposed additions describe capabilities; property names in rejected probes are illustrative.", "",
            "| ID | Capability | Candidate canonical checks | STANDARD-related checks | Suggested work group |", "|---|---|---:|---:|---|"]
    for name, definition in definitions.items():
        members = [r for r in rows if name in r["gap_families"]]
        ids = sorted({r["canonical_rule_id"] for r in members if r["canonical_rule_id"]})
        standards = sorted({r["canonical_rule_id"] for r in members if r["classification"] == "STANDARD" and r["canonical_rule_id"]})
        group = "1 foundation" if name in FOUNDATION else "2 safety geometry" if name in GEOMETRY else "3 equipment and specialist evidence"
        record = {"gap_id": family_ids[name], "family": name, **definition, "suggested_work_group": group,
                  "candidate_canonical_checks": ids, "standard_related_canonical_checks": standards,
                  "source_clauses": [{k: r[k] for k in ("document", "source_rule_id", "clause_id", "classification", "confidence", "source_url")} for r in members],
                  "residual_blockers": sorted({v for r in members for v in r["residual_blockers"]})}
        family_records.append(record)
        label = name.replace("_", " ")
        text.append(f"| [{record['gap_id']}](#{record['gap_id'].lower()}-{name.replace('_', '-')}) | {label} | {len(ids)} | {len(standards)} | {group} |")
    for record in family_records:
        label = record["family"].replace("_", " ")
        members = [r for r in rows if record["family"] in r["gap_families"]]
        text.extend(["", f"## {record['gap_id']} {label}", "", f"**Required facts:** {record['required_facts']}", "",
                     f"**Current limitation:** {record['absence']}", "", f"**Minimum capability addition:** {record['minimal_extension']}", "",
                     "**Current schema locations:** " + ", ".join(f"`{p}`" for p in record["related_schema_pointers"]) + ".", "",
                     (f"**Candidate impact:** {len(record['candidate_canonical_checks'])} distinct canonical checks, {len(members)} source clauses; "
                      f"{len(record['standard_related_canonical_checks'])} distinct checks have at least one STANDARD clause in this mapping. Suggested group: {record['suggested_work_group']}.")])
        for document, prefix in [("TCP Rules Document.md", "Full document"), ("TCP-W1-1 Rules.md", "W1")]:
            refs = [f"[{r['source_rule_id']}.{r['clause_id']}]({r['source_url']})" for r in members if r["document"] == document]
            if refs:
                text.extend(["", f"**{prefix} clauses:** " + ", ".join(refs) + "."])
        examples = []
        for row in members:
            for probe in row["runtime_evidence"]["focused_probes"]:
                name = probe["probe"]
                if name not in examples:
                    examples.append(name)
        if examples:
            text.extend(["", "**Representative focused probes:** " + ", ".join(f"`{n}`" for n in examples[:6]) + ". See [focused-results.json](evidence/probes/focused-results.json)."])
        specific = []
        for row in members:
            if row["document"] == "TCP-W1-1 Rules.md":
                for fact in row["required_facts"]:
                    if fact not in specific:
                        specific.append(fact)
        if specific:
            text.extend(["", "**Additional clause-specific facts:** " + "; ".join(specific[:12]) + ". Exact facts for every member remain in the matrix."])
        if record["residual_blockers"]:
            text.extend(["", "**Residual blockers, representative examples:**", ""] + [f"- {s}" for s in record["residual_blockers"][:5]])
        elif record["family"] == "inventory_completeness":
            text.extend(["", "**Evidence:** the synthetic buffer inputs have no elements; absence-based checks can return not_applicable. See [inventory-completeness.json](evidence/inventory-completeness.json). The extractor's separate diagnostics already preserve unmapped/skipped content; propagate that evidence rather than inventing real-world absence."])
    write(ROOT / "gap-families.json", family_records)
    (ROOT / "gap-families.md").write_text("\n".join(text) + "\n")
    validation = {"source_entries": len({(r["document"], r["source_rule_id"]) for r in rows}),
                  "clauses": len(rows), "canonical_checks": 419,
                  "clauses_by_document": dict(Counter(r["document"] for r in rows)),
                  "blocker_categories_overlapping": dict(Counter(c for r in rows for c in r["blocker_categories"])),
                  "confidence": dict(Counter(r["confidence"] for r in rows)),
                  "families": len(family_records), "schema_mapped_clauses": sum(bool(r["gap_families"]) for r in rows),
                  "schema_classified_without_family": [list(key(r)) for r in rows if "schema" in r["blocker_categories"] and not r["gap_families"]],
                  "canonical_checks_with_rule_specific_evaluator": len(evaluators), "canonical_placeholder_checks": 419 - len(evaluators),
                  "root_adjustments": root_adjustments, "assertions_passed": True}
    assert not validation["schema_classified_without_family"]
    write(ROOT / "evidence/matrix-validation.json", validation)
    print(json.dumps(validation, indent=2))


if __name__ == "__main__":
    main()
