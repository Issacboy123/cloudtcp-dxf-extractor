"""DXF extraction and conservative IF conversion command-line interface."""
import argparse
import json
import os
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile
from .extract import extract_dxf
from .if_conversion import convert_dxf
from .validation import ConversionError, issue, validate_if

def write_json(path, data):
    path = Path(path)
    serialized = json.dumps(data, indent=2, allow_nan=False)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(serialized)
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def same_path(first, second):
    return first.resolve() == second.resolve() or (first.exists() and second.exists() and first.samefile(second))

def main(argv=None):
    parser = argparse.ArgumentParser(description="Inspect a DXF or convert mapped block inserts to IF v1")
    parser.add_argument("input", type=Path)
    parser.add_argument("-o", "--output", type=Path)
    parser.add_argument("--log", type=Path)
    parser.add_argument("--max-entities", type=int)
    parser.add_argument("--if-config", type=Path, help="JSON config for IF v1 conversion; requires explicit road facts and centerline")
    parser.add_argument("--schema", type=Path, help="Additional schema constraints; bundled IF v1 validation always runs")
    args = parser.parse_args(argv)
    log = {"issues": []}
    can_write_log = False
    try:
        if args.max_entities is not None and args.max_entities < 0:
            parser.error("--max-entities must be nonnegative")
        output = args.output or args.input.with_suffix(".if.json" if args.if_config else ".extracted.json")
        protected = [p for p in (args.input, args.if_config, args.schema) if p is not None]
        if any(same_path(output, p) for p in protected):
            raise ValueError("Output must differ from input, configuration and schema paths")
        if args.log and any(same_path(args.log, p) for p in [*protected, output]):
            raise ValueError("Log must differ from input, configuration, schema and output paths")
        can_write_log = True
        if args.if_config:
            if args.max_entities is not None:
                parser.error("--max-entities is incompatible with --if-config")
            config = json.loads(args.if_config.read_text(encoding="utf-8"))
            document, log = convert_dxf(args.input, config)
            if args.schema:
                validate_if(document, args.schema)
            write_json(output, document)
        else:
            if args.schema:
                parser.error("--schema requires --if-config")
            result = extract_dxf(args.input, max_entities=args.max_entities)
            log = {"source": result["source"], "entity_types": result["entity_types"], "layers": result["layers"], "log": result["log"]}
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
