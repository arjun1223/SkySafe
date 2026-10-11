#!/usr/bin/env python3
"""Check exported flexible-wing geometry; does not predict elastic range or sag."""
import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh


def main():
    root = Path(__file__).resolve().parent
    path = root / "stl" / "wing.stl"
    mesh = trimesh.load_mesh(path, process=True)
    native = json.loads((root / "native_build_report.json").read_text())
    meshes = json.loads((root / "verification" / "mesh_report.json").read_text())
    source_hash = hashlib.sha256((root / "SkySafeFusion" / "SkySafeFusion.py").read_bytes()).hexdigest()
    assert native["status"].startswith("PASS") and meshes["passed"]
    assert source_hash == native["source_sha256"] == meshes["source_sha256"]
    assert native["flex_wing"]["revision"] == "short-guides-v1"

    def section(x):
        lines = trimesh.intersections.mesh_plane(mesh, plane_origin=[x, 0, 0], plane_normal=[1, 0, 0])
        return np.unique(lines.reshape(-1, 3), axis=0)[:, 1:3]

    bores = []
    for x in [10, 29, 49, 69, 89, 109, 120]:
        points = section(x)
        for y in [-18, 18]:
            distance = np.linalg.norm(points - [y, 3.4], axis=1)
            yz = points[(distance > 2.1) & (distance < 2.4)]
            assert len(yz) > 20, (x, y, len(yz))
            a = np.column_stack([2 * yz[:, 0], 2 * yz[:, 1], np.ones(len(yz))])
            cy, cz, c = np.linalg.lstsq(a, (yz * yz).sum(axis=1), rcond=None)[0]
            diameter = float(2 * np.sqrt(c + cy * cy + cz * cz))
            assert abs(diameter - 4.5) < .02 and abs(cy - y) < .02 and abs(cz - 3.4) < .02
            bores.append({"section_x_mm": x, "center_yz_mm": [float(cy), float(cz)], "diameter_mm": diameter})

    gaps = []
    for x in [40, 60]:
        points = section(x)
        low, high = points.min(axis=0), points.max(axis=0)
        assert np.allclose(low, [-6, 0], atol=.001) and np.allclose(high, [6, 1.8], atol=.001)
        gaps.append({"section_x_mm": x, "strip_width_mm": float(high[0] - low[0]),
                     "strip_thickness_mm": float(high[1] - low[1]), "no_spar_tubes_or_edge_rails": True})
    result = {"passed": True, "scope": "Export geometry only; self-weight sag and elastic range untested",
              "source_sha256": source_hash, "wing_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
              "selected_bore_mm": 4.5, "bores": bores, "open_bays": gaps}
    (root / "verification" / "spar_bore_check.json").write_text(json.dumps(result, indent=2) + "\n")
    print("PASS: 14 bore sections, two open bays, 1.8 mm strip, source/native/mesh hashes")


if __name__ == "__main__":
    main()
