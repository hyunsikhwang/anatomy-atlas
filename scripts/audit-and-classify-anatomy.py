"""Upgrade v6: source-verified deduplication, regional classification and spine.

Requires the v6 runtime pack and the attributed BodyParts3D atlas/chunk files.
All retained source vertices stay in their native coordinate frame.
"""
import copy
import gzip
import json
import pathlib
import re
import numpy as np

root = pathlib.Path('/workspace/scratch/anatomy-assets')
out = pathlib.Path('public/models')
meta = json.loads((out / 'anatomy-v6.json').read_text())
original = copy.deepcopy(meta)
records = {s['id']: s for s in meta}
manifest = json.loads((out / 'anatomy-v6-manifest.json').read_text())
raw = gzip.decompress(b''.join((out / pathlib.Path(f).name).read_bytes() for f in manifest['files']))
atlas = json.loads((root / 'atlas.json').read_text())
parts = {p['id']: p for p in atlas['parts']}
chunks = {}
changed = set()
moves = []
custom_buffers = {}

def component(id):
    p = parts[id]
    if p['chunk'] not in chunks:
        chunks[p['chunk']] = gzip.decompress((root / f"body-{p['chunk']}.bin.gz").read_bytes())
    b = chunks[p['chunk']]
    return (np.frombuffer(b, '<f4', p['vertexCount'] * 3, p['positions']).reshape(-1, 3),
            np.frombuffer(b, '<i2', p['vertexCount'] * 3, p['normals']),
            np.frombuffer(b, '<u4', p['indexCount'], p['indices']))

duplicates = [('FJ2772', 'FJ3201'), ('FJ2440', 'FJ2769'), ('FJ2386', 'FJ1916'), ('FJ1450', 'FJ2548')]
duplicate_results = []
for removed, retained in duplicates:
    a, b = component(removed), component(retained)
    assert np.array_equal(a[2], b[2]), (removed, retained, 'different connectivity')
    error = float(np.max(np.abs(a[0] - b[0])))
    assert error <= .0000011, (removed, retained, error)
    duplicate_results.append(dict(removed=removed, retained=retained, maxVertexDifferenceMeters=error))
    for s in meta:
        if removed in s.get('sourceIds', []):
            s['sourceIds'].remove(removed)
            changed.add(s['id'])

# Revision 5 added named thalami, amygdalae and corpus callosum as children.
# Include them in the non-rendered whole-brain aggregate/source inventory too.
brain_children = [s for s in meta if s.get('parentId') == 'brain']
brain_sources = list(dict.fromkeys(id for s in brain_children for id in s['sourceIds']))
brain_added = [id for id in brain_sources if id not in records['brain']['sourceIds']]
assert set(brain_added) == {'FJ1742', 'FJ1753', 'FJ1782', 'FJ1827', 'FJ1829'}
records['brain']['sourceIds'] += brain_added
changed.add('brain')

def move(id, source, destination, reason):
    assert source != destination
    records[source]['sourceIds'].remove(id)
    assert id not in records[destination]['sourceIds']
    records[destination]['sourceIds'].append(id)
    changed.update([source, destination])
    moves.append(dict(sourceId=id, name=parts[id]['name'], previous=source, corrected=destination, reason=reason))

for id in ['FJ3201', 'FJ2773', 'FJ2795']:
    move(id, 'skull', 'neck-bones', 'Hyoid/laryngeal anatomy belongs to the neck group')
records['skull'].update(name='머리 골격·치아', source='7-2-the-skull')
records['neck-bones'].update(description='', functions=['혀·후두 지지', '기도 유지·발성 보조'], source='7-2-the-skull')

# Use named anatomical regions, not the old center-height cutoffs. Physical
# laterality is preserved for FJ1469/FJ1469M, whose upstream names are reversed.
for s in list(meta):
    if s['layer'] != 1 or s.get('parentId'):
        continue
    for id in list(s['sourceIds']):
        n = parts[id]['name'].lower()
        side = 'left' if sum(b[0] for b in parts[id]['bounds']) > 0 else 'right'
        destination = s['id']
        if re.search(r'of (?:left|right) hand|flexor pollicis brevis|adductor pollicis|abductor pollicis brevis|opponens pollicis', n):
            destination = side + '-hand-muscles'
        elif re.search(r'deltoid|subscapularis|supraspinatus|infraspinatus|teres (?:minor|major)', n):
            destination = side + '-upper-muscles'
        elif 'gluteus' in n:
            destination = 'pelvic-muscles'
        elif 'fibularis tertius' in n:
            destination = side + '-calf-muscles'
        elif re.search(r'adductor minimus|pectineus', n):
            destination = side + '-thigh-muscles'
        elif re.search(r'trapezius|rhomboid|interspinalis thoracis|serratus posterior', n) or n == 'spinalis':
            destination = 'back-muscles'
        elif 'subclavius' in n:
            destination = 'chest-muscles'
        elif s['id'] == 'head-muscles' and re.search(r'capitis|cervic|colli|hyoid|digastric|aryepiglott|thyro-arytenoid', n):
            destination = 'neck-muscles'
        if destination != s['id']:
            move(id, s['id'], destination, 'Named regional anatomy replaces coordinate-threshold grouping')

