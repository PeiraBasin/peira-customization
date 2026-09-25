#!/usr/bin/env python3
"""Generate the Peira avatar: an attractor-basin contour map with a dotted
trial-trajectory descending into the basin. Pure stdlib, seeded, reproducible.

Concept: terrain = the basin (runner-up name, the shape); dotted path = peira,
the trial — the empirical trajectory that finds the basin by moving through it.
"""
import math, random, json

random.seed(1546201395210752162)  # the message that named me
W = 512
CX = CY = 256
R = 250

# ---- scalar field: sum of anisotropic gaussians over a disc ----
N = 180  # grid resolution
hills = []
for i in range(11):
    ang = random.uniform(0, 2*math.pi)
    rad = random.uniform(0, 0.75) * R
    hx = CX + rad*math.cos(ang)
    hy = CY + rad*math.sin(ang)
    hills.append({
        'x': hx, 'y': hy,
        'a': random.choice([1, -1]) * random.uniform(0.5, 1.0),
        'sx': random.uniform(40, 130),
        'sy': random.uniform(40, 130),
        'rot': random.uniform(0, math.pi),
    })

def field(x, y):
    v = 0.0
    for h in hills:
        dx, dy = x - h['x'], y - h['y']
        c, s = math.cos(h['rot']), math.sin(h['rot'])
        u = (dx*c + dy*s)**2 / (2*h['sx']**2)
        w = (-dx*s + dy*c)**2 / (2*h['sy']**2)
        v += h['a'] * math.exp(-(u + w))
    # radial containment: push values up near the rim so contours close inside
    d = math.hypot(x - CX, y - CY) / R
    v += 0.9 * d**8 + 0.25*math.sin(3*math.atan2(y-CY, x-CX)+1.2)*d**4
    return v

xs = [CX - R + (2*R)*i/(N-1) for i in range(N)]
ys = [CY - R + (2*R)*j/(N-1) for j in range(N)]
grid = [[field(x, y) for x in xs] for y in ys]

lo = min(min(r) for r in grid)
hi = max(max(r) for r in grid)

# ---- marching squares -> contour segments ----
def contour(level):
    segs = []
    for j in range(N-1):
        for i in range(N-1):
            v00, v10 = grid[j][i], grid[j][i+1]
            v01, v11 = grid[j+1][i], grid[j+1][i+1]
            idx = (v00 > level) | ((v10 > level) << 1) | ((v11 > level) << 2) | ((v01 > level) << 3)
            if idx in (0, 15):
                continue
            x0, x1 = xs[i], xs[i+1]
            y0, y1 = ys[j], ys[j+1]
            def ip(va, vb, pa, pb):
                if vb == va: return pa
                t = (level - va) / (vb - va)
                return pa + t*(pb - pa)
            top    = (ip(v00, v10, x0, x1), y0)
            right  = (x1, ip(v10, v11, y0, y1))
            bottom = (ip(v01, v11, x0, x1), y1)
            left   = (x0, ip(v00, v01, y0, y1))
            pts = []
            if idx in (1, 14): pts = [left, top]
            elif idx in (2, 13): pts = [top, right]
            elif idx in (3, 12): pts = [left, right]
            elif idx in (4, 11): pts = [right, bottom]
            elif idx in (5, 10): pts = [left, top, right, bottom]  # saddle: two segs
            elif idx in (6, 9): pts = [top, bottom]
            elif idx in (7, 8): pts = [left, bottom]
            if len(pts) == 4:
                segs.append((pts[0], pts[1])); segs.append((pts[2], pts[3]))
            elif len(pts) == 2:
                segs.append((pts[0], pts[1]))
    return segs

LEVELS = 14
contours = []
for k in range(1, LEVELS+1):
    lvl = lo + (hi - lo) * k / (LEVELS + 1)
    contours.append(contour(lvl))

# ---- trial trajectory: noisy gradient descent to the deepest local min ----
# find global min grid point inside disc
best = None
for j in range(1, N-1):
    for i in range(1, N-1):
        if math.hypot(xs[i]-CX, ys[j]-CY) < 0.85*R:
            if best is None or grid[j][i] < best[0]:
                best = (grid[j][i], xs[i], ys[j])
tx, ty = CX + 0.8*R*math.cos(2.4), CY + 0.8*R*math.sin(2.4)  # start near rim
path = [(tx, ty)]
step = 5.5
mx, my = 0.0, 0.0   # momentum for smooth curvature
for _ in range(400):
    gx = gy = 0.0
    i = max(1, min(N-2, int((tx - (CX-R)) / (2*R/(N-1)))))
    j = max(1, min(N-2, int((ty - (CY-R)) / (2*R/(N-1)))))
    gx = (grid[j][i+1] - grid[j][i-1]) / 2
    gy = (grid[j+1][i] - grid[j-1][i]) / 2
    g = math.hypot(gx, gy)
    if g < 1e-9: break
    nx, ny = -gx/g, -gy/g
    wander = random.gauss(0, 0.35)
    ca, sa = math.cos(wander), math.sin(wander)
    nx, ny = nx*ca - ny*sa, nx*sa + ny*ca
    mx, my = 0.72*mx + 0.28*nx, 0.72*my + 0.28*ny   # inertia smooths the descent
    m = math.hypot(mx, my) or 1.0
    tx, ty = tx + step*mx/m, ty + step*my/m
    if math.hypot(tx-CX, ty-CY) > 0.93*R:  # bounce off rim
        tx, ty = path[-1]
        continue
    path.append((tx, ty))
    if math.hypot(tx-best[1], ty-best[2]) < 6:
        break

