"""Prepare attributed BodyParts3D reference geometry from human-atlas packed files."""
import json,gzip,re,pathlib,numpy as np
src=pathlib.Path('/workspace/scratch/anatomy-assets');out=pathlib.Path('public/models');atlas=json.loads((src/'atlas.json').read_text());parts={p['id']:p for p in atlas['parts']};concepts={c['name'].lower():c for c in atlas['concepts']};chunks={i:gzip.decompress((src/f'body-{i}.bin.gz').read_bytes()) for i in range(15)}
groups={};assigned=set()
def group(key,name,en,layer,system,color,desc,functions,ids,source='1-2-structural-organization-of-the-human-body'):
 ids=[i for i in ids if i in parts and i not in assigned]
 if not ids:return
 assigned.update(ids);groups[key]=dict(id=key,name=name,en=en,layer=layer,system=system,color=color,description=desc,functions=functions,source=source,ids=ids)
def organ(key,name,en,color,system,desc,func,source):
 group(key,name,en,2,system,color,desc,func,concepts[en.lower()]['elements'],source)
organ('brain','뇌','Brain','#c8afa1','신경계','머리뼈 안에 위치하며 감각 정보와 신체 활동을 통합하는 중추 기관입니다.',['감각 정보의 처리와 운동 조절','기억·사고·언어 기능','호흡과 체온 등 생명 유지 기능의 조절'],'13-2-the-central-nervous-system')
organ('heart','심장','Heart','#a34e4a','심혈관계','양쪽 폐 사이의 종격에 위치한 근육성 펌프입니다. 네 개의 방과 판막이 혈액을 일정한 방향으로 보냅니다.',['폐순환과 체순환으로 혈액을 펌프질','조직에 산소와 영양소를 공급하는 혈류 유지'],'19-1-heart-anatomy')
for side,ko in [('right','오른쪽'),('left','왼쪽')]:
 organ(side+'-lung',ko+' 폐',side.title()+' lung','#c58d8d','호흡계','가슴 안에서 심장 양옆에 위치합니다. '+('오른쪽 폐는 세 개의 엽으로 구성됩니다.' if side=='right' else '왼쪽 폐는 두 개의 엽으로 구성되며 심장 자리가 있습니다.'),['폐포에서 산소와 이산화탄소 교환','이산화탄소 배출을 통한 산·염기 균형 조절'],'22-1-organs-and-structures-of-the-respiratory-system')
organ('liver','간','Liver','#955747','소화계','주로 오른쪽 윗배, 가로막 아래에 위치한 큰 장기입니다.',['담즙 생성과 영양소 대사','알부민·응고인자 등 단백질 합성','약물과 대사산물의 처리'],'23-6-accessory-organs-in-digestion-the-liver-pancreas-and-gallbladder')
organ('stomach','위','Stomach','#c18c7c','소화계','식도와 소장 사이에 있는 주머니 모양의 근육성 기관입니다.',['음식의 일시 저장과 혼합','위산·효소를 통한 단백질 소화 시작','내용물을 십이지장으로 배출'],'23-4-the-stomach')
for side,ko in [('right','오른쪽'),('left','왼쪽')]:
 organ(side+'-kidney',ko+' 신장',side.title()+' kidney','#985b51','비뇨계','배의 뒤쪽, 척주 양옆의 후복막 공간에 위치합니다.',['혈액 여과와 소변 생성','수분·전해질·산·염기 균형 조절','혈압 및 적혈구 생성에 관여'],'25-3-gross-anatomy-of-the-kidney')