for side in ['left', 'right']:
    ko = '왼쪽' if side == 'left' else '오른쪽'
    records[side + '-thigh-muscles'].update(name=ko + ' 넓적다리 근육·근막', source='11-6-appendicular-muscles-of-the-pelvic-girdle-and-lower-limbs')
    for region in ['upper', 'forearm', 'hand']:
        records[f'{side}-{region}-muscles']['source'] = '11-5-muscles-of-the-pectoral-girdle-and-upper-limbs'
    for region in ['calf', 'foot']:
        records[f'{side}-{region}-muscles']['source'] = '11-6-appendicular-muscles-of-the-pelvic-girdle-and-lower-limbs'
records['back-muscles']['name'] = '등·어깨띠 근육'
for id in ['head-muscles', 'neck-muscles', 'back-muscles']:
    records[id]['source'] = '11-3-axial-muscles-of-the-head-neck-and-back'
records['pelvic-muscles']['source'] = '11-6-appendicular-muscles-of-the-pelvic-girdle-and-lower-limbs'

def child(parent_id, key, name, en, ids, color, description, functions, source):
    parent = records[parent_id]
    id = parent_id + '--' + key
    assert id not in records and ids
    s = dict(id=id, parentId=parent_id, name=name, en=en, sex=parent['sex'], layer=parent['layer'],
             system=parent['system'], color=color, description=description, functions=functions,
             source=source, sourceIds=ids)
    records[id] = s
    meta.append(s)
    parent.setdefault('childrenIds', []).append(id)
    changed.add(id)

spine = records['spine']
spine.update(name='척추', en='Vertebral column', description='경추·흉추·요추 · 천골은 골반뼈 항목',
             functions=['머리·몸통 지지', '척수 보호', '몸통 운동·충격 흡수'], source='7-3-the-vertebral-column')
def spine_ids(predicate):
    return sorted([id for id in spine['sourceIds'] if predicate(parts[id]['name'].lower())],
                  key=lambda id: -sum(b[1] for b in parts[id]['bounds']))
cervical = spine_ids(lambda n: 'disk' not in n and ('cervical vertebra' in n or n in ['atlas', 'axis']))
thoracic = spine_ids(lambda n: 'disk' not in n and 'thoracic vertebra' in n)
lumbar = spine_ids(lambda n: 'disk' not in n and 'lumbar vertebra' in n)
discs = spine_ids(lambda n: 'intervertebral disk' in n)
assert [len(cervical), len(thoracic), len(lumbar), len(discs)] == [7, 12, 5, 23]
for key, name, en, ids, color, description, functions in [
    ('cervical', '경추 · C1–C7', 'Cervical vertebrae', cervical, '#84a89e', '7개 · C1 환추 · C2 축추', ['머리 지지·목 운동', '경부 척수 보호']),
    ('thoracic', '흉추 · T1–T12', 'Thoracic vertebrae', thoracic, '#a5a0be', '12개 · 갈비뼈 연결', ['흉곽 지지', '흉부 척수 보호']),
    ('lumbar', '요추 · L1–L5', 'Lumbar vertebrae', lumbar, '#bfaa7d', '5개 · 허리 부위', ['몸통 하중 지지', '허리 굽힘·폄']),
    ('discs', '추간판 · 23개', 'Intervertebral discs', discs, '#809eae', 'C2–C3부터 L5–S1까지', ['충격 흡수·하중 분산', '척추뼈 사이 움직임']),
]:
    child('spine', key, name, en, ids, color, description, functions, '7-3-the-vertebral-column')

