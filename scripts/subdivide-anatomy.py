"""Extract named anatomical substructures without inventing segmentation planes."""
import json, gzip, struct, pathlib, numpy as np
root=pathlib.Path('/workspace/scratch/anatomy-assets');out=pathlib.Path('public/models')
meta=json.loads((root/'base-v4.json').read_text());parents={s['id']:s for s in meta}
atlas=json.loads((root/'atlas.json').read_text());parts={p['id']:p for p in atlas['parts']};chunks={}
raw=(root/'base-v4.bin').read_bytes();blobs=[raw];offset=len(raw);used={};children={}
b=(root/'female.glb').read_bytes();jlen=struct.unpack_from('<I',b,12)[0];g=json.loads(b[20:20+jlen]);data=b[28+jlen:]
scope=json.loads(pathlib.Path('public/model-scope.json').read_text());translation=np.array(scope['femaleTransform']['translation'])
def acc(i):
 a=g['accessors'][i];v=g['bufferViews'][a['bufferView']];dim=3 if a['type']=='VEC3' else 1;dt=np.dtype({5126:'<f4',5125:'<u4',5123:'<u2'}[a['componentType']])
 return np.ndarray((a['count'],dim),dtype=dt,buffer=data,offset=v.get('byteOffset',0)+a.get('byteOffset',0),strides=(v.get('byteStride',dim*dt.itemsize),dt.itemsize)).copy()
def bp(ids):
 result=[]
 for id in ids:
  p=parts[id]
  if p['chunk'] not in chunks:chunks[p['chunk']]=gzip.decompress((root/f"body-{p['chunk']}.bin.gz").read_bytes())
  z=chunks[p['chunk']];n=p['vertexCount']
  result.append((np.frombuffer(z,'<f4',n*3,p['positions']).reshape(-1,3).copy(),np.frombuffer(z,'<i2',n*3,p['normals']).reshape(-1,3).copy(),np.frombuffer(z,'<u4',p['indexCount'],p['indices']).copy()))
 return result
def hra(ids,parent):
 result=[]
 for ni in ids:
  for p in g['meshes'][g['nodes'][ni]['mesh']]['primitives']:
   v=acc(p['attributes']['POSITION']);n=acc(p['attributes']['NORMAL']);ix=acc(p['indices']).flatten().astype('<u4')
   if parent.endswith('-lung'):
    # Use the identical per-axis registration as the existing whole lung.
    all_ids=[i for i in (range(851,866) if parent=='left-lung' else range(867,884)) if 'mesh' in g['nodes'][i]]
    whole=np.concatenate([acc(pr['attributes']['POSITION']) for i in all_ids for pr in g['meshes'][g['nodes'][i]['mesh']]['primitives']]);lo=whole.min(0);hi=whole.max(0);scale=np.array(parents[parent]['size'])/(hi-lo)
    v=(v-(lo+hi)/2)*scale+np.array(parents[parent]['center']);n=n/scale;n/=np.linalg.norm(n,axis=1,keepdims=True)
   else:v=v+translation
   result.append((v,(np.clip(n,-1,1)*32767).astype('<i2'),ix))
 return result
palette=['#b98980','#bb9c6a','#80a698','#9297ba','#b88eab','#b2ac83','#7296ac','#be947d']
def add(parent,key,name,en,ids,functions,description='',color=None,provider='bp'):
 global offset
 assert ids,(parent,key)
 prior=used.setdefault(parent,set());assert not prior.intersection(ids),(parent,key,'overlap');prior.update(ids)
 components=bp(ids) if provider=='bp' else hra(ids,parent);ps=[];ns=[];ix=[];count=0
 for p,n,ind in components:ps.append(p);ns.append(n);ix.append(ind+count);count+=len(p)
 p=np.concatenate(ps);n=np.concatenate(ns);ind=np.concatenate(ix).astype('<u4');lo=p.min(0);hi=p.max(0);center=(lo+hi)/2
 pb=(p-center).astype('<f4').tobytes();nb=n.astype('<i2').tobytes();pad=b'\0'*((-len(nb))%4);ib=ind.tobytes()
 par=parents[parent];siblings=children.setdefault(parent,[]);id=parent+'--'+key
 s=dict(id=id,parentId=parent,name=name,en=en,sex=par['sex'],layer=par['layer'],system=par['system'],color=color or palette[len(siblings)%len(palette)],description=description,functions=functions,source=par['source'],center=center.tolist(),size=(hi-lo).tolist(),positions=offset,normals=offset+len(pb),indices=offset+len(pb)+len(nb)+len(pad),vertexCount=len(p),indexCount=len(ind))
 s['detailOffset']=((center-np.array(par['center']))*1.1).tolist()
 if provider=='bp':s['sourceIds']=ids
 elif parent.endswith('-lung'):s['lungNodes']=ids;s['surfaceSource']=par['surfaceSource']
 else:s['hraNodes']=ids
 siblings.append(id);meta.append(s);blob=pb+nb+pad+ib;offset+=len(blob);blobs.append(blob)
