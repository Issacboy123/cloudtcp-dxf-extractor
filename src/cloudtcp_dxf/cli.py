"""DXF extraction and conservative IF conversion command-line interface."""

import argparse
import json
import os
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile

from .extract import extract_dxf
from .if_conversion import convert_dxf
from .v2_conversion import convert_v2_extraction
from .v2_validation import validate_v2_document
from .validation import ConversionError, issue, validate_if


def write_json(path, data):
    path = Path(path)
    serialized = json.dumps(data, indent=2, allow_nan=False)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, delete=False
        ) as stream:
            temporary = Path(stream.name)
            stream.write(serialized)
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def same_path(first, second):
    return first.resolve() == second.resolve() or (
        first.exists() and second.exists() and first.samefile(second)
    )


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Inspect a DXF or convert mapped block inserts to CloudTCP IF"
    )
    parser.add_argument("input", type=Path)
    parser.add_argument("-o", "--output", type=Path)
    parser.add_argument("--log", type=Path)
    parser.add_argument("--max-entities", type=int)
    parser.add_argument(
        "--if-config", type=Path, help="JSON config for the selected IF version"
    )
    parser.add_argument(
        "--schema",
        type=Path,
        help="Additional schema constraints; bundled validation always runs",
    )
    parser.add_argument(
        "--format-version",
        choices=("1.0.0", "2.0.0"),
        default=None,
        help="IF export version (default: 2.0.0 with --if-config); select 1.0.0 for legacy configuration",
    )
    args = parser.parse_args(argv)
    log = {"issues": []}
    can_write_log = False
    try:
        if args.max_entities is not None and args.max_entities < 0:
            parser.error("--max-entities must be nonnegative")
        if args.format_version == "2.0.0" and not args.if_config:
            parser.error("--format-version 2.0.0 requires --if-config")
        format_version = args.format_version or "2.0.0"
        is_v2 = args.if_config is not None and format_version == "2.0.0"
        output = args.output or args.input.with_suffix(
            ".v2.if.json"
            if is_v2
            else ".if.json"
            if args.if_config
            else ".extracted.json"
        )
        if is_v2 and args.log is None:
            args.log = output.with_suffix(".report.json")
        raw_output = output.with_suffix(".extracted.json") if is_v2 else None
        protected = [
            p for p in (args.input, args.if_config, args.schema) if p is not None
        ]
        if any(same_path(output, p) for p in protected):
            raise ValueError(
                "Output must differ from input, configuration and schema paths"
            )
        if args.log and any(same_path(args.log, p) for p in [*protected, output]):
            raise ValueError(
                "Log must differ from input, configuration, schema and output paths"
            )
        if raw_output and any(
            same_path(raw_output, p) for p in [*protected, output, args.log]
        ):
            raise ValueError("Raw extraction must differ from all input/output paths")
        if is_v2:
            for destination in (output, raw_output, args.log):
                if not destination.exists():
                    continue
                try:
                    previous = json.loads(destination.read_text(encoding="utf-8"))
                except (ValueError, UnicodeError):
                    previous = {}
                if (
                    isinstance(previous, dict)
                    and previous.get("format_version") == "1.0.0"
                ):
                    raise ValueError(
                        "Preserve the existing v1 artifact; choose separate v2 output paths"
                    )
        can_write_log = True
        if args.if_config:
            if args.max_entities is not None:
                parser.error("--max-entities is incompatible with --if-config")
            config = json.loads(args.if_config.read_text(encoding="utf-8"))
            if isinstance(config, dict):
                if (
                    is_v2
                    and "document" not in config
                    and {"site", "typical_application", "zones", "centerline"}.issubset(
                        config
                    )
                ):
                    raise ValueError(
                        "Legacy v1 configuration cannot be used for CloudTCP IF v2.0.0. "
                        "Use --format-version 1.0.0 for legacy conversion, or supply a "
                        "v2 configuration; cloudtcp-migrate-v1 migrates existing v1 documents."
                    )
                if not is_v2 and {"document", "stationing"}.issubset(config):
                    raise ValueError(
                        "V2 configuration cannot be used with --format-version 1.0.0. "
                        "Omit --format-version or select --format-version 2.0.0."
                    )
            if is_v2:
                extraction = extract_dxf(args.input)
                write_json(raw_output, extraction)
                document, log = convert_v2_extraction(extraction, config)
            else:
                document, log = convert_dxf(args.input, config)
            if args.schema:
                if is_v2:
                    from jsonschema import Draft202012Validator, FormatChecker

                    additional = json.loads(args.schema.read_text(encoding="utf-8"))
                    Draft202012Validator.check_schema(additional)
                    Draft202012Validator(
                        additional, format_checker=FormatChecker()
                    ).validate(document)
                    validate_v2_document(document)
                else:
                    validate_if(document, args.schema)
            write_json(output, document)
        else:
            if args.schema:
                parser.error("--schema requires --if-config")
            result = extract_dxf(args.input, max_entities=args.max_entities)
            log = {
                "source": result["source"],
                "entity_types": result["entity_types"],
                "layers": result["layers"],
                "log": result["log"],
            }
            write_json(output, result)
        if args.log:
            write_json(args.log, log)
        print(f"Wrote {output}")
        return 0
    except Exception as exc:
        if isinstance(exc, ConversionError):
            if "source" in exc.report:
                log = exc.report
            else:
                log.setdefault("issues", []).extend(exc.report["issues"])
        else:
            log.setdefault("issues", []).append(issue(str(exc), "/"))
        if args.log and can_write_log:
            try:
                write_json(args.log, log)
            except Exception as log_exc:
                print(f"Could not write diagnostics: {log_exc}", file=sys.stderr)
        print(f"Conversion failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
