"""Review v8 source geometry and append corrected groups for viewer revision 11.

Uses cached, attributed BP3D chunks and the HRA GLB JSON manifest. No source
surface is stretched, sculpted, or moved to imitate an educational cutaway.
"""
import copy, gzip, hashlib, json, pathlib
import numpy as np
from scipy.spatial import cKDTree

root=pathlib.Path('.sites-runtime/anatomy-sources');out=pathlib.Path('public/models')
meta=json.loads((out/'anatomy-v8.json').read_text());original=copy.deepcopy(meta)
records={s['id']:s for s in meta}
manifest=json.loads((out/'anatomy-v8-manifest.json').read_text())
raw=gzip.decompress(b''.join(pathlib.Path('public'+f).read_bytes() for f in manifest['files']))
atlas=json.loads((root/'atlas.json').read_text());parts={p['id']:p for p in atlas['parts']}
g=json.loads((root/'female-manifest.json').read_text())
chunks={i:gzip.decompress((root/f'body-{i}.bin.gz').read_bytes()) for i in range(15)}
blobs=[raw];offset=len(raw);changes=[]

def bp(id):
    p=parts[id];b=chunks[p['chunk']]
    return (np.frombuffer(b,'<f4',p['vertexCount']*3,p['positions']).reshape(-1,3),
        np.frombuffer(b,'<i2',p['vertexCount']*3,p['normals']).reshape(-1,3),
        np.frombuffer(b,'<u4',p['indexCount'],p['indices']))

def append(s,components):
    global offset
    ps,ns,ix,count=[],[],[],0
    for p,n,i in components:
        ps.append(p);ns.append(n);ix.append(i+count);count+=len(p)
    p=np.concatenate(ps).astype('f8');n=np.concatenate(ns).astype('<i2');i=np.concatenate(ix).astype('<u4')
    lo,hi=p.min(0),p.max(0);center=(lo+hi)/2;local=(p-center).astype('<f4')
    assert np.max(np.abs(local.astype('f8')+center-p))<1e-7
    pb,nb,ib=local.tobytes(),n.tobytes(),i.tobytes();pad=bytes(-len(nb)%4)
    s.update(center=center.tolist(),size=(hi-lo).tolist(),positions=offset,normals=offset+len(pb),
        indices=offset+len(pb)+len(nb)+len(pad),vertexCount=len(p),indexCount=len(i))
    if s.get('parentId'):s['detailOffset']=((center-np.array(records[s['parentId']]['center']))*1.1).tolist()
    blob=pb+nb+pad+ib;blobs.append(blob);offset+=len(blob)

# Older mirrored representations and native left surfaces have the same FMA
# identity and occupy the same anatomy. Keep the native non-mirrored surfaces.
duplicates=[('FJ1449M','FJ2542'),('FJ1450M','FJ2543'),('FJ1453M','FJ2544'),('FJ1457M','FJ2545'),('FJ1458M','FJ2546')]
for removed,retained in duplicates:
    p,q=parts[removed],parts[retained]
    assert p['conceptId']==q['conceptId'] and p['name']==q['name']
    a,b=np.array(p['bounds']),np.array(q['bounds'])
    intersection=np.maximum(0,np.minimum(a[1],b[1])-np.maximum(a[0],b[0])).prod()
    iou=intersection/(np.ptp(a,axis=0).prod()+np.ptp(b,axis=0).prod()-intersection)
    assert iou>.98
    records['pelvic-muscles']['sourceIds'].remove(removed)
    changes.append(dict(removed=removed,retained=retained,name=p['name'],concept=p['conceptId'],
        boundsIntersectionOverUnion=float(iou),reason='Redundant mirrored representation of the same named left pelvic structure'))
append(records['pelvic-muscles'],[bp(id) for id in records['pelvic-muscles']['sourceIds']])

# The whole-pancreas envelope and parenchymal envelope overlap. The detailed
# parenchyma already supplies the organ surface; do not render both envelopes.
a,b=bp('FJ1895')[0],bp('FJ2629')[0]
distances=cKDTree(a).query(b)[0]
assert float(np.median(distances))<.00002
for id in ['pancreas','pancreas--parenchyma']:
    records[id]['sourceIds'].remove('FJ1895');append(records[id],[bp(i) for i in records[id]['sourceIds']])
changes.append(dict(removed='FJ1895',retained='FJ2629',name='Pancreatic exterior',
    medianNearestVertexDistanceMeters=float(np.median(distances)),reason='Whole-organ envelope overlapped its parenchymal envelope'))

