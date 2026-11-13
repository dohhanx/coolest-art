#!/usr/bin/env python3
"""The nave inside a whale.

A skull fills the frame and is cut off by it. Cold light traces the melon.
Warm light comes only from a lamp of round glass set in the throat. Baleen
hangs beside that lamp, black water keeps its echo, and a single hull gives
the skull a scale. Python standard library, fixed arithmetic, no clock in
the pixels.
"""

import math
import os
import struct
import sys
import zlib

SIDE = 1024
MID = 512.0
LAMP_Y = 466.0
LAMP_R = 120.0
TIDE = 702.0
HULL_X = 374.0
HULL_Y = 702.0

# Slot zero sits at the top of the lamp. Later slots fold across the vertical.
OUTER_GLASS = (
    (1.00, 0.86, 0.46),
    (0.97, 0.52, 0.11),
    (0.64, 0.11, 0.14),
    (0.16, 0.62, 0.58),
    (0.90, 0.48, 0.13),
    (0.98, 0.72, 0.34),
    (1.00, 0.78, 0.42),
)
INNER_GLASS = (
    (1.00, 0.92, 0.66),
    (0.98, 0.64, 0.24),
    (0.22, 0.70, 0.64),
    (0.76, 0.26, 0.13),
    (1.00, 0.80, 0.44),
)
GAZE = (
    (242.0, 226.0, 54.0, 28.0),
    (782.0, 226.0, 54.0, 28.0),
)


def bound(v, lo, hi):
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v


def span(a, b, t):
    return a * (1.0 - t) + b * t


def fuse(p, q, t):
    return (span(p[0], q[0], t), span(p[1], q[1], t), span(p[2], q[2], t))


def ramp(a, b, x):
    if a == b:
        return 1.0 if x >= b else 0.0
    u = (x - a) / (b - a)
    u = bound(u, 0.0, 1.0)
    return u * u * (3.0 - 2.0 * u)


def lattice(ix, iy):
    n = (ix * 198491317 + iy * 6542989 + 1013904223) & 0xFFFFFFFF
    n = (n ^ (n >> 13)) * 747796405 & 0xFFFFFFFF
    n = (n ^ (n >> 16)) & 0xFFFFFF
    return n / 16777215.0


def mottled(x, y, grain):
    xs = x / grain
    ys = y / grain
    xi = math.floor(xs)
    yi = math.floor(ys)
    xf = xs - xi
    yf = ys - yi
    sx = xf * xf * (3.0 - 2.0 * xf)
    sy = yf * yf * (3.0 - 2.0 * yf)
    n00 = lattice(xi, yi)
    n10 = lattice(xi + 1, yi)
    n01 = lattice(xi, yi + 1)
    n11 = lattice(xi + 1, yi + 1)
    return span(span(n00, n10, sx), span(n01, n11, sx), sy)


def crown(x):
    """Low wide melon. Only this curve meets the night; the cheeks run off the frame."""
    nx = abs(x - MID) / float(SIDE)
    return 62.0 + 186.0 * (nx ** 2.18)


def crown_slope(x):
    nx = abs(x - MID) / float(SIDE)
    if nx < 1e-5:
        return 0.0
    return (186.0 * 2.18 * (nx ** 1.18)) / float(SIDE)


def palate(x):
    u = (x - MID) / 404.0
    return 304.0 + 206.0 * u * u


def jaw(x):
    nx = abs(x - MID) / 516.0
    if nx > 1.0:
        nx = 1.0
    return 1010.0 - 168.0 * (nx ** 1.72)


def mouth_reach(y):
    t = (y - 546.0) / 468.0
    return 432.0 - 60.0 * t * t


def lamp_falloff(x, y):
    dx = x - MID
    dy = y - LAMP_Y
    return math.exp(-(dx * dx + dy * dy) / (2.0 * 172.0 * 172.0))