def match(parent,rule):return [id for id in parents[parent]['sourceIds'] if rule(parts[id]['name'].lower())]
brain='brain'
for side,ko in [('left','왼쪽'),('right','오른쪽')]:
 for key,name,terms,functions in [
  ('frontal','전두엽 피질',['frontal gyrus','precentral gyrus'],['운동 계획·수의운동','판단·언어 생성에 관여']),
  ('parietal','두정엽 피질',['angular gyrus','postcentral gyrus','superior parietal','supramarginal'],['체성감각 처리','공간 정보 통합']),
  ('temporal','측두엽 피질',['temporal gyrus','fusiform','parahippocampal'],['감각 정보 처리','기억 형성에 관여']),
  ('occipital','후두엽',['occipital lobe'],['시각 정보 처리']),
  ('insula','섬엽',['insula'],['내장 감각·미각 처리']),
  ('cingulate','대상회',['cingulate gyrus'],['정서·주의 조절'])]:
  add(brain,side+'-'+key,ko+' '+name,side.title()+' '+key,match(brain,lambda n:n.startswith(side+' ') and any(t in n for t in terms)),functions,'원본 피질 영역' if key in ['frontal','parietal','temporal'] else '')
 add(brain,side+'-white-matter',ko+' 대뇌 백질',side.title()+' cerebral white matter',match(brain,lambda n:(side in n and ('white matter' in n or 'internal capsule' in n))),['대뇌 영역 간 신호 전달'])
 add(brain,side+'-hippocampus',ko+' 해마',side.title()+' hippocampus',match(brain,lambda n:n==side+' hippocampus'),['새로운 기억 형성'])
 add(brain,side+'-thalamus',ko+' 시상',side.title()+' thalamus',['FJ1782' if side=='left' else 'FJ1827'],['감각·운동 정보 중계'])
 add(brain,side+'-amygdala',ko+' 편도체',side.title()+' amygdala',['FJ1753' if side=='left' else 'FJ1829'],['정서 처리·정서 기억'])
for key,name,terms,functions in [
 ('cerebellum','소뇌',['cerebellum'],['운동 협응·균형 조절']),
 ('midbrain','중뇌',['midbrain','colliculus'],['감각·운동 신호 중계','시각·청각 반사에 관여']),
 ('pons','교뇌',['pons'],['대뇌·소뇌 신호 중계','호흡 조절에 관여']),
 ('medulla','연수',['medulla oblongata'],['호흡·심혈관 기능 조절']),
 ('hypothalamus','시상하부',['hypothalamus','tuber cinereum'],['체온·갈증·내분비 조절']),
 ('pineal','송과체',['pineal body'],['멜라토닌 분비·생체리듬 조절']),
 ('habenula','고삐핵 영역',['habenula'],['변연계 신호 중계']),
 ('ventricles','뇌실·중뇌수도관',['ventricle','aqueduct'],['뇌척수액 순환 통로'])]:
 add(brain,key,name,key.title(),match(brain,lambda n:any(t in n for t in terms)),functions)
