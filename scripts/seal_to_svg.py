#!/usr/bin/env python3
"""印章图矢量化为 SVG。用法: seal_to_svg.py stitched.png -o seal.svg [--close 7,3]"""
import argparse
import sys

import seal_lib as L


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--close", default=None, help="形态学闭运算核 w,h，仅在确认有拼缝断缝时使用")
    ap.add_argument("--color", default=None, help="覆盖主色，如 #DB2017")
    args = ap.parse_args()

    ink, color = L.load_ink(args.image)
    ck = tuple(int(v) for v in args.close.split(",")) if args.close else None
    contours, hier, eps, min_area, scale = L.trace(ink, close_kernel=ck)
    polys = L.contours_to_polys(contours, hier, eps, min_area, scale)

    paths = []
    for outer, holes in polys:
        for ring in [outer] + holes:
            paths.append("M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in ring) + " Z")

    h, w = ink.shape
    col = args.color or L.hex_color(color)
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">\n'
        f'<path fill="{col}" fill-rule="evenodd" d="{"".join(paths)}"/>\n</svg>'
    )
    open(args.out, "w").write(svg)
    print(f"{len(polys)} polygons, color {col} -> {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
