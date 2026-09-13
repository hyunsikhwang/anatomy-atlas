import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import * as T from 'three';
import {DIAGRAM_TISSUES,activeDiagramRoots,diagramRoot,diagramState,diagramRadius,diagramPoint,buildDiagramGeometry} from '../app/anatomy-diagram.ts';
import {INITIAL} from '../app/anatomy-types.ts';
import {selectionState,sexState,fitAnatomyBounds,contextIdsForSelection,structurePosition} from '../app/anatomy-view.ts';
const data=JSON.parse(readFileSync('public/models/diagram-profiles-v1.json'));
const structures=JSON.parse(readFileSync('public/models/anatomy-v13.json'));
const manifest=JSON.parse(readFileSync('public/models/anatomy-v13-manifest.json'));
const packed=Buffer.concat(manifest.files.map(f=>readFileSync('public'+f)));
assert.equal(createHash('sha256').update(packed).digest('hex'),data.sourceSha256,'Illustrations must reference the unchanged source pack');
assert.equal(structures.length,193);assert.equal(data.units,'meters');assert.equal(data.profiles.length,2);
const vagina=data.profiles.find(p=>p.root==='vagina'),uterus=data.profiles.find(p=>p.root==='uterus');
const externalOs=new T.Vector3(-.00199864,.89064944,-.02424901),internalOs=new T.Vector3(-.00225804,.89911324,-.01051247);
assert(new T.Vector3().fromArray(vagina.rows.at(-1).center).distanceTo(externalOs)<1e-7);
assert(new T.Vector3().fromArray(uterus.rows[0].center).distanceTo(externalOs)<1e-7);
assert(new T.Vector3().fromArray(uterus.rows.find(r=>Math.abs(r.t-uterus.split)<1e-8).center).distanceTo(internalOs)<1e-7);
assert(uterus.axis[2]>.8,'Preserve anterior uterine inclination');
let geometries=0,channelRays=0,picks=0,fits=0;
for(const opening of [0,55,100])for(const rugae of [false,true]){
 const meshes=[];
 for(const tissue of DIAGRAM_TISSUES){
  const profile=data.profiles.find(p=>p.root===tissue.root);
  const geometry=buildDiagramGeometry(profile,tissue,opening,rugae,uterus);
  const positions=geometry.attributes.position.array;
  for(const v of positions)assert(Number.isFinite(v));for(const n of geometry.attributes.normal.array)assert(Number.isFinite(n));for(const i of geometry.index.array)assert(i<positions.length/3);
  const source=structures.find(s=>s.id===tissue.root),center=new T.Vector3().fromArray(source.center),half=new T.Vector3().fromArray(source.size).multiplyScalar(.5);
  const sourceBounds=new T.Box3(center.clone().sub(half),center.clone().add(half)).expandByScalar(1e-6);
  assert(sourceBounds.containsBox(geometry.boundingBox),`${tissue.id}: illustrative envelope leaves original organ bounds`);
  const mesh=new T.Mesh(geometry,new T.MeshBasicMaterial({side:T.DoubleSide}));mesh.userData.id=tissue.id;mesh.updateMatrixWorld(true);meshes.push(mesh);
  // Each tissue remains independently ray-selectable from a cut face.
  const index=geometry.index.array;let picked=false;
  for(let k=index.length-3;k>=0;k-=3){const a=new T.Vector3().fromArray(positions,index[k]*3),b=new T.Vector3().fromArray(positions,index[k+1]*3),c=new T.Vector3().fromArray(positions,index[k+2]*3);
   const normal=b.clone().sub(a).cross(c.clone().sub(a)).normalize(),target=a.clone().add(b).add(c).divideScalar(3);
   if(normal.lengthSq()>.5){const ray=new T.Raycaster(target.clone().addScaledVector(normal,.02),normal.clone().negate());assert(ray.intersectObject(mesh,false).length);picked=true;break;}}
  assert(picked,`${tissue.id}: no pickable tissue surface`);picks++;
  for(const [width,height] of [[900,760],[420,620],[280,480]]){
   const fit=fitAnatomyBounds(geometry.boundingBox,new T.Vector3(.08,-.32,1),width,height);
   const camera=new T.PerspectiveCamera(32,width/height,.001,80);camera.position.copy(fit.position);camera.lookAt(fit.center);camera.updateMatrixWorld(true);
   for(let i=0;i<8;i++){const bounds=geometry.boundingBox,p=new T.Vector3(i&1?bounds.max.x:bounds.min.x,i&2?bounds.max.y:bounds.min.y,i&4?bounds.max.z:bounds.min.z).project(camera);assert(Math.abs(p.x)<.94&&Math.abs(p.y)<.94);}fits++;
  }
  geometries++;
 }
 // A ray entering the opened channel reaches the inner mucosa, never a solid cap.
 for(const profile of data.profiles)for(const t of profile.root==='vagina'?[.25,.5,.75]:[.13,.5,.78]){
  const row=profile.rows.reduce((a,b)=>Math.abs(a.t-t)<Math.abs(b.t-t)?a:b),center=new T.Vector3().fromArray(row.center),front=new T.Vector3().fromArray(profile.front);
  const ray=new T.Raycaster(center.clone().addScaledVector(front,.08),front.clone().negate());
  const relevant=meshes.filter(m=>DIAGRAM_TISSUES.find(t=>t.id===m.userData.id).root===profile.root);
  const hits=ray.intersectObjects(relevant,false);assert(hits.length);
  const expected=profile.root==='vagina'?'vaginal-mucosa':row.t<profile.split?'cervical-mucosa':'endometrium';
  assert.equal(hits[0].object.userData.id,expected,`${profile.root} t=${t}: inner wall obscured`);
  assert(hits[0].point.clone().sub(center).dot(front)<0,'Lumen must stay empty in front of the posterior wall');channelRays++;
 }
 meshes.forEach(m=>{m.geometry.dispose();m.material.dispose();});
}
for(const profile of data.profiles)for(const row of profile.rows)for(let i=0;i<24;i++){
 const angle=i*Math.PI/12,rs=[0,.14,.27,.8,.92,1].map(f=>diagramRadius(profile,row,angle,f,true));
 assert(rs[0]>=0);for(let j=1;j<rs.length;j++)assert(rs[j]>=rs[j-1]);
 if(profile.root==='vagina')assert(diagramRadius(profile,row,angle,0,true)<=diagramRadius(profile,row,angle,0,false));
}
for(let i=0;i<24;i++)assert.equal(diagramRadius(uterus,uterus.rows.at(-1),i*Math.PI/12,0),0,'Fundus must close, not form another opening');
for(const root of ['vagina','uterus']){
 const state=diagramState({...INITIAL,visible:[false,false,false],opacity:[0,0,0]},root);
 assert.equal(state.sex,'female');assert.equal(state.mode,'diagram');assert.equal(state.selected,root);assert.deepEqual(activeDiagramRoots(state),['vagina','uterus']);assert(state.visible[2]);assert.equal(state.opacity[2],100);
 assert.deepEqual(activeDiagramRoots({...state,isolate:true}),[root]);assert.deepEqual(activeDiagramRoots({...state,context:false}),[root]);
 for(const mode of ['whole','explode','section'])assert.deepEqual(activeDiagramRoots({...state,mode}),[]);
 for(const off of [{sex:'male'},{selected:null},{visible:[true,true,false]},{opacity:[100,100,0]}])assert.deepEqual(activeDiagramRoots({...state,...off}),[]);
 assert.equal(sexState(state,'male').mode,'whole');assert.equal(sexState(state,'male').diagramTissue,null);
 const source=structures.find(s=>s.id===root);assert(contextIdsForSelection(state,source).length>0);
 assert.deepEqual(structurePosition(source,state,0).toArray(),source.center);
 const child=structures.find(s=>s.parentId===root);assert.equal(selectionState(state,child).selected,root);
 assert.equal(selectionState(state,structures.find(s=>s.id==='left-ovary')).mode,'whole');
}
assert.equal(DIAGRAM_TISSUES.filter(t=>t.group==='자궁체부').length,3);assert.equal(DIAGRAM_TISSUES.filter(t=>t.group==='자궁경부').length,2);assert.equal(DIAGRAM_TISSUES.filter(t=>t.group==='질').length,3);
assert.equal(diagramRoot('male-bladder'),null);
console.log(JSON.stringify({sourceStructures:193,geometries,channelRays,tissuePicking:picks,cameraFits:fits,osLandmarks:3,tissueGroups:3}));