add(brain,'corpus-callosum','뇌량','Corpus callosum',['FJ1742'],['좌우 대뇌반구 간 신호 전달'])
# Cardiac cavities are deliberately labelled as cavities, not invented ventricular walls.
for key,name,ids,functions,description in [
 ('right-atrium','우심방',['FJ2424','FJ2439'],['전신 정맥혈 수용'],''),
 ('left-atrium','좌심방',['FJ2425','FJ2438'],['폐정맥혈 수용'],''),
 ('right-ventricle','우심실 내강',['FJ2423','FJ2419','FJ2430','FJ2437'],['폐순환으로 혈액 박출'],'내강·유두근 참조형'),
 ('left-ventricle','좌심실 내강',['FJ2422','FJ2418','FJ2429'],['체순환으로 혈액 박출'],'내강·유두근 참조형'),
 ('tricuspid','삼첨판',['FJ2421','FJ2433','FJ2436'],['우심실→우심방 역류 방지'],''),
 ('mitral','승모판',['FJ2420','FJ2432'],['좌심실→좌심방 역류 방지'],''),
 ('pulmonary','폐동맥판',['FJ2417','FJ2427','FJ2434'],['폐동맥→우심실 역류 방지'],''),
 ('aortic','대동맥판',['FJ2426','FJ2431','FJ2435'],['대동맥→좌심실 역류 방지'],'')]:add('heart',key,name,key.replace('-',' ').title(),ids,functions,description)
add('heart','coronary-arteries','관상동맥','Coronary arteries',match('heart',lambda n:'artery' in n),['심장근육에 혈액 공급'])
add('heart','cardiac-veins','심장정맥·관상정맥동','Cardiac veins',match('heart',lambda n:'vein' in n or 'coronary sinus' in n),['심장근육의 정맥혈 회수'])
for numeral in ['I','II','III','IV','V','VI','VII','VIII']:
 ids=match('liver',lambda n:n==('caudate lobe of liver' if numeral=='I' else 'hepatovenous segment '+numeral.lower()))
 add('liver','segment-'+numeral.lower(),'간 '+numeral+'구역'+(' · 미상엽' if numeral=='I' else ''),'Liver segment '+numeral,ids,['영양소 대사·담즙 생성'],'원본 간 구역 분할')
for key,name,rule,functions in [
 ('portal','간문맥',lambda n:'portal vein' in n,['장관 유래 혈액 유입']),
 ('arteries','간동맥',lambda n:'artery' in n,['산소가 풍부한 혈액 공급']),
 ('veins','간정맥',lambda n:'hepatic vein' in n,['간의 정맥혈 배출']),
 ('bile-ducts','간내 담관',lambda n:'biliary' in n or 'hepatic duct' in n,['담즙 운반'])]:
 add('liver',key,name,{'portal':'Hepatic portal vein','arteries':'Hepatic arteries','veins':'Hepatic veins','bile-ducts':'Intrahepatic bile ducts'}[key],match('liver',rule),functions)
for side,ko,groups in [('left','왼쪽',[('upper','상엽',list(range(853,859))),('lower','하엽',list(range(860,866))),('hilum','폐문',[851])]),('right','오른쪽',[('upper','상엽',list(range(880,884))),('middle','중엽',list(range(876,879))),('lower','하엽',list(range(869,875))),('hilum','폐문',[867])])]:
 for key,name,ids in groups:add(side+'-lung',key,ko+' 폐 '+name,side.title()+' lung '+key,ids,['기관지·혈관 통과'] if key=='hilum' else ['산소·이산화탄소 교환'],provider='hra')
for key,name,rule,functions in [
 ('duodenum','십이지장',lambda n:n=='duodenum',['담즙·췌장액과 음식물 혼합']),
 ('jejunum','공장',lambda n:'jejunum' in n,['영양소 흡수']),
 ('ileum','회장',lambda n:'ileum' in n or 'ileocecal junction' in n,['영양소·담즙산 흡수'])]:add('small-intestine',key,name,key.title(),match('small-intestine',rule),functions)