child('neck-bones', 'hyoid', '목뿔뼈', 'Hyoid bone', ['FJ3201'], '#cfbf9f', '혀·후두 근육 부착', ['혀·후두 지지', '삼킴·발성 보조'], '7-2-the-skull')
child('neck-bones', 'laryngeal-cartilages', '후두 연골', 'Laryngeal cartilages',
      [id for id in records['neck-bones']['sourceIds'] if id != 'FJ3201'], '#a1b3a8', '윤상·갑상·피열·후두개 연골 등', ['후두 형태 유지', '기도 보호·발성 보조'], '22-1-organs-and-structures-of-the-respiratory-system')

def native(ids):
    ps, ns, ix, count = [], [], [], 0
    for id in ids:
        p, n, i = component(id)
        ps.append(p); ns.append(n); ix.append(i + count); count += len(p)
    v = np.concatenate(ps); lo, hi = v.min(0), v.max(0); center = (lo + hi) / 2
    return center, hi - lo, ((v - center).astype('<f4').tobytes(), np.concatenate(ns).astype('<i2').tobytes(), np.concatenate(ix).astype('<u4').tobytes())

# The original female traversal included node 432 both as node 431's child and
# as a second explicit root. Remove the duplicate using the original primitive
# counts; retain each unique position and normal byte, and rebase indices only.
female_manifest = json.loads((root / 'female-manifest.json').read_text())
vagina = records['vagina']
assert vagina['hraNodes'] == [431, 432, 432]
positions = np.frombuffer(raw, '<f4', vagina['vertexCount'] * 3, vagina['positions']).reshape(-1, 3)
normals = np.frombuffer(raw, '<i2', vagina['vertexCount'] * 3, vagina['normals']).reshape(-1, 3)
indices = np.frombuffer(raw, '<u4', vagina['indexCount'], vagina['indices'])
seen, unique_nodes, pbs, nbs, ibs = {}, [], [], [], []
old_vertex = old_index = new_vertex = 0
for node_id in vagina['hraNodes']:
    primitives = female_manifest['meshes'][female_manifest['nodes'][node_id]['mesh']]['primitives']
    nv = sum(female_manifest['accessors'][p['attributes']['POSITION']]['count'] for p in primitives)
    ni = sum(female_manifest['accessors'][p['indices']]['count'] for p in primitives)
    pb = positions[old_vertex:old_vertex + nv].tobytes()
    nb = normals[old_vertex:old_vertex + nv].tobytes()
    local_indices = indices[old_index:old_index + ni] - old_vertex
    assert local_indices.max() < nv
    identity = (pb, nb, local_indices.tobytes())
    if node_id in seen:
        assert seen[node_id] == identity, 'Repeated HRA node differs geometrically'
    else:
        seen[node_id] = identity; unique_nodes.append(node_id)
        pbs.append(pb); nbs.append(nb); ibs.append((local_indices + new_vertex).astype('<u4').tobytes())
        new_vertex += nv
    old_vertex += nv; old_index += ni
assert old_vertex == vagina['vertexCount'] and old_index == vagina['indexCount']
vagina['hraNodes'] = unique_nodes
vagina['vertexCount'] = new_vertex
vagina['indexCount'] = sum(len(b) for b in ibs) // 4
custom_buffers['vagina'] = (b''.join(pbs), b''.join(nbs), b''.join(ibs))
changed.add('vagina')

