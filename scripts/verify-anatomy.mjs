import assert from 'node:assert/strict';
import {readFileSync,existsSync} from 'node:fs';
import {gunzipSync} from 'node:zlib';
import * as T from 'three';
import {fitAnatomyBounds,structurePosition,sectionPlane,selectionState,chooseVisibleHit,isStructureInSex,sexState,panTranslation,navigationMapping,familyForSelection,structureDrawState,pickStructureId,contextIdsForSelection,isContextStructure} from '../app/anatomy-view.ts';
import {INITIAL} from '../app/anatomy-types.ts';
const structures=JSON.parse(readFileSync(new URL('../public/models/anatomy-v13.json',import.meta.url)));
const manifest=JSON.parse(readFileSync(new URL('../public/models/anatomy-v13-manifest.json',import.meta.url)));
const files=manifest.files.map(file=>readFileSync(new URL('../public'+file,import.meta.url)));for(const file of files)assert(file.length<25*1024*1024);assert.equal(files.reduce((n,b)=>n+b.length,0),manifest.bytes);
const packed=gunzipSync(Buffer.concat(files));
const buffer=packed.buffer.slice(packed.byteOffset,packed.byteOffset+packed.byteLength);
const ids=new Set();let fits=0,slices=0,picks=0,sourceChecks=0,femaleChecks=0,panChecks=0,detailChecks=0,lungChecks=0,femaleManifestChecks=0;
const originalRoot=existsSync('.sites-runtime/anatomy-sources/atlas.json')?'.sites-runtime/anatomy-sources':'/workspace/scratch/anatomy-assets';
const original=existsSync(originalRoot+'/atlas.json')?JSON.parse(readFileSync(originalRoot+'/atlas.json')):null;
const originalParts=new Map(original?.parts.map(p=>[p.id,p])??[]),chunks=new Map();
const femaleRaw=existsSync(originalRoot+'/female.glb')?readFileSync(originalRoot+'/female.glb'):null;
const femaleJson=femaleRaw?JSON.parse(femaleRaw.subarray(20,20+femaleRaw.readUInt32LE(12)).toString()):existsSync(originalRoot+'/female-manifest.json')?JSON.parse(readFileSync(originalRoot+'/female-manifest.json')):null;
const femaleData=femaleRaw?.subarray(28+femaleRaw.readUInt32LE(12));
const registration=JSON.parse(readFileSync(new URL('../public/model-scope.json',import.meta.url))).femaleTransform;
const lungAudit=JSON.parse(readFileSync(new URL('../public/lung-audit.json',import.meta.url)));
let lungRegistrationChecks=0;
for(const s of structures){
 assert(!ids.has(s.id));ids.add(s.id);assert(s.vertexCount>0&&s.indexCount>0);assert(['male','female','both'].includes(s.sex));
 if(s.colors!==undefined){const colors=new Uint8Array(buffer,s.colors,s.vertexCount*3);assert(new Set(colors).size>2);}
 const positions=new Float32Array(buffer,s.positions,s.vertexCount*3),indices=new Uint32Array(buffer,s.indices,s.indexCount);
 for(const v of positions)assert(Number.isFinite(v));for(const index of indices)assert(index<s.vertexCount);
 const geometry=new T.BufferGeometry();geometry.setAttribute('position',new T.BufferAttribute(positions,3));geometry.setIndex(new T.BufferAttribute(indices,1));geometry.computeBoundingBox();geometry.computeBoundingSphere();
 const worldBounds=geometry.boundingBox.clone().translate(new T.Vector3().fromArray(s.center));
 for(const [axis,i] of ['x','y','z'].map((axis,i)=>[axis,i])){
  assert(Math.abs(worldBounds.min[axis]-(s.center[i]-s.size[i]/2))<1e-6,`${s.id}: incorrect bounds`);
  assert(Math.abs(worldBounds.max[axis]-(s.center[i]+s.size[i]/2))<1e-6,`${s.id}: incorrect bounds`);
 }
 // Body-side pairs use the body midline. Intrinsic labels such as right
 // ventricle are relative to an oblique organ, not an absolute x coordinate.
 const sideId=s.parentId?'':s.id;
 if(sideId.startsWith('left-'))assert(s.center[0]>0,`${s.id}: left/right reversal`);
 if(sideId.startsWith('right-'))assert(s.center[0]<0,`${s.id}: right/left reversal`);
 const selected=selectionState({...INITIAL,sex:s.sex==='female'?'female':'male',visible:[false,false,false],opacity:[0,0,0],mode:'section',cut:0},s);
 assert(selected.visible[s.layer]);assert.equal(selected.opacity[s.layer],100);assert.equal(selected.cut,50);
 const mesh=new T.Mesh(geometry,new T.MeshBasicMaterial({side:T.DoubleSide}));mesh.position.fromArray(s.center);mesh.layers.set(1);mesh.updateMatrixWorld(true);
 const organIndex=structures.filter(p=>!p.parentId&&p.layer===2&&isStructureInSex(p,selected.sex)).findIndex(p=>p.id===(s.parentId??s.id));
 for(const mode of ['whole','explode'])for(const explode of mode==='explode'?[0,55,100]:[0]){
  const state={...INITIAL,sex:selected.sex,selected:s.id,mode,explode};const activeFamily=familyForSelection(s);const pos=structurePosition(s,state,organIndex,activeFamily);const bounds=geometry.boundingBox.clone().translate(pos);
  if(s.childrenIds?.length){bounds.makeEmpty();for(const child of structures.filter(c=>c.parentId===s.id)){const center=structurePosition(child,state,organIndex,activeFamily),half=new T.Vector3().fromArray(child.size).multiplyScalar(.5);bounds.union(new T.Box3(center.clone().sub(half),center.clone().add(half)));}}
  for(const [w,h] of [[900,760],[420,620],[320,480],[480,300],[280,700]]){
   const direction=new T.Vector3(.17,.1,1);const fit=fitAnatomyBounds(bounds,direction,w,h);
   const camera=new T.PerspectiveCamera(32,w/h,.001,80);camera.position.copy(fit.position);camera.lookAt(fit.center);camera.updateMatrixWorld(true);
   for(let i=0;i<8;i++){
    const p=new T.Vector3(i&1?bounds.max.x:bounds.min.x,i&2?bounds.max.y:bounds.min.y,i&4?bounds.max.z:bounds.min.z).project(camera);
    assert(Math.abs(p.x)<.94&&Math.abs(p.y)<.94&&p.z>-1&&p.z<1,`${s.id} ${mode} ${w}x${h} outside viewport`);
   }
   fits++;
  }
 }
 for(const axis of ['x','y','z']){
  const plane=sectionPlane({...selected,axis},worldBounds);let kept=0,removed=0;
  for(let i=0;i<positions.length;i+=3){const point=new T.Vector3(positions[i],positions[i+1],positions[i+2]).add(mesh.position);if(plane.distanceToPoint(point)>=0)kept++;else removed++;}
  assert(kept>0&&removed>0,`${s.id} ${axis} erased by selection slice`);slices++;
 }
 const fit=fitAnatomyBounds(worldBounds,new T.Vector3(.17,.1,1),800,650);const camera=new T.PerspectiveCamera(32,800/650,.001,80);camera.position.copy(fit.position);camera.lookAt(fit.center);camera.updateMatrixWorld(true);
 const sample=new T.Vector3();for(let k=0;k<3;k++)sample.add(new T.Vector3().fromArray(positions,indices[k]*3));sample.multiplyScalar(1/3).add(mesh.position).project(camera);
 const ray=new T.Raycaster();ray.layers.enable(1);ray.setFromCamera(new T.Vector2(sample.x,sample.y),camera);assert(ray.intersectObject(mesh,false).length>0,`${s.id} not pickable in selected pass`);picks++;
 // Validate common-coordinate positions against original packed vertices; HRA lung surfaces are a documented exception.
 if(original&&s.sourceIds&&s.id!=='left-lung'&&s.id!=='right-lung'){
  let cursor=0,indexCursor=0;
  for(const id of s.sourceIds){const p=originalParts.get(id);assert(p,`${s.id}: unknown source ${id}`);if(!chunks.has(p.chunk)){const c=gunzipSync(readFileSync(`${originalRoot}/body-${p.chunk}.bin.gz`));chunks.set(p.chunk,c.buffer.slice(c.byteOffset,c.byteOffset+c.byteLength));}
   const originalPositions=new Float32Array(chunks.get(p.chunk),p.positions,p.vertexCount*3);
   const originalNormals=new Int16Array(chunks.get(p.chunk),p.normals,p.vertexCount*3),normals=new Int16Array(buffer,s.normals,s.vertexCount*3),originalIndices=new Uint32Array(chunks.get(p.chunk),p.indices,p.indexCount);
   for(let i=0;i<originalNormals.length;i++)assert.equal(normals[cursor+i],originalNormals[i],`${s.id}: source normal changed`);
   for(let i=0;i<originalIndices.length;i++)assert.equal(indices[indexCursor+i],originalIndices[i]+cursor/3,`${s.id}: source triangle changed`);indexCursor+=originalIndices.length;
   for(let i=0;i<originalPositions.length;i++)assert(Math.abs(positions[cursor+i]+s.center[i%3]-originalPositions[i])<1e-6,`${s.id} source position changed`);
   cursor+=originalPositions.length;
  }assert.equal(cursor,positions.length);assert.equal(indexCursor,indices.length);sourceChecks++;
 }
 if(femaleData&&s.hraNodes){let cursor=0;
  for(const nodeId of s.hraNodes)for(const primitive of femaleJson.meshes[femaleJson.nodes[nodeId].mesh].primitives){
   const accessor=femaleJson.accessors[primitive.attributes.POSITION],view=femaleJson.bufferViews[accessor.bufferView];
   for(let vertex=0;vertex<accessor.count;vertex++)for(let axis=0;axis<3;axis++){
    const raw=femaleData.readFloatLE((view.byteOffset??0)+(accessor.byteOffset??0)+vertex*(view.byteStride??12)+axis*4);
    assert(Math.abs(positions[cursor++]+s.center[axis]-(raw*registration.scale+registration.translation[axis]))<1e-6,`${s.id} female registration mismatch`);
   }
  }assert.equal(cursor,positions.length);femaleChecks++;
 }
 if(femaleJson&&s.hraNodes){
  const sourceBounds=new T.Box3();let vertices=0,indices=0;
  assert.equal(new Set(s.hraNodes).size,s.hraNodes.length,`${s.id}: repeated HRA node`);
  for(const nodeId of s.hraNodes){
   const node=femaleJson.nodes[nodeId];assert(node&&node.mesh!==undefined);
   assert(!node.matrix&&!node.translation&&!node.rotation&&!node.scale,`${s.id}: unhandled source transform`);
   for(const primitive of femaleJson.meshes[node.mesh].primitives){
    const accessor=femaleJson.accessors[primitive.attributes.POSITION];vertices+=accessor.count;indices+=femaleJson.accessors[primitive.indices].count;
    sourceBounds.union(new T.Box3(new T.Vector3().fromArray(accessor.min),new T.Vector3().fromArray(accessor.max)));
   }
  }
  sourceBounds.min.multiplyScalar(registration.scale).add(new T.Vector3().fromArray(registration.translation));
  sourceBounds.max.multiplyScalar(registration.scale).add(new T.Vector3().fromArray(registration.translation));
  assert(sourceBounds.min.distanceTo(worldBounds.min)<2e-6&&sourceBounds.max.distanceTo(worldBounds.max)<2e-6,`${s.id}: HRA source bounds mismatch`);
  assert.equal(vertices,s.vertexCount);assert.equal(indices,s.indexCount);femaleManifestChecks++;
 }
 if(s.lungNodes&&femaleJson){
  const nativeBounds=new T.Box3();let sourceVertices=0,sourceIndices=0;
  for(const nodeId of s.lungNodes)for(const primitive of femaleJson.meshes[femaleJson.nodes[nodeId].mesh].primitives){
   const accessor=femaleJson.accessors[primitive.attributes.POSITION];nativeBounds.union(new T.Box3(new T.Vector3().fromArray(accessor.min),new T.Vector3().fromArray(accessor.max)));sourceVertices+=accessor.count;sourceIndices+=femaleJson.accessors[primitive.indices].count;
  }
  assert.equal(lungAudit.registration.scale,1);assert.equal(lungAudit.registration.rotation,'identity');
  const expected=nativeBounds.translate(new T.Vector3().fromArray(lungAudit.registration.translation));
  assert(expected.min.distanceTo(worldBounds.min)<1e-6&&expected.max.distanceTo(worldBounds.max)<1e-6,`${s.id}: native bilateral proportions changed`);
  assert.equal(s.vertexCount,sourceVertices);assert.equal(s.indexCount,sourceIndices);
  const normals=new Int16Array(buffer,s.normals,s.vertexCount*3);
  for(let i=0;i<normals.length;i+=3)assert(Math.abs(Math.hypot(normals[i],normals[i+1],normals[i+2])/32767-1)<.0001,`${s.id}: bad restored normal`);
  lungRegistrationChecks++;
 }
 if(s.lungNodes&&s.parentId&&femaleJson){
  // Compare child vertices directly to their existing registered parent lung buffer.
  const parent=structures.find(p=>p.id===s.parentId);let parentCursor=0,childCursor=0;
  const range=parent.id==='left-lung'?[851,866]:[867,884];
  const parentPositions=new Float32Array(buffer,parent.positions,parent.vertexCount*3);
  for(let node=range[0];node<range[1];node++){if(femaleJson.nodes[node].mesh===undefined)continue;
   for(const primitive of femaleJson.meshes[femaleJson.nodes[node].mesh].primitives){const count=femaleJson.accessors[primitive.attributes.POSITION].count*3;
    if(s.lungNodes.includes(node))for(let i=0;i<count;i++){assert(Math.abs(positions[childCursor+i]+s.center[i%3]-parentPositions[parentCursor+i]-parent.center[i%3])<1e-6,`${s.id} parent lung alignment mismatch`);}if(s.lungNodes.includes(node))childCursor+=count;parentCursor+=count;
   }
  }assert.equal(childCursor,positions.length);lungChecks++;
 }
 geometry.dispose();mesh.material.dispose();
}
assert.equal(chooseVisibleHit([{id:'liver',opacity:.065},{id:'gallbladder',opacity:1}],'gallbladder'),'gallbladder');
assert.equal(chooseVisibleHit([{id:'liver',opacity:.065},{id:'gallbladder',opacity:1}],null),'gallbladder');
assert.equal(chooseVisibleHit([],null),null);
const leftLung=structures.find(s=>s.id==='left-lung'),rightLung=structures.find(s=>s.id==='right-lung');
assert(rightLung.size[0]>leftLung.size[0]&&rightLung.size[1]<leftLung.size[1],'Reference right lung must remain wider and shorter');
assert(rightLung.center[1]-rightLung.size[1]/2>leftLung.center[1]-leftLung.size[1]/2,'Right lung base displaced below left');
assert.equal(leftLung.childrenIds.length,3);assert.equal(rightLung.childrenIds.length,4);
assert(!rightLung.registrationReferenceIds.includes('FJ2041')&&!rightLung.registrationReferenceIds.includes('FJ2044'));
for(const sex of ['male','female']){
 const active=structures.filter(s=>isStructureInSex(s,sex));
 const sourceOwners=new Map();
 for(const s of active.filter(s=>!s.childrenIds?.length))for(const [provider,sourceIds] of [['bp',s.sourceIds??[]],['hra',s.hraNodes??s.lungNodes??[]]])for(const id of sourceIds){
  const key=provider+':'+id;assert(!sourceOwners.has(key),`${sex}: repeated source ${key}`);sourceOwners.set(key,s.id);
 }
 // Regression: appendix presence must not depend on sex. The native cecal
 // surface belongs to male colon, never to the shared small intestine.
 const colon=active.find(s=>s.name==='대장');
 const appendices=active.filter(s=>s.id.endsWith('--appendix'));
 const ceca=active.filter(s=>s.id.endsWith('--cecum'));
 assert.equal(appendices.length,1,`${sex}: missing or duplicate appendix`);
 assert.equal(ceca.length,1,`${sex}: missing or duplicate cecum`);
 for(const part of [...appendices,...ceca]){
  assert.equal(part.parentId,colon.id);assert(colon.childrenIds.includes(part.id));
  assert(part.center[0]<0,`${sex}: cecal region on wrong side`);
  const selected=selectionState({...INITIAL,sex,mode:'section',cut:0,visible:[false,false,false],opacity:[0,0,0]},part);
  assert.equal(selected.cut,50);assert(structureDrawState(part,selected).selected);assert(structureDrawState(part,selected).visible);
 }
 const worldVertices=s=>{const p=new Float32Array(buffer,s.positions,s.vertexCount*3);return Array.from({length:s.vertexCount},(_,i)=>new T.Vector3(p[i*3]+s.center[0],p[i*3+1]+s.center[1],p[i*3+2]+s.center[2]));};
 const appendixVertices=worldVertices(appendices[0]),cecumVertices=worldVertices(ceca[0]);
 // Nearest-vertex allowance for coarse reference meshes; source coordinates
 // are independently checked above. This rejects a displaced appendix.
 assert(Math.min(...appendixVertices.map(p=>Math.min(...cecumVertices.map(q=>p.distanceTo(q)))))<.006,`${sex}: appendix detached from cecal region`);
 const nativeCecalLeaves=active.filter(s=>!s.childrenIds?.length&&s.sourceIds?.includes('FJ2599'));
 assert.deepEqual(nativeCecalLeaves.map(s=>s.id),sex==='male'?['large-intestine--cecum']:[]);
 const nativeAppendixLeaves=active.filter(s=>!s.childrenIds?.length&&s.sourceIds?.includes('FJ2565'));
 assert.deepEqual(nativeAppendixLeaves.map(s=>s.id),sex==='male'?['large-intestine--appendix']:[]);
 for(const id of ['left-eye','right-eye','left-adrenal','right-adrenal','gallbladder'])assert(active.some(s=>s.id===id));
 for(const name of ['골반뼈','방광','대장'])assert.equal(active.filter(s=>s.name===name).length,1,`${sex} duplicate ${name}`);
 for(const s of structures){const initial={...INITIAL,sex};assert.equal(selectionState(initial,s).selected,isStructureInSex(s,sex)?s.id:null);}
 const changed=sexState({...INITIAL,selected:'prostate',isolate:true},sex);assert.equal(changed.selected,null);assert(!changed.isolate);assert.equal(changed.sex,sex);
 assert.equal(active.some(s=>s.id==='prostate'),sex==='male');assert.equal(active.some(s=>s.id==='uterus'),sex==='female');
}
for(const parent of structures.filter(s=>s.childrenIds?.length&&s.sourceIds&&s.id!=='left-lung'&&s.id!=='right-lung')){
 const id=parent.id,children=structures.filter(s=>s.parentId===id);
 const sourceIds=children.flatMap(s=>s.sourceIds);
 assert.equal(new Set(sourceIds).size,sourceIds.length,`${id}: duplicate child source mesh`);
 assert.deepEqual(new Set(sourceIds),new Set(parent.sourceIds),`${id}: parent/child source mismatch`);
}
for(const parent of structures.filter(s=>s.childrenIds?.length)){
 const children=structures.filter(s=>s.parentId===parent.id);assert.deepEqual(new Set(children.map(s=>s.id)),new Set(parent.childrenIds));
 const rootState=selectionState({...INITIAL,sex:parent.sex==='female'?'female':'male',isolate:true},parent);
 assert.equal(structureDrawState(parent,rootState).visible,false);
 assert.equal(familyForSelection(parent),parent.id);
 assert.equal(structures.filter(s=>structureDrawState(s,rootState).visible).length,children.length);
 for(const child of children){
  assert.equal(child.sex,parent.sex);assert.equal(child.layer,parent.layer);assert(structureDrawState(child,rootState).selected);assert(structureDrawState(child,rootState).visible);
  const childState=selectionState(rootState,child);assert.equal(familyForSelection(child),parent.id);
  const drawn=structures.filter(s=>structureDrawState(s,childState).visible);assert.deepEqual(drawn.map(s=>s.id),[child.id]);
  assert.equal(pickStructureId(child,null),parent.id);assert.equal(pickStructureId(child,parent.id),child.id);
  for(const sex of ['male','female'])if(!isStructureInSex(parent,sex))assert(!structureDrawState(child,{...childState,sex}).visible);
  detailChecks++;
 }
}
assert.equal(structures.find(s=>s.id==='brain').childrenIds.length,29);
const byId=new Map(structures.map(s=>[s.id,s]));
// Pelvic extraction is checked against the retained original parent buffers.
// Source counts are from the committed BP3D/HRA manifests, not inferred cuts.
const pelvicSources=JSON.parse(readFileSync(new URL('./source-manifests/pelvis.json',import.meta.url)));
let pelvicComponentChecks=0;
for(const [parentId,provider,field] of [['pelvis','bodyParts3D','sourceIds'],['female-pelvis','hraFemale','hraNodes']]){
 const parent=byId.get(parentId),defs=new Map(pelvicSources[provider].parts.map(p=>[p.id,p]));
 const parentPositions=new Float32Array(buffer,parent.positions,parent.vertexCount*3),parentNormals=new Int16Array(buffer,parent.normals,parent.vertexCount*3),parentIndices=new Uint32Array(buffer,parent.indices,parent.indexCount);
 const ranges=new Map();let pv=0,pi=0;
 for(const id of parent[field]){const def=defs.get(id);assert(def);ranges.set(id,{vertex:pv,index:pi,...def});pv+=def.vertexCount;pi+=def.indexCount;}
 assert.equal(pv,parent.vertexCount);assert.equal(pi,parent.indexCount);
 const children=parent.childrenIds.map(id=>byId.get(id));
 assert.equal(children.reduce((n,c)=>n+c.vertexCount,0),parent.vertexCount);
 assert.equal(children.reduce((n,c)=>n+c.indexCount,0),parent.indexCount);
 assert.deepEqual(new Set(children.flatMap(c=>c[field])),new Set(parent[field]));
 for(const child of children){
  const positions=new Float32Array(buffer,child.positions,child.vertexCount*3),normals=new Int16Array(buffer,child.normals,child.vertexCount*3),indices=new Uint32Array(buffer,child.indices,child.indexCount);
  let cv=0,ci=0;
  for(const id of child[field]){
   const r=ranges.get(id);assert(r);
   for(let i=0;i<r.vertexCount*3;i++){
    assert(Math.abs(positions[cv*3+i]+child.center[i%3]-parentPositions[r.vertex*3+i]-parent.center[i%3])<1e-7,`${child.id}: moved original surface`);
    assert.equal(normals[cv*3+i],parentNormals[r.vertex*3+i]);
   }
   for(let i=0;i<r.indexCount;i++)assert.equal(indices[ci+i]-cv,parentIndices[r.index+i]-r.vertex);
   cv+=r.vertexCount;ci+=r.indexCount;pelvicComponentChecks++;
  }
  assert.equal(cv,child.vertexCount);assert.equal(ci,child.indexCount);
 }
}
for(const sex of ['male','female']){
 const linked=byId.get('spine').relatedIds.map(id=>byId.get(id)).filter(s=>isStructureInSex(s,sex));
 assert.deepEqual(linked.map(s=>s.id),sex==='male'?['pelvis--sacrum']:['female-pelvis--sacrum','female-pelvis--coccyx']);
 for(const s of linked){const selected=selectionState({...INITIAL,sex,visible:[false,false,false],opacity:[0,0,0]},s);assert(structureDrawState(s,selected).visible);assert(structureDrawState(s,selected).selected);}
}
assert.deepEqual(byId.get('pelvis--sacrum').sourceIds,['FJ3393']);
assert.deepEqual(byId.get('female-pelvis--sacrum').hraNodes,[963]);
assert.deepEqual(byId.get('female-pelvis--coccyx').hraNodes,[964]);
assert(byId.get('female-pelvis--coccyx').center[1]<byId.get('female-pelvis--sacrum').center[1]);
assert.deepEqual(byId.get('spine').childrenIds,['spine--cervical','spine--thoracic','spine--lumbar','spine--discs']);
for(const [key,count,terms] of [['cervical',7,/cervical vertebra|^atlas$|^axis$/],['thoracic',12,/thoracic vertebra/],['lumbar',5,/lumbar vertebra/],['discs',23,/intervertebral disk/]]){
 const part=byId.get('spine--'+key);assert.equal(part.sourceIds.length,count);assert.equal(part.layer,0);assert.equal(part.sex,'both');
 if(original)for(const id of part.sourceIds){const name=originalParts.get(id).name.toLowerCase();assert(terms.test(name));assert.equal(name.includes('disk'),key==='discs');}
}
assert(byId.get('spine--cervical').center[1]>byId.get('spine--thoracic').center[1]);
assert(byId.get('spine--thoracic').center[1]>byId.get('spine--lumbar').center[1]);
for(const id of ['FJ2772','FJ2440','FJ2386','FJ1450'])assert(!structures.some(s=>s.sourceIds?.includes(id)),`duplicate alias ${id} returned`);
assert.deepEqual(byId.get('vagina').hraNodes,[431,432]);
assert.deepEqual(byId.get('neck-bones--hyoid').sourceIds,['FJ3201']);
assert(!byId.get('skull').sourceIds.some(id=>['FJ2772','FJ3201','FJ2773','FJ2795'].includes(id)));
assert(byId.get('right-hand-muscles').sourceIds.includes('FJ1469'));
assert(byId.get('left-hand-muscles').sourceIds.includes('FJ1469M'));
if(original)for(const s of structures.filter(s=>s.layer===1))for(const id of s.sourceIds??[]){
 const n=originalParts.get(id).name.toLowerCase();
 if(/of (?:left|right) hand|flexor pollicis brevis|adductor pollicis|abductor pollicis brevis|opponens pollicis/.test(n))assert(s.id.endsWith('-hand-muscles'));
 if(/deltoid|subscapularis|supraspinatus|infraspinatus|teres (?:minor|major)/.test(n))assert(s.id.endsWith('-upper-muscles'));
 if(n.includes('gluteus'))assert.equal(s.id,'pelvic-muscles');
}
for(const side of ['left','right']){const eye=structures.find(s=>s.id===side+'-eye');assert(eye.size.every(v=>v<.035));assert(side==='left'?eye.center[0]-.5*eye.size[0]>0:eye.center[0]+.5*eye.size[0]<0);}
for(const direction of [new T.Vector3(0,0,1),new T.Vector3(1,.4,1),new T.Vector3(-1,.7,-1)])for(const distance of [.1,1,4])for(const [dx,dy] of [[44,0],[-44,0],[0,44],[0,-44],[44,-44]]){
 const target=new T.Vector3(.1,.9,-.1),camera=new T.PerspectiveCamera(32,800/600,.001,80);camera.position.copy(target).addScaledVector(direction.clone().normalize(),distance);camera.lookAt(target);camera.updateMatrixWorld();const before=target.clone().project(camera);
 const offset=panTranslation(camera,target,dx,dy,600);const separation=camera.position.clone().sub(target);camera.position.add(offset);const nextTarget=target.clone().add(offset);camera.lookAt(nextTarget);camera.updateMatrixWorld();const after=target.clone().project(camera);
 assert(camera.position.clone().sub(nextTarget).distanceTo(separation)<1e-10);assert(Math.abs((after.x-before.x)*400+dx)<1e-8);assert(Math.abs((after.y-before.y)*-300+dy)<1e-8);panChecks++;
}
assert.equal(navigationMapping('pan').mouse.LEFT,T.MOUSE.PAN);assert.equal(navigationMapping('rotate').mouse.LEFT,T.MOUSE.ROTATE);assert.equal(navigationMapping('rotate').touch.TWO,T.TOUCH.DOLLY_PAN);
// Revision 11: preserve the vaginal source assembly and context camera bounds.
let contextChecks=0;
for(const id of ['FJ1449M','FJ1450M','FJ1453M','FJ1457M','FJ1458M','FJ1895'])assert(!structures.some(s=>s.sourceIds?.includes(id)),`${id}: redundant envelope returned`);
assert.deepEqual(byId.get('pancreas--parenchyma').sourceIds,['FJ2629']);
assert.deepEqual(byId.get('vagina').childrenIds,['vagina--surface','vagina--junction']);
assert.deepEqual(byId.get('vagina--surface').hraNodes,[431]);assert.deepEqual(byId.get('vagina--junction').hraNodes,[432]);
{
 const parent=byId.get('vagina');let vertex=0,index=0;
 for(const id of parent.childrenIds){const child=byId.get(id);const cp=new Float32Array(buffer,child.positions,child.vertexCount*3),pp=new Float32Array(buffer,parent.positions,parent.vertexCount*3);for(let i=0;i<cp.length;i++)assert(Math.abs(cp[i]+child.center[i%3]-pp[vertex*3+i]-parent.center[i%3])<1e-7);const ci=new Uint32Array(buffer,child.indices,child.indexCount),pi=new Uint32Array(buffer,parent.indices,parent.indexCount);for(let i=0;i<ci.length;i++)assert.equal(ci[i]+vertex,pi[index+i]);vertex+=child.vertexCount;index+=child.indexCount;}assert.equal(vertex,parent.vertexCount);assert.equal(index,parent.indexCount);
}
for(const selected of structures.filter(s=>s.contextIds)){
 const state=selectionState({...INITIAL,sex:'female'},selected);const ids=contextIdsForSelection(state,selected);
 for(const id of ids)assert(isStructureInSex(byId.get(id),'female'));
 const members=structures.filter(s=>structureDrawState(s,state).visible&&(structureDrawState(s,state).selected||isContextStructure(s,ids)));
 const bounds=new T.Box3();for(const s of members){const c=new T.Vector3().fromArray(s.center),h=new T.Vector3().fromArray(s.size).multiplyScalar(.5);bounds.union(new T.Box3(c.clone().sub(h),c.clone().add(h)));}
 for(const [w,h] of [[900,760],[420,620],[280,700]]){
  const fit=fitAnatomyBounds(bounds,new T.Vector3(.17,.1,1),w,h);const camera=new T.PerspectiveCamera(32,w/h,.001,80);camera.position.copy(fit.position);camera.lookAt(fit.center);camera.updateMatrixWorld(true);
  for(let i=0;i<8;i++){const p=new T.Vector3(i&1?bounds.max.x:bounds.min.x,i&2?bounds.max.y:bounds.min.y,i&4?bounds.max.z:bounds.min.z).project(camera);assert(Math.abs(p.x)<.94&&Math.abs(p.y)<.94);}
  contextChecks++;
 }
 for(const patch of [{context:false},{isolate:true},{mode:'explode'},{mode:'section'}])assert.deepEqual(contextIdsForSelection({...state,...patch},selected),[]);
}
const sceneSource=readFileSync(new URL('../app/anatomy-scene.tsx',import.meta.url),'utf8');assert(!sceneSource.includes('stencilWrite'));assert(!sceneSource.includes('PlaneGeometry(5,5)'));
console.log(JSON.stringify({structures:structures.length,organs:structures.filter(s=>s.layer===2).length,cameraFits:fits,organLocalSlices:slices,selectedPicking:picks,sourceCoordinateComparisons:sourceChecks,femaleAssemblyComparisons:femaleChecks,femaleSourceManifestComparisons:femaleManifestChecks,panProjectionChecks:panChecks,maleStructures:structures.filter(s=>isStructureInSex(s,'male')).length,femaleStructures:structures.filter(s=>isStructureInSex(s,'female')).length,detailSelectionChecks:detailChecks,lungChildAlignmentChecks:lungChecks,lungSourceRegistrationChecks:lungRegistrationChecks,pelvicComponentPreservationChecks:pelvicComponentChecks,documentedCompositeLungs:2,connectedStructureCameraFits:contextChecks}));