organ('small-intestine','소장','Small intestine','#c6a18b','소화계','위와 대장 사이의 긴 관으로, 십이지장·공장·회장으로 구분합니다.',['음식물의 화학적 소화','대부분의 영양소와 수분 흡수'],'23-5-the-small-and-large-intestines')
organ('large-intestine','대장','Large intestine','#ab8b70','소화계','소장에서 이어지며 복부의 소장 주변을 둘러싸는 형태로 놓입니다.',['남은 수분과 전해질 흡수','대변의 형성·저장·배출'],'23-5-the-small-and-large-intestines')
organ('pancreas','췌장','Pancreas','#cead78','소화계 · 내분비계','위의 뒤쪽에 가로로 놓인 장기로, 소화와 혈당 조절에 함께 관여합니다.',['소화효소와 중탄산염 분비','인슐린·글루카곤을 통한 혈당 조절'],'23-6-accessory-organs-in-digestion-the-liver-pancreas-and-gallbladder')
organ('spleen','비장','Spleen','#8c6478','림프계 · 면역계','왼쪽 윗배의 위 뒤쪽에 위치한 림프성 장기입니다.',['혈액 여과와 노화 적혈구 제거','혈액 속 항원에 대한 면역 반응'],'21-1-anatomy-of-the-lymphatic-and-immune-systems')
organ('bladder','방광','Urinary bladder','#c5a08a','비뇨계','골반 안에서 신장으로부터 내려온 소변을 저장하는 근육성 기관입니다.',['소변의 일시 저장','배뇨 시 수축하여 소변 배출'],'25-2-gross-anatomy-of-urine-transport')
organ('gallbladder','담낭','Gallbladder','#789481','소화계','간의 아랫면에 붙어 있는 작은 주머니 형태의 기관입니다.',['간에서 만들어진 담즙의 저장과 농축','소화 시 담즙을 십이지장으로 방출'],'23-6-accessory-organs-in-digestion-the-liver-pancreas-and-gallbladder')
organ('trachea','기관','Trachea','#acb5ac','호흡계','후두와 기관지를 연결하는 기도입니다. 연골이 관의 형태를 지탱합니다.',['폐로 드나드는 공기의 통로','점액·섬모를 통한 이물질 제거'],'22-1-organs-and-structures-of-the-respiratory-system')
organ('esophagus','식도','Esophagus','#b7887b','소화계','인두와 위를 연결하며 가슴을 지나 가로막을 통과합니다.',['연동운동으로 음식물을 위로 운반'],'23-3-the-mouth-pharynx-and-esophagus')
# Classify the remaining reference skeleton and muscles by named bone or anatomical region.
regions={}
for p in atlas['parts']:
 if p['id'] in assigned:continue
 n=p['name'].lower();c=(np.array(p['bounds'][0])+p['bounds'][1])/2;x,y,z=c;side='left' if x>0 else 'right';ko='왼쪽' if x>0 else '오른쪽'
 muscle=p['system']=='muscular' or (p['system']=='skeletal' and re.search('fibularis|tibialis|subscapularis|levator scapulae|iliotibial',n))
 if muscle:
  if y>1.49:rid,label='head-muscles','머리 근육'
  elif y>1.38 and abs(x)<.09:rid,label='neck-muscles','목 근육'
  elif abs(x)>.15 and y>1.12:rid,label=side+'-upper-muscles',ko+' 위팔·어깨 근육'
  elif abs(x)>.17 and y>.81:rid,label=side+'-forearm-muscles',ko+' 아래팔 근육'
  elif abs(x)>.17 and y>.67:rid,label=side+'-hand-muscles',ko+' 손 근육'
  elif y>1.1:rid,label=('back-muscles','등 근육') if z<-.055 else ('chest-muscles','가슴 근육')
  elif y>.94:rid,label='abdominal-muscles','복부·허리 근육'
  elif y>.8:rid,label='pelvic-muscles','골반·엉덩이 근육'
  elif y>.44:rid,label=side+'-thigh-muscles',ko+' 넓적다리 근육'
  elif y>.13:rid,label=side+'-calf-muscles',ko+' 종아리 근육'
  else:rid,label=side+'-foot-muscles',ko+' 발 근육'
  key=(rid,label,1)
 elif p['system']=='skeletal':
  if 'gingiva' in n:continue
  if 'vertebra' in n or 'intervertebral' in n or n in ['atlas','axis']:rid,label='spine','척주'
  elif re.search('rib|sternum|xiphoid|manubrium',n):rid,label='ribcage','갈비뼈·복장뼈'
  elif re.search('hip bone|sacrum|coccyx',n):rid,label='pelvis','골반뼈'
  elif re.search('clavicle|scapula',n):rid,label='shoulder-bones','어깨뼈·빗장뼈'
  elif 'humerus' in n:rid,label=side+'-humerus',ko+' 위팔뼈'
  elif re.search('radius|ulna',n):rid,label=side+'-forearm',ko+' 아래팔뼈'
  elif 'femur' in n:rid,label=side+'-femur',ko+' 넙다리뼈'
  elif re.search('tibia|fibula|patella',n):rid,label=side+'-shin',ko+' 정강이·종아리뼈'
  elif y<.17:rid,label=side+'-foot',ko+' 발뼈'
  elif y<1 and abs(x)>.15:rid,label=side+'-hand',ko+' 손뼈'
  elif y>1.49:rid,label='skull','머리뼈·치아'
  elif y>1.35:rid,label='neck-bones','목뿔뼈·후두 연골'
  else:continue
  key=(rid,label,0)
 else:continue
 regions.setdefault(key,[]).append(p['id'])
