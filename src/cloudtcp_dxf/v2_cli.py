"""Standalone data validation and conservative migration, independent of any verifier."""

import argparse
import json
import sys
from pathlib import Path

from .cli import same_path, write_json
from .v2_migration import migrate_v1_document
from .v2_validation import V2ValidationError, validate_v2_document


def validate_main(argv=None):
    parser = argparse.ArgumentParser(
        description="Validate CloudTCP 2.0.0 data integrity only"
    )
    parser.add_argument("input", type=Path)
    args = parser.parse_args(argv)
    try:
        validate_v2_document(json.loads(args.input.read_text(encoding="utf-8")))
        print(json.dumps({"valid": True, "diagnostics": []}))
        return 0
    except V2ValidationError as exc:
        print(json.dumps({"valid": False, "diagnostics": exc.diagnostics}))
        return 1
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


def migrate_main(argv=None):
    parser = argparse.ArgumentParser(
        description="Import v1 into partial v2 while preserving the original file"
    )
    parser.add_argument("input", type=Path)
    parser.add_argument("-o", "--output", type=Path)
    parser.add_argument("--context", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args(argv)
    try:
        output = args.output or args.input.with_suffix(".v2.json")
        report = args.report or output.with_suffix(".migration.json")
        protected = [args.input, *([args.context] if args.context else [])]
        if any(
            same_path(p, q) for p in (output, report) for q in protected
        ) or same_path(output, report):
            raise ValueError(
                "Output, report and original/context files must be distinct"
            )
        for destination in (output, report):
            if not destination.exists():
                continue
            try:
                existing = json.loads(destination.read_text(encoding="utf-8"))
            except (ValueError, UnicodeError):
                existing = {}
            if isinstance(existing, dict) and existing.get("format_version") == "1.0.0":
                raise ValueError(
                    "Preserve the existing v1 artifact; choose separate v2 paths"
                )
        source = json.loads(args.input.read_text(encoding="utf-8"))
        context = (
            json.loads(args.context.read_text(encoding="utf-8"))
            if args.context
            else None
        )
        result = migrate_v1_document(source, context)
        write_json(report, result["migration_report"])
        write_json(output, result["document"])
        print(f"Wrote {output}; original retained at {args.input}")
        return 0
    except V2ValidationError as exc:
        print(json.dumps({"diagnostics": exc.diagnostics}), file=sys.stderr)
        return 1
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