def ink(x, y):
    t = bound(y / (SIDE - 1), 0.0, 1.0)
    r = span(0.009, 0.017, t)
    g = span(0.016, 0.024, t)
    b = span(0.046, 0.056, t)
    nx = (x - MID) / 512.0
    ny = (y - 400.0) / 640.0
    vig = bound(1.0 - 0.68 * (nx * nx + 0.52 * ny * ny), 0.0, 1.0)
    return (r * vig, g * vig, b * vig)


def fold_slot(i, n):
    i %= n
    half = n // 2
    return i if i <= half else n - i


def stamp_roundel(base, x, y, ang, orbit, radius, pigment):
    px = MID + math.sin(ang) * orbit
    py = LAMP_Y - math.cos(ang) * orbit
    if abs(x - px) > radius + 2.0 or abs(y - py) > radius + 2.0:
        return base
    d = math.hypot(x - px, y - py)
    if d > radius + 1.4:
        return base
    cover = ramp(radius + 1.3, radius - 0.6, d)
    # Flat backlit glass, a little hotter in the middle, never a shiny bead.
    hot = 0.76 + 0.24 * bound(1.0 - d / radius, 0.0, 1.0)
    pane = (
        bound(pigment[0] * hot, 0.0, 1.0),
        bound(pigment[1] * hot, 0.0, 1.0),
        bound(pigment[2] * hot, 0.0, 1.0),
    )
    if d > radius - 2.2:
        pane = fuse(pane, (0.04, 0.026, 0.02), ramp(radius - 2.2, radius - 0.15, d))
    return fuse(base, pane, cover)


def lamp_color(x, y):
    """Roundels in pale stone. None once the point leaves the disk."""
    dx = x - MID
    dy = y - LAMP_Y
    r = math.hypot(dx, dy)
    if r >= LAMP_R:
        return None
    if r > LAMP_R - 13.0:
        lip = ramp(LAMP_R - 13.0, LAMP_R - 9.6, r) * (1.0 - ramp(LAMP_R - 6.2, LAMP_R - 3.4, r))
        return fuse((0.15, 0.10, 0.065), (1.0, 0.85, 0.50), lip)
    ground = 0.052 + 0.038 * (1.0 - r / LAMP_R)
    col = (ground * 1.5, ground * 0.70, ground * 0.28)
    stone = (0.76, 0.60, 0.36)
    for ring, width in ((33.0, 3.2), (67.0, 3.4)):
        gap = abs(r - ring)
        if gap < width:
            col = fuse(col, stone, ramp(width, 0.65, gap))
    for i in range(8):
        ang = i * (math.tau / 8.0)
        col = stamp_roundel(col, x, y, ang, 48.0, 14.5, INNER_GLASS[fold_slot(i, 8)])
    for i in range(12):
        ang = i * (math.tau / 12.0)
        col = stamp_roundel(col, x, y, ang, 88.0, 18.5, OUTER_GLASS[fold_slot(i, 12)])
    if r < 35.0:
        core = fuse((1.0, 0.72, 0.32), (1.0, 0.99, 0.96), bound(1.0 - r / 25.0, 0.0, 1.0) ** 0.52)
        col = fuse(col, core, ramp(34.5, 22.0, r))
    return col


