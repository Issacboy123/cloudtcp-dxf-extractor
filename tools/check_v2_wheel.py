"""Smoke-test a wheel installed with --no-deps --target, using that target on PYTHONPATH."""

import argparse
import json
import subprocess
import tempfile
import zipfile
from importlib.resources import files
from pathlib import Path

import ezdxf

import cloudtcp_dxf

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("wheel", type=Path)
parser.add_argument("installed_target", type=Path)
parser.add_argument("--report", type=Path)
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
installed = args.installed_target.resolve()
assert Path(cloudtcp_dxf.__file__).resolve().is_relative_to(installed)
assert (
    files("cloudtcp_dxf").joinpath("schemas/2.0.0/schema.json").read_bytes()
    == (root / "schemas/2.0.0/schema.json").read_bytes()
)
assert (
    files("cloudtcp_dxf").joinpath("tcp-intermediate-format.schema.json").read_bytes()
    == (root / "tcp-intermediate-format.schema.json").read_bytes()
)
with zipfile.ZipFile(args.wheel) as archive:
    assert "cloudtcp_dxf/schemas/2.0.0/schema.json" in archive.namelist()
    assert "cloudtcp_dxf/tcp-intermediate-format.schema.json" in archive.namelist()
    entry_file = next(
        name
        for name in archive.namelist()
        if name.endswith(".dist-info/entry_points.txt")
    )
    entries = archive.read(entry_file).decode()
    for module in (root / "src/cloudtcp_dxf").glob("*.py"):
        assert archive.read("cloudtcp_dxf/" + module.name) == module.read_bytes()
    assert all(
        name in entries
        for name in ["cloudtcp-dxf", "cloudtcp-validate-v2", "cloudtcp-migrate-v1"]
    )
working = Path(tempfile.mkdtemp(prefix="cloudtcp-v2-smoke-"))
cad = ezdxf.new()
cad.units = 2
for block, xy in [
    ("W20_1", (20, 5)),
    ("ARROW_BOARD", (30, -5)),
    ("FLAGGER", (40, 3)),
    ("UNMAPPED", (50, 4)),
]:
    cad.blocks.new(block)
    cad.modelspace().add_blockref(block, xy)
source = working / "plan.dxf"
cad.saveas(source)
original = working / "original.if.json"
commands = [
    [
        "cloudtcp-dxf",
        str(source),
        "--format-version",
        "1.0.0",
        "--if-config",
        str(root / "examples/if-config.example.json"),
        "-o",
        str(original),
        "--log",
        str(working / "v1.log.json"),
    ],
    [
        "cloudtcp-dxf",
        str(source),
        "--if-config",
        str(root / "examples/v2/if-config.example.json"),
    ],
    ["cloudtcp-validate-v2", str(source.with_suffix(".v2.if.json"))],
    ["cloudtcp-migrate-v1", str(original)],
    ["cloudtcp-validate-v2", str(original.with_suffix(".v2.json"))],
]
results = []
original_bytes = None
for command in commands:
    command[0] = str(installed / "bin" / command[0])
    result = subprocess.run(command, capture_output=True, text=True, cwd=working)
    results.append(
        {
            "command": command,
            "returncode": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
        }
    )
    assert result.returncode == 0, results[-1]
    if original_bytes is None:
        original_bytes = original.read_bytes()
    assert original.read_bytes() == original_bytes
v2 = json.loads(source.with_suffix(".v2.if.json").read_text())
assert v2["format_version"] == "2.0.0"
report = json.loads(source.with_suffix(".v2.if.report.json").read_text())
assert report["converted_elements"] == 3 and report["unmapped_elements"] == 1
assert any(e["kind"] == "actor" and e["role"] == "flagger" for e in v2["entities"])
assert json.loads(original.with_suffix(".v2.json").read_text())["legacy_records"][0][
    "value"
] == json.loads(original.read_text())
assert source.with_suffix(".v2.if.extracted.json").exists()
summary = {
    "package_path": str(cloudtcp_dxf.__file__),
    "resource_equality": True,
    "default_if_format_version": v2["format_version"],
    "original_v1_unchanged": True,
    "converted": report["converted_elements"],
    "unmapped": report["unmapped_elements"],
    "commands": results,
}
report_path = args.report or working / "verification.json"
report_path.parent.mkdir(parents=True, exist_ok=True)
summary["wheel_sha256"] = (
    __import__("hashlib").sha256(args.wheel.read_bytes()).hexdigest()
)
report_path.write_text(json.dumps(summary, indent=2) + "\n")
print(
    json.dumps(
        {
            "passed": True,
            "verification": str(report_path),
            "commands": len(results),
            "resources": ["1.0.0", "2.0.0"],
            "converted": 3,
            "unmapped": 1,
        }
    )
)