for (rid,label,layer),ids in regions.items():
 en=rid.replace('-',' ').title();system='골격계' if layer==0 else '근육계';desc=label+'의 참조 구조를 함께 표시합니다.'
 fs=['신체 지지와 장기 보호','근육 부착 및 관절 운동에 기여'] if layer==0 else ['수축을 통한 해당 부위의 움직임','자세 유지와 관절 안정화']
 group(rid,label,en,layer,system,'#ddd2b8' if layer==0 else '#a66359',desc,fs,ids)
meta=[];blobs=[];offset=0
for key,g in groups.items():
 ps=[];ns=[];ix=[];nv=0
 for id in g['ids']:
  p=parts[id];b=chunks[p['chunk']];pos=np.frombuffer(b,'<f4',p['vertexCount']*3,p['positions']).reshape(-1,3).copy();norm=np.frombuffer(b,'<i2',p['vertexCount']*3,p['normals']).copy();idx=np.frombuffer(b,'<u4',p['indexCount'],p['indices']).copy()+nv
  ps.append(pos);ns.append(norm);ix.append(idx);nv+=p['vertexCount']
 pos=np.concatenate(ps);norm=np.concatenate(ns);idx=np.concatenate(ix);lo=pos.min(0);hi=pos.max(0);center=(lo+hi)/2
 pos=(pos-center).astype('<f4');pb=pos.tobytes();nb=norm.astype('<i2').tobytes();ib=idx.astype('<u4').tobytes()
 d={k:v for k,v in g.items() if k!='ids'};d.update(center=center.tolist(),size=(hi-lo).tolist(),positions=offset,normals=offset+len(pb),indices=offset+len(pb)+len(nb)+(4-len(nb)%4)%4,vertexCount=len(pos),indexCount=len(idx),sourceIds=g['ids'])
 pad=b'\0'*((4-len(nb)%4)%4);blob=pb+nb+pad+ib;blobs.append(blob);offset+=len(blob);meta.append(d)
bin=b''.join(blobs);(out/'anatomy.bin').write_bytes(bin);(out/'anatomy.bin.gz').write_bytes(gzip.compress(bin,compresslevel=9));(out/'anatomy.json').write_text(json.dumps(meta,ensure_ascii=False,separators=(',',':')))
print('Groups',len(meta),'source meshes',sum(len(g['ids']) for g in groups.values()),'triangles',sum(d['indexCount']//3 for d in meta),'MB',len(bin)/1e6,'gzMB',(out/'anatomy.bin.gz').stat().st_size/1e6)
print([(d['id'],d['vertexCount']) for d in meta])
pathlib.Path('public/ATTRIBUTION.md').write_text((src/'ATTRIBUTION.md').read_text()+'\n## This viewer\nSelected BodyParts3D structures regrouped into Korean anatomical regions; geometry translated to local group centers, colors adapted, layer opacity, organ separation and geometric clipping added. Upstream display classifications were adjusted for selected muscle meshes. No claim of clinical validation.\n')