# Split the two existing native vaginal components, without changing geometry.
parent=records['vagina'];p=np.frombuffer(raw,'<f4',parent['vertexCount']*3,parent['positions']).reshape(-1,3).astype('f8')+parent['center']
n=np.frombuffer(raw,'<i2',parent['vertexCount']*3,parent['normals']).reshape(-1,3)
idx=np.frombuffer(raw,'<u4',parent['indexCount'],parent['indices']);vi=ii=0;parent['childrenIds']=[]
for node,key,name,en in [(431,'surface','질 외곽','Vaginal exterior'),(432,'junction','자궁경부 연결부','Cervicovaginal junction')]:
    primitives=g['meshes'][g['nodes'][node]['mesh']]['primitives'];assert len(primitives)==1
    pr=primitives[0];nv=g['accessors'][pr['attributes']['POSITION']]['count'];ni=g['accessors'][pr['indices']]['count']
    child={k:copy.deepcopy(parent[k]) for k in ['sex','layer','system','color','functions','source']}
    child.update(id='vagina--'+key,parentId='vagina',name=name,en=en,description='',hraNodes=[node])
    child['modelNote']='외곽 표면 · 점막 주름·조직층 미포함' if node==431 else '자궁경부·질 접합 표면'
    child['color']='#bc807d' if node==431 else '#b39a8b'
    append(child,[(p[vi:vi+nv],n[vi:vi+nv],idx[ii:ii+ni]-vi)])
    meta.append(child);records[child['id']]=child;parent['childrenIds'].append(child['id']);vi+=nv;ii+=ni
assert vi==parent['vertexCount'] and ii==parent['indexCount']

tract=['vagina','uterus','left-uterine-tube','right-uterine-tube','left-ovary','right-ovary']
for s in meta:
    if s['id'] in tract or s.get('parentId') in ['vagina','uterus']:
        s['contextIds']=[id for id in tract if id!=s['id']]
        s['relatedIds']=[id for id in tract if id not in [s['id'],s.get('parentId')]]
records['vagina'].update(description='자궁경부 아래 · 방광 뒤·직장 앞',modelNote='외곽 표면 · 점막 주름·조직층 미포함\n외음부 · 별도 형상 미제공')
records['uterus']['modelNote']='표면·벽 구획 · 자궁내막층 미구분'
records['heart']['modelNote']='심방·심실 내강·판막 · 심실벽 미포함'
records['brain--ventricles']['modelNote']='뇌척수액 공간의 형상 · 신경조직 아님'
records['liver--bile-ducts']['name']='간 담관'
for id in ['stomach','small-intestine','large-intestine','female-large-intestine','bladder','female-bladder','gallbladder','esophagus','trachea','left-uterine-tube','right-uterine-tube']:
    records[id]['modelNote']='표면 참조형 · 조직층 미구분'
for s in meta:
    if s.get('parentId') and not s.get('modelNote'):
        note=records[s['parentId']].get('modelNote')
        if note:s['modelNote']=note
for s in meta:
    if s.get('parentId')=='heart':
        if 'ventricle' in s['id']:s['modelNote']='심실 내강·유두근 · 심실벽 미포함'
        elif 'atrium' in s['id']:s['modelNote']='심방 내강·벽 표면'
        else:s.pop('modelNote',None)
for parent_id in ['pancreas','vagina']:
    parent=records[parent_id];children=[records[id] for id in parent['childrenIds']]
    parent['detailBounds']=[np.min([np.array(s['center'])-np.array(s['size'])/2 for s in children],axis=0).tolist(),np.max([np.array(s['center'])+np.array(s['size'])/2 for s in children],axis=0).tolist()]

data=b''.join(blobs);assert data[:len(raw)]==raw
packed=gzip.compress(data,compresslevel=9,mtime=0);files=[]
for i,start in enumerate(range(0,len(packed),12_000_000)):
    name=f'anatomy-v11-{i}.bin.part';(out/name).write_bytes(packed[start:start+12_000_000]);files.append('/models/'+name)
(out/'anatomy-v11.json').write_text(json.dumps(meta,ensure_ascii=False,separators=(',',':')))
(out/'anatomy-v11-manifest.json').write_text(json.dumps({'files':files,'bytes':len(packed)}))
audit={'revision':11,'structures':len(meta),'corrections':changes,
    'vagina':{'originalNodes':[431,432],'newSelections':parent['childrenIds'] if parent['id']=='vagina' else records['vagina']['childrenIds'],
        'shapeChanged':False,'interpretation':'Native external envelope, not an opened mucosal illustration; connected organs retain their original HRA assembly transform'},
    'sectionRendering':'Only supplied mesh triangles are clipped. Artificial solid cut fills removed from every structure; tissue layers and luminal histology are not reconstructed.',
    'auditLimits':['Educational composite of different reference bodies, not a clinically certified full-body anatomy',
        'A source-coordinate audit cannot certify every upstream anatomical segmentation or individual variation',
        'Different named source components are retained unless redundancy can be established; no synthetic replacement of missing anatomy'],
    'references':['https://training.seer.cancer.gov/anatomy/reproductive/female/tract.html',
        'https://my.clevelandclinic.org/health/body/22469-vagina',
        'https://github.com/ashemag/human-atlas','https://doi.org/10.48539/HBM352.BTSQ.586']}
pathlib.Path('public/surface-audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2))
print(json.dumps({'structures':len(meta),'corrections':len(changes),'compressedBytes':len(packed)},indent=2))
