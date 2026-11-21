#!/usr/bin/env python3
"""Add monotonic Greek to every Allo source (the 48 variable masters and the 18 static fonts).

    python tools/greek/make_greek.py --inter path/to/inter/src/Inter-Roman.glyphspackage

How the glyphs are made:

* Greek capitals that share a Latin shape (Α Β Ε Ζ Η Ι Κ Μ Ν Ο Ρ Τ Υ Χ) and ο μ ϰ-like κ are components of
  Allo's own letters, so they follow every edit, axis and sparse layer of the Latin.
* Γ is Allo's L, turned over (a component too).
* The other letters start from Inter 4 (Allo began from Inter 4.2 and keeps its metrics, stems and weights),
  interpolated to each master's optical size and weight, respaced with Allo's sidebearings (measured per master
  from H O n o and friends), and then given Allo's corners: every convex corner becomes the same cubic arc Allo
  draws, with the radius and handle ratio measured from that master's L (ROND 0 ≈ sharp, 50 friendly, 100
  round, capped at half the stroke so terminals turn into full round ends). Every master gets the same points,
  so the variable font interpolates.
* Accented letters (tonos, dialytika) are components placed by anchors.
* Static obliques: the upright drawing slanted 9° about the x-height middle, then rounded.

Run it again after changing a Latin letter: it rebuilds the Greek it owns (listed in GREEK) and leaves
everything else as it is.
"""
import argparse
import math
import re
from pathlib import Path

import glyphsLib
import ufoLib2
from fontTools.designspaceLib import DesignSpaceDocument
from fontTools.misc.transform import Transform
from fontTools.pens.boundsPen import BoundsPen

ROOT = Path(__file__).resolve().parents[2]
SLANT = math.tan(math.radians(9))
SMALL_SHIFT = 17

# ---------------------------------------------------------------------------------------------------------------
# The glyph set
# ---------------------------------------------------------------------------------------------------------------

# Capitals and lowercase that are an Allo glyph as they are.
ALIAS = {
    'Alpha': ('A', 0x391), 'Beta': ('B', 0x392), 'Epsilon': ('E', 0x395), 'Zeta': ('Z', 0x396),
    'Eta': ('H', 0x397), 'Iota': ('I', 0x399), 'Kappa': ('K', 0x39A), 'Mu': ('M', 0x39C), 'Nu': ('N', 0x39D),
    'Omicron': ('O', 0x39F), 'Rho': ('P', 0x3A1), 'Tau': ('T', 0x3A4), 'Upsilon': ('Y', 0x3A5),
    'Chi': ('X', 0x3A7), 'Iotadieresis': ('Idieresis', 0x3AA), 'Upsilondieresis': ('Ydieresis', 0x3AB),
    'omicron': ('o', 0x3BF), 'mugreek': ('micro', 0x3BC), 'kappa': ('kgreenlandic', 0x3BA),
    'questiongreek': ('semicolon', 0x37E),
}

# Drawn from Inter: name -> (Inter glyph, unicodes, left spacing reference, right spacing reference).
# A reference is an Allo/Inter glyph whose sidebearing change (Inter -> Allo) the side takes on.
DRAWN = {
    'Delta': ('Delta', [0x394, 0x2206], 'A', 'A'),
    'Lambda': ('Lambda', [0x39B], 'A', 'A'),
    'Xi': ('Xi', [0x39E], 'Z', 'Z'),
    'Pi': ('Pi', [0x3A0], 'H', 'H'),
    'Sigma': ('Sigma', [0x3A3], 'Z', 'Z'),
    'Phi': ('Phi', [0x3A6], 'O', 'O'),
    'Psi': ('Psi', [0x3A8], 'U', 'U'),
    'Omega': ('Omega', [0x3A9, 0x2126], 'O', 'O'),
    'alpha': ('alpha', [0x3B1], 'o', 'n'),
    'beta': ('beta', [0x3B2], 'n', 'o'),
    'gamma': ('gamma', [0x3B3], 'v', 'v'),
    'delta': ('delta', [0x3B4], 'o', 'o'),
    'epsilon': ('epsilon', [0x3B5], 'o', 'c'),
    'zeta': ('zeta', [0x3B6], 'o', 'c'),
    'eta': ('eta', [0x3B7], 'n', 'n'),
    'theta': ('theta', [0x3B8], 'o', 'o'),
    'iota': ('iota', [0x3B9], 'n', 'c'),
    'lambda': ('lambda', [0x3BB], 'v', 'v'),
    'nu': ('nu', [0x3BD], 'v', 'v'),
    'xi': ('xi', [0x3BE], 'o', 'c'),
    'pi': ('pi', [0x3C0], 'x', 'x'),
    'rho': ('rho', [0x3C1], 'o', 'o'),
    'sigmafinal': ('sigma1', [0x3C2], 'o', 'c'),
    'sigma': ('sigma', [0x3C3], 'o', 'c'),
    'tau': ('tau', [0x3C4], 'x', 'c'),
    'upsilon': ('upsilon', [0x3C5], 'n', 'o'),
    'phi': ('phi', [0x3C6], 'o', 'o'),
    'chi': ('chi', [0x3C7], 'x', 'x'),
    'psi': ('psi', [0x3C8], 'n', 'n'),
    'omega': ('omega', [0x3C9], 'o', 'o'),
    'tonos.top': ('tonos.top', [], None, None),
}

