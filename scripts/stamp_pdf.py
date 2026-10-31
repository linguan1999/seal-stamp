#!/usr/bin/env python3
"""PDF 盖骑缝章（按页数切条贴右缘）+ 可选最后一页签名整章。
用法: stamp_pdf.py in.pdf stitched.png -o out.pdf --sign-text "乙方：某某公司"
注意: 若输入 PDF 已含骑缝章，重复运行会叠加。"""
import argparse
import os
import tempfile

import cv2
import numpy as np
import pymupdf


def make_transparent(path):
    """白底/透明底印章图 -> BGRA 透明底红章。"""
    img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if img.ndim == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    if img.shape[2] == 3:
        b, g, r = img[..., 0].astype(float), img[..., 1].astype(float), img[..., 2].astype(float)
        lo = np.percentile(np.minimum(g, b), 1)
        ink = np.clip((255 - np.minimum(g, b)) * 255 / max(255 - lo, 1), 0, 255).astype(np.uint8)
        return np.dstack([np.full_like(ink, 23), np.full_like(ink, 32), np.full_like(ink, 219), ink])
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("seal", help="拼合后的完整印章图")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--diameter", type=float, default=42.0, help="印章直径 mm")
    ap.add_argument("--sign-text", default=None, help="最后一页压名盖章的锚点文字")
    args = ap.parse_args()

    seal = make_transparent(args.seal)
    h, w = seal.shape[:2]
    doc = pymupdf.open(args.pdf)
    n = len(doc)
    pt = args.diameter * 72 / 25.4

    # 1) 骑缝章：按页数等分切条，右边缘垂直居中
    for i in range(n):
        page = doc[i]
        x0, x1 = int(i * w / n), int((i + 1) * w / n)
        tmp = os.path.join(tempfile.gettempdir(), f"_seal_strip_{i}.png")
        cv2.imwrite(tmp, seal[:, x0:x1])
        sw = pt * (x1 - x0) / w
        ph = page.rect.height
        rect = pymupdf.Rect(page.rect.width - sw, (ph - pt) / 2, page.rect.width, (ph - pt) / 2 + pt)
        page.insert_image(rect, filename=tmp, keep_proportion=False)
        os.remove(tmp)

    # 2) 签名整章
    if args.sign_text:
        page = doc[-1]
        hits = page.search_for(args.sign_text)
        if not hits:
            raise SystemExit(f"anchor not found on last page: {args.sign_text}")
        r = hits[0]
        cx = (r.x0 + r.x1) / 2
        cy = r.y0 + pt * 0.15
        tmp = os.path.join(tempfile.gettempdir(), "_seal_full.png")
        cv2.imwrite(tmp, seal)
        rect = pymupdf.Rect(cx - pt / 2, cy - pt / 2, cx + pt / 2, cy + pt / 2)
        page.insert_image(rect, filename=tmp, keep_proportion=True, overlay=True)
        os.remove(tmp)

    doc.save(args.out, garbage=3, deflate=True)
    print(f"stamped {n} pages -> {args.out}")


if __name__ == "__main__":
    main()
