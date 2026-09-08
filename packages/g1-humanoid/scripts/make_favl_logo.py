#!/usr/bin/env python3
"""Build the FAVL neon-tube chest mark that replaces the Unitree nameplate.

The mark is the connected FAVL wordmark: F, a rounded V-valley, an A peak,
then L. Tubes sit in a recessed mid-chest plaque so they read as carved armor,
not a sticker floating off the torso.
"""

from __future__ import annotations

import math
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
VISUALS = ROOT / "frontend" / "public" / "robot" / "g1" / "assets" / "visuals"
OUT = VISUALS / "logo_link.STL"
PLATE = VISUALS / "logo_plate.STL"
COLLISION = (
    ROOT / "frontend" / "public" / "robot" / "g1" / "assets" / "collisions" / "logo_link_collision.STL"
)

# Mid-chest pocket. Chest skin is x≈0.0836; keep the bezel behind that and the
# tubes inside the pocket so the mark is inlaid, not proud of the armor.
CHEST_X = 0.0776
PLATE_BACK = 0.0728
FLOOR_FRONT = 0.0754
BEZEL_BACK = 0.0794
BEZEL_FRONT = 0.0818
Z0 = 0.150
LOGO_W = 0.102
LOGO_H = 0.063
RADIUS = 0.00255
RADIAL = 16
# Belly-button hexagon, lower torso. Carved socket behind the chest skin
# (x≈0.0836); the gem sits in that well so it reads as armor, not a sticker.
MIC_Z = 0.118
WELL_R = 0.022
WELL_BACK = 0.0718
WELL_RIM = 0.0814
MIC_R = 0.0118
MIC_BACK = 0.0742
MIC_FRONT = 0.0806
HEADER = b"FAVL inlaid chest mark - TermPilot / Frank Van Laarhoven"
MIC_OUT = VISUALS / "mic_button.STL"
WELL_OUT = VISUALS / "mic_well.STL"


