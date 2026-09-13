"""Derive envelope samples for OPTIONAL educational cutaways; never edit source meshes.

The radii come from convex envelopes of current HRA surface cross-sections, in
their registered frame. They constrain an illustrative loft, not measured layers.
"""
import gzip
import hashlib
import json
from pathlib import Path
import numpy as np
from scipy.spatial import ConvexHull

ROOT = Path(__file__).resolve().parents[1]
meta = json.loads((ROOT / 'public/models/anatomy-v13.json').read_text())
manifest = json.loads((ROOT / 'public/models/anatomy-v13-manifest.json').read_text())
packed = b''.join((ROOT / ('public' + f)).read_bytes() for f in manifest['files'])
raw = gzip.decompress(packed)
structures = {s['id']: s for s in meta}

def geometry(ids):
    vertices, triangles = [], []
    for id in ids:
        s = structures[id]
        p = np.frombuffer(raw, '<f4', s['vertexCount'] * 3, s['positions']).reshape(-1, 3).astype(float) + s['center']
        i = np.frombuffer(raw, '<u4', s['indexCount'], s['indices']).reshape(-1, 3)
        vertices.append(p)
        triangles.append(p[i])
    return np.concatenate(vertices), np.concatenate(triangles)

def sample(root, ids, axis, origin, internal_os=None, external_os=None):
    p, triangles = geometry(ids)
    axis = np.array(axis, dtype=float); axis /= np.linalg.norm(axis)
    right = np.array([1., 0., 0.]); right -= axis * right.dot(axis); right /= np.linalg.norm(right)
    front = np.cross(right, axis)
    frame = np.stack([right, front, axis], axis=1)
    local = (triangles - origin) @ frame
    h = (p - origin) @ axis
    # Slightly inset from source extrema: the source envelopes have closed tips.
    lo, hi = h.min() + .0005, h.max() - .0003
    if root == 'uterus':
        lo = 0.  # The cervical channel opens at the supplied external-os landmark.
    elif external_os is not None:
        hi = float((external_os-origin) @ axis)
    heights = np.linspace(lo, hi, 105)
    split = float((np.array(internal_os) - origin) @ axis) if internal_os is not None else None
    if split is not None:
        heights = np.unique(np.r_[heights, split])
    rows = []
    for height in heights:
        segs = []
        crossing = local[(local[:, :, 2].min(axis=1) < height) & (local[:, :, 2].max(axis=1) > height)]
        for tri in crossing:
            points = []
            for a, b in [(0, 1), (1, 2), (2, 0)]:
                pa, pb = tri[a], tri[b]
                if (pa[2] < height) != (pb[2] < height):
                    points.append((pa + (pb-pa) * ((height-pa[2])/(pb[2]-pa[2])))[:2])
            if len(points) == 2:
                segs.append(points)
        segs = np.array(segs)
        assert len(segs), (root, height)
        # Some source surfaces form thin walls and overlapping component loops.
        # A convex section ENVELOPE avoids tracking a wall as if it were the lumen.
        # This is deliberately an approximate loft; original surfaces remain separate.
        points = segs.reshape(-1, 2)
        polygon = points[ConvexHull(points).vertices]
        other = np.roll(polygon, -1, axis=0)
        cross = polygon[:, 0]*other[:, 1]-other[:, 0]*polygon[:, 1]
        center = ((polygon+other)*cross[:, None]).sum(axis=0)/(3*cross.sum())
        if root == 'uterus':
            # Anchor the schematic channel at BOTH supplied cervical-os landmarks.
            at_os = ((np.array(internal_os)-origin) @ frame)[:2]
            if height <= split:
                center = at_os * height/split
            else:
                blend = min(1., (height-split)/(hi-split)*5)
                center = at_os*(1-blend)+center*blend
        elif external_os is not None:
            blend = max(0., ((height-lo)/(hi-lo)-.8)/.2)
            at_os = ((external_os-origin) @ frame)[:2]
            center = center*(1-blend)+at_os*blend
        segs = np.stack([polygon, other], axis=1)
        a, b = segs[:, 0] - center, segs[:, 1] - center
        edge = b-a
        radii = []
        for angle in np.arange(64) * 2*np.pi/64:
            direction = np.array([np.sin(angle), np.cos(angle)])
            den = direction[0]*edge[:, 1] - direction[1]*edge[:, 0]
            valid = abs(den) > 1e-12
            r = np.divide(a[:, 0]*edge[:, 1]-a[:, 1]*edge[:, 0], den, out=np.zeros(len(a)), where=valid)
            u = np.divide(a[:, 0]*direction[1]-a[:, 1]*direction[0], den, out=np.zeros(len(a)), where=valid)
            hits = r[valid & (r > 0) & (u >= -1e-6) & (u <= 1+1e-6)]
            assert len(hits), (root, height, angle)
            radii.append(float(hits.max()))
        world = origin + axis*height + right*center[0] + front*center[1]
        rows.append({'t': float((height-lo)/(hi-lo)), 'center': world.tolist(), 'radii': radii})
    return {'root': root, 'sourceIds': ids, 'right': right.tolist(), 'front': front.tolist(), 'axis': axis.tolist(),
            'split': float((split-lo)/(hi-lo)) if split is not None else None, 'rows': rows}

external_os = np.array([-.00199864, .89064944, -.02424901])
fundus = np.array(structures['uterus--fundus']['center'])
profiles = [sample('vagina', ['vagina'], [0, 1, 0], np.zeros(3), external_os=external_os),
            sample('uterus', ['uterus--body', 'uterus--fundus', 'uterus--cervix'], fundus-external_os, external_os,
                   [-.00225804, .89911324, -.01051247])]
output = {'kind': 'educational-schematic-envelope', 'method': 'convex envelope of source cross-sections; illustrative inner contours', 'sourceSha256': hashlib.sha256(packed).hexdigest(),
          'units': 'meters', 'profiles': profiles}
path = ROOT / 'public/models/diagram-profiles-v1.json'
path.write_text(json.dumps(output, separators=(',', ':')) + '\n')
print(json.dumps({'profiles': [{k: p[k] for k in ['root', 'split']} for p in profiles], 'bytes': path.stat().st_size}))