# Capitals with tonos: base, unicode (Inter's composite gives the base's shift and the extra advance).
CAP_TONOS = {
    'Alphatonos': ('Alpha', 'A', 0x386), 'Epsilontonos': ('Epsilon', 'E', 0x388),
    'Etatonos': ('Eta', 'H', 0x389), 'Iotatonos': ('Iota', 'I', 0x38A),
    'Omicrontonos': ('Omicron', 'O', 0x38C), 'Upsilontonos': ('Upsilon', 'Y', 0x38E),
    'Omegatonos': ('Omega', 'Omega', 0x38F),
}

# Lowercase with a mark on its top anchor.
LOWER_MARKS = {
    'alphatonos': ('alpha', 'tonos.top', 0x3AC), 'epsilontonos': ('epsilon', 'tonos.top', 0x3AD),
    'etatonos': ('eta', 'tonos.top', 0x3AE), 'iotatonos': ('iota', 'tonos.top', 0x3AF),
    'omicrontonos': ('omicron', 'tonos.top', 0x3CC), 'upsilontonos': ('upsilon', 'tonos.top', 0x3CD),
    'omegatonos': ('omega', 'tonos.top', 0x3CE),
    'iotadieresis': ('iota', 'dieresiscomb', 0x3CA), 'upsilondieresis': ('upsilon', 'dieresiscomb', 0x3CB),
    'iotadieresistonos': ('iota', 'dieresistonos.top', 0x390),
    'upsilondieresistonos': ('upsilon', 'dieresistonos.top', 0x3B0),
}

MARKS = ['tonos.top', 'dieresistonos.top']

# Kerning: which Latin glyph's kerning group each side joins (left side = kern2, right side = kern1).
KERN_PROXY = {
    'Alpha': ('A', 'A'), 'Beta': ('B', 'B'), 'Gamma': ('L', 'F'), 'Delta': ('A', 'A'), 'Epsilon': ('E', 'E'),
    'Zeta': ('Z', 'Z'), 'Eta': ('H', 'H'), 'Theta': ('O', 'O'), 'Iota': ('I', 'I'), 'Kappa': ('K', 'K'),
    'Lambda': ('A', 'A'), 'Mu': ('M', 'M'), 'Nu': ('N', 'N'), 'Xi': ('Z', 'Z'), 'Omicron': ('O', 'O'),
    'Pi': ('H', 'H'), 'Rho': ('P', 'P'), 'Sigma': ('Z', 'E'), 'Tau': ('T', 'T'), 'Upsilon': ('Y', 'Y'),
    'Phi': ('O', 'O'), 'Chi': ('X', 'X'), 'Psi': ('U', 'U'), 'Omega': ('O', 'O'),
    'alpha': ('o', None), 'beta': (None, 'o'), 'gamma': ('v', 'v'), 'delta': ('o', 'o'), 'epsilon': ('o', 'c'),
    'eta': ('n', 'n'), 'theta': ('o', 'o'), 'iota': ('n', None), 'kappa': ('n', 'k'), 'lambda': (None, None),
    'mugreek': ('u', None), 'nu': ('v', 'v'), 'omicron': ('o', 'o'), 'rho': ('o', 'o'), 'sigma': ('o', None),
    'sigmafinal': ('o', 'c'), 'upsilon': ('u', 'o'), 'phi': ('o', 'o'), 'chi': ('x', 'x'), 'psi': ('u', 'u'),
    'omega': ('o', 'o'), 'pi': (None, None), 'tau': (None, None), 'xi': ('o', None), 'zeta': ('o', None),
}
for _n, (_b, _m, _u) in LOWER_MARKS.items():
    KERN_PROXY.setdefault(_n, KERN_PROXY.get(_b, (None, None)))
