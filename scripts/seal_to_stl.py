#!/usr/bin/env python3
"""印章图 -> 3D打印STL印模（阳文、左右镜像、文字正立）。
用法: seal_to_stl.py stitched.png -o seal.stl --diameter 42"""
import argparse

import numpy as np
import trimesh
from shapely.geometry import Polygon

import seal_lib as L


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--diameter", type=float, default=42.0, help="印章外径 mm")
    ap.add_argument("--plate-h", type=float, default=3.0, help="底板厚 mm")
    ap.add_argument("--relief", type=float, default=1.2, help="浮雕高出底板 mm")
    ap.add_argument("--plate-extra", type=float, default=3.0, help="底板比章径大 mm")
    args = ap.parse_args()

    ink, _ = L.load_ink(args.image)
    contours, hier, eps, min_area, scale = L.trace(ink)
    polys = L.contours_to_polys(contours, hier, eps, min_area, scale)
    if not polys:
        raise SystemExit("no contours found")

    allpts = np.vstack([p for o, hs in polys for p in [o] + hs])
    ring_d = max(allpts[:, 0].max() - allpts[:, 0].min(), allpts[:, 1].max() - allpts[:, 1].min())
    s = args.diameter / ring_d
    cx, cy = (allpts[:, 0].min() + allpts[:, 0].max()) / 2, (allpts[:, 1].min() + allpts[:, 1].max()) / 2

    def to_mm(pts):
        out = pts.copy()
        out[:, 0] = (cx - out[:, 0]) * s  # 仅镜像 X：顶视图文字左右翻、正立
        out[:, 1] = (out[:, 1] - cy) * s
        return out

    ph, relief = args.plate_h, args.relief
    solids = [trimesh.creation.cylinder(radius=(args.diameter + args.plate_extra) / 2, height=ph, sections=128)]
    solids[0].apply_translation([0, 0, ph / 2])

    for outer, holes in polys:
        poly = Polygon(L.dedup(to_mm(outer)), [L.dedup(to_mm(h)) for h in holes])
        if not poly.is_valid:
            poly = poly.buffer(0)
        geoms = list(poly.geoms) if poly.geom_type == "MultiPolygon" else [poly]
        for gp in geoms:
            if gp.area < 0.005:
                continue
            sol = trimesh.creation.extrude_polygon(gp, height=ph + relief)
            if not sol.is_volume:
                # 内孔与外轮廓零宽接触 -> 微缓冲分离
                gp = gp.buffer(0.02).buffer(-0.02)
                g2 = list(gp.geoms) if gp.geom_type == "MultiPolygon" else [gp]
                for gg in g2:
                    if gg.area < 0.005:
                        continue
                    sol2 = trimesh.creation.extrude_polygon(gg, height=ph + relief)
                    if sol2.is_volume:
                        solids.append(sol2)
                continue
            solids.append(sol)

    union = trimesh.boolean.union(solids, engine="manifold")
    union.process(validate=True)
    print("watertight:", union.is_watertight, "| tris:", len(union.faces), "| extents mm:", np.round(union.extents, 2).tolist())
    if not union.is_watertight:
        raise SystemExit("result not watertight — check input image")
    union.export(args.out)
    print("saved", args.out)


if __name__ == "__main__":
    main()
