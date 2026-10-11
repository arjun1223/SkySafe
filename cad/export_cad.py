#!/usr/bin/env python3
"""Export individual, flat-on-bed STL parts with the installed OpenSCAD CLI."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess

PARTS = ("wing", "root_base", "root_cap", "tip_adapter", "cell_spacer", "load_hanger", "spar_fit_coupon")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--openscad", default=os.environ.get("SKYSAFE_OPENSCAD_BIN") or shutil.which("openscad") or "/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD")
    parser.add_argument("--spar-clearance", type=float, default=0.4)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    output = root / "stl"
    output.mkdir(exist_ok=True)
    logs = root / "verification" / "export_logs"
    logs.mkdir(parents=True, exist_ok=True)
    for part in PARTS:
        result = subprocess.run([args.openscad, "--hardwarnings", "--export-format", "binstl",
                                 "-D", f'part="{part}"', "-D", f"spar_clearance={args.spar_clearance}",
                                 "-o", str(output / f"{part}.stl"), str(root / "SkySafe.scad")],
                                text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        (logs / f"{part}.log").write_text(result.stdout)
        if result.returncode or "ERROR:" in result.stdout or "WARNING:" in result.stdout:
            raise SystemExit(f"Export failed for {part}:\n{result.stdout}")
        print(f"Exported {part}.stl")

if __name__ == "__main__":
    main()
