# 印章处理共享库：墨迹提取、轮廓矢量化、多边形构建
import cv2
import numpy as np


def load_ink(path):
    """读取印章图，返回 (ink 0-255 uint8, 主色BGR)。自动判定透明底/白底。"""
    img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if img is None:
        raise FileNotFoundError(path)
    if img.ndim == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGRA)
    if img.shape[2] == 4 and img[..., 3].min() < 250:
        # 透明底：alpha 即墨迹覆盖率
        b, g, r, a = cv2.split(img)
        ink = a
        sel = a > 200
        color = (int(b[sel].mean()), int(g[sel].mean()), int(r[sel].mean())) if sel.any() else (23, 32, 219)
    else:
        # 白底：用颜色解混估计墨迹覆盖率（白->0，墨->255）
        b, g, r = img[..., 0].astype(float), img[..., 1].astype(float), img[..., 2].astype(float)
        gray = np.minimum(g, b) if (r > 150).mean() > 0.5 else np.minimum(np.minimum(g, r), b)
        lo = np.percentile(gray, 1)  # 墨心通道值
        ink = np.clip((255 - gray) * 255 / max(255 - lo, 1), 0, 255).astype(np.uint8)
        sel = ink > 200
        mean = img[..., :3][sel].mean(axis=0).astype(int) if sel.any() else np.array([23, 32, 219])
        color = (int(mean[0]), int(mean[1]), int(mean[2]))
    return ink, color


def trace(ink, close_kernel=None, eps=1.2, min_area=4, scale=2):
    """墨迹图 -> (轮廓列表, hierarchy)。close_kernel 仅在确认存在拼缝断缝时传入 (w,h)。"""
    mask = (ink > 128).astype(np.uint8) * 255
    if close_kernel:
        k = cv2.getStructuringElement(cv2.MORPH_RECT, close_kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k)
    up = cv2.resize(mask, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    up = cv2.GaussianBlur(up, (3, 3), 0)
    _, bw = cv2.threshold(up, 127, 255, cv2.THRESH_BINARY)
    contours, hier = cv2.findContours(bw.astype(np.uint8), cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    return contours, hier[0], eps, min_area, scale


def contours_to_polys(contours, hier, eps=1.2, min_area=4, scale=2):
    """层级轮廓 -> [(outer Nx2, [holes...])]，坐标已除以 scale 回到原图尺度。"""
    polys = []
    for i, c in enumerate(contours):
        if hier[i][3] != -1 or cv2.contourArea(c) < min_area:
            continue
        outer = cv2.approxPolyDP(c, eps, True).reshape(-1, 2).astype(float) / scale
        holes, j = [], hier[i][2]
        while j != -1:
            if cv2.contourArea(contours[j]) >= min_area:
                holes.append(cv2.approxPolyDP(contours[j], eps, True).reshape(-1, 2).astype(float) / scale)
            j = hier[j][0]
        polys.append((outer, holes))
    return polys


def dedup(ring, eps=1e-6):
    keep = [ring[0]]
    for p in ring[1:]:
        if np.abs(p - keep[-1]).max() > eps:
            keep.append(p)
    if len(keep) > 1 and np.abs(keep[0] - keep[-1]).max() <= eps:
        keep.pop()
    return np.array(keep)


def hex_color(color_bgr):
    b, g, r = color_bgr
    return "#%02X%02X%02X" % (r, g, b)