for _n, (_b, _l, _u) in CAP_TONOS.items():
    KERN_PROXY.setdefault(_n, (None, KERN_PROXY[_b][1]))
KERN_PROXY['Iotadieresis'] = ('I', 'I')
KERN_PROXY['Upsilondieresis'] = ('Y', 'Y')

GREEK = (list(ALIAS) + ['Gamma', 'Theta'] + list(DRAWN) + ['tonos', 'dieresistonos', 'dieresistonos.top',
         'anoteleia'] + list(CAP_TONOS) + list(LOWER_MARKS))

# ---------------------------------------------------------------------------------------------------------------
# Inter: interpolated, decomposed outlines
# ---------------------------------------------------------------------------------------------------------------


class Inter:
    def __init__(self, path):
        self.font = glyphsLib.GSFont(str(path))
        self.masters = {(m.axes[0], m.axes[1]): m.id for m in self.font.masters}

    def _layer(self, name, mid):
        return self.font.glyphs[name].layers[mid]

    def _decompose(self, name, mid, t=Transform()):
        """Contours [(x, y, type, smooth)] and anchors {name: (x, y)} of a master layer, components drawn in."""
        layer = self._layer(name, mid)
        contours = []
        for path in layer.paths:
            pts = []
            for node in path.nodes:
                x, y = t.transformPoint((node.position.x, node.position.y))
                pts.append((x, y, node.type, node.smooth))
            contours.append(pts)
        for comp in layer.components:
            ct = t.transform(Transform(*comp.transform))
            sub, _ = self._decompose(comp.name, mid, ct)
            if ct[0] * ct[3] - ct[1] * ct[2] < 0:
                sub = [reverse(c) for c in sub]
            contours += sub
        anchors = {a.name: t.transformPoint((a.position.x, a.position.y)) for a in layer.anchors}
        if not anchors and layer.components:
            _, anchors = self._decompose(layer.components[0].name, mid,
                                         t.transform(Transform(*layer.components[0].transform)))
        return contours, anchors

    def _weights(self, opsz, wght):
        """Bilinear weights of the six masters (opsz 14/32 x wght 100/400/900)."""
        u = min(max((opsz - 14) / 18, 0), 1)
        if wght <= 400:
            lo, hi, v = 100, 400, (wght - 100) / 300
        else:
            lo, hi, v = 400, 900, (wght - 400) / 500
        return {(14, lo): (1 - u) * (1 - v), (14, hi): (1 - u) * v, (32, lo): u * (1 - v), (32, hi): u * v}

    def glyph(self, name, opsz, wght):
        """(contours, anchors, width) of an Inter glyph at a location."""
        out_c, out_a, out_w = None, {}, 0
        for key, k in self._weights(opsz, wght).items():
            if k == 0:
                continue
            mid = self.masters[key]
            contours, anchors = self._decompose(name, mid)
            width = self._layer(name, mid).width
            if out_c is None:
                out_c = [[(x * k, y * k, ty, sm) for x, y, ty, sm in c] for c in contours]
                out_a = {n: (x * k, y * k) for n, (x, y) in anchors.items()}
            else:
                assert [len(c) for c in contours] == [len(c) for c in out_c], f'Inter {name} not compatible'
                out_c = [[(a[0] + x * k, a[1] + y * k, ty, sm) for a, (x, y, ty, sm) in zip(oc, c)]
                         for oc, c in zip(out_c, contours)]
                out_a = {n: (out_a[n][0] + x * k, out_a[n][1] + y * k) for n, (x, y) in anchors.items() if n in out_a}
            out_w += width * k
        return out_c, out_a, out_w

    def component_offsets(self, name, opsz, wght):
        """The interpolated offsets of a composite's components, [(base, dx, dy)], and its width."""
        offs, width = None, 0
        for key, k in self._weights(opsz, wght).items():
            if k == 0:
                continue
            layer = self._layer(name, self.masters[key])
            here = [(c.name, c.transform[4] * k, c.transform[5] * k) for c in layer.components]
            offs = here if offs is None else [(n, a + x, b + y) for (n, a, b), (_, x, y) in zip(offs, here)]
            width += layer.width * k
        return offs, width

    def sidebearings(self, name, opsz, wght):
        contours, _, width = self.glyph(name, opsz, wght)
        xs = [p[0] for c in contours for p in c]
        return min(xs), width - max(xs)