def comb(x, y):
    """Wide umber plates. Returns (coverage, color) or (0, None)."""
    if y < 286.0 or y > TIDE - 10.0:
        return 0.0, None
    bow = math.sin(bound((y - 316.0) / 390.0, 0.0, 1.0) * math.pi) * 7.0
    side = 1.0 if x >= MID else -1.0
    xb = x - side * bow
    ax = abs(xb - MID)
    inner = 156.0
    step = 27.0
    count = 9
    outer = inner + (count - 1) * step
    if ax < inner - 4.0 or ax > outer + 12.0:
        return 0.0, None
    slot = int((ax - inner) / step + 0.5)
    if slot < 0 or slot >= count:
        return 0.0, None
    root = inner + slot * step
    local = ax - root
    along = (root - inner) / (outer - inner)
    top = palate(xb) - 1.0
    tip = min(TIDE - 24.0, top + span(246.0, 312.0, along ** 0.88))
    if y < top - 2.0 or y > tip + 2.0:
        return 0.0, None
    t = bound((y - top) / max(tip - top, 1.0), 0.0, 1.0)
    half = span(10.2, 5.5, t)
    cover = ramp(half + 1.85, half - 0.95, abs(local))
    cover *= ramp(top - 1.5, top + 1.3, y)
    cover *= ramp(tip + 2.1, tip - 2.0, y)
    rd = math.hypot(x - MID, y - LAMP_Y)
    cover *= ramp(LAMP_R + 8.0, LAMP_R + 18.0, rd)
    if cover <= 0.0:
        return 0.0, None
    light = lamp_falloff(x, y)
    face = 0.80 + 0.20 * math.exp(-((y - LAMP_Y) / 168.0) ** 2)
    body = (
        (0.23 + 0.13 * light) * face,
        (0.14 + 0.075 * light) * face,
        (0.075 + 0.032 * light) * face,
    )
    lip = ramp(half - 3.5, half - 0.65, -local)
    col = fuse(body, (0.97, 0.76, 0.40), lip * (0.52 + 0.48 * light))
    if local > half - 1.55:
        col = fuse(col, (0.028, 0.016, 0.014), ramp(half - 1.55, half - 0.2, local))
    if t < 0.05:
        col = fuse(col, (0.64, 0.48, 0.30), (0.05 - t) / 0.05 * 0.42)
    if t > 0.88:
        col = fuse(col, (0.76, 0.62, 0.40), (t - 0.88) / 0.12 * 0.5)
    return cover, col


def ivory(x, y):
    light = lamp_falloff(x, y)
    amb = math.exp(-((x - MID) ** 2) / (2.0 * 236.0 * 236.0) - ((y - 124.0) ** 2) / (2.0 * 94.0 * 94.0))
    grain = 0.955 + 0.045 * mottled(x, y, 136.0)
    pore = (mottled(x, y, 50.0) - 0.5) * 0.028
    flank = bound(abs(x - MID) / 512.0, 0.0, 1.0)
    turn = 1.0 - 0.36 * (flank ** 1.32)
    r = (0.19 + 0.46 * amb + 0.32 * light + pore) * grain * turn
    g = (0.145 + 0.34 * amb + 0.21 * light + pore * 0.82) * grain * turn
    b = (0.105 + 0.22 * amb + 0.085 * light + pore * 0.55) * grain * turn
    for s in (-1.0, 1.0):
        lobe = math.exp(-((x - (MID + s * 70.0)) ** 2) / (2.0 * 76.0 * 76.0) - ((y - 138.0) ** 2) / (2.0 * 56.0 * 56.0))
        r += 0.055 * lobe
        g += 0.042 * lobe
        b += 0.026 * lobe
    if 80.0 < y < 280.0:
        fade = ramp(280.0, 226.0, y) * ramp(80.0, 118.0, y)
        seam = abs(x - MID)
        if seam < 2.3:
            k = 0.38 * fade * (1.0 - seam / 2.3)
            r = r * (1.0 - k) + 0.05 * k
            g = g * (1.0 - k) + 0.038 * k
            b = b * (1.0 - k) + 0.028 * k
    for ex, ey, rx, ry in GAZE:
        dxe = (x - ex) / (rx * 1.06)
        if abs(dxe) < 1.04 and y < ey:
            ridge = ey - ry - 6.0 - 8.5 * (1.0 - dxe * dxe)
            d = abs(y - ridge)
            if d < 6.2:
                k = (1.0 - d / 6.2) * (1.0 - abs(dxe) / 1.04) * 0.32
                r += 0.16 * k
                g += 0.12 * k
                b += 0.065 * k
    return (bound(r, 0.0, 1.0), bound(g, 0.0, 1.0), bound(b, 0.0, 1.0))


