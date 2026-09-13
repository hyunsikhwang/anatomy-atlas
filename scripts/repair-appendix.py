"""Repair the v5 bowel hierarchy using unmodified native BodyParts3D surfaces.

Input: v5 runtime pack, atlas.json and body-9.bin.gz. Output: v6 runtime pack.
The upstream cecum concept (FMA14541) resolves to the ileocecal-junction mesh.
Do not synthesize a cecal boundary or move the appendix to a guessed position.
"""
import argparse
import copy
import gzip
import hashlib
import json
import pathlib
import numpy as np

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source', type=pathlib.Path, default=pathlib.Path('/workspace/scratch/anatomy-assets'))
parser.add_argument('--models', type=pathlib.Path, default=pathlib.Path('public/models'))
args = parser.parse_args()
out = args.models
meta = json.loads((out / 'anatomy-v5.json').read_text())
manifest = json.loads((out / 'anatomy-v5-manifest.json').read_text())
raw = gzip.decompress(b''.join((out / pathlib.Path(f).name).read_bytes() for f in manifest['files']))
original = copy.deepcopy(meta)
records = {s['id']: s for s in meta}
atlas = json.loads((args.source / 'atlas.json').read_text())
parts = {p['id']: p for p in atlas['parts']}
concepts = {c['id']: c for c in atlas['concepts']}
assert concepts['FMA14542']['elements'] == ['FJ2565']
assert concepts['FMA14541']['elements'] == ['FJ2599']
chunk_path = args.source / 'body-9.bin.gz'
chunk = gzip.decompress(chunk_path.read_bytes())

def native(ids):
    positions, normals, indices, count = [], [], [], 0
    for id in ids:
        p = parts[id]
        assert p['chunk'] == 9
        positions.append(np.frombuffer(chunk, '<f4', p['vertexCount'] * 3, p['positions']).reshape(-1, 3))
        normals.append(np.frombuffer(chunk, '<i2', p['vertexCount'] * 3, p['normals']))
        indices.append(np.frombuffer(chunk, '<u4', p['indexCount'], p['indices']) + count)
        count += p['vertexCount']
    v = np.concatenate(positions)
    lo, hi = v.min(0), v.max(0)
    center = (lo + hi) / 2
    return center, hi - lo, ((v - center).astype('<f4').tobytes(), np.concatenate(normals).astype('<i2').tobytes(), np.concatenate(indices).astype('<u4').tobytes())

# The junction was previously grouped under the common ileum, duplicating the
# native male cecal region in the female configuration. Assign it to male colon.
changed = {'small-intestine', 'small-intestine--ileum', 'large-intestine'}
for id in ['small-intestine', 'small-intestine--ileum']:
    records[id]['sourceIds'].remove('FJ2599')
colon = records['large-intestine']
colon['sourceIds'] += ['FJ2599', 'FJ2565']
for suffix, name, en, source_id, color, description, functions in [
    ('cecum', '맹장', 'Cecum', 'FJ2599', '#b2ac83', '회맹접합부 참조형', ['소장 내용물 수용']),
    ('appendix', '충수', 'Appendix', 'FJ2565', '#7296ac', '맹장에 연결 · 남녀 공통', ['장관 면역에 관여']),
]:
    id = 'large-intestine--' + suffix
    s = dict(id=id, parentId=colon['id'], name=name, en=en, sex='male', layer=2,
             system='소화계', color=color, description=description, functions=functions,
             source=colon['source'], sourceIds=[source_id])
    if suffix == 'cecum':
        s['referenceNote'] = 'BodyParts3D FMA14541 · FJ2599 회맹접합부 표면'
    meta.append(s)
    records[id] = s
    changed.add(id)
colon['childrenIds'] = ['large-intestine--cecum', 'large-intestine--appendix'] + colon['childrenIds']
for id in ['large-intestine', 'female-large-intestine']:
    records[id]['description'] = '맹장·충수·결장·직장'
