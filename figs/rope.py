"""Tiny 3D rope renderer: ropes are lists of (x, y, z) control points; pieces are painted in
depth order so over/under crossings come out right by construction."""
def catmull(pts, n=10):
    out = []
    P = [pts[0]] + pts + [pts[-1]]
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i-1], P[i], P[i+1], P[i+2]
        for k in range(n):
            t = k / n
            out.append(tuple(0.5 * ((2*p1[j]) + (-p0[j]+p2[j])*t + (2*p0[j]-5*p1[j]+4*p2[j]-p3[j])*t*t
                       + (-p0[j]+3*p1[j]-3*p2[j]+p3[j])*t**3) for j in range(3)))
    out.append(pts[-1])
    return out

def rope_svg(ropes, width=7, n=10):
    """ropes: list of (points, cls). Returns svg markup."""
    pieces = []
    for pts, cls in ropes:
        dense = catmull(pts, n)
        # one piece per control-point span
        for i in range(len(pts) - 1):
            seg = dense[i*n:(i+1)*n+1]
            z = sum(p[2] for p in seg) / len(seg)
            first, last = i == 0, i == len(pts) - 2
            pieces.append((z, seg, cls, first, last))
    pieces.sort(key=lambda p: p[0])
    out = []
    for idx, (z, seg, cls, first, last) in enumerate(pieces):
        d = 'M' + ' L'.join(f'{x:.1f} {y:.1f}' for x, y, _ in seg)
        # fill runs a little past each joint so no hairline seams show between pieces
        ext = list(seg)
        if not first:
            (x0, y0, _), (x1, y1, _) = seg[0], seg[1]
            ext.insert(0, (x0 - (x1 - x0) * 0.6, y0 - (y1 - y0) * 0.6, 0))
        if not last:
            (x0, y0, _), (x1, y1, _) = seg[-1], seg[-2]
            ext.append((x0 - (x1 - x0) * 0.6, y0 - (y1 - y0) * 0.6, 0))
        de = 'M' + ' L'.join(f'{x:.1f} {y:.1f}' for x, y, _ in ext)
        out.append(f'<path d="{d}" class="ro" stroke-width="{width+3}" stroke-linecap="butt"/>')
        for end in ([seg[0]] if first else []) + ([seg[-1]] if last else []):
            out.append(f'<circle cx="{end[0]:.1f}" cy="{end[1]:.1f}" r="{(width+3)/2}" class="rof"/>')
        out.append(f'<path d="{de}" class="{cls}" stroke-width="{width}" stroke-linecap="butt"/>')
        for end in ([seg[0]] if first else []) + ([seg[-1]] if last else []):
            out.append(f'<circle cx="{end[0]:.1f}" cy="{end[1]:.1f}" r="{width/2}" class="{cls}f"/>')
    return '\n'.join(out)