def rims(x, y, col, dist):
    if 0.0 <= dist < 5.0:
        t = (1.0 - dist / 5.0) ** 1.5
        col = fuse(col, (0.80, 0.93, 0.99), t * 0.95)
    d_roof = palate(x) - y
    if 0.0 <= d_roof < 7.5:
        t = (1.0 - d_roof / 7.5) ** 1.05
        col = fuse(col, (1.0, 0.75, 0.40), t * (0.52 + 0.48 * lamp_falloff(x, y)))
    d_jaw = y - jaw(x)
    if 0.0 <= d_jaw < 7.2:
        t = (1.0 - d_jaw / 7.2) ** 1.08
        col = fuse(col, (0.95, 0.70, 0.36), t * (0.40 + 0.60 * lamp_falloff(x, y)))
    d_cheek = mouth_reach(y) - abs(x - MID)
    if 0.0 <= d_cheek < 6.2 and palate(x) < y < jaw(x):
        t = 1.0 - d_cheek / 6.2
        col = fuse(col, (0.92, 0.66, 0.32), t * 0.78 * lamp_falloff(x, y))
    return col


def gaze_over(x, y, bone):
    col = bone
    for ex, ey, rx, ry in GAZE:
        if abs(x - ex) > rx + 16.0 or abs(y - ey) > ry + 14.0:
            continue
        nx = (x - ex) / rx
        ny = (y - ey) / ry
        p = math.hypot(nx, ny)
        radial = math.hypot(rx * nx, ry * ny) / max(p, 1e-6)
        dist = (1.0 - p) * radial
        sock = math.hypot((x - ex) / (rx + 20.0), (y - ey) / (ry + 14.0))
        if sock < 1.0:
            shade = (1.0 - sock) ** 1.15 * 0.40
            col = (col[0] * (1.0 - shade), col[1] * (1.0 - shade), col[2] * (1.0 - shade))
        if dist < -2.1:
            continue
        cover = ramp(-1.3, 1.1, dist)
        if cover <= 0.0:
            continue
        lid = ramp(0.04, -0.88, ny)
        globe = (0.011 + 0.011 * (1.0 - lid), 0.015 + 0.015 * (1.0 - lid), 0.025)
        if ny > 0.52 and abs(dist) < 3.0:
            wet = ramp(0.52, 0.86, ny) * ramp(3.0, 0.45, abs(dist))
            globe = fuse(globe, (0.48, 0.56, 0.60), wet * 0.36)
        toward = 1.0 if ex < MID else -1.0
        d1 = math.hypot(x - (ex + toward * rx * 0.18), y - (ey + ry * 0.30))
        d2 = math.hypot(x - (ex - toward * rx * 0.30), y - (ey - ry * 0.34))
        if d1 < 4.4:
            globe = fuse(globe, (1.0, 0.92, 0.78), ramp(4.4, 1.2, d1))
        if d2 < 2.6:
            globe = fuse(globe, (0.76, 0.88, 0.95), ramp(2.6, 0.65, d2))
        col = fuse(col, globe, cover)
    return col


def vessel(x, y):
    """Wood hull on the tide line, sail above it. (color, coverage)."""
    bx = x - HULL_X
    by = y - HULL_Y
    if bx < -44.0 or bx > 50.0 or by < -116.0 or by > 24.0:
        return None, 0.0
    col = (0.0, 0.0, 0.0)
    cover = 0.0
    if -1.1 <= by <= 19.0 and abs(bx) < 40.0:
        t = bound(by / 17.5, 0.0, 1.0)
        half = 34.0 * (1.0 - t ** 0.56)
        d = min(half - abs(bx), 17.5 - by)
        c = ramp(-1.45, 1.15, d) * ramp(-1.05, 0.65, by + 0.25)
        if c > 0.0:
            hull = (0.40, 0.19, 0.085)
            if by < 2.3:
                hull = fuse((0.94, 0.73, 0.36), hull, bound(by / 2.3, 0.0, 1.0))
            hull = fuse(hull, (0.20, 0.09, 0.045), bound((by - 8.5) / 9.0, 0.0, 1.0) * 0.32)
            ld = math.hypot(bx - 15.0, by - 6.5)
            if ld < 1.9:
                hull = (1.0, 0.45, 0.13)
            col, cover = hull, c
    if -102.0 <= by <= 1.0 and abs(bx) <= 2.1:
        c = ramp(2.1, 0.3, abs(bx))
        if c > cover:
            col, cover = (0.075, 0.048, 0.032), c
    y0, y1 = -102.0, -3.2
    if y0 - 2.0 <= by <= y1 + 2.0 and -2.0 <= bx <= 44.0:
        t = bound((by - y0) / (y1 - y0), 0.0, 1.0)
        reach = 1.5 + 37.0 * t
        d = min(reach - bx, bx - 0.55, by - y0, y1 - by)
        c = ramp(-1.5, 1.1, d)
        if c > 0.0:
            facing = 0.73 + 0.27 * bound(bx / 37.0, 0.0, 1.0)
            facing *= 0.91 + 0.09 * (1.0 - t)
            if abs(by + 46.0) < 0.8:
                facing *= 0.86
            sail = (0.98 * facing, 0.90 * facing, 0.68 * facing)
            if c > cover:
                col, cover = sail, c
    return (col if cover > 0.0 else None), cover