blobs, offset = [], 0
for s in meta:
    color_bytes = raw[s['colors']:s['colors'] + s['vertexCount'] * 3] if 'colors' in s else None
    if s['id'] in custom_buffers:
        pb, nb, ib = custom_buffers[s['id']]
    elif s['id'] in changed:
        assert color_bytes is None, 'Rebuilt colored geometry needs explicit color preservation'
        center, size, (pb, nb, ib) = native(s['sourceIds'])
        s.update(center=center.tolist(), size=size.tolist(), vertexCount=len(pb) // 12, indexCount=len(ib) // 4)
    else:
        pb = raw[s['positions']:s['positions'] + s['vertexCount'] * 12]
        nb = raw[s['normals']:s['normals'] + s['vertexCount'] * 6]
        ib = raw[s['indices']:s['indices'] + s['indexCount'] * 4]
    s.update(positions=offset, normals=offset + len(pb), indices=offset + len(pb) + len(nb) + (-len(nb)) % 4)
    blob = pb + nb + bytes((-len(nb)) % 4) + ib
    if color_bytes is not None:
        s['colors'] = offset + len(blob)
        blob += color_bytes + bytes((-len(color_bytes)) % 4)
    blobs.append(blob); offset += len(blob)

for parent in [s for s in meta if s.get('childrenIds')]:
    children = [records[id] for id in parent['childrenIds']]
    for c in children:
        c['detailOffset'] = ((np.array(c['center']) - parent['center']) * 1.1).tolist()
    parent['detailBounds'] = [
        np.min([np.array(c['center']) - np.array(c['size']) / 2 for c in children], axis=0).tolist(),
        np.max([np.array(c['center']) + np.array(c['size']) / 2 for c in children], axis=0).tolist(),
    ]

result = b''.join(blobs)
unchanged_checks = 0
for previous in original:
    if previous['id'] in changed:
        continue
    current = records[previous['id']]
    for field, length in [('positions', previous['vertexCount'] * 12), ('normals', previous['vertexCount'] * 6), ('indices', previous['indexCount'] * 4)] + ([('colors', previous['vertexCount'] * 3)] if 'colors' in previous else []):
        assert raw[previous[field]:previous[field] + length] == result[current[field]:current[field] + length]
    unchanged_checks += 1

packed = gzip.compress(result, compresslevel=9, mtime=0); files = []
for i, start in enumerate(range(0, len(packed), 12000000)):
    name = f'anatomy-v7-{i}.bin.part'
    (out / name).write_bytes(packed[start:start + 12000000]); files.append('/models/' + name)
(out / 'anatomy-v7.json').write_text(json.dumps(meta, ensure_ascii=False, separators=(',', ':')))
(out / 'anatomy-v7-manifest.json').write_text(json.dumps(dict(files=files, bytes=len(packed))))
scope_path = out.parent / 'substructure-scope.json'; scope = json.loads(scope_path.read_text())
scope['parentCounts'] = {s['id']: len(s['childrenIds']) for s in meta if s.get('childrenIds')}
scope['spine'] = {'cervicalVertebrae': 7, 'thoracicVertebrae': 12, 'lumbarVertebrae': 5, 'intervertebralDiscs': 23, 'sacrum': 'Retained in sex-specific pelvis references; no synthetic coccyx segmentation'}
scope_path.write_text(json.dumps(scope, ensure_ascii=False, indent=2))
audit = {
    'date': '2026-09-13', 'scope': 'Included reference structures: source identity, topology duplicates, regional grouping, laterality, sex filtering, geometry and selection',
    'duplicateSurfacesRemoved': duplicate_results, 'regionalReassignments': moves,
    'hraDuplicateNodesRemoved': [{'structure': 'vagina', 'node': 432, 'previousOccurrences': 2, 'correctedOccurrences': 1, 'retainedGeometry': 'Byte-identical positions and normals; indices rebased'}],
    'aggregateInventoryCorrection': {'parent': 'brain', 'includedExistingChildSources': brain_added, 'display': 'Existing child surfaces unchanged'},
    'sourceLabelExceptions': [{'ids': ['FJ1469', 'FJ1469M'], 'issue': 'Reversed left/right names in upstream thumb-muscle elements', 'handling': 'Native coordinates and correct physical side retained; assigned to intrinsic hand muscles'}],
    'spine': scope['spine'], 'unchangedGeometryByteChecks': unchanged_checks,
    'sources': ['https://github.com/ashemag/human-atlas', 'https://openstax.org/books/anatomy-and-physiology-2e/pages/7-3-the-vertebral-column', 'https://openstax.org/books/anatomy-and-physiology-2e/pages/11-3-axial-muscles-of-the-head-neck-and-back', 'https://openstax.org/books/anatomy-and-physiology-2e/pages/11-5-muscles-of-the-pectoral-girdle-and-upper-limbs', 'https://openstax.org/books/anatomy-and-physiology-2e/pages/11-6-appendicular-muscles-of-the-pelvic-girdle-and-lower-limbs'],
    'limits': ['Source-based educational audit, not clinical anatomical certification', 'Selected anatomy, not a complete inventory of all human organs, vessels, nerves or tissue layers', 'Common male-based reference plus documented HRA female pelvis and lung registrations; no claim of a complete female body scan', 'Reference shapes, gaps and source segmentation limits are preserved; no fabricated anatomy'],
}
(out.parent / 'model-audit.json').write_text(json.dumps(audit, ensure_ascii=False, indent=2))
print(json.dumps(dict(structures=len(meta), childSelections=sum(bool(s.get('parentId')) for s in meta), removedDuplicateSurfaces=len(duplicates)+1, regionalReassignments=len(moves), unchangedGeometryChecks=unchanged_checks, compressedBytes=len(packed))))
