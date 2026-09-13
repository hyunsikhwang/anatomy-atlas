"""Undo independent lung stretches; retain HRA bilateral geometry at native scale.

Migration input: v11 assets from the preceding git revision and the source JSON
manifests used by the original importer. No anatomy is resized to a clinical norm.
"""
import copy
import gzip
import hashlib
import json
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'public/models'
CACHE = ROOT / '.sites-runtime/anatomy-sources'
meta = json.loads((OUT / 'anatomy-v11.json').read_text())
old = copy.deepcopy(meta)
by_id = {s['id']: s for s in meta}
old_by_id = {s['id']: s for s in old}
manifest = json.loads((OUT / 'anatomy-v11-manifest.json').read_text())
old_packed = b''.join((ROOT / ('public'+f)).read_bytes() for f in manifest['files'])
original = gzip.decompress(old_packed)
raw = bytearray(original)
hra = json.loads((CACHE / 'female-manifest.json').read_text())
bp = {s['id']: s for s in json.loads((CACHE / 'atlas.json').read_text())['parts']}
roots = ['left-lung', 'right-lung']
excluded = ['FJ2041', 'FJ2044']
source = {}
reference = {}
for root in roots:
    ids = [n for n in (range(851,866) if root=='left-lung' else range(867,884)) if 'mesh' in hra['nodes'][n]]
    bounds = []
    for ni in ids:
        n = hra['nodes'][ni]
        assert not any(k in n for k in ['matrix','translation','rotation','scale'])
        for primitive in hra['meshes'][n['mesh']]['primitives']:
            a = hra['accessors'][primitive['attributes']['POSITION']]
            bounds.append(np.array([a['min'], a['max']]))
    lo, hi = np.min([b[0] for b in bounds],axis=0), np.max([b[1] for b in bounds],axis=0)
    source[root] = {'nodes':ids, 'bounds':[lo.tolist(),hi.tolist()], 'center':(lo+hi)/2, 'size':hi-lo}
    kept = [i for i in old_by_id[root]['sourceIds'] if i not in excluded]
    ref_lo = np.min([bp[i]['bounds'][0] for i in kept],axis=0)
    ref_hi = np.max([bp[i]['bounds'][1] for i in kept],axis=0)
    reference[root] = {'ids':kept, 'bounds':[ref_lo.tolist(),ref_hi.tolist()]}

# One translation of the WHOLE pair. Both donors use meters/Y-up. Do not fit
# independent x/y/z scales to bronchovascular extents or enforce a volume ratio.
source_lo = np.min([s['bounds'][0] for s in source.values()],axis=0)
source_hi = np.max([s['bounds'][1] for s in source.values()],axis=0)
ref_lo = np.min([s['bounds'][0] for s in reference.values()],axis=0)
ref_hi = np.max([s['bounds'][1] for s in reference.values()],axis=0)
translation = (ref_lo+ref_hi-source_lo-source_hi)/2
corrected = []
for s in meta:
    root = s['id'] if s['id'] in roots else s.get('parentId')
    if root not in roots:
        continue
    par, src = old_by_id[root], source[root]
    old_scale = np.array(par['size'])/src['size']
    local = np.frombuffer(original,'<f4',s['vertexCount']*3,s['positions']).reshape(-1,3).astype(float)
    old_normal = np.frombuffer(original,'<i2',s['vertexCount']*3,s['normals']).reshape(-1,3).astype(float)/32767
    native = (local+np.array(s['center'])-np.array(par['center']))/old_scale+src['center']
    world = native+translation
    lo, hi = world.min(axis=0), world.max(axis=0)
    center = (lo+hi)/2
    positions = (world-center).astype('<f4').tobytes()
    normals = old_normal*old_scale
    normals /= np.maximum(np.linalg.norm(normals,axis=1,keepdims=True),1e-20)
    normals = np.rint(np.clip(normals,-1,1)*32767).astype('<i2').tobytes()
    raw[s['positions']:s['positions']+len(positions)] = positions
    raw[s['normals']:s['normals']+len(normals)] = normals
    s['center'], s['size'] = center.tolist(), (hi-lo).tolist()
    s['surfaceSource'] = 'HRA united-female v1.5; native bilateral proportions, one shared translation (revision 13)'
    if s['id']==root:
        s.pop('sourceIds',None)  # Old BP IDs described alignment references, not this mesh.
        s['lungNodes'] = src['nodes']
        s['registrationReferenceIds'] = reference[root]['ids']
        s['modelNote'] = ('오른쪽 3엽 · 상대적으로 넓고 짧음' if root=='right-lung' else '왼쪽 2엽 · 심장패임')
    corrected.append(s['id'])