def reverse(contour):
    """Reverse a contour of (x, y, type, smooth) nodes, keeping each segment's type on its end point."""
    n = len(contour)
    on = [i for i, p in enumerate(contour) if p[2] != 'offcurve']
    rev = list(reversed(contour))
    # types move: the segment type belongs to the point the segment ends on; after reversing, the segment
    # that ended at on[k] now ends at the previous on-curve point.
    types = {}
    for k, i in enumerate(on):
        prev = on[k - 1]
        types[prev] = contour[i][2]
    return [(x, y, types.get(n - 1 - j, 'offcurve') if t != 'offcurve' else 'offcurve', s)
            for j, (x, y, t, s) in enumerate(rev)]


# ---------------------------------------------------------------------------------------------------------------
# Allo's corners
# ---------------------------------------------------------------------------------------------------------------


def segments(contour):
    """Split a closed contour of (x, y, type, smooth) into segments [(kind, [P0, ..., P3]), ...] where each
    segment's last point is an on-curve node (the corner it ends at)."""
    on = [i for i, p in enumerate(contour) if p[2] != 'offcurve']
    start = on[0]
    pts = contour[start:] + contour[:start]
    segs, cur = [], [pts[0]]
    for p in pts[1:] + [pts[0]]:
        cur.append(p)
        if p[2] != 'offcurve':
            kind = 'line' if len(cur) == 2 else 'curve'
            segs.append([kind, [(q[0], q[1]) for q in cur], p[3]])
            cur = [p]
    return segs


def bez(seg, t):
    P = seg
    if len(P) == 2:
        return (P[0][0] + (P[1][0] - P[0][0]) * t, P[0][1] + (P[1][1] - P[0][1]) * t)
    mt = 1 - t
    return (mt ** 3 * P[0][0] + 3 * mt * mt * t * P[1][0] + 3 * mt * t * t * P[2][0] + t ** 3 * P[3][0],
            mt ** 3 * P[0][1] + 3 * mt * mt * t * P[1][1] + 3 * mt * t * t * P[2][1] + t ** 3 * P[3][1])


