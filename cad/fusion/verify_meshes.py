#!/usr/bin/env python3
"""Geometric print checks, not mechanical or sensor validation.

Requires numpy, trimesh and networkx (separate from dashboard requirements).
"""
import json
import hashlib
from pathlib import Path
import numpy as np
import trimesh

def main():
    root = Path(__file__).resolve().parent
    results = []
    for path in sorted((root / "stl").glob("*.stl")):
        mesh = trimesh.load_mesh(path, process=True)
        components = mesh.split(only_watertight=False)
        extents = mesh.extents
        checks = {
            "watertight": bool(mesh.is_watertight),
            "consistent_winding": bool(mesh.is_winding_consistent),
            "positive_volume": bool(mesh.volume > 0),
            "one_connected_solid": len(components) == 1,
            "fits_140_mm_volume": bool(np.all(extents <= 140.0001)),
            "fits_130_mm_xy_with_5_mm_bed_margin": bool(np.all(extents[:2] <= 130.0001)),
            "flat_on_z_zero": bool(abs(mesh.bounds[0,2]) < 0.0001),
        }
        results.append({"part": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                        "dimensions_mm": np.round(extents,3).tolist(),
                        "triangles": len(mesh.faces), "volume_mm3": round(float(mesh.volume),3),
                        "checks": checks, "passed": all(checks.values())})
    assert len(results) == 7, "Expected seven separate printable parts"
    report = {"scope": "Mesh geometry only; no load rating or printed fit claimed", "parts": results,
              "source_sha256": hashlib.sha256((root / "SkySafeFusion" / "SkySafeFusion.py").read_bytes()).hexdigest(),
              "trimesh_version": trimesh.__version__,
              "passed": all(part["passed"] for part in results)}
    out = root / "verification" / "mesh_report.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(report, indent=2)+"\n")
    print(json.dumps(report, indent=2))
    if not report["passed"]:
        raise SystemExit("CAD geometry check failed")

if __name__ == "__main__":
    main()