# ---- SVG ----
def fmt(p): return f"{p[0]:.1f},{p[1]:.1f}"

svg = []
svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {W}" width="{W}" height="{W}">')
svg.append(f'  <defs><clipPath id="disc"><circle cx="{CX}" cy="{CY}" r="{R}"/></clipPath>'
           f'<radialGradient id="bg" cx="50%" cy="42%" r="75%">'
           f'<stop offset="0%" stop-color="#101a33"/><stop offset="100%" stop-color="#060a18"/>'
           f'</radialGradient></defs>')
svg.append(f'  <circle cx="{CX}" cy="{CY}" r="{R}" fill="url(#bg)"/>')
svg.append(f'  <g clip-path="url(#disc)">')
# filled bands: build from high (outer) to low (inner) so lows paint over highs
levels = [lo + (hi - lo) * k / (LEVELS + 1) for k in range(1, LEVELS+1)]
def region_paths(level):
    # filled region below level via even-odd on contour polylines is unreliable in
    # marching-squares output; instead paint each band as stroke-only thick strokes.
    return None
# bands as stacked translucent wide strokes (painter's algorithm, low on top)
for k in reversed(range(len(contours))):
    t = k / (LEVELS - 1)
    hue = 200 + 35*t
    light = 16 + 30*t
    d = " ".join(f"M{fmt(a)}L{fmt(b)}" for a, b in contours[k])
    svg.append(f'    <path d="{d}" fill="none" stroke="hsl({hue:.0f},80%,{light:.0f}%)" '
               f'stroke-opacity="0.55" stroke-width="16" stroke-linecap="round"/>')
# crisp contour lines on top
for k, segs in enumerate(contours):
    t = k / (LEVELS - 1)
    hue = 185 + 35*t
    light = 55 + 25*t
    d = " ".join(f"M{fmt(a)}L{fmt(b)}" for a, b in segs)
    svg.append(f'    <path d="{d}" fill="none" stroke="hsl({hue:.0f},85%,{light:.0f}%)" '
               f'stroke-opacity="{0.5+0.5*t:.2f}" stroke-width="{1.6+1.6*t:.1f}" stroke-linecap="round"/>')
# basin floor shading: fill innermost contour approx as polygon
if contours[-1]:
    # chain the innermost segments loosely into a polygon-ish blob via centroid sort
    pts = [a for a, b in contours[-1]]
    cxm = sum(pt[0] for pt in pts)/len(pts); cym = sum(pt[1] for pt in pts)/len(pts)
    pts.sort(key=lambda q: math.atan2(q[1]-cym, q[0]-cxm))
    poly = " ".join(fmt(q) for q in pts)
    svg.append(f'    <polygon points="{poly}" fill="#04070f" fill-opacity="0.75"/>')
# trial trajectory: amber dots growing toward arrival (a settling, not a march)
n = len(path)
for idx, pt in enumerate(path):
    t = idx / (n - 1)
    r = 1.6 + 4.6*t*t
    op = 0.45 + 0.55*t
    svg.append(f'    <circle cx="{pt[0]:.1f}" cy="{pt[1]:.1f}" r="{r:.1f}" '
               f'fill="#f5a623" fill-opacity="{op:.2f}"/>')
svg.append('  </g>')
# landing point with glow
ex, ey = path[-1]
svg.append(f'  <circle cx="{ex:.1f}" cy="{ey:.1f}" r="16" fill="#f5a623" fill-opacity="0.22"/>')
svg.append(f'  <circle cx="{ex:.1f}" cy="{ey:.1f}" r="8.5" fill="#f5a623"/>')
svg.append(f'  <circle cx="{ex:.1f}" cy="{ey:.1f}" r="3.2" fill="#fff4e0"/>')
svg.append(f'  <circle cx="{CX}" cy="{CY}" r="{R}" fill="none" stroke="#2a3a5c" stroke-width="4"/>')
svg.append('</svg>')

out = "/opt/data/projects/peira-customization/avatar/peira-avatar.svg"
open(out, "w").write("\n".join(svg))
print(f"wrote {out}")
print(f"contour levels: {len(contours)}, segs per level: {[len(c) for c in contours]}")
print(f"trajectory: {len(path)} pts, start=({path[0][0]:.0f},{path[0][1]:.0f}), end=({ex:.0f},{ey:.0f}), basin_min=({best[1]:.0f},{best[2]:.0f})")