def split(P, t):
    """Split a line or cubic at t: (first part, second part)."""
    if len(P) == 2:
        m = bez(P, t)
        return [P[0], m], [m, P[1]]
    lerp = lambda a, b: (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
    a, b, c = lerp(P[0], P[1]), lerp(P[1], P[2]), lerp(P[2], P[3])
    d, e = lerp(a, b), lerp(b, c)
    f = lerp(d, e)
    return [P[0], a, d, f], [f, e, c, P[3]]


def subsegment(P, a, b):
    """The part of P between parameters a <= b."""
    if b < 1:
        P = split(P, b)[0]
    if a > 0:
        P = split(P, a / b if b > 0 else 0)[1]
    return P


def derivative(P, t, at_end):
    """Unit direction of P at t (falls back to the end tangents where a handle sits on its point)."""
    if len(P) == 2:
        return unit((P[1][0] - P[0][0], P[1][1] - P[0][1]))
    mt = 1 - t
    d = [3 * (mt * mt * (P[1][k] - P[0][k]) + 2 * mt * t * (P[2][k] - P[1][k]) + t * t * (P[3][k] - P[2][k]))
         for k in (0, 1)]
    if math.hypot(*d) < 1e-6:
        return end_tangent(P) if at_end else start_tangent(P)
    return unit(d)


def unit(v):
    n = math.hypot(*v)
    return (v[0] / n, v[1] / n) if n > 1e-9 else (0.0, 0.0)


def end_tangent(P):
    """Direction the segment arrives at its end with."""
    for q in reversed(P[:-1]):
        if math.dist(q, P[-1]) > 1e-6:
            return unit((P[-1][0] - q[0], P[-1][1] - q[1]))
    return (0.0, 0.0)


def start_tangent(P):
    for q in P[1:]:
        if math.dist(q, P[0]) > 1e-6:
            return unit((q[0] - P[0][0], q[1] - P[0][1]))
    return (0.0, 0.0)


def area(contour):
    s = 0
    for i in range(len(contour)):
        x0, y0 = contour[i][:2]
        x1, y1 = contour[(i + 1) % len(contour)][:2]
        s += x0 * y1 - x1 * y0
    return s / 2


def find_corners(contour):
    """Indices (into segments()) of the segments whose end is a convex corner: a turn of more than 25°, toward
    the inside of the contour's own direction."""
    segs = segments(contour)
    orient = 1 if area(contour) > 0 else -1
    corners = []
    for i, (kind, P, smooth) in enumerate(segs):
        nxt = segs[(i + 1) % len(segs)][1]
        a, b = end_tangent(P), start_tangent(nxt)
        cross = a[0] * b[1] - a[1] * b[0]
        angle = math.degrees(math.acos(max(-1, min(1, a[0] * b[0] + a[1] * b[1]))))
        if angle > 25 and cross * orient > 0:
            corners.append(i)
    return corners


def round_contour(contour, corners, radius, ratio, ratio_capped=0.552):
    """The contour with each corner (indices from find_corners, decided once for all masters) replaced by
    Allo's arc. The result is a UFO point list [(x, y, type)]; same structure whatever the radius."""
    segs = [[k, list(P)] for k, P, _ in segments(contour)]
    n = len(segs)
    cset = set(corners)
    plan = {}
    for i in corners:
        seg_in, seg_out = segs[i][1], segs[(i + 1) % n][1]
        a, b = end_tangent(seg_in), start_tangent(seg_out)
        cosang = max(-1, min(1, -(a[0] * b[0] + a[1] * b[1])))
        theta = math.acos(cosang)  # interior angle
        theta = min(max(theta, math.radians(20)), math.radians(170))
        tangent = radius / math.tan(theta / 2) ** 0.6
        tangent = min(tangent, 2 * radius)
        # never more than half an edge shared with another rounded corner, or most of a free edge
        lim_in = math.dist(seg_in[0], seg_in[-1]) * (0.5 if (i - 1) % n in cset else 0.9)
        lim_out = math.dist(seg_out[0], seg_out[-1]) * (0.5 if (i + 1) % n in cset else 0.9)
        cap = min(lim_in, lim_out)
        capped = tangent > cap
        plan[i] = (min(tangent, cap), ratio_capped if capped else ratio)

    def cut_t(P, dist, from_end):
        """Parameter on P at chord distance `dist` from its end (from_end) or start."""
        corner = P[-1] if from_end else P[0]
        lo, hi = 0.0, 1.0
        for _ in range(60):
            mid = (lo + hi) / 2
            t = 1 - mid if from_end else mid
            if math.dist(bez(P, t), corner) < dist:
                lo = mid
            else:
                hi = mid
        m = (lo + hi) / 2
        return 1 - m if from_end else m

    # cut every segment on the original curve: corner i takes the end of segment i and the start of segment
    # i+1; directions come from the original segment, so an edge that two corners use up still has one
    t0 = [0.0] * n
    t1 = [1.0] * n
    for i, (dist, _) in plan.items():
        t1[i] = cut_t(segs[i][1], dist, True)
        t0[(i + 1) % n] = cut_t(segs[(i + 1) % n][1], dist, False)
    for j in range(n):
        if t0[j] > t1[j]:
            t0[j] = t1[j] = (t0[j] + t1[j]) / 2
    trimmed = [subsegment(segs[j][1], t0[j], t1[j]) for j in range(n)]
    out = []
    for i in range(n):
        kind, P = segs[i][0], trimmed[i]
        if kind == 'line':
            out.append((P[-1][0], P[-1][1], 'line'))
        else:
            out += [(P[1][0], P[1][1], None), (P[2][0], P[2][1], None), (P[3][0], P[3][1], 'curve')]
        if i in plan:
            dist, k = plan[i]
            j = (i + 1) % n
            A, B = P[-1], trimmed[j][0]
            ta, tb = derivative(segs[i][1], t1[i], True), derivative(segs[j][1], t0[j], False)
            h = k * dist
            out += [(A[0] + ta[0] * h, A[1] + ta[1] * h, None), (B[0] - tb[0] * h, B[1] - tb[1] * h, None),
                    (B[0], B[1], 'curve')]
    # UFO closed contours: rotate so the list ends on the point the first segment starts from (any rotation
    # is fine as long as it's the same in every master; this one is)
    return out


# ---------------------------------------------------------------------------------------------------------------
# Measuring an Allo source
# ---------------------------------------------------------------------------------------------------------------


def corner_style(font):
    """Radius and handle ratio of Allo's corners in this source, from L's bottom-left corner."""
    pts = font['L'].contours[0].points
    xmin = min(p.x for p in pts)
    on = [p for p in pts if p.type and abs(p.x - xmin) < 0.5 and p.y > 0]
    r = min(p.y for p in on)
    off = [p for p in pts if p.type is None and abs(p.x - xmin) < 0.5 and 0 <= p.y < r]
    ratio = (r - min(p.y for p in off)) / r if off and r > 0.1 else 0.7387
    return r, ratio


def bounds(font, name):
    pen = BoundsPen(font)
    font[name].draw(pen)
    return pen.bounds


def spacing_deltas(font, inter, opsz, wght, refs):
    """{ref: (left change, right change)}: Allo's sidebearings minus Inter's, at this location."""
    out = {}
    for ref in refs:
        b = bounds(font, ref)
        li, ri = inter.sidebearings(ref, opsz, wght)
        out[ref] = (b[0] - li, (font[ref].width - b[2]) - ri)
    return out


# ---------------------------------------------------------------------------------------------------------------
# Writing glyphs
# ---------------------------------------------------------------------------------------------------------------


def set_glyph(font, name, unicodes=(), width=0, contours=(), components=(), anchors=()):
    if name in font:
        del font[name]
    g = font.newGlyph(name)
    g.width = round(width)
    g.unicodes = list(unicodes)
    pen = g.getPointPen()
    for c in contours:
        pen.beginPath()
        for x, y, t in c:
            pen.addPoint((round(x, 3), round(y, 3)), segmentType=t)
        pen.endPath()
    for base, dx, dy in components:
        pen.addComponent(base, (1, 0, 0, 1, round(dx), round(dy)))
    for n, (x, y) in anchors:
        g.appendAnchor({'name': n, 'x': round(x), 'y': round(y)})
    return g


def anchor(font, name, which):
    for a in font[name].anchors:
        if a.name == which:
            return a.x, a.y
    raise KeyError(f'{name} has no {which} anchor')


def drawn(font, inter, name, spec, opsz, wght, deltas, style, oblique):
    iname, unis, lref, rref = spec
    contours, anchors, width = inter.glyph(iname, opsz, wght)
    dl, dr = (deltas[lref][0], deltas[rref][1]) if lref else (0, 0)
    xs = [p[0] for c in contours for p in c]
    if lref:
        # each side takes its reference's change; the drawing moves with the left
        width = width + dl + dr
    contours = [[(x + dl, y, t, s) for x, y, t, s in c] for c in contours]
    anchors = {k: (x + dl, y) for k, (x, y) in anchors.items()}
    if oblique:
        sk = lambda x, y: (x + (y - 559) * SLANT, y)
        contours = [[(*sk(x, y), t, s) for x, y, t, s in c] for c in contours]
        anchors = {k: sk(*v) for k, v in anchors.items()}
    corners = CORNERS[iname]
    radius, ratio = style
    out = [round_contour(c, cs, radius, ratio) for c, cs in zip(contours, corners)]
    if name in MARKS:
        width = 0
    return set_glyph(font, name, unis, width, out, (), sorted(anchors.items()))


CORNERS = {}


def decide_corners(inter):
    """Which corners get rounded, from Inter's Regular, once for every master (so the points match)."""
    for iname in [spec[0] for spec in DRAWN.values()] + ['Theta']:
        contours, _, _ = inter.glyph(iname, 14, 400)
        polys = [flatten(c) for c in contours]
        CORNERS[iname] = []
        for k, c in enumerate(contours):
            segs = segments(c)
            keep = []
            for i in find_corners(c):
                p = segs[i][1][-1]
                # a corner inside (or on) another contour isn't on the letter's outline: rounding it there only
                # leaves a notch where the shapes overlap
                if any(j != k and (inside(p, poly) or near(p, poly, 3)) for j, poly in enumerate(polys)):
                    continue
                keep.append(i)
            CORNERS[iname].append(keep)


def flatten(contour, steps=24):
    pts = []
    for kind, P, _ in segments(contour):
        if kind == 'line':
            pts.append(P[-1])
        else:
            pts += [bez(P, s / steps) for s in range(1, steps + 1)]
    return pts


def inside(p, poly):
    x, y = p
    hit = False
    for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]):
        if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
            hit = not hit
    return hit