def _sub(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _add(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _scale(a: tuple[float, float, float], s: float) -> tuple[float, float, float]:
    return (a[0] * s, a[1] * s, a[2] * s)


def _dot(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _norm(a: tuple[float, float, float]) -> tuple[float, float, float]:
    length = math.sqrt(_dot(a, a)) or 1.0
    return _scale(a, 1.0 / length)


def _normal(a: tuple[float, float, float], b: tuple[float, float, float], c: tuple[float, float, float]):
    return _norm(_cross(_sub(b, a), _sub(c, a)))


def uv_to_world(u: float, v: float) -> tuple[float, float, float]:
    """u=0 is screen-left F (URDF -Y). v=0 is the bottom of the mark."""
    y = (u - 0.5) * LOGO_W
    z = Z0 + v * LOGO_H
    return (CHEST_X, y, z)


def sample_polyline(points: list[tuple[float, float, float]], spacing: float = 0.00085) -> list[tuple[float, float, float]]:
    out: list[tuple[float, float, float]] = []
    for start, end in zip(points, points[1:]):
        delta = _sub(end, start)
        length = math.sqrt(_dot(delta, delta))
        steps = max(1, int(math.ceil(length / spacing)))
        for i in range(steps):
            t = i / steps
            out.append(_add(start, _scale(delta, t)))
    out.append(points[-1])
    return out


def arc_yz(
    cy: float,
    cz: float,
    radius: float,
    a0: float,
    a1: float,
    steps: int = 12,
) -> list[tuple[float, float, float]]:
    pts: list[tuple[float, float, float]] = []
    for i in range(steps + 1):
        t = a0 + (a1 - a0) * i / steps
        pts.append((CHEST_X, cy + radius * math.cos(t), cz + radius * math.sin(t)))
    return pts


def orthonormal(direction: tuple[float, float, float]) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    axis = _norm(direction)
    helper = (0.0, 1.0, 0.0) if abs(axis[0]) > 0.9 else (1.0, 0.0, 0.0)
    side = _norm(_cross(axis, helper))
    up = _norm(_cross(axis, side))
    return side, up


def add_sphere(tris: list, center: tuple[float, float, float], radius: float, slices: int = 12, stacks: int = 8) -> None:
    rings: list[list[tuple[float, float, float]]] = []
    for i in range(stacks + 1):
        phi = math.pi * i / stacks
        ring = []
        for j in range(slices):
            theta = 2 * math.pi * j / slices
            x = center[0] + radius * math.sin(phi) * math.cos(theta)
            y = center[1] + radius * math.sin(phi) * math.sin(theta)
            z = center[2] + radius * math.cos(phi)
            ring.append((x, y, z))
        rings.append(ring)
    for i in range(stacks):
        for j in range(slices):
            jn = (j + 1) % slices
            a, b = rings[i][j], rings[i][jn]
            c, d = rings[i + 1][j], rings[i + 1][jn]
            if i:
                tris.append((a, b, c))
            if i + 1 < stacks:
                tris.append((c, b, d))


def add_tube(
    tris: list,
    path: list[tuple[float, float, float]],
    radius: float,
    cap_start: bool = True,
    cap_end: bool = True,
) -> None:
    if len(path) < 2:
        return
    rings: list[list[tuple[float, float, float]]] = []
    for i, point in enumerate(path):
        if i == 0:
            direction = _sub(path[1], point)
        elif i == len(path) - 1:
            direction = _sub(point, path[i - 1])
        else:
            direction = _add(_sub(path[i + 1], point), _sub(point, path[i - 1]))
        side, up = orthonormal(direction)
        ring = []
        for k in range(RADIAL):
            ang = 2 * math.pi * k / RADIAL
            offset = _add(_scale(side, math.cos(ang) * radius), _scale(up, math.sin(ang) * radius))
            ring.append(_add(point, offset))
        rings.append(ring)
    for i in range(len(rings) - 1):
        for k in range(RADIAL):
            kn = (k + 1) % RADIAL
            a, b = rings[i][k], rings[i][kn]
            c, d = rings[i + 1][k], rings[i + 1][kn]
            tris.append((a, b, c))
            tris.append((c, b, d))
    if cap_start:
        add_sphere(tris, path[0], radius)
    if cap_end:
        add_sphere(tris, path[-1], radius)


def add_box(tris: list, min_pt: tuple[float, float, float], max_pt: tuple[float, float, float]) -> None:
    x0, y0, z0 = min_pt
    x1, y1, z1 = max_pt
    v = [
        (x0, y0, z0),
        (x1, y0, z0),
        (x1, y1, z0),
        (x0, y1, z0),
        (x0, y0, z1),
        (x1, y0, z1),
        (x1, y1, z1),
        (x0, y1, z1),
    ]
    faces = [
        (0, 1, 2, 3),
        (4, 7, 6, 5),
        (0, 4, 5, 1),
        (3, 2, 6, 7),
        (0, 3, 7, 4),
        (1, 5, 6, 2),
    ]
    for a, b, c, d in faces:
        tris.append((v[a], v[b], v[c]))
        tris.append((v[a], v[c], v[d]))


def wordmark_paths() -> list[list[tuple[float, float, float]]]:
    """Connected FAVL neon tubes, traced from the brand wordmark.

    Stroke 1: F spine and top bar (rounded Γ).
    Stroke 2: F middle bar into the V-valley, then up to the A peak.
    Stroke 3: L stem and foot.
    """
    r_f = 0.0060
    r_l = 0.0062
    stem_u = 0.018
    mid_v = 0.50
    top_v = 0.97
    bot_v = 0.018
    f_bar_u = 0.338
    l_u = 0.782

    stem = uv_to_world(stem_u, bot_v)
    f_top_end = uv_to_world(f_bar_u, top_v)
    # F top-left: up the stem, quarter-turn into the top bar (increasing Y).
    y_stem = stem[1]
    z_top = f_top_end[2]
    f_arc_c = (y_stem + r_f, z_top - r_f)
    f_spine: list[tuple[float, float, float]] = [
        stem,
        (CHEST_X, y_stem, f_arc_c[1]),
    ]
    f_spine += arc_yz(f_arc_c[0], f_arc_c[1], r_f, math.pi, math.pi / 2, 14)
    f_spine.append(f_top_end)

    # F middle into the V-valley and up the A peak. Points traced from the
    # brand wordmark centerline (neon-tube photograph).
    wave_uv = [
        (stem_u, mid_v),
        (0.18, mid_v),
        (0.30, mid_v),
        (0.345, 0.46),
        (0.375, 0.28),
        (0.400, 0.12),
        (0.425, 0.04),
        (0.448, 0.015),
        (0.470, 0.015),
        (0.492, 0.04),
        (0.518, 0.12),
        (0.545, 0.26),
        (0.575, 0.42),
        (0.608, 0.58),
        (0.642, 0.74),
        (0.675, 0.88),
        (0.700, 0.95),
        (0.722, 0.97),
    ]
    wave = [uv_to_world(u, v) for u, v in wave_uv]

    # L: round cap, down, quarter-turn, foot to the right.
    l_top = uv_to_world(l_u, top_v)
    l_y = l_top[1]
    z_l_bot = uv_to_world(l_u, bot_v)[2]
    l_arc_c = (l_y + r_l, z_l_bot + r_l)
    ell: list[tuple[float, float, float]] = [
        l_top,
        (CHEST_X, l_y, l_arc_c[1]),
    ]
    ell += arc_yz(l_arc_c[0], l_arc_c[1], r_l, math.pi, 1.5 * math.pi, 14)
    ell.append(uv_to_world(0.995, bot_v))
    return [f_spine, wave, ell]


def plate_bounds() -> tuple[float, float, float, float]:
    pad_y, pad_z = 0.010, 0.008
    y0, y1 = -LOGO_W / 2 - pad_y, LOGO_W / 2 + pad_y
    z0, z1 = Z0 - pad_z, Z0 + LOGO_H + pad_z
    return y0, y1, z0, z1


def build_plate() -> list[tuple]:
    """Recessed chest plaque: dark floor + raised bezel, open over the tubes."""
    tris: list = []
    y0, y1, z0, z1 = plate_bounds()
    # Floor of the pocket, behind the tubes.
    add_box(tris, (PLATE_BACK, y0, z0), (FLOOR_FRONT, y1, z1))
    # Inner opening slightly larger than the wordmark so tubes sit in a window.
    inner_y0, inner_y1 = y0 + 0.0048, y1 - 0.0048
    inner_z0, inner_z1 = z0 + 0.0042, z1 - 0.0042
    # Raised bezel frame around the recess.
    add_box(tris, (BEZEL_BACK, y0, z0), (BEZEL_FRONT, y1, inner_z0))
    add_box(tris, (BEZEL_BACK, y0, inner_z1), (BEZEL_FRONT, y1, z1))
    add_box(tris, (BEZEL_BACK, y0, inner_z0), (BEZEL_FRONT, inner_y0, inner_z1))
    add_box(tris, (BEZEL_BACK, inner_y1, inner_z0), (BEZEL_FRONT, y1, inner_z1))
    return tris


def add_hexagon_prism(
    tris: list,
    cx: float,
    cy: float,
    cz: float,
    radius: float,
    x0: float,
    x1: float,
    jewel: bool = False,
) -> None:
    front: list[tuple[float, float, float]] = []
    back: list[tuple[float, float, float]] = []
    for i in range(6):
        ang = math.pi / 6 + i * math.pi / 3
        y = cy + radius * math.cos(ang)
        z = cz + radius * math.sin(ang)
        front.append((x1, y, z))
        back.append((x0, y, z))
    fc, bc = (x1, cy, cz), (x0, cy, cz)
    for i in range(6):
        j = (i + 1) % 6
        tris.append((fc, front[i], front[j]))
        tris.append((bc, back[j], back[i]))
        tris.append((front[i], back[i], back[j]))
        tris.append((front[i], back[j], front[j]))
    if jewel:
        add_sphere(tris, fc, radius * 0.16)


def add_hexagon_ring(
    tris: list,
    cy: float,
    cz: float,
    r_inner: float,
    r_outer: float,
    x0: float,
    x1: float,
) -> None:
    """Raised lip around the navel well, still behind the chest skin."""
    inner: list[tuple[float, float, float]] = []
    outer: list[tuple[float, float, float]] = []
    inner_b: list[tuple[float, float, float]] = []
    outer_b: list[tuple[float, float, float]] = []
    for i in range(6):
        ang = math.pi / 6 + i * math.pi / 3
        c, s = math.cos(ang), math.sin(ang)
        inner.append((x1, cy + r_inner * c, cz + r_inner * s))
        outer.append((x1, cy + r_outer * c, cz + r_outer * s))
        inner_b.append((x0, cy + r_inner * c, cz + r_inner * s))
        outer_b.append((x0, cy + r_outer * c, cz + r_outer * s))
    for i in range(6):
        j = (i + 1) % 6
        tris.append((outer[i], outer[j], inner[j]))
        tris.append((outer[i], inner[j], inner[i]))
        tris.append((outer_b[i], inner_b[i], inner_b[j]))
        tris.append((outer_b[i], inner_b[j], outer_b[j]))
        tris.append((outer[i], outer_b[i], outer_b[j]))
        tris.append((outer[i], outer_b[j], outer[j]))
        tris.append((inner[i], inner[j], inner_b[j]))
        tris.append((inner[i], inner_b[j], inner_b[i]))


def build_letters() -> list[tuple]:
    tris: list = []
    for index, stroke in enumerate(wordmark_paths()):
        path = sample_polyline(stroke)
        # Wave starts inside the F stem; skip that cap so the T-junction fuses.
        add_tube(tris, path, RADIUS, cap_start=index != 1, cap_end=True)
    return tris


def write_stl(path: Path, tris: list, header: bytes = HEADER) -> None:
    blob = bytearray(80)
    blob[: min(80, len(header))] = header[:80]
    blob += struct.pack("<I", len(tris))
    for a, b, c in tris:
        n = _normal(a, b, c)
        blob += struct.pack("<12fH", *n, *a, *b, *c, 0)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(blob)


def write_preview(path: Path, strokes: list[list[tuple[float, float, float]]]) -> None:
    """Orthographic YZ preview (screen-left = -Y) so we can match the wordmark."""
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return
    w, h = 640, 400
    img = Image.new("RGB", (w, h), (4, 10, 18))
    draw = ImageDraw.Draw(img)
    y0, y1, z0, z1 = plate_bounds()
    pad = 0.012
    y0, y1, z0, z1 = y0 - pad, y1 + pad, z0 - pad, z1 + pad

    def xy(pt: tuple[float, float, float]) -> tuple[float, float]:
        # URDF -Y is screen-left, +Z is up.
        px = (pt[1] - y0) / (y1 - y0) * (w - 1)
        py = (z1 - pt[2]) / (z1 - z0) * (h - 1)
        return px, py

    # Pocket outline.
    corners = [
        uv_to_world(-0.02, -0.04),
        uv_to_world(1.02, -0.04),
        uv_to_world(1.02, 1.04),
        uv_to_world(-0.02, 1.04),
    ]
    draw.polygon([xy(p) for p in corners], outline=(20, 48, 62), width=2)
    for stroke in strokes:
        dense = sample_polyline(stroke, 0.0006)
        pts = [xy(p) for p in dense]
        draw.line(pts, fill=(0, 229, 255), width=9)
        draw.line(pts, fill=(180, 250, 255), width=3)
        for cap in (dense[0], dense[-1]):
            cx, cy = xy(cap)
            draw.ellipse((cx - 5, cy - 5, cx + 5, cy + 5), fill=(0, 229, 255))
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)


def main() -> None:
    strokes = wordmark_paths()
    letters = build_letters()
    plate = build_plate()
    write_stl(OUT, letters)
    write_stl(PLATE, plate, b"FAVL chest plaque")
    well: list = []
    add_hexagon_prism(well, (WELL_BACK + WELL_RIM) / 2, 0.0, MIC_Z, WELL_R, WELL_BACK, WELL_RIM - 0.0016, jewel=False)
    add_hexagon_ring(well, 0.0, MIC_Z, MIC_R + 0.0016, WELL_R, WELL_RIM - 0.0018, WELL_RIM)
    write_stl(WELL_OUT, well, b"FAVL chest mic well")
    mic: list = []
    add_hexagon_prism(mic, (MIC_BACK + MIC_FRONT) / 2, 0.0, MIC_Z, MIC_R, MIC_BACK, MIC_FRONT, jewel=True)
    write_stl(MIC_OUT, mic, b"FAVL chest mic hex")
    print(f"mic gem tris={len(mic)} well tris={len(well)}")
    y0, y1, z0, z1 = plate_bounds()
    collision: list = []
    add_box(collision, (PLATE_BACK, y0, z0), (BEZEL_FRONT + RADIUS, y1, z1))
    write_stl(COLLISION, collision, b"FAVL logo collision")
    preview = Path("/tmp/favl_chest_preview.png")
    write_preview(preview, strokes)
    xs = [p[0] for tri in letters for p in tri]
    ys = [p[1] for tri in letters for p in tri]
    zs = [p[2] for tri in letters for p in tri]
    print(
        f"wrote {OUT} tris={len(letters)} plate={len(plate)} "
        f"x[{min(xs):.4f},{max(xs):.4f}] y[{min(ys):.4f},{max(ys):.4f}] z[{min(zs):.4f},{max(zs):.4f}]"
    )
    print(f"preview {preview}")


if __name__ == "__main__":
    main()
