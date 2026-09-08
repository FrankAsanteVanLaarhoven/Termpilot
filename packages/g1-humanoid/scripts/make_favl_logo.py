#!/usr/bin/env python3
"""Build the FAVL neon-tube chest mark that replaces the Unitree nameplate."""

from __future__ import annotations

import math
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "frontend" / "public" / "robot" / "g1" / "assets" / "visuals" / "logo_link.STL"
COLLISION = (
    ROOT / "frontend" / "public" / "robot" / "g1" / "assets" / "collisions" / "logo_link_collision.STL"
)

# Sit on the original Unitree plate: front +X, letters along Y, height in Z.
X_FRONT = 0.0812
Z0 = 0.2578
LETTER_W = 0.022
LETTER_H = 0.028
GAP = 0.0076
RADIUS = 0.00255
RADIAL = 14
HEADER = b"FAVL neon chest mark - TermPilot / Frank Van Laarhoven"


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


def letter_to_world(index: int, u: float, v: float) -> tuple[float, float, float]:
    total = 4 * LETTER_W + 3 * GAP
    y_left = total / 2 - index * (LETTER_W + GAP)
    # Camera looks down -X; screen-left is -Y, so F (index 0) must sit on -Y.
    y = -(y_left - u * LETTER_W)
    z = Z0 + v * LETTER_H
    return (X_FRONT, y, z)


def sample_polyline(points: list[tuple[float, float, float]], spacing: float = 0.0009) -> list[tuple[float, float, float]]:
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


def add_tube(tris: list, path: list[tuple[float, float, float]], radius: float) -> None:
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
    add_sphere(tris, path[0], radius)
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


GLYPHS: list[list[list[tuple[float, float]]]] = [
    # F
    [[(0.08, 0.00), (0.08, 1.00), (0.92, 1.00)], [(0.08, 0.54), (0.72, 0.54)]],
    # A
    [[(0.04, 0.00), (0.50, 1.00), (0.96, 0.00)], [(0.24, 0.38), (0.76, 0.38)]],
    # V
    [[(0.04, 1.00), (0.50, 0.00), (0.96, 1.00)]],
    # L
    [[(0.10, 1.00), (0.10, 0.00), (0.90, 0.00)]],
]


def build_mark() -> list[tuple]:
    tris: list = []
    for index, strokes in enumerate(GLYPHS):
        for stroke in strokes:
            world = [letter_to_world(index, u, v) for u, v in stroke]
            path = sample_polyline(world)
            add_tube(tris, path, RADIUS)
            for point in world:
                add_sphere(tris, point, RADIUS * 1.02)
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


def main() -> None:
    tris = build_mark()
    write_stl(OUT, tris)
    total = 4 * LETTER_W + 3 * GAP
    collision: list = []
    add_box(
        collision,
        (X_FRONT - RADIUS * 2, -total / 2 - RADIUS, Z0 - RADIUS),
        (X_FRONT + RADIUS * 2, total / 2 + RADIUS, Z0 + LETTER_H + RADIUS),
    )
    write_stl(COLLISION, collision, b"FAVL logo collision")
    xs = [p[0] for tri in tris for p in tri]
    ys = [p[1] for tri in tris for p in tri]
    zs = [p[2] for tri in tris for p in tri]
    print(
        f"wrote {OUT} tris={len(tris)} "
        f"x[{min(xs):.4f},{max(xs):.4f}] y[{min(ys):.4f},{max(ys):.4f}] z[{min(zs):.4f},{max(zs):.4f}]"
    )


if __name__ == "__main__":
    main()
