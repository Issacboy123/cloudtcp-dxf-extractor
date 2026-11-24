# CloudTCP schema audit artifacts

Read [report.md](report.md) for conclusions, [rule-gap-matrix.csv](rule-gap-matrix.csv) for every source clause, and [gap-families.md](gap-families.md) for the complete gap-to-rule mapping.

The audit uses verifier commit `ef5e47459aea9559ae8fad7f0087f376308fe09e`. Its source and schema were not modified. The checkout used for this run is `/private/tmp/cloudtcp-schema-audit-ef5e474/cloudtcp-python-verifier`; the Python environment is its sibling `venv` directory. The temporary checkout can be recreated using the commands below.

## Reproduce the execution evidence

Run from the extractor workspace root. Python 3.14.10 was used; the verifier supports Python 3.11 or newer. The frozen dependency versions are in `evidence/dependencies.stdout.txt`.

```sh
git clone https://github.com/Issacboy123/cloudtcp-python-verifier.git /tmp/cloudtcp-verifier-audit
git -C /tmp/cloudtcp-verifier-audit checkout --detach ef5e47459aea9559ae8fad7f0087f376308fe09e
python3 -m venv /tmp/cloudtcp-audit-venv
/tmp/cloudtcp-audit-venv/bin/python -m pip install -r reports/schema-gap-audit/evidence/dependencies.stdout.txt
/tmp/cloudtcp-audit-venv/bin/python reports/schema-gap-audit/run_audit.py --repo /tmp/cloudtcp-verifier-audit
/tmp/cloudtcp-audit-venv/bin/python reports/schema-gap-audit/evidence/probes/run_probes.py --repo /tmp/cloudtcp-verifier-audit
/tmp/cloudtcp-audit-venv/bin/python reports/schema-gap-audit/build_matrix.py
```

The runtime harness reruns pytest, Ruff, all examples through the API, and CLI smoke comparisons. It requires the extractor's two unchanged schema copies for the three-way comparison. The focused harness checks its expected outcomes and validates all baseline synthetic documents before evaluation. The matrix builder checks complete clause coverage and combines the saved semantic reviews with observed runtime results. Semantic interpretations are reviewed audit records, not an automatic classification of new or changed rules.

## Evidence formats

| Artifact | Contents |
|---|---|
| `evidence/manifest.json` | Commit, environment, evaluator inventory, three schema hashes |
| `evidence/source-reconciliation.json` | Independent heading, full substantive text, and citation matching for all 457 source entries |
| `evidence/source-catalog.json` | Pinned clause text, normative strength, aliases, declared dispositions and limitations |
| `evidence/run-summary.json` | Baseline and fixture counts; read alongside raw results |
| `evidence/pytest.*`, `evidence/ruff.*` | Commands, exit codes, stdout and stderr |
| `evidence/example-reports.jsonl.xz` | All 310 complete API reports, one JSON object per line |
| `evidence/example-rule-results.csv.xz` | All individual default/W1 example results, including completeness and reasons |
| `evidence/runtime-index.json` | Distinct observed default-registry outcomes and a representative fixture for each |
| `evidence/cli-smoke-summary.json` | 24 CLI runs and exact API/CLI agreement results |
| `evidence/cli-*.stdout.txt[.gz]` | Original CLI JSON/text outputs, compressed when large |
| `evidence/probes/` | Synthetic inputs, targeted outcomes, full reports, rejected extension diagnostics, and hypothetical counterexamples |
| `analysis/` | Separate full-document, W1, and focused-runtime reviews |
| `evidence/matrix-validation.json` | Final reconciliation, classifications, and coverage checks |

Open XZ/Gzip files with a decompressor or Python's standard `lzma`/`gzip` modules. Compression preserves complete reports, including repeated source metadata. No schema-coverage percentage is derived from verifier scores.