def skull_gap(x, y):
    top = crown(x)
    slope = crown_slope(x)
    return (y - top) / math.sqrt(1.0 + slope * slope)


def dry(x, y):
    """Night, bone, throat, comb, and lamp. No water and no boat."""
    if y < -4.0 or y > SIDE + 4.0 or x < -4.0 or x > SIDE + 4.0:
        return ink(bound(x, 0.0, SIDE - 1.0), bound(y, 0.0, SIDE - 1.0))
    dist = skull_gap(x, y)
    if dist <= -1.7:
        return ink(x, y)
    roof = palate(x)
    chin = jaw(x)
    in_throat = (y >= roof) and (y <= chin) and (abs(x - MID) <= mouth_reach(y) + 1.4)
    if in_throat:
        light = lamp_falloff(x, y)
        col = (0.018 + 0.05 * light, 0.008 + 0.026 * light, 0.011 + 0.013 * light)
        dx = x - MID
        dy = y - LAMP_Y
        rr = math.hypot(dx, dy)
        if y > LAMP_Y and abs(dx) < 146.0:
            halfw = 17.0 + (y - LAMP_Y) * 0.040
            shaft = math.exp(-(dx / halfw) ** 2)
            fall = math.exp(-(y - LAMP_Y) / 350.0)
            col = fuse(col, (1.0, 0.77, 0.40), shaft * fall * 0.48)
        if rr > LAMP_R and abs(dx) < 136.0:
            up = math.atan2(dx, -dy)
            ray = (0.5 + 0.5 * math.cos(up * 12.0)) ** 8
            ray *= math.exp(-(rr - LAMP_R) / 230.0)
            col = fuse(col, (1.0, 0.80, 0.48), ray * 0.065)
        pcov, pcol = comb(x, y)
        if pcov > 0.0:
            col = fuse(col, pcol, pcov)
        glass = lamp_color(x, y)
        if glass is not None:
            col = fuse(col, glass, ramp(LAMP_R + 1.1, LAMP_R - 1.2, rr))
        elif rr < LAMP_R + 30.0:
            glow = ramp(LAMP_R + 30.0, LAMP_R + 1.0, rr)
            col = fuse(col, (1.0, 0.78, 0.44), glow * 0.40)
    else:
        col = ivory(x, y)
        col = rims(x, y, col, dist)
        col = gaze_over(x, y, col)
    if dist < 2.3:
        col = fuse(ink(x, y), col, ramp(-1.4, 1.4, dist))
    return col


