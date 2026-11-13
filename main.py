#!/usr/bin/env python3
"""Baleen Cathedral.

A frontal whale skull fills the frame and is cropped by it. The mouth is a
flooded nave: a rose window of gold, amber, wine and teal burns in the throat,
umber baleen plates hang on either side, and a sailboat on the black water
gives the skull its scale. Cool light rims the melon. Every warm highlight
comes from the window.

Python 3.13, standard library only. Fully deterministic.
"""

import math
import os
import struct
import sys
import time
import zlib

W = H = 1024
CX = 512.0
WIN_Y = 470.0
WIN_R = 124.0
WATER_Y = 706.0
BOAT_X = 386.0
BOAT_Y = 706.0

# Folded around the vertical: index 0 is the top pane, the last is the bottom.
OUTER = (
    (1.00, 0.88, 0.48),
    (0.98, 0.56, 0.12),
    (0.66, 0.10, 0.13),
    (0.14, 0.64, 0.60),
    (0.92, 0.50, 0.12),
    (1.00, 0.74, 0.32),
    (1.00, 0.80, 0.40),
)
INNER = (
    (1.00, 0.94, 0.70),
    (1.00, 0.68, 0.26),
    (0.20, 0.72, 0.66),
    (0.78, 0.24, 0.12),
    (1.00, 0.82, 0.42),
)
LEAD = (0.045, 0.028, 0.022)

EYES = (
    (246.0, 224.0, 56.0, 29.0),
    (778.0, 224.0, 56.0, 29.0),
)


def clamp(v, lo, hi):
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v


def lerp(a, b, t):
    return a + (b - a) * t


def mix(c0, c1, t):
    return (lerp(c0[0], c1[0], t), lerp(c0[1], c1[1], t), lerp(c0[2], c1[2], t))


