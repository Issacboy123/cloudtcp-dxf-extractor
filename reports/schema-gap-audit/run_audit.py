"""Reproduce the pinned verifier audit without changing verifier source or schema."""
import argparse
import csv
import gzip
import hashlib
import json
import lzma
import platform
import re
import subprocess
import sys
import time
from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

PIN = "ef5e47459aea9559ae8fad7f0087f376308fe09e"


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def capture(command, repo, output, name):
    start = time.monotonic()
    result = subprocess.run(command, cwd=repo, capture_output=True, text=True, check=False)
    stdout_name = f"{name}.stdout.txt"
    if len(result.stdout) > 20000:
        stdout_name += ".gz"
        with gzip.open(output / stdout_name, "wt") as stream:
            stream.write(result.stdout)
    else:
        (output / stdout_name).write_text(result.stdout)
    (output / f"{name}.stderr.txt").write_text(result.stderr)
    record = {"command": command, "cwd": str(repo), "exit_code": result.returncode,
              "duration_seconds": round(time.monotonic() - start, 3),
              "stdout": stdout_name, "stderr": f"{name}.stderr.txt"}
    write_json(output / f"{name}.command.json", record)
    return result, record


def reconcile(repo, catalog):
    grouped = defaultdict(list)
    for clause in catalog:
        grouped[(clause.source_document, clause.source_rule_id)].append(clause)
    rows = []
    for filename in ("TCP Rules Document.md", "TCP-W1-1 Rules.md"):
        text = (repo / filename).read_text()
        headings = list(re.finditer(
            r"^### ([A-Z]+-\d+(?:-[A-Z])?) — (STANDARD|GUIDANCE|OPTION|SUPPORT) — (.+)$",
            text, re.MULTILINE))
        for index, heading in enumerate(headings):
            end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
            body, citation = text[heading.end():end].split("\n## ", 1)[0].split("**Citation:** ", 1)
            clauses = grouped[(filename, heading[1])]
            reconstructed = clauses
            if filename == "TCP-W1-1 Rules.md" and heading[1] == "SIGN-26":
                assert clauses[1].text == clauses[2].text
                reconstructed = clauses[:2]
            same_text = " ".join(" ".join(c.text for c in reconstructed).split()) == " ".join(body.split())
            same_citation = all(c.citation == citation.splitlines()[0].strip() for c in clauses)
            same_heading = all(c.heading == heading[0][4:] for c in clauses)
            rows.append({"document": filename, "source_rule_id": heading[1],
                         "clause_count": len(clauses), "text_matches": same_text,
                         "citation_matches": same_citation, "heading_matches": same_heading})
    assert len(rows) == len(grouped) == 457
    assert all(r["text_matches"] and r["citation_matches"] and r["heading_matches"] for r in rows)
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parent / "evidence")
    args = parser.parse_args()
    repo, out = args.repo.resolve(), args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    assert revision == PIN, f"Expected {PIN}, got {revision}"
    assert not subprocess.check_output(["git", "diff", "HEAD", "--"], cwd=repo)
    sys.path.insert(0, str(repo))
    from rules.full_evaluable import CAPABILITIES, EVALUATORS
    from rules.source_catalog import SOURCE_CATALOG
    from verifier import DEFAULT_REGISTRY, LEGACY_REGISTRY, W1_REGISTRY, verify_file

    workspace = Path(__file__).resolve().parents[2]
    schemas = [repo / "tcp-intermediate-format.schema.json",
               workspace / "tcp-intermediate-format.schema.json",
               workspace / "src/cloudtcp_dxf/tcp-intermediate-format.schema.json"]
    hashes = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in schemas}
    assert len(set(hashes.values())) == 1
    manifest = {"utc_timestamp": datetime.now(timezone.utc).isoformat(), "commit": revision,
                "repository": "https://github.com/Issacboy123/cloudtcp-python-verifier.git",
                "python": sys.version, "platform": platform.platform(), "schema_sha256": hashes,
                "workspace_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=workspace, text=True).strip(),
                "evaluator_keys": sorted(EVALUATORS), "capabilities": CAPABILITIES}
    write_json(out / "manifest.json", manifest)
    capture([sys.executable, "-m", "pip", "freeze"], repo, out, "dependencies")
    commands = []
    for name, command in [("pytest", [sys.executable, "-m", "pytest", "-q"]),
                          ("ruff", [sys.executable, "-m", "ruff", "check", "."])]:
        _, record = capture(command, repo, out, name)
        commands.append(record)
        print(name, record["exit_code"], flush=True)
    reconciliation = reconcile(repo, SOURCE_CATALOG)
    write_json(out / "source-reconciliation.json", reconciliation)
    write_json(out / "source-catalog.json", [asdict(c) for c in SOURCE_CATALOG])

    from verifier import verify_document
    sparse = json.loads((repo / "examples/taper-75ft.json").read_text())
    sparse["elements"] = []
    sparse_report = verify_document(sparse)
    evaluator_ids = {"mutcd." + name for name in EVALUATORS}
    write_json(out / "inventory-completeness.json", {
        "input": sparse, "input_valid": sparse_report.input_valid,
        "evaluation_complete": sparse_report.evaluation_complete,
        "exit_code": sparse_report.exit_code,
        "rule_specific_results": [asdict(r) for r in sparse_report.rule_results if r.rule_id in evaluator_ids],
        "interpretation": "Absent subjects can yield not_applicable. The contract has no scoped inventory-completeness evidence distinguishing true absence from partial extraction; this is an evidence-contract concern, not proof that any device is legally required."
    })

    example_rows, counts, runtime_index = [], Counter(), defaultdict(list)
    examples = sorted((repo / "examples").rglob("*.json"))
    raw = out / "example-reports.jsonl.xz"
    with lzma.open(raw, "wt", preset=6) as stream, lzma.open(out / "example-rule-results.csv.xz", "wt", newline="", preset=6) as csvstream:
        columns = ["fixture", "registry", "rule_id", "status", "complete", "reason", "finding_count", "error_count"]
        writer = csv.DictWriter(csvstream, fieldnames=columns)
        writer.writeheader()
        for fixture in examples:
            relative = str(fixture.relative_to(repo))
            for registry_name, registry in [("default", DEFAULT_REGISTRY), ("w1", W1_REGISTRY)]:
                report = verify_file(fixture, registry=registry)
                payload = report.to_dict()
                stream.write(json.dumps({"fixture": relative, "registry": registry_name, "exit_code": report.exit_code, "report": payload}) + "\n")
                statuses = Counter(r.status for r in report.rule_results)
                counts.update({f"{registry_name}:{k}": v for k, v in statuses.items()})
                example_rows.append({"fixture": relative, "registry": registry_name,
                                     "exit_code": report.exit_code, "input_valid": report.input_valid,
                                     "evaluation_complete": report.evaluation_complete,
                                     "statuses": dict(statuses), "findings": len(report.findings),
                                     "incomplete_failures": sum(r.status == "fail" and not r.complete for r in report.rule_results)})
                for result in report.rule_results:
                    writer.writerow({"fixture": relative, "registry": registry_name, "rule_id": result.rule_id,
                                     "status": result.status, "complete": result.complete, "reason": result.reason,
                                     "finding_count": len(result.findings), "error_count": len(result.errors)})
                    if registry_name == "default":
                        signature = (result.status, result.complete, result.reason)
                        if not any((r["status"], r["complete"], r["reason"]) == signature for r in runtime_index[result.rule_id]):
                            runtime_index[result.rule_id].append({"fixture": relative, "status": result.status,
                                                                  "complete": result.complete, "reason": result.reason})
    write_json(out / "example-summary.json", example_rows)
    write_json(out / "runtime-index.json", runtime_index)

    smoke, agreement_errors = [], []
    registry_map = {"default": DEFAULT_REGISTRY, "all": DEFAULT_REGISTRY, "w1": W1_REGISTRY, "legacy": LEGACY_REGISTRY}
    for filename, expected_default in [("taper-75ft.json", 3), ("taper-125ft.json", 1), ("invalid.json", 2)]:
        for registry_name, registry in registry_map.items():
            api = verify_file(repo / "examples" / filename, registry=registry)
            for fmt in ("json", "text"):
                label = f"cli-{filename[:-5]}-{registry_name}-{fmt}"
                result, record = capture([sys.executable, "-m", "verifier", f"examples/{filename}",
                                          "--registry", registry_name, "--format", fmt], repo, out, label)
                exact = result.returncode == api.exit_code
                if fmt == "json":
                    exact = exact and json.loads(result.stdout) == api.to_dict()
                else:
                    from reporting import format_text
                    exact = exact and result.stdout.rstrip() == format_text(api).rstrip()
                if registry_name in ("default", "all"):
                    exact = exact and result.returncode == expected_default
                if not exact:
                    agreement_errors.append(label)
                smoke.append({**record, "api_agreement": exact, "fixture": filename,
                              "registry": registry_name, "format": fmt})
    write_json(out / "cli-smoke-summary.json", smoke)
    summary = {"example_files": len(examples), "example_api_runs": len(example_rows),
               "cli_smoke_runs": len(smoke), "api_cli_agreement_errors": agreement_errors,
               "source_entries": len(reconciliation), "source_clauses": len(SOURCE_CATALOG),
               "canonical_checks": len(DEFAULT_REGISTRY.rules),
               "dispositions": dict(Counter(c.disposition for c in SOURCE_CATALOG)),
               "source_classifications": dict(Counter(c.classification for c in SOURCE_CATALOG)),
               "runtime_status_totals": dict(counts),
               "example_exit_codes": dict(Counter(f"{r['registry']}:{r['exit_code']}" for r in example_rows)),
               "incomplete_failures": sum(r["incomplete_failures"] for r in example_rows),
               "test_commands": commands}
    write_json(out / "run-summary.json", summary)
    assert not agreement_errors, agreement_errors
    assert not subprocess.check_output(["git", "diff", "HEAD", "--"], cwd=repo)
    print(json.dumps(summary, indent=2), flush=True)
    return int(any(c["exit_code"] for c in commands))


if __name__ == "__main__":
    raise SystemExit(main())
