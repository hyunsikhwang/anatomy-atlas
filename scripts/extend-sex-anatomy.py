"""Add native BP3D organs and a documented HRA female pelvic reference assembly."""
import pathlib,json,gzip,struct,numpy as np
root=pathlib.Path('/workspace/scratch/anatomy-assets');out=pathlib.Path('public/models');meta=json.loads((root/'base-v2-anatomy.json').read_text());raw=gzip.decompress((root/'base-v2-anatomy.bin.gz').read_bytes());atlas=json.loads((root/'atlas.json').read_text());parts={p['id']:p for p in atlas['parts']};concepts={c['name'].lower():c for c in atlas['concepts']};chunks={}
blobs=[raw];offset=len(raw)
for s in meta:s['sex']='male' if s['id'] in ['pelvis','bladder','large-intestine'] else 'both'
def add(id,name,en,system,desc,functions,color,sex,components,source,layer=2,source_ids=None,nodes=None,eye=False):
 global offset
 pos=[];norm=[];ind=[];cols=[];count=0
 for p,n,ix,partname in components:
  pos.append(p);norm.append(n);ind.append(ix+count);count+=len(p)
  if eye:
   c='#e6e5df'
   if 'iris' in partname.lower():c='#476567'
   elif 'choroid' in partname.lower() or 'lens' in partname.lower():c='#152321'
   rgb=np.array([int(c[i:i+2],16)/255 for i in [1,3,5]]);rgb=np.where(rgb<=.04045,rgb/12.92,((rgb+.055)/1.055)**2.4);cols.append(np.tile(np.round(rgb*255).astype('u1'),(len(p),1)))
 p=np.concatenate(pos);n=np.concatenate(norm);ix=np.concatenate(ind).astype('<u4');lo=p.min(0);hi=p.max(0);center=(lo+hi)/2;p=(p-center).astype('<f4')
 pb=p.tobytes();nb=n.astype('<i2').tobytes();pad=b'\0'*((-len(nb))%4);ib=ix.tobytes();colorbytes=np.concatenate(cols).astype('u1').tobytes() if eye else b''
 s=dict(id=id,name=name,en=en,layer=layer,system=system,description=desc,functions=functions,color=color,sex=sex,source=source,center=center.tolist(),size=(hi-lo).tolist(),positions=offset,normals=offset+len(pb),indices=offset+len(pb)+len(nb)+len(pad),vertexCount=len(p),indexCount=len(ix))
 if eye:s['colors']=offset+len(pb)+len(nb)+len(pad)+len(ib)
 if source_ids:s['sourceIds']=source_ids
 if nodes:s['hraNodes']=nodes;s['referenceNote']='HRA 여성 참조 구조를 골반 기준으로 공통 좌표계에 정렬했습니다.'
 blob=pb+nb+pad+ib+colorbytes;blob+=b'\0'*((-len(blob))%4);offset+=len(blob);blobs.append(blob);meta.append(s)
def bp(ids):
 values=[]
 for id in ids:
  p=parts[id]
  if p['chunk'] not in chunks:chunks[p['chunk']]=gzip.decompress((root/f"body-{p['chunk']}.bin.gz").read_bytes())
  b=chunks[p['chunk']];v=np.frombuffer(b,'<f4',p['vertexCount']*3,p['positions']).reshape(-1,3).copy();n=np.frombuffer(b,'<i2',p['vertexCount']*3,p['normals']).reshape(-1,3).copy();ix=np.frombuffer(b,'<u4',p['indexCount'],p['indices']).copy();values.append((v,n,ix,p['name']))
 return values