def lagoon(x, y):
    depth = (y - TIDE) / 276.0
    wob = math.sin(x * 0.038 + y * 0.10) * 4.8 + math.sin(x * 0.014 - y * 0.044) * 1.8
    sx = x + math.sin(y * 0.05) * 3.0
    sy = (TIDE - (y - TIDE)) + wob
    if sy > TIDE - 3.0:
        sy = TIDE - 3.0
    reflected = dry(sx, sy)
    fade = math.exp(-depth * 1.02)
    ref = (reflected[0] * 0.38 * fade, reflected[1] * 0.48 * fade, reflected[2] * 0.60 * fade)
    rip = math.sin(y * 0.58 + math.sin(x * 0.02) * 1.8)
    col = (
        bound(0.009 + ref[0], 0.0, 1.0),
        bound(0.016 + ref[1], 0.0, 1.0),
        bound(0.036 + 0.009 * (0.5 + 0.5 * rip) + ref[2], 0.0, 1.0),
    )
    halfw = 17.0 + (y - LAMP_Y) * 0.040
    shaft = math.exp(-((x - MID) / halfw) ** 2) * math.exp(-(y - TIDE) / 200.0)
    col = fuse(col, (0.88, 0.64, 0.30), shaft * 0.36)
    sh = ((x - HULL_X) / 24.0) ** 2 + ((y - (HULL_Y + 14.0)) / 4.2) ** 2
    if sh < 1.0:
        col = fuse(col, (0.004, 0.006, 0.011), (1.0 - sh) * 0.32)
    bx = x - HULL_X + math.sin(y * 0.13) * 1.2
    by = y - (HULL_Y + 15.0)
    if 0.0 <= by <= 44.0 and 0.0 <= bx <= 32.0:
        reach = 30.0 * (by / 44.0)
        if bx < reach:
            a = 0.26 * (1.0 - by / 44.0) * ramp(reach + 0.2, reach - 1.1, bx)
            col = fuse(col, (0.72, 0.60, 0.40), a)
    return col


def paint(x, y):
    dist = skull_gap(x, y)
    roof = palate(x)
    chin = jaw(x)
    in_throat = dist > -1.1 and (y >= roof) and (y <= chin + 2.0) and (abs(x - MID) <= mouth_reach(y) + 2.0)
    if in_throat and y >= TIDE - 1.5 and y < chin:
        water = ramp(TIDE - 1.45, TIDE + 1.1, y)
        bone = ramp(chin - 1.1, chin + 1.3, y)
        col = fuse(dry(x, y), lagoon(x, y), water * (1.0 - bone))
        if bone > 0.0:
            jaw_col = rims(x, y, ivory(x, y), max(dist, 4.0))
            col = fuse(col, jaw_col, bone)
    else:
        col = dry(x, y)
    dline = abs(y - TIDE)
    if dline < 1.9 and in_throat and y < chin - 6.0:
        shine = math.exp(-((x - MID) / 206.0) ** 2)
        col = fuse(col, (1.0, 0.86, 0.56), (1.0 - dline / 1.9) * shine * 0.66)
    bcol, bcov = vessel(x, y)
    if bcov > 0.0:
        col = fuse(col, bcol, bcov)
    return col


def to_byte(v):
    return int(bound(v, 0.0, 1.0) * 255.0 + 0.5)


def build():
    buf = bytearray(SIDE * SIDE * 3)
    view = memoryview(buf)
    i = 0
    for y in range(SIDE):
        yy = float(y)
        for x in range(SIDE):
            r, g, b = paint(float(x), yy)
            view[i] = to_byte(r)
            view[i + 1] = to_byte(g)
            view[i + 2] = to_byte(b)
            i += 3
    return buf


def png_chunk(tag, payload):
    crc = zlib.crc32(tag)
    crc = zlib.crc32(payload, crc) & 0xFFFFFFFF
    return struct.pack(">I", len(payload)) + tag + payload + struct.pack(">I", crc)


def save_png(path, buf):
    raw = bytearray()
    stride = SIDE * 3
    for y in range(SIDE):
        raw.append(0)
        raw.extend(buf[y * stride:(y + 1) * stride])
    header = struct.pack(">IIBBBBB", SIDE, SIDE, 8, 2, 0, 0, 0)
    blob = b"\x89PNG\r\n\x1a\n" + png_chunk(b"IHDR", header) + png_chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + png_chunk(b"IEND", b"")
    with open(path, "wb") as handle:
        handle.write(blob)
    return len(blob)


def main():
    folder = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, "entry.png")
    size = save_png(path, build())
    print(f"{path} {SIDE}x{SIDE} {size}", file=sys.stderr)


if __name__ == "__main__":
    main()
