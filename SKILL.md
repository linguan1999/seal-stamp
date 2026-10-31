---
name: seal-stamp
description: 中文印章全流程——骑缝章条带拼合、印章矢量化为SVG、生成3D打印STL印模、PDF盖骑缝章与签名整章。当用户要求提取/拼合骑缝章、印章转SVG、做印章STL、给合同PDF盖章时使用。不处理语音修复或重新作曲。
---

# Seal Stamp 印章工作流

从合同 PDF 的骑缝章条带图出发，完成拼合、矢量化、STL 印模、PDF 盖章四类任务。

## 依赖

```bash
pip install opencv-python-headless numpy shapely trimesh mapbox_earcut manifold3d pymupdf
```

macOS 上 `.doc → .pdf` 用 Pages AppleScript（无需安装任何东西）。

## 核心经验（务必遵守）

1. **背景判定**：条带 PNG 可能带 alpha（透明底）或不透明白底。用 `alpha.max()==255 且四角为白` 判定白底，白底时改用颜色提取墨迹：`ink = clip((255 - min(g,b)) * 255/(255 - min_ink_channel))`，阈值 128。
2. **禁止全局形态学闭运算**：闭运算会填死密笔画汉字（如"播""鑫"）1–2px 的笔画间隙，造成粘连色块。先逐列检测拼缝处是否真有断缝（左右2px为墨、缝心为白的行数），多数提取工具输出的条带衔接处无断缝，直接拼合即可。
3. **矢量化参数**：mask → 2x INTER_CUBIC 上采样 → GaussianBlur(3,3) → threshold 127 → `findContours(RETR_CCOMP)` → `approxPolyDP(1.2)`，面积 <4 的轮廓丢弃。SVG 用单 path + `fill-rule="evenodd"`。
4. **STL 镜像方向**：印模顶视图必须是"左右镜像 + 文字正立"（只对 X 做 `cx - x`，Y 保持图像方向）。同时翻转 X 和 Y 等于旋转 180°，是错的。
5. **STL 水密修复**：复杂汉字的内孔与外轮廓存在零宽接触，挤出体不水密。对非法实体做 `polygon.buffer(0.02).buffer(-0.02)` 分离接触环后再挤出。布尔合并用 `trimesh.boolean.union(engine="manifold")`。
6. **盖章尺寸**：企业合同章/公章外径 42mm（也有 45mm），骑缝章按页数等分圆章、每页右边缘垂直居中贴一条；签名整章用 `page.search_for("乙方：…")` 定位，章心压在公司名称行上（压名盖章）。

## 脚本

均位于 `scripts/`，共享 `seal_lib.py`。

### 1. 拼合骑缝章条带

```bash
python scripts/stitch_seal.py 第1页.png 第2页.png ... 第N页.png -o stitched.png
```
按给定顺序横向拼接（顺序即页码顺序，拼错页序章就碎了）。

### 2. 拼合图 → SVG

```bash
python scripts/seal_to_svg.py stitched.png -o seal.svg
```
自动判定 alpha/白底，输出主色自动取墨迹均值（典型红为 `#DB2017`）。
验证：渲染后放大检查"播"类密笔画字无粘连、圆环无断口。

### 3. 拼合图 → STL 印模（3D 打印）

```bash
python scripts/seal_to_stl.py stitched.png -o seal.stl --diameter 42 --plate-h 3 --relief 1.2
```
输出水密实体：底板 Ø(直径+3)mm、浮雕高出板面 relief mm。打印建议 SLA/DLP 树脂。

### 4. PDF 盖骑缝章（+可选签名整章）

```bash
python scripts/stamp_pdf.py input.pdf stitched.png -o out.pdf \
    --diameter 42 --sign-text "乙方：深圳市元映文化传播有限公司"
```
- 骑缝章：圆章按页数等分切条，每页右边缘垂直居中。
- `--sign-text` 给出时在最后一页该文字处压名盖整章（可省略）。

### 5. .doc → .pdf（macOS Pages）

```bash
python scripts/doc2pdf.py input.doc output.pdf
```
AppleScript 驱动 Pages 导出；首次运行需在弹窗中允许自动化权限。

## 标准流程示例

用户给了 5 张骑缝章条带 PNG：

```bash
python scripts/stitch_seal.py p1.png p2.png p3.png p4.png p5.png -o stitched.png
python scripts/seal_to_svg.py stitched.png -o seal.svg
python scripts/seal_to_stl.py stitched.png -o seal_42mm.stl --diameter 42
python scripts/doc2pdf.py contract.doc contract.pdf
python scripts/stamp_pdf.py contract.pdf stitched.png -o contract_盖章.pdf --sign-text "乙方：某某公司"
```

## 验证清单

- SVG：pymupdf 渲染后目检圆环连续、文字无粘连、编号完整。
- STL：`is_watertight == True`；投影顶面三角确认镜像方向（文字左右翻、正立）。
- PDF：渲染签署区与边缘条带目检位置。
