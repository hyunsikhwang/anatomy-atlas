"""Align attributed HRA lung segment surfaces to the BodyParts3D lung envelopes."""
import json,struct,gzip,pathlib,numpy as np
path=pathlib.Path('public/models');meta=json.loads((path/'anatomy.json').read_text());raw=(path/'anatomy.bin').read_bytes();b=pathlib.Path('/workspace/scratch/anatomy-assets/female.glb').read_bytes();jlen=struct.unpack_from('<I',b,12)[0];gltf=json.loads(b[20:20+jlen]);data=b[28+jlen:];dtype={5126:'<f4',5125:'<u4',5123:'<u2'}
def acc(i):
 a=gltf['accessors'][i];v=gltf['bufferViews'][a['bufferView']];count=a['count'];dim=3 if a['type']=='VEC3' else 1;dt=np.dtype(dtype[a['componentType']]);offset=v.get('byteOffset',0)+a.get('byteOffset',0);stride=v.get('byteStride',dt.itemsize*dim)
 return np.ndarray((count,dim),dtype=dt,buffer=data,offset=offset,strides=(stride,dt.itemsize)).copy()
blobs=[];offset=0
for s in meta:
 pos=np.frombuffer(raw,'<f4',s['vertexCount']*3,s['positions']).reshape(-1,3).copy();norm=np.frombuffer(raw,'<i2',s['vertexCount']*3,s['normals']).reshape(-1,3).copy();idx=np.frombuffer(raw,'<u4',s['indexCount'],s['indices']).copy()
 if s['id'] in ['left-lung','right-lung']:
  rng=range(851,866) if s['id']=='left-lung' else range(867,884);vp=[];vn=[];vi=[];nv=0
  for ni in rng:
   n=gltf['nodes'][ni]
   if 'mesh' not in n:continue
   for primitive in gltf['meshes'][n['mesh']]['primitives']:
    p=acc(primitive['attributes']['POSITION']);no=acc(primitive['attributes']['NORMAL']);ix=acc(primitive['indices']).flatten().astype('<u4')+nv;vp.append(p);vn.append(no);vi.append(ix);nv+=len(p)
  p=np.concatenate(vp);no=np.concatenate(vn);ix=np.concatenate(vi);lo=p.min(0);hi=p.max(0);c=(lo+hi)/2;target=np.array(s['size'])*[1.06,.88,1.1];scale=target/(hi-lo);p=(p-c)*scale;no=no/scale;no/=np.linalg.norm(no,axis=1,keepdims=True);pos=p.astype('<f4');norm=(np.clip(no,-1,1)*32767).astype('<i2');idx=ix;s['size']=target.tolist();s['surfaceSource']='HRA united-female v1.5 lung segments, scaled and aligned to BodyParts3D envelopes';print(s['id'],'vertices',len(pos),'triangles',len(idx)//3)
 pb=pos.astype('<f4').tobytes();nb=norm.astype('<i2').tobytes();ib=idx.astype('<u4').tobytes();pad=b'\0'*((4-len(nb)%4)%4);s.update(positions=offset,normals=offset+len(pb),indices=offset+len(pb)+len(nb)+len(pad),vertexCount=len(pos),indexCount=len(idx));blob=pb+nb+pad+ib;blobs.append(blob);offset+=len(blob)
packed=b''.join(blobs);(path/'anatomy.bin.gz').write_bytes(gzip.compress(packed,compresslevel=9));(path/'anatomy.json').write_text(json.dumps(meta,ensure_ascii=False,separators=(',',':')));(path/'anatomy.bin').unlink();print('Compressed MB',(path/'anatomy.bin.gz').stat().st_size/1e6)
p=pathlib.Path('public/ATTRIBUTION.md');p.write_text(p.read_text()+'''\n## Lung surfaces included in this viewer\nKristen Browne and Heidi Schlehlein, Human Reference Atlas / HuBMAP, 3D Reference Organ Set for Female v1.5 (2023), CC BY 4.0.\nhttps://doi.org/10.48539/HBM352.BTSQ.586\nhttps://lod.humanatlas.io/ref-organ/united-female/v1.5\nhttps://creativecommons.org/licenses/by/4.0/\nLung bronchopulmonary segment surfaces extracted from the united-female GLB, scaled per axis and aligned to the BodyParts3D lung-region envelopes. This is a composite reference assembly, not a single-person scan or a clinically validated registration. Original HRA coordinates and demographic characteristics are not preserved by this alignment. The historical-assets paragraph above describes the upstream human-atlas project; this viewer includes these adapted lung surfaces.\n''')