def bpadd(id,name,en,system,desc,func,color,sex,ids,source,eye=False):add(id,name,en,system,desc,func,color,sex,bp(ids),source,source_ids=ids,eye=eye)
male_source='27-1-anatomy-and-physiology-of-the-male-reproductive-system';female_source='27-2-anatomy-and-physiology-of-the-female-reproductive-system'
for side,ko in [('left','왼쪽'),('right','오른쪽')]:
 ids=[i for i in concepts[side+' eyeball']['elements'] if any(k in parts[i]['name'].lower() for k in ['sclera','iris','choroid','lens']) and 'ligament' not in parts[i]['name'].lower() and i!='FJ1337']
 bpadd(side+'-eye',ko+' 안구',side.title()+' eyeball','감각계 · 신경계','안와에 위치한 시각 기관입니다. 공막·홍채·수정체 등 주요 구조를 표시합니다.',['빛을 받아 망막에서 신경 신호로 변환','수정체의 초점 조절과 홍채의 입사광 조절'],'#d8dfd9','both',ids,'14-1-sensory-perception',eye=True)
 bpadd(side+'-adrenal',ko+' 부신',side.title()+' adrenal gland','내분비계','신장의 위쪽에 위치한 내분비 기관입니다.',['스트레스 반응과 대사 조절 호르몬 분비','수분·전해질 균형과 혈압 조절에 관여'],'#c7af70','both',concepts[side+' adrenal gland']['elements'],'17-6-the-adrenal-glands')
 bpadd(side+'-testis',ko+' 고환',side.title()+' testis','남성 생식계','음낭 안에 위치한 남성 생식샘입니다.',['정자 생성','테스토스테론 분비'],'#b68c87','male',concepts[side+' testis']['elements'],male_source)
 for term,kname,key in [('epididymis','부고환','epididymis'),('seminal vesicle','정낭','seminal-vesicle'),('deferent duct','정관','deferent-duct')]:
  ids=[p['id'] for p in parts.values() if p['name'].lower()==side+' '+term]
  functions={'epididymis':['정자의 성숙과 저장'],'seminal vesicle':['정액을 구성하는 분비액 생성'],'deferent duct':['부고환에서 이어지는 정자 운반']}[term]
  bpadd(side+'-'+key,ko+' '+kname,side.title()+' '+term,'남성 생식계','남성 생식관을 구성하는 구조입니다.',functions,'#b79287','male',ids,male_source)
bpadd('prostate','전립선','Prostate','남성 생식계','방광 아래에서 요도의 일부를 둘러싸는 샘입니다.',['정액을 구성하는 분비액 생성'],'#ae8277','male',concepts['prostate']['elements'],male_source)
bpadd('penis','음경','Penis','남성 생식계 · 비뇨계','음경해면체·요도해면체·귀두를 표시합니다.',['요도를 통한 소변과 정액의 배출'],'#b78d81','male',[p['id'] for p in parts.values() if p['name'] in ['Corpus cavernosum of penis','Corpus spongiosum of penis','Glans penis']],male_source)
bpadd('pituitary','뇌하수체','Pituitary gland','내분비계','뇌의 아래쪽, 시상하부와 연결된 작은 내분비샘입니다.',['다른 내분비샘의 활동 조절','성장·생식·수분 균형에 관여'],'#c7a39c','both',['FJ1796'],'17-3-the-pituitary-gland-and-hypothalamus')
bpadd('tongue','혀','Tongue','소화계 · 감각계','입안 바닥의 근육성 기관입니다.',['음식물 조작과 삼킴','미각과 발음에 관여'],'#b17874','both',['FJ2761'],'23-3-the-mouth-pharynx-and-esophagus')
# HRA pelvic structures share one translation and uniform scale. No per-organ repositioning.
b=(root/'female.glb').read_bytes();l=struct.unpack_from('<I',b,12)[0];g=json.loads(b[20:20+l]);data=b[l+28:];nodes=g['nodes']
def descendants(i):
 n=nodes[i];return ([i] if 'mesh' in n else [])+sum([descendants(j) for j in n.get('children',[])],[])
def acc(i):
 a=g['accessors'][i];v=g['bufferViews'][a['bufferView']];dim=3 if a['type']=='VEC3' else 1;dt=np.dtype({5126:'<f4',5125:'<u4',5123:'<u2'}[a['componentType']]);return np.ndarray((a['count'],dim),dtype=dt,buffer=data,offset=v.get('byteOffset',0)+a.get('byteOffset',0),strides=(v.get('byteStride',dim*dt.itemsize),dt.itemsize)).copy()
female_pelvis_center=np.array([-.0086,.05895,-.0911]);common_pelvis_center=np.array(next(s for s in meta if s['id']=='pelvis')['center']);scale=1.0;translation=common_pelvis_center-female_pelvis_center
# Preserve the native female pelvis dimensions and all internal pelvic spatial relationships.
def hra(ids):
 values=[]
 for ni in ids:
  for p in g['meshes'][nodes[ni]['mesh']]['primitives']:
   pos=acc(p['attributes']['POSITION'])*scale+translation;n=(np.clip(acc(p['attributes']['NORMAL']),-1,1)*32767).astype('<i2');ix=acc(p['indices']).flatten().astype('<u4');values.append((pos,n,ix,nodes[ni]['name']))
 return values
def h(id,name,en,system,desc,func,color,node_ids,source=female_source,layer=2):
 ns=list(dict.fromkeys(sum([descendants(i) for i in node_ids],[])));add(id,name,en,system,desc,func,color,'female',hra(ns),source,layer=layer,nodes=ns)
