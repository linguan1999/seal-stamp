#!/usr/bin/env python3
"""按顺序横向拼合骑缝章条带。用法: stitch_seal.py p1.png p2.png ... -o stitched.png"""
import argparse
import cv2
import numpy as np


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("strips", nargs="+", help="按页码顺序排列的条带图")
    ap.add_argument("-o", "--out", required=True)
    args = ap.parse_args()

    imgs = []
    for p in args.strips:
        im = cv2.imread(p, cv2.IMREAD_UNCHANGED)
        if im is None:
            raise FileNotFoundError(p)
        if im.ndim == 2:
            im = cv2.cvtColor(im, cv2.COLOR_GRAY2BGR)
        imgs.append(im)

    h = max(im.shape[0] for im in imgs)
    w = sum(im.shape[1] for im in imgs)
    canvas = np.full((h, w, imgs[0].shape[2]), 255, imgs[0].dtype)
    x = 0
    for im in imgs:
        canvas[: im.shape[0], x : x + im.shape[1], : im.shape[2]] = im
        x += im.shape[1]
    cv2.imwrite(args.out, canvas)
    print(f"stitched {w}x{h} -> {args.out}")


if __name__ == "__main__":
    main()