for key,name,term,functions in [('ascending','상행결장','ascending colon',['수분·전해질 흡수']),('transverse','횡행결장','transverse colon',['수분·전해질 흡수']),('descending','하행결장','descending colon',['대변 이동']),('rectum','직장','rectum',['대변 저장·배출']),('taeniae','결장띠','taenia',['결장 수축에 관여'])]:add('large-intestine',key,name,term.title(),match('large-intestine',lambda n:term in n),functions)
for key,name,ids,functions in [('ascending','상행결장',[489,487],['수분·전해질 흡수']),('transverse','횡행결장',[488],['수분·전해질 흡수']),('descending','하행결장',[491,496],['대변 이동']),('sigmoid','구불결장',[495],['대변 이동·저장']),('rectum','직장',[494],['대변 저장·배출']),('cecum','맹장',[493],['소장 내용물 수용']),('appendix','충수',[490],['장관 면역에 관여']),('ileocecal-valve','회맹판',[492],['소장→대장 흐름 조절'])]:add('female-large-intestine',key,name,key.title(),ids,functions,provider='hra')
for side,ko in [('left','왼쪽'),('right','오른쪽')]:
 for key,name,color,functions in [('sclera','공막','#dddeda',['안구 형태 유지·보호']),('iris','홍채','#526f71',['입사광 조절']),('lens','수정체','#a2b4b3',['빛의 초점 조절']),('choroid','맥락막','#694c4a',['망막 바깥층에 혈액 공급'])]:add(side+'-eye',key,ko+' '+name,side.title()+' '+key,match(side+'-eye',lambda n:key in n),functions,color=color)
add('pancreas','parenchyma','췌장 실질','Pancreatic parenchyma',match('pancreas',lambda n:'duct' not in n),['소화효소·혈당 조절 호르몬 분비'])
add('pancreas','duct','췌관','Pancreatic duct',match('pancreas',lambda n:'duct' in n),['췌장액 운반'])
for key,name,ids,functions in [('body','자궁체부',[473,476,477,478],['임신 중 태아 발달 공간']),('fundus','자궁저부',[474],['자궁 상부 구성']),('cornua','자궁각·난관 입구',[472,475],['자궁·난관 연결']),('cervix','자궁경부',[479,480,481],['자궁·질 연결'])]:add('uterus',key,name,key.title(),ids,functions,provider='hra')
for side,ko,ids in [('left','왼쪽',[9,10,11]),('right','오른쪽',[20,19,18])]:
 for key,name,ni,functions in [('lobes','유선엽',ids[0],['모유 생성']),('ducts','유관',ids[1],['모유 운반']),('sinuses','유관팽대부',ids[2],['유관 확장 부위'])]:add(side+'-mammary',key,ko+' '+name,side.title()+' mammary '+key,[ni],functions,provider='hra')
for key,name,id,functions in [('cavernosa','음경해면체','FJ3132',['혈액 충만에 따른 발기']),('spongiosum','요도해면체','FJ3133',['음경 요도 둘레 구성']),('glans','귀두','FJ3134',['감각 수용'])]:add('penis',key,name,key.title(),[id],functions)
for parent,ids in children.items():
 par=parents[parent];par['childrenIds']=ids
 expected=set(par.get('sourceIds',[])) if parent not in ['left-lung','right-lung'] and not par.get('hraNodes') else set(par.get('hraNodes',[]))
 if expected:assert expected.issubset(used[parent]),(parent,'unmapped',expected-used[parent])
 group=[s for s in meta if s.get('parentId')==parent];lo=np.min([np.array(s['center'])-np.array(s['size'])/2 for s in group],axis=0);hi=np.max([np.array(s['center'])+np.array(s['size'])/2 for s in group],axis=0)
 par['detailBounds']=[lo.tolist(),hi.tolist()]
packed=gzip.compress(b''.join(blobs),compresslevel=9);files=[]
for i,start in enumerate(range(0,len(packed),12000000)):
 name=f'anatomy-v5-{i}.bin.part';(out/name).write_bytes(packed[start:start+12000000]);files.append('/models/'+name)
(out/'anatomy-v5-manifest.json').write_text(json.dumps({'files':files,'bytes':len(packed)}))
(out/'anatomy-v5.json').write_text(json.dumps(meta,ensure_ascii=False,separators=(',',':')))
pathlib.Path('public/substructure-scope.json').write_text(json.dumps({'source':'BodyParts3D named surfaces and HRA named components','parentCounts':{k:len(v) for k,v in children.items()},'brainCortex':'Available named gyri grouped by cortical region; not a complete cortical parcellation','heartVentricles':'Cavity and papillary-muscle surfaces; no invented ventricular wall','lungRegistration':'Same axis scales and translation as existing whole-lung meshes','coordinateRule':'All child vertices retain their source registration; only exploded mode displaces them'},indent=2))
print(json.dumps({'parents':len(children),'children':sum(map(len,children.values())),'total':len(meta),'compressedMB':len(packed)/1e6,'groups':{k:len(v) for k,v in children.items()}}))