h('female-pelvis','골반뼈','Female pelvis','골격계','여성 참조 모델의 골반뼈입니다. 남성 골반과 별도로 표시합니다.',['체중 전달과 골반 장기 보호'],'#ddd2b8',[962],'8-3-the-pelvic-girdle-and-pelvis',0)
h('female-bladder','방광','Urinary bladder','비뇨계','여성 골반에서 자궁의 앞쪽에 위치합니다.',['소변 저장과 배뇨'],'#c5a08a',[664],'25-2-gross-anatomy-of-urine-transport')
h('female-large-intestine','대장','Large intestine','소화계','결장과 직장을 포함합니다. 골반에서 직장은 자궁의 뒤쪽에 위치합니다.',['수분과 전해질 흡수','대변의 형성·저장·배출'],'#ab8b70',[486],'23-5-the-small-and-large-intestines')
h('uterus','자궁','Uterus','여성 생식계','골반 안에서 방광의 뒤쪽, 직장의 앞쪽에 위치합니다. 자궁경부를 포함합니다.',['배아의 착상과 태아 발달을 위한 공간','월경 주기에 따른 자궁내막 변화'],'#b98583',[471])
h('vagina','질','Vagina','여성 생식계','자궁경부에서 외부로 이어지는 근육성 통로입니다.',['월경혈 배출 통로','출산 시 산도 형성'],'#b78f92',[431,432])
for side,ko,ov,tube in [('left','왼쪽',469,439),('right','오른쪽',470,434)]:
 h(side+'-ovary',ko+' 난소',side.title()+' ovary','여성 생식계 · 내분비계','자궁 양옆에 위치한 여성 생식샘입니다.',['난자 성숙과 배란','에스트로겐·프로게스테론 분비'],'#ba98a0',[ov])
 h(side+'-uterine-tube',ko+' 난관',side.title()+' uterine tube','여성 생식계','난소 부근과 자궁 사이를 연결하는 관입니다.',['난자의 이동','일반적으로 수정이 이루어지는 부위'],'#d1a6a1',[tube])
# Keep developed mammary reference out of the male variant without implying men have no mammary tissue.
for id,name,node in [('left-mammary','왼쪽 유선',[9,10,11]),('right-mammary','오른쪽 유선',[20,19,18])]:
 h(id,name,'Mammary gland','생식계 · 외피계','여성 참조 모델의 유선엽과 유관을 표시합니다. 남성에도 유선 조직이 존재합니다.',['출산 후 호르몬 자극에 따른 모유 생성'],'#cda69d',node)
packed=gzip.compress(b''.join(blobs),compresslevel=9);files=[]
for i,start in enumerate(range(0,len(packed),12000000)):
 name=f'anatomy-v3-{i}.bin.part';(out/name).write_bytes(packed[start:start+12000000]);files.append('/models/'+name)
(out/'anatomy-v3-manifest.json').write_text(json.dumps({'files':files,'bytes':len(packed)}))
(out/'anatomy-v3.json').write_text(json.dumps(meta,ensure_ascii=False,separators=(',',':')))
print('total',len(meta),'male',sum(s['sex']!='female' for s in meta),'female',sum(s['sex']!='male' for s in meta),'MB',len(packed)/1e6)
pathlib.Path('public/model-scope.json').write_text(json.dumps({'commonReference':'BodyParts3D 4.0 adult male base; common teaching reference, not a sex-specific body scan','male':'BodyParts3D native male reproductive organs','female':'HRA female reproductive organs, pelvis, bladder, colon and developed mammary structures aligned as one assembly','femaleTransform':{'scale':scale,'translation':translation.tolist()},'pregnancyModelsIncluded':False},indent=2))
p=pathlib.Path('public/ATTRIBUTION.md');p.write_text(p.read_text().split('## Sex-specific organ configurations')[0].rstrip()+'''
\n## Sex-specific organ configurations (viewer revision 3)\nBodyParts3D male eye, adrenal, pituitary, tongue and male reproductive meshes are added in their original coordinates. Eye display uses sclera, iris, choroid and lens surfaces; transparent chamber volumes are omitted. The mislabeled FJ1337 right-choroid mesh has out-of-orbit vertices and is excluded; the remaining right-eye surfaces retain their original coordinates. Developed mammary gland display includes lobes, ducts and sinuses; surrounding skin and fat are omitted.\nHRA united-female v1.5 reproductive structures, pelvic bones, bladder, colon and developed mammary glands are adapted by a single uniform transform into the common frame. Pelvic internal spatial relationships are preserved. The common skeleton, muscles and remaining organs are teaching references based on the male BodyParts3D model; they are not relabelled as a full female scan. Female pelvic bones replace the male pelvis. Mammary tissue exists in men as well; only the developed female reference is separately represented here. Placenta and umbilical structures are excluded from the non-pregnant configuration.\nHRA: Kristen Browne and Heidi Schlehlein; https://doi.org/10.48539/HBM352.BTSQ.586 ; CC BY 4.0.\n''')