def near(p, poly, tol):
    for a, b in zip(poly, poly[1:] + poly[:1]):
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = dx * dx + dy * dy
        t = 0 if L == 0 else max(0, min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L))
        if math.dist(p, (a[0] + t * dx, a[1] + t * dy)) < tol:
            return True
    return False


def theta_bar(inter, opsz, wght):
    """Θ's bar: Inter's Theta drawn without its O."""
    contours, _, _ = inter.glyph('Theta', opsz, wght)
    o, _, _ = inter.glyph('O', opsz, wght)
    return contours[:len(contours) - len(o)], CORNERS['Theta'][:len(contours) - len(o)]


def make(font, inter, opsz, wght, style, oblique, upright=None):
    """Write the Greek into one source. `upright`: for an oblique, its upright source (for measurements)."""
    measure = upright or font
    refs = sorted({s[2] for s in DRAWN.values() if s[2]} | {s[3] for s in DRAWN.values() if s[3]})
    deltas = spacing_deltas(measure, inter, opsz, wght, refs)
    # aliases
    for name, (base, uni) in ALIAS.items():
        set_glyph(font, name, [uni], font[base].width, (), [(base, 0, 0)])
    # Gamma: L turned over (cap height 1490)
    if 'Gamma' in font:
        del font['Gamma']
    g = font.newGlyph('Gamma')
    g.width, g.unicodes = font['L'].width, [0x393]
    if oblique:
        # turning a slanted L over would slant it the other way: draw from the upright and slant
        up = upright['L']
        pts = []
        for c in up.contours:
            pts.append([(p.x, 1490 - p.y, p.type) for p in c.points])
        pen = g.getPointPen()
        for c in pts:
            pen.beginPath()
            rev = reverse([(x, y, t or 'offcurve', False) for x, y, t in c])
            for x, y, t, _ in rev:
                xx = x + (y - 559) * SLANT
                pen.addPoint((round(xx, 3), round(y, 3)), segmentType=None if t == 'offcurve' else t)
            pen.endPath()
    else:
        g.getPointPen().addComponent('L', (1, 0, 0, -1, 0, 1490))
    # drawn
    for name, spec in DRAWN.items():
        drawn(font, inter, name, spec, opsz, wght, deltas, style, oblique)
    # Theta: O + Inter's bar, centred on Allo's O
    bar, bar_corners = theta_bar(inter, opsz, wght)
    ob = bounds(measure, 'O')
    io, _, _ = inter.glyph('O', opsz, wght)
    ixs = [p[0] for c in io for p in c]
    shift = (ob[0] + ob[2]) / 2 - (min(ixs) + max(ixs)) / 2
    bar = [[(x + shift, y, t, s) for x, y, t, s in c] for c in bar]
    if oblique:
        bar = [[(x + (y - 559) * SLANT, y, t, s) for x, y, t, s in c] for c in bar]
    bar = [round_contour(c, cs, *style) for c, cs in zip(bar, bar_corners)]
    set_glyph(font, 'Theta', [0x398], font['O'].width, bar, [('O', 0, 0)])
    # spacing tonos (U+0384): tonos.top, with Inter's sidebearings and its _tonos anchor for the capitals
    offs, width = inter.component_offsets('tonos', opsz, wght)
    _, ia, _ = inter.glyph('tonos', opsz, wght)
    tb = bounds(font, 'tonos.top')
    it, _, _ = inter.glyph('tonos.top', opsz, wght)
    ixs = [p[0] for c in it for p in c]
    dx = min(ixs) - tb[0]  # keep Inter's left sidebearing
    tx, ty = ia['_tonos']
    set_glyph(font, 'tonos', [0x384], width, (), [('tonos.top', dx, 0)], [('_tonos', (tx + dx, ty))])
    # dieresis + tonos: one mark for ΐ ΰ, one spacing glyph U+0385
    db = bounds(font, 'dieresiscomb')
    offs, _ = inter.component_offsets('dieresistonos', opsz, wght)
    raise_ = offs[0][2]
    centre = (db[0] + db[2]) / 2
    tcx = (tb[0] + tb[2]) / 2
    if oblique:
        centre += raise_ * SLANT * 0  # the mark is slanted already; its centre moves with the raise below
    tdx = centre - tcx + raise_ * (SLANT if oblique else 0)
    ta = anchor(font, 'dieresiscomb', '_top')
    set_glyph(font, 'dieresistonos.top', (), 0, (), [('dieresiscomb', 0, 0), ('tonos.top', tdx, raise_)],
              [('_top', ta)])
    side = 120
    set_glyph(font, 'dieresistonos', [0x385], (db[2] - db[0]) + 2 * side, (),
              [('dieresistonos.top', side - db[0], 0)])
    # ano teleia: the period at x-height
    pb = bounds(font, 'period')
    xh = font.info.xHeight
    lift = xh - pb[3]
    set_glyph(font, 'anoteleia', [0x387], font['period'].width, (),
              [('period', lift * (SLANT if oblique else 0), lift)])
    # capitals with tonos
    for name, (base, latin, uni) in CAP_TONOS.items():
        iname = name
        offs, iwidth = inter.component_offsets(iname, opsz, wght)
        ibase_w = inter.glyph(offs[0][0], opsz, wght)[2]
        shift = offs[0][1]
        bx, by = anchor(font, latin, 'tonos')
        mx, my = anchor(font, 'tonos', '_tonos')
        width = font[base].width + (iwidth - ibase_w)
        set_glyph(font, name, [uni], width, (), [(base, shift, 0), ('tonos', shift + bx - mx, by - my)])
    # lowercase with marks, on the base's top anchor
    for name, (base, mark, uni) in LOWER_MARKS.items():
        source = ALIAS[base][0] if base in ALIAS else base
        bx, by = anchor(font, source, 'top')
        mx, my = anchor(font, mark, '_top')
        set_glyph(font, name, [uni], font[base].width, (), [(base, 0, 0), (mark, bx - mx, by - my)])