for root in roots:
    parent = by_id[root]
    children = [s for s in meta if s.get('parentId')==root]
    for child in children:
        child['detailOffset'] = ((np.array(child['center'])-parent['center'])*1.1).tolist()
    parent['detailBounds'] = [np.min([np.array(c['center'])-np.array(c['size'])/2 for c in children],axis=0).tolist(),
                              np.max([np.array(c['center'])+np.array(c['size'])/2 for c in children],axis=0).tolist()]

# All triangles and every other structure's positions/normals stay byte-identical.
for s in meta:
    n = s['indexCount']*4
    assert raw[s['indices']:s['indices']+n] == original[s['indices']:s['indices']+n]
    if s['id'] not in corrected:
        for field,n in [('positions',s['vertexCount']*12),('normals',s['vertexCount']*6)]:
            assert raw[s[field]:s[field]+n] == original[s[field]:s[field]+n]
        assert s==old_by_id[s['id']]

def measures(s,data):
    p = np.frombuffer(data,'<f4',s['vertexCount']*3,s['positions']).reshape(-1,3).astype(float)
    i = np.frombuffer(data,'<u4',s['indexCount'],s['indices']).reshape(-1,3)
    tri = p[i]
    signed = abs(np.einsum('ij,ij->i',tri[:,0],np.cross(tri[:,1],tri[:,2])).sum()/6)
    return {'dimensionsCm':(np.array(s['size'])*100).tolist(), 'center':s['center'], 'signedMeshVolumeCm3':signed*1e6}

packed = gzip.compress(raw,compresslevel=9,mtime=0)
files = []
for i,start in enumerate(range(0,len(packed),12000000)):
    name = f'anatomy-v13-{i}.bin.part'
    (OUT/name).write_bytes(packed[start:start+12000000]); files.append('/models/'+name)
(OUT/'anatomy-v13-manifest.json').write_text(json.dumps({'files':files,'bytes':len(packed)}))
(OUT/'anatomy-v13.json').write_text(json.dumps(meta,ensure_ascii=False,separators=(',',':')))

audit = {
    'revision':13, 'review':'Bilateral lung size and source registration',
    'cause':'The old right-lung reference bounds included FJ2041/FJ2044 far below the thoracic bronchial trees. Independent per-axis fits then stretched the right lung vertically and shifted it inferiorly; the left lung used a different stretch.',
    'excludedAlignmentReferences':[{k:bp[i][k] for k in ['id','name','conceptId','bounds']} for i in excluded],
    'source':'HRA united-female v1.5, DOI 10.48539/HBM352.BTSQ.586, CC BY 4.0',
    'sourceBounds':{root:{k:v for k,v in src.items() if k in ['nodes','bounds']} for root,src in source.items()},
    'referenceBounds':reference,
    'previousAxisScales':{root:(np.array(old_by_id[root]['size'])/source[root]['size']).tolist() for root in roots},
    'registration':{'scale':1.0,'rotation':'identity','translation':translation.tolist(),'method':'Pairwise source envelope center translated to the combined valid BP bronchovascular envelope center; no separate lung transforms.'},
    'before':{root:measures(old_by_id[root],original) for root in roots},
    'after':{root:measures(by_id[root],raw) for root in roots},
    'correctedStructures':corrected,'unchangedStructures':len(meta)-len(corrected),'allTriangleIndicesUnchanged':True,
    'beforePackSha256':hashlib.sha256(old_packed).hexdigest(),'afterPackSha256':hashlib.sha256(packed).hexdigest(),
    'limits':['Composite donor reference; the shared translation is not a clinically validated registration.',
              'Signed surface-mesh volumes are geometry diagnostics, not lung capacity or population reference values.',
              'Source geometry and relative proportions are recovered within the previous float/normal quantization precision.',
              'The two excluded BP arterial meshes are removed only from alignment references; their biological attribution is not changed by this migration.'],
    'medicalSources':['https://www.nhlbi.nih.gov/health/lungs/respiratory-system','https://my.clevelandclinic.org/health/body/8960-lungs']
}
(ROOT/'public/lung-audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n')
# The genital profiles are unchanged; only their whole-pack provenance checksum advances.
profiles_path = OUT/'diagram-profiles-v1.json'
profiles = json.loads(profiles_path.read_text());profiles['sourceSha256']=audit['afterPackSha256']
profiles_path.write_text(json.dumps(profiles,separators=(',',':'))+'\n')
print(json.dumps({'corrected':len(corrected),'unchanged':len(meta)-len(corrected),'translation':translation.tolist(),
                 'before':audit['before'],'after':audit['after'],'compressedBytes':len(packed)},ensure_ascii=False))
