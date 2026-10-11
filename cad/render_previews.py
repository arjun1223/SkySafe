#!/usr/bin/env python3
"""Render assembly, part and cutaway views; reference hardware is schematic."""
import os
from pathlib import Path
import shutil
import subprocess

root = Path(__file__).resolve().parent
binary = os.environ.get("SKYSAFE_OPENSCAD_BIN") or shutil.which("openscad") or "/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD"
out = root / "previews"
out.mkdir(exist_ok=True)
for part, camera in [
    ("assembly", "75,0,0,63,0,28,440"),
    ("exploded", "75,0,25,63,0,28,440"),
    ("wing", "64,0,3,32,0,0,180"),
    ("spar_section", "64,0,3,55,0,25,190"),
    ("spar_fit_coupon", "12,30,4,50,0,35,120"),
]:
    result = subprocess.run([binary, "--hardwarnings", "--imgsize", "1600,1000",
                             "--colorscheme", "Tomorrow", "--projection", "o", "--camera", camera,
                             "--viewall", "--autocenter", "-D", f'part="{part}"',
                             "-o", str(out / f"{part}.png"), str(root / "SkySafe.scad")],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if result.returncode or "WARNING:" in result.stdout or "ERROR:" in result.stdout:
        raise SystemExit(result.stdout)
    print(f"Rendered {part}")