def shift_small(font, names):
    """opsz 9: the opsz 14 glyphs moved SMALL_SHIFT right, SMALL_SHIFT wider each side (release.json)."""
    d = SMALL_SHIFT
    for name in names:
        g = font[name]
        if not g.width:
            continue
        for c in g.contours:
            for p in c.points:
                p.x += d
        for a in g.anchors:
            a.x += d
        for c in g.components:
            bw = font[c.baseGlyph].width
            if not bw:
                t = c.transformation
                c.transformation = (t[0], t[1], t[2], t[3], t[4] + d, t[5])
        g.width += 2 * d


def register(font):
    """glyph order, mark categories, kerning groups, Greek language system."""
    order = list(font.lib.get('public.glyphOrder', []))
    order = [n for n in order if n not in GREEK] + GREEK
    font.lib['public.glyphOrder'] = order
    cats = font.lib.setdefault('public.openTypeCategories', {})
    for n in GREEK:
        cats[n] = 'mark' if n in MARKS else 'base'
    names = font.lib.setdefault('public.postscriptNames', {})
    for n in GREEK:
        g = font[n]
        if g.unicodes and not re.fullmatch(r'[A-Za-z]+', n):
            names[n] = 'uni%04X' % g.unicodes[0]
    # kerning groups
    for k in list(font.groups):
        font.groups[k] = [n for n in font.groups[k] if n not in GREEK]
    for name, (left, right) in KERN_PROXY.items():
        if name not in font:
            continue
        for side, proxy in (('public.kern2.', left), ('public.kern1.', right)):
            if not proxy:
                continue
            for k, members in font.groups.items():
                if k.startswith(side) and proxy in members:
                    if name not in members:
                        members.append(name)
                    break
    for k in list(font.groups):
        font.groups[k] = list(font.groups[k])
    fea = font.features.text
    if 'languagesystem grek dflt;' not in fea:
        font.features.text = fea.replace('languagesystem latn dflt;',
                                         'languagesystem grek dflt;\nlanguagesystem latn dflt;', 1)