records['female-large-intestine--appendix']['description'] = '맹장에 연결 · 남녀 공통'

# Repack every record; unchanged vertex/index/color bytes remain identical.
blobs, offset, unchanged_checks = [], 0, 0
for s in meta:
    color_bytes = raw[s['colors']:s['colors'] + s['vertexCount'] * 3] if 'colors' in s else None
    if s['id'] in changed:
        center, size, (pb, nb, ib) = native(s['sourceIds'])
        s.update(center=center.tolist(), size=size.tolist(), vertexCount=len(pb) // 12, indexCount=len(ib) // 4)
    else:
        pb = raw[s['positions']:s['positions'] + s['vertexCount'] * 12]
        nb = raw[s['normals']:s['normals'] + s['vertexCount'] * 6]
        ib = raw[s['indices']:s['indices'] + s['indexCount'] * 4]
        unchanged_checks += 1
    s.update(positions=offset, normals=offset + len(pb), indices=offset + len(pb) + len(nb) + (-len(nb)) % 4)
    blob = pb + nb + bytes((-len(nb)) % 4) + ib
    if color_bytes is not None:
        s['colors'] = offset + len(blob)
        blob += color_bytes + bytes((-len(color_bytes)) % 4)
    blobs.append(blob)
    offset += len(blob)

for parent_id in ['small-intestine', 'large-intestine']:
    parent = records[parent_id]
    children = [s for s in meta if s.get('parentId') == parent_id]
    for child in children:
        child['detailOffset'] = ((np.array(child['center']) - parent['center']) * 1.1).tolist()
    parent['detailBounds'] = [
        np.min([np.array(c['center']) - np.array(c['size']) / 2 for c in children], axis=0).tolist(),
        np.max([np.array(c['center']) + np.array(c['size']) / 2 for c in children], axis=0).tolist(),
    ]

result = b''.join(blobs)
for previous in original:
    if previous['id'] in changed:
        continue
    current = records[previous['id']]
    for field, length in [('positions', previous['vertexCount'] * 12), ('normals', previous['vertexCount'] * 6), ('indices', previous['indexCount'] * 4)] + ([('colors', previous['vertexCount'] * 3)] if 'colors' in previous else []):
        assert raw[previous[field]:previous[field] + length] == result[current[field]:current[field] + length], (previous['id'], field)

packed = gzip.compress(result, compresslevel=9, mtime=0)
files = []
for i, start in enumerate(range(0, len(packed), 12000000)):
    name = f'anatomy-v6-{i}.bin.part'
    (out / name).write_bytes(packed[start:start + 12000000])
    files.append('/models/' + name)
(out / 'anatomy-v6-manifest.json').write_text(json.dumps(dict(files=files, bytes=len(packed))))
(out / 'anatomy-v6.json').write_text(json.dumps(meta, ensure_ascii=False, separators=(',', ':')))
scope_path = out.parent / 'substructure-scope.json'
scope = json.loads(scope_path.read_text())
scope['parentCounts']['large-intestine'] = 7
scope['appendixCorrection'] = {
    'maleAppendix': 'BodyParts3D FJ2565, FMA14542; original native coordinates',
    'maleCecum': 'BodyParts3D FMA14541 resolves to FJ2599 ileocecal junction; moved from common ileum to male colon',
    'femaleAppendix': 'Existing HRA node 490 and cecum node 493; geometry and registration unchanged',
    'sourceChunkSha256': hashlib.sha256(chunk_path.read_bytes()).hexdigest(),
    'sexRule': 'One appendix and one cecum in each sex configuration; presence is not a sex difference',
}
scope_path.write_text(json.dumps(scope, ensure_ascii=False, indent=2))
print(json.dumps(dict(structures=len(meta), childSelections=sum(bool(s.get('parentId')) for s in meta), unchangedGeometryChecks=unchanged_checks, compressedBytes=len(packed))))
