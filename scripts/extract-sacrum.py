"""Extract v7 pelvic substructures using verified source component boundaries.

No new anatomy or segmentation planes: keep the original pelvic assembly and
reuse each supplied component once. The source counts/bounds are committed so
this migration does not depend on a previous scratch download.
"""
import gzip
import json
import pathlib
import numpy as np

out = pathlib.Path('public/models')
meta = json.loads((out / 'anatomy-v7.json').read_text())
manifest = json.loads((out / 'anatomy-v7-manifest.json').read_text())
raw = gzip.decompress(b''.join((out / pathlib.Path(f).name).read_bytes() for f in manifest['files']))
records = {s['id']: s for s in meta}
sources = json.loads(pathlib.Path('scripts/source-manifests/pelvis.json').read_text())
translation = np.array(json.loads(pathlib.Path('public/model-scope.json').read_text())['femaleTransform']['translation'])
blobs, offset = [raw], len(raw)
checks = []

def components(parent, provider):
    field = 'sourceIds' if provider == 'bodyParts3D' else 'hraNodes'
    definitions = {p['id']: p for p in sources[provider]['parts']}
    pos = np.frombuffer(raw, '<f4', parent['vertexCount'] * 3, parent['positions']).reshape(-1, 3)
    norm = np.frombuffer(raw, '<i2', parent['vertexCount'] * 3, parent['normals']).reshape(-1, 3)
    indices = np.frombuffer(raw, '<u4', parent['indexCount'], parent['indices'])
    vertex = index = 0
    result = {}
    for id in parent[field]:
        source = definitions[id]; nv, ni = source['vertexCount'], source['indexCount']
        v = pos[vertex:vertex + nv].astype('f8') + parent['center']
        ix = indices[index:index + ni].astype('i8') - vertex
        assert len(v) == nv and len(ix) == ni and ix.min() >= 0 and ix.max() < nv
        # BP3D atlas bounds precede simplification; use the verified packed
        # vertex bounds, not those wider pre-simplification envelopes.
        expected = np.array(source.get('packedBounds', source['bounds'])) + (translation if provider == 'hraFemale' else 0)
        error = float(np.max(np.abs(np.array([v.min(0), v.max(0)]) - expected)))
        assert error < 2e-6, (parent['id'], id, 'source boundary mismatch', error)
        result[id] = (v, norm[vertex:vertex + nv], ix.astype('<u4'))
        checks.append(dict(parent=parent['id'], sourceId=id, maxSourceBoundsErrorMeters=error))
        vertex += nv; index += ni
    assert vertex == parent['vertexCount'] and index == parent['indexCount']
    return result, field

def add(parent, component_map, field, key, name, en, source_ids, color, description, functions):
    global offset
    ps, ns, ix, count = [], [], [], 0
    for source_id in source_ids:
        p, n, i = component_map[source_id]
        ps.append(p); ns.append(n); ix.append(i + count); count += len(p)
    p = np.concatenate(ps); n = np.concatenate(ns); indices = np.concatenate(ix)
    lo, hi = p.min(0), p.max(0); center = (lo + hi) / 2
    local = (p - center).astype('<f4')
    assert np.max(np.abs(local.astype('f8') + center - p)) < 1e-7
    pb, nb, ib = local.tobytes(), n.astype('<i2').tobytes(), indices.astype('<u4').tobytes()
    id = parent['id'] + '--' + key
    s = dict(id=id, parentId=parent['id'], name=name, en=en, sex=parent['sex'], layer=0, system='골격계',
             color=color, description=description, functions=functions,
             source='7-3-the-vertebral-column' if key in ['sacrum', 'coccyx'] else '8-3-the-pelvic-girdle-and-pelvis',
             center=center.tolist(), size=(hi-lo).tolist(), vertexCount=len(p), indexCount=len(indices),
             positions=offset, normals=offset + len(pb), indices=offset + len(pb) + len(nb) + (-len(nb)) % 4,
             detailOffset=((center - parent['center']) * 1.1).tolist())
    s[field] = source_ids
    blob = pb + nb + bytes((-len(nb)) % 4) + ib
    blobs.append(blob); offset += len(blob); meta.append(s); records[id] = s
    parent.setdefault('childrenIds', []).append(id)