# ---------------------------------------------------------------------------------------------------------------

STATIC_WEIGHTS = {'Thin': 100, 'ExtraLight': 200, 'Light': 300, 'Regular': 400, 'Medium': 490, 'SemiBold': 580,
                  'Bold': 670, 'ExtraBold': 780, 'Black': 900}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--inter', required=True, help='Inter-Roman.glyphspackage from github.com/rsms/inter (src/)')
    ap.add_argument('--only', help='only sources whose file name contains this')
    args = ap.parse_args()
    inter = Inter(args.inter)
    decide_corners(inter)

    ds = DesignSpaceDocument.fromfile(ROOT / 'sources/Allo.designspace')
    done = {}
    jobs = []
    for s in ds.sources:
        if s.layerName:
            continue
        loc = s.location
        jobs.append((ROOT / 'sources' / s.filename, loc['Optical size'], loc['Weight'], loc['Roundness']))
    jobs.sort(key=lambda j: j[1] == 9)  # opsz 9 after 14
    for path, opsz, wght, rond in jobs:
        if args.only and args.only not in path.name:
            continue
        font = ufoLib2.Font.open(path)
        if opsz == 9:
            twin = ufoLib2.Font.open(Path(str(path).replace('opsz9-', 'opsz14-')))
            for n in GREEK:
                if n in font:
                    del font[n]
            for n in GREEK:
                font.layers.defaultLayer.insertGlyph(twin[n], name=n, overwrite=True)
            shift_small(font, GREEK)
        else:
            style = corner_style(font)
            make(font, inter, opsz, wght, style, False)
        register(font)
        font.save()
        print('master', path.name)
    for path in sorted((ROOT / 'sources/static').glob('*.ufo')):
        if args.only and args.only not in path.name:
            continue
        stem = path.stem.replace('Allo-', '')
        oblique = stem.endswith('Oblique')
        wname = stem[:-len('Oblique')] if oblique else stem
        wname = wname or 'Regular'
        font = ufoLib2.Font.open(path)
        upright = ufoLib2.Font.open(ROOT / f'sources/static/Allo-{wname}.ufo') if oblique else None
        style = corner_style(upright or font)
        make(font, inter, 14, STATIC_WEIGHTS[wname], style, oblique, upright)
        register(font)
        font.save()
        print('static', path.name)


if __name__ == '__main__':
    main()