def smoother(edge0, edge1, x):
    if edge0 == edge1:
        return 1.0 if x >= edge1 else 0.0
    t = (x - edge0) / (edge1 - edge0)
    t = clamp(t, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def hash2(ix, iy):
    n = (ix * 374761393 + iy * 668265263 + 1442695041) & 0xFFFFFFFF
    n = (n ^ (n >> 13)) * 1274126177 & 0xFFFFFFFF
    n = (n ^ (n >> 16)) & 0xFFFFFF
    return n / 16777215.0


def noise(x, y, scale):
    xs = x / scale
    ys = y / scale
    xi = math.floor(xs)
    yi = math.floor(ys)
    xf = xs - xi
    yf = ys - yi
    sx = xf * xf * (3.0 - 2.0 * xf)
    sy = yf * yf * (3.0 - 2.0 * yf)
    n00 = hash2(xi, yi)
    n10 = hash2(xi + 1, yi)
    n01 = hash2(xi, yi + 1)
    n11 = hash2(xi + 1, yi + 1)
    return lerp(lerp(n00, n10, sx), lerp(n01, n11, sx), sy)


def dome_top(x):
    """Broad melon. The crown is the only outer contour; the flanks run off the frame."""
    nx = abs(x - CX) / 512.0
    return 58.0 + 176.0 * (nx ** 2.15)


def dome_slope(x):
    nx = abs(x - CX) / 512.0
    if nx < 1e-4:
        return 0.0
    return (176.0 * 2.15 * (nx ** 1.15)) / 512.0


def roof_y(x):
    u = (x - CX) / 408.0
    return 300.0 + 214.0 * u * u


def mouth_half(y):
    t = (y - 548.0) / 470.0
    return 436.0 - 64.0 * t * t


def chin_y(x):
    nx = abs(x - CX) / 520.0
    if nx > 1.0:
        nx = 1.0
    # Wide U, a whale jaw rather than a pointed shield.
    return 1012.0 - 176.0 * (nx ** 1.7)


def halo(x, y):
    dx = x - CX
    dy = y - WIN_Y
    return math.exp(-(dx * dx + dy * dy) / (2.0 * 176.0 * 176.0))


def sea(x, y):
    t = clamp(y / (H - 1), 0.0, 1.0)
    r = lerp(0.010, 0.018, t)
    g = lerp(0.018, 0.026, t)
    b = lerp(0.048, 0.058, t)
    nx = (x - CX) / 512.0
    ny = (y - 420.0) / 620.0
    vig = clamp(1.0 - 0.70 * (nx * nx + 0.55 * ny * ny), 0.0, 1.0)
    return (r * vig, g * vig, b * vig)


def _fold(i, n):
    i %= n
    half = n // 2
    return i if i <= half else n - i


def _pane(col, x, y, ang, ring_r, pane_r, color):
    pcx = CX + math.sin(ang) * ring_r
    pcy = WIN_Y - math.cos(ang) * ring_r
    if abs(x - pcx) > pane_r + 2.0 or abs(y - pcy) > pane_r + 2.0:
        return col
    d = math.hypot(x - pcx, y - pcy)
    if d > pane_r + 1.5:
        return col
    cov = smoother(pane_r + 1.35, pane_r - 0.7, d)
    # Backlit glass: nearly even, a little hotter toward the middle. Not a sphere.
    glow = 0.78 + 0.22 * clamp(1.0 - d / pane_r, 0.0, 1.0)
    pane = (
        clamp(color[0] * glow, 0.0, 1.0),
        clamp(color[1] * glow, 0.0, 1.0),
        clamp(color[2] * glow, 0.0, 1.0),
    )
    if d > pane_r - 2.3:
        pane = mix(pane, LEAD, smoother(pane_r - 2.3, pane_r - 0.15, d))
    return mix(col, pane, cov)


def window_color(x, y):
    """Rose window as jewels set in lead, not a color wheel. None outside the disk."""
    dx = x - CX
    dy = y - WIN_Y
    r = math.hypot(dx, dy)
    if r >= WIN_R:
        return None
    if r > WIN_R - 13.5:
        lip = smoother(WIN_R - 13.5, WIN_R - 10.0, r) * (1.0 - smoother(WIN_R - 6.4, WIN_R - 3.6, r))
        return mix((0.16, 0.11, 0.07), (1.0, 0.86, 0.52), lip)

    # Dark amber ground so the gaps read as glass, not holes.
    ground = 0.055 + 0.04 * (1.0 - r / WIN_R)
    col = (ground * 1.55, ground * 0.72, ground * 0.30)
    stone = (0.78, 0.62, 0.38)
    for ring_r, width in ((33.5, 3.3), (68.0, 3.5)):
        d = abs(r - ring_r)
        if d < width:
            col = mix(col, stone, smoother(width, 0.7, d))
    for i in range(8):
        ang = i * (math.tau / 8.0)
        col = _pane(col, x, y, ang, 49.0, 15.0, INNER[_fold(i, 8)])
    for i in range(12):
        ang = i * (math.tau / 12.0)
        col = _pane(col, x, y, ang, 90.0, 19.0, OUTER[_fold(i, 12)])

    if r < 36.0:
        core = mix((1.0, 0.74, 0.34), (1.0, 0.99, 0.97), clamp(1.0 - r / 26.0, 0.0, 1.0) ** 0.55)
        col = mix(col, core, smoother(35.5, 23.0, r))
    return col


def plate_field(x, y):
    """Wide umber baleen plates. Coverage plus color, or (0, None)."""
    if y < 280.0 or y > WATER_Y - 8.0:
        return 0.0, None
    bow = math.sin(clamp((y - 310.0) / 400.0, 0.0, 1.0) * math.pi) * 8.0
    sign = 1.0 if x >= CX else -1.0
    xb = x - sign * bow
    ax = abs(xb - CX)
    inner = 158.0
    pitch = 26.0
    count = 9
    outer = inner + (count - 1) * pitch
    if ax < inner - 4.0 or ax > outer + 10.0:
        return 0.0, None
    i = int((ax - inner) / pitch + 0.5)
    if i < 0 or i >= count:
        return 0.0, None
    attach = inner + i * pitch
    local = ax - attach
    span = (attach - inner) / (outer - inner)
    top = roof_y(xb) - 1.0
    bottom = min(WATER_Y - 22.0, top + lerp(250.0, 320.0, span ** 0.9))
    if y < top - 2.0 or y > bottom + 12.0:
        return 0.0, None
    t = clamp((y - top) / max(bottom - top, 1.0), 0.0, 1.0)
    half = lerp(10.4, 5.6, t)
    cov = smoother(half + 1.9, half - 1.0, abs(local))
    cov *= smoother(top - 1.6, top + 1.4, y)
    cov *= smoother(bottom + 2.2, bottom - 2.2, y)
    # Clear the stone so the window stays a disk.
    rd = math.hypot(x - CX, y - WIN_Y)
    cov *= smoother(WIN_R + 8.0, WIN_R + 18.0, rd)
    if cov <= 0.0:
        return 0.0, None

    light = halo(x, y)
    face = 0.82 + 0.18 * math.exp(-((y - WIN_Y) / 170.0) ** 2)
    body = (
        (0.24 + 0.14 * light) * face,
        (0.15 + 0.08 * light) * face,
        (0.08 + 0.035 * light) * face,
    )
    # Inner lip faces the window (negative local, toward the centerline).
    lip = smoother(half - 3.6, half - 0.7, -local)
    col = mix(body, (0.98, 0.78, 0.42), lip * (0.55 + 0.45 * light))
    if local > half - 1.6:
        col = mix(col, (0.03, 0.018, 0.016), smoother(half - 1.6, half - 0.2, local))
    if t < 0.05:
        col = mix(col, (0.66, 0.50, 0.32), (0.05 - t) / 0.05 * 0.45)
    if t > 0.88:
        col = mix(col, (0.78, 0.64, 0.42), (t - 0.88) / 0.12 * 0.55)
    return cov, col


def eye_color(x, y, bone):
    col = bone
    for ex, ey, rx, ry in EYES:
        if abs(x - ex) > rx + 18.0 or abs(y - ey) > ry + 16.0:
            continue
        nx = (x - ex) / rx
        ny = (y - ey) / ry
        p = math.hypot(nx, ny)
        radial = math.hypot(rx * nx, ry * ny) / max(p, 1e-6)
        dist = (1.0 - p) * radial
        sock = math.hypot((x - ex) / (rx + 22.0), (y - ey) / (ry + 16.0))
        if sock < 1.0:
            shade = (1.0 - sock) ** 1.2 * 0.42
            col = (col[0] * (1.0 - shade), col[1] * (1.0 - shade), col[2] * (1.0 - shade))
        if dist < -2.2:
            continue
        cov = smoother(-1.35, 1.15, dist)
        if cov <= 0.0:
            continue
        lid = smoother(0.05, -0.9, ny)
        globe = (0.010 + 0.012 * (1.0 - lid), 0.014 + 0.016 * (1.0 - lid), 0.026)
        if ny > 0.55 and abs(dist) < 3.2:
            wet = smoother(0.55, 0.88, ny) * smoother(3.2, 0.5, abs(dist))
            globe = mix(globe, (0.50, 0.58, 0.62), wet * 0.40)
        toward = 1.0 if ex < CX else -1.0
        d1 = math.hypot(x - (ex + toward * rx * 0.20), y - (ey + ry * 0.32))
        d2 = math.hypot(x - (ex - toward * rx * 0.32), y - (ey - ry * 0.36))
        if d1 < 4.6:
            globe = mix(globe, (1.0, 0.93, 0.80), smoother(4.6, 1.3, d1))
        if d2 < 2.8:
            globe = mix(globe, (0.78, 0.90, 0.96), smoother(2.8, 0.7, d2))
        col = mix(col, globe, cov)
    return col


def bone_color(x, y):
    h = halo(x, y)
    amb = math.exp(-((x - CX) ** 2) / (2.0 * 240.0 * 240.0) - ((y - 128.0) ** 2) / (2.0 * 96.0 * 96.0))
    n = 0.95 + 0.05 * noise(x, y, 140.0)
    pore = (noise(x, y, 52.0) - 0.5) * 0.030
    flank = clamp(abs(x - CX) / 512.0, 0.0, 1.0)
    turn = 1.0 - 0.38 * (flank ** 1.35)
    r = (0.20 + 0.48 * amb + 0.34 * h + pore) * n * turn
    g = (0.15 + 0.36 * amb + 0.22 * h + pore * 0.85) * n * turn
    b = (0.11 + 0.24 * amb + 0.09 * h + pore * 0.6) * n * turn
    # Two melon lobes and a thin frontal suture between them.
    for s in (-1.0, 1.0):
        lob = math.exp(-((x - (CX + s * 72.0)) ** 2) / (2.0 * 78.0 * 78.0) - ((y - 142.0) ** 2) / (2.0 * 58.0 * 58.0))
        r += 0.06 * lob
        g += 0.045 * lob
        b += 0.028 * lob
    if 78.0 < y < 286.0:
        fade = smoother(286.0, 230.0, y) * smoother(78.0, 120.0, y)
        s = abs(x - CX)
        if s < 2.4:
            k = 0.40 * fade * (1.0 - s / 2.4)
            r = r * (1.0 - k) + 0.05 * k
            g = g * (1.0 - k) + 0.04 * k
            b = b * (1.0 - k) + 0.03 * k
    # Brow ridge over each eye.
    for ex, ey, rx, ry in EYES:
        dxe = (x - ex) / (rx * 1.08)
        if abs(dxe) < 1.05 and y < ey:
            ridge = ey - ry - 6.0 - 9.0 * (1.0 - dxe * dxe)
            d = abs(y - ridge)
            if d < 6.5:
                k = (1.0 - d / 6.5) * (1.0 - abs(dxe) / 1.05) * 0.34
                r += 0.18 * k
                g += 0.13 * k
                b += 0.07 * k
    return (clamp(r, 0.0, 1.0), clamp(g, 0.0, 1.0), clamp(b, 0.0, 1.0))


def apply_bone_rims(x, y, col, dist_out):
    if 0.0 <= dist_out < 5.2:
        t = (1.0 - dist_out / 5.2) ** 1.55
        col = mix(col, (0.82, 0.94, 0.99), t * 0.96)
    d_palate = roof_y(x) - y
    if 0.0 <= d_palate < 8.0:
        t = (1.0 - d_palate / 8.0) ** 1.05
        col = mix(col, (1.0, 0.76, 0.42), t * (0.55 + 0.45 * halo(x, y)))
    d_chin = y - chin_y(x)
    if 0.0 <= d_chin < 7.5:
        t = (1.0 - d_chin / 7.5) ** 1.1
        col = mix(col, (0.96, 0.72, 0.38), t * (0.42 + 0.58 * halo(x, y)))
    d_cheek = mouth_half(y) - abs(x - CX)
    if 0.0 <= d_cheek < 6.5 and roof_y(x) < y < chin_y(x):
        t = 1.0 - d_cheek / 6.5
        col = mix(col, (0.94, 0.68, 0.34), t * 0.80 * halo(x, y))
    return col


def boat(x, y):
    """Sailboat. Returns (color, coverage). Coverage 0 when the pixel misses."""
    bx = x - BOAT_X
    by = y - BOAT_Y
    if bx < -42.0 or bx > 52.0 or by < -118.0 or by > 26.0:
        return None, 0.0
    col = (0.0, 0.0, 0.0)
    cov = 0.0
    # Hull sits on the waterline: visible wood, a gold gunwale, a small lantern.
    if -1.2 <= by <= 20.0 and abs(bx) < 40.0:
        t = clamp(by / 18.0, 0.0, 1.0)
        half = 36.0 * (1.0 - t ** 0.58)
        d = min(half - abs(bx), 18.0 - by)
        c = smoother(-1.5, 1.2, d) * smoother(-1.1, 0.7, by + 0.3)
        if c > 0.0:
            hull = (0.36, 0.16, 0.07)
            if by < 2.8:
                hull = mix((0.96, 0.76, 0.38), hull, clamp(by / 2.8, 0.0, 1.0))
            hull = mix(hull, (0.10, 0.045, 0.025), clamp((by - 8.0) / 10.0, 0.0, 1.0) * 0.55)
            ld = math.hypot(bx - 15.0, by - 8.0)
            if ld < 2.2:
                hull = (1.0, 0.50, 0.16)
            elif ld < 7.0:
                hull = mix(hull, (1.0, 0.55, 0.20), smoother(7.0, 2.2, ld) * 0.40)
            col, cov = hull, c
    # Mast.
    if -104.0 <= by <= 1.2 and abs(bx) <= 2.2:
        c = smoother(2.2, 0.35, abs(bx))
        if c > cov:
            col, cov = (0.08, 0.05, 0.035), c
    # Sail, lit on the side that faces the window. It ends above the waterline.
    y0, y1 = -104.0, -3.0
    if y0 - 2.0 <= by <= y1 + 2.0 and -2.0 <= bx <= 46.0:
        t = clamp((by - y0) / (y1 - y0), 0.0, 1.0)
        reach = 1.6 + 39.0 * t
        d = min(reach - bx, bx - 0.6, by - y0, y1 - by)
        c = smoother(-1.55, 1.15, d)
        if c > 0.0:
            facing = 0.74 + 0.26 * clamp(bx / 39.0, 0.0, 1.0)
            facing *= 0.90 + 0.10 * (1.0 - t)
            if abs(by + 48.0) < 0.85:
                facing *= 0.86
            sail = (0.99 * facing, 0.91 * facing, 0.70 * facing)
            if c > cov:
                col, cov = sail, c
    return (col if cov > 0.0 else None), cov


def outline_dist(x, y):
    top = dome_top(x)
    slope = dome_slope(x)
    return (y - top) / math.sqrt(1.0 + slope * slope), top


def surface(x, y):
    """Sea, skull, mouth, baleen and window. No water and no boat."""
    if y < -4.0 or y > H + 4.0 or x < -4.0 or x > W + 4.0:
        return sea(clamp(x, 0.0, W - 1.0), clamp(y, 0.0, H - 1.0))
    dist_out, top = outline_dist(x, y)
    if dist_out <= -1.8:
        return sea(x, y)

    ry = roof_y(x)
    cy = chin_y(x)
    in_mouth = (y >= ry) and (y <= cy) and (abs(x - CX) <= mouth_half(y) + 1.5)
    if in_mouth:
        h = halo(x, y)
        col = (0.020 + 0.055 * h, 0.009 + 0.028 * h, 0.012 + 0.014 * h)
        dx = x - CX
        dy = y - WIN_Y
        rr = math.hypot(dx, dy)
        if y > WIN_Y and abs(dx) < 150.0:
            halfw = 18.0 + (y - WIN_Y) * 0.042
            shaft = math.exp(-(dx / halfw) ** 2)
            fall = math.exp(-(y - WIN_Y) / 360.0)
            col = mix(col, (1.0, 0.78, 0.42), shaft * fall * 0.50)
        if rr > WIN_R and abs(dx) < 140.0:
            up = math.atan2(dx, -dy)
            ray = (0.5 + 0.5 * math.cos(up * 12.0)) ** 8
            ray *= math.exp(-(rr - WIN_R) / 240.0)
            col = mix(col, (1.0, 0.82, 0.50), ray * 0.07)
        pcov, pcol = plate_field(x, y)
        if pcov > 0.0:
            col = mix(col, pcol, pcov)
        wc = window_color(x, y)
        if wc is not None:
            wc_cov = smoother(WIN_R + 1.15, WIN_R - 1.25, rr)
            col = mix(col, wc, wc_cov)
        elif rr < WIN_R + 32.0:
            glow = smoother(WIN_R + 32.0, WIN_R + 1.0, rr)
            col = mix(col, (1.0, 0.80, 0.46), glow * 0.42)
    else:
        col = bone_color(x, y)
        col = apply_bone_rims(x, y, col, dist_out)
        col = eye_color(x, y, col)

    if dist_out < 2.4:
        col = mix(sea(x, y), col, smoother(-1.45, 1.45, dist_out))
    return col


def water_color(x, y):
    depth = (y - WATER_Y) / 280.0
    wob = math.sin(x * 0.040 + y * 0.105) * 5.2 + math.sin(x * 0.015 - y * 0.046) * 2.0
    sx = x + math.sin(y * 0.052) * 3.2
    sy = (WATER_Y - (y - WATER_Y)) + wob
    if sy > WATER_Y - 3.0:
        sy = WATER_Y - 3.0
    reflected = surface(sx, sy)
    fade = math.exp(-depth * 1.05)
    ref = (reflected[0] * 0.40 * fade, reflected[1] * 0.50 * fade, reflected[2] * 0.62 * fade)
    rip = math.sin(y * 0.62 + math.sin(x * 0.021) * 2.0)
    col = (
        clamp(0.010 + ref[0], 0.0, 1.0),
        clamp(0.018 + ref[1], 0.0, 1.0),
        clamp(0.038 + 0.010 * (0.5 + 0.5 * rip) + ref[2], 0.0, 1.0),
    )
    halfw = 18.0 + (y - WIN_Y) * 0.042
    shaft = math.exp(-((x - CX) / halfw) ** 2) * math.exp(-(y - WATER_Y) / 210.0)
    col = mix(col, (0.90, 0.66, 0.32), shaft * 0.38)
    sh = ((x - BOAT_X) / 40.0) ** 2 + ((y - (BOAT_Y + 14.0)) / 8.0) ** 2
    if sh < 1.0:
        col = mix(col, (0.003, 0.005, 0.010), (1.0 - sh) * 0.60)
    bx = x - BOAT_X + math.sin(y * 0.14) * 1.3
    by = y - (BOAT_Y + 16.0)
    if 0.0 <= by <= 48.0 and 0.0 <= bx <= 34.0:
        reach = 32.0 * (by / 48.0)
        if bx < reach:
            a = 0.28 * (1.0 - by / 48.0) * smoother(reach + 0.2, reach - 1.2, bx)
            col = mix(col, (0.75, 0.62, 0.42), a)
    return col


def shade(x, y):
    dist_out, top = outline_dist(x, y)
    ry = roof_y(x)
    cy = chin_y(x)
    in_mouth = dist_out > -1.2 and (y >= ry) and (y <= cy + 2.0) and (abs(x - CX) <= mouth_half(y) + 2.0)
    if in_mouth and y >= WATER_Y - 1.6 and y < cy:
        water_cov = smoother(WATER_Y - 1.5, WATER_Y + 1.15, y)
        jaw_cov = smoother(cy - 1.15, cy + 1.35, y)
        col = mix(surface(x, y), water_color(x, y), water_cov * (1.0 - jaw_cov))
        if jaw_cov > 0.0:
            bone = apply_bone_rims(x, y, bone_color(x, y), max(dist_out, 4.0))
            col = mix(col, bone, jaw_cov)
    else:
        col = surface(x, y)

    dline = abs(y - WATER_Y)
    if dline < 2.0 and in_mouth and y < cy - 6.0:
        shine = math.exp(-((x - CX) / 210.0) ** 2)
        col = mix(col, (1.0, 0.88, 0.58), (1.0 - dline / 2.0) * shine * 0.70)

    bcol, bcov = boat(x, y)
    if bcov > 0.0:
        col = mix(col, bcol, bcov)
    return col


def encode(v):
    return int(clamp(v, 0.0, 1.0) * 255.0 + 0.5)


def render():
    img = bytearray(W * H * 3)
    mv = memoryview(img)
    i = 0
    for y in range(H):
        yy = float(y)
        for x in range(W):
            r, g, b = shade(float(x), yy)
            mv[i] = encode(r)
            mv[i + 1] = encode(g)
            mv[i + 2] = encode(b)
            i += 3
    return img


def _chunk(tag, data):
    crc = zlib.crc32(tag)
    crc = zlib.crc32(data, crc) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)


def write_png(path, img):
    raw = bytearray()
    stride = W * 3
    for y in range(H):
        raw.append(0)
        raw.extend(img[y * stride:(y + 1) * stride])
    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + _chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)
    return len(png)


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "entry.png")
    t0 = time.perf_counter()
    img = render()
    size = write_png(path, img)
    dt = time.perf_counter() - t0
    print(f"wrote {path} {W}x{H} {size} bytes in {dt:.2f}s", file=sys.stderr)


if __name__ == "__main__":
    main()
