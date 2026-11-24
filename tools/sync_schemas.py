"""Copy authoritative versioned schemas into the installed package; --check for CI."""

import argparse
from pathlib import Path

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--check", action="store_true")
args = parser.parse_args()
for source in sorted((root / "schemas").glob("*/schema.json")):
    target = root / "src/cloudtcp_dxf/schemas" / source.parent.name / source.name
    if args.check:
        if not target.exists() or source.read_bytes() != target.read_bytes():
            raise SystemExit(f"Unsynchronized schema: {target}")
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())