for parent_id, provider in [('pelvis', 'bodyParts3D'), ('female-pelvis', 'hraFemale')]:
    parent = records[parent_id]
    component_map, field = components(parent, provider)
    if provider == 'bodyParts3D':
        left, right, sacrum = ['FJ3288'], ['FJ3152'], ['FJ3393']
    else:
        left, right, sacrum = [967, 971, 975, 977, 982, 985], [968, 970, 974, 978, 981, 984], [963]
    add(parent, component_map, field, 'sacrum', '천골 · S1–S5', 'Sacrum · fused S1–S5', sacrum,
        '#b3a27b', '천추 5개 융합 · S1–S5 개별 경계 미구분', ['척추 하중을 골반으로 전달', '골반 뒷벽 형성'])
    if provider == 'hraFemale':
        add(parent, component_map, field, 'coccyx', '미추 · 꼬리뼈', 'Coccyx', [964],
            '#95a8a3', '천골 아래 · 남녀 공통 구조', ['골반저 근육·인대 부착'])
    add(parent, component_map, field, 'left-hip', '왼쪽 관골', 'Left hip bone', left,
        '#d0bea0', '장골·좌골·치골', ['체중 전달·골반 장기 보호'])
    add(parent, component_map, field, 'right-hip', '오른쪽 관골', 'Right hip bone', right,
        '#bcb393', '장골·좌골·치골', ['체중 전달·골반 장기 보호'])
    used = [id for child_id in parent['childrenIds'] for id in records[child_id][field]]
    assert len(used) == len(set(used)) and set(used) == set(parent[field])
    assert sum(records[id]['vertexCount'] for id in parent['childrenIds']) == parent['vertexCount']
    assert sum(records[id]['indexCount'] for id in parent['childrenIds']) == parent['indexCount']
    children = [records[id] for id in parent['childrenIds']]
    parent['detailBounds'] = [np.min([np.array(c['center'])-np.array(c['size'])/2 for c in children], axis=0).tolist(),
                              np.max([np.array(c['center'])+np.array(c['size'])/2 for c in children], axis=0).tolist()]
    parent['description'] = '좌우 관골·천골' + ('·미추' if provider == 'hraFemale' else '')
    parent['source'] = '8-3-the-pelvic-girdle-and-pelvis'

spine = records['spine']
spine['description'] = '경추·흉추·요추 · 천골·미추 바로가기'
spine['relatedIds'] = ['pelvis--sacrum', 'female-pelvis--sacrum', 'female-pelvis--coccyx']
notice = '미추 · 남녀 공통\n남성 원본 · 개별 형상 미제공'
spine['noticeBySex'] = {'male': notice}
records['pelvis']['noticeBySex'] = {'male': notice}

packed = gzip.compress(b''.join(blobs), compresslevel=9, mtime=0); files = []
for i, start in enumerate(range(0, len(packed), 12000000)):
    name = f'anatomy-v8-{i}.bin.part'; (out/name).write_bytes(packed[start:start+12000000]); files.append('/models/'+name)
(out/'anatomy-v8.json').write_text(json.dumps(meta,ensure_ascii=False,separators=(',',':')))
(out/'anatomy-v8-manifest.json').write_text(json.dumps(dict(files=files,bytes=len(packed))))
scope_path = out.parent/'substructure-scope.json'; scope = json.loads(scope_path.read_text())
scope['parentCounts'] = {s['id']:len(s['childrenIds']) for s in meta if s.get('childrenIds')}
scope['spine']['sacrum'] = 'Both original sacra individually selectable as fused S1–S5; linked from spine, rendered once within pelvic hierarchy'
scope['spine']['coccyx'] = 'Female HRA node 964 individually selectable; no separately supplied male surface; presence is not a sex difference'
scope['pelvicExtractionChecks'] = checks
scope_path.write_text(json.dumps(scope,ensure_ascii=False,indent=2))
print(json.dumps(dict(structures=len(meta),children=sum(bool(s.get('parentId')) for s in meta),pelvicSourceChecks=len(checks),compressedBytes=len(packed))))
