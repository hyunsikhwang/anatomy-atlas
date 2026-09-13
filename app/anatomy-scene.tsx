"use client";
import {useEffect,useRef} from 'react';
import * as T from 'three';
import {OrbitControls} from 'three/examples/jsm/controls/OrbitControls.js';
import {RoomEnvironment} from 'three/examples/jsm/environments/RoomEnvironment.js';
import type {Structure,ViewerState} from './anatomy-types';
import {structurePosition,sectionPlane,fitAnatomyBounds,chooseVisibleHit,isStructureInSex,panTranslation,navigationMapping,familyForSelection,structureDrawState,pickStructureId,contextIdsForSelection,isContextStructure} from './anatomy-view';
import {DIAGRAM_TISSUES,activeDiagramRoots,diagramRoot,buildDiagramGeometry,diagramPoint,openingAngle,type DiagramData,type DiagramTissue} from './anatomy-diagram';
type Props={structures:Structure[];state:ViewerState;onSelect:(id:string)=>void;onDiagramSelect:(id:string)=>void;onDiagramReady:()=>void;onDiagramError:()=>void;onProgress:(n:number)=>void;onError:(s:string)=>void;onReady:()=>void};
type Piece={bounds:T.Box3;organIndex:number;s:Structure;mesh:T.Mesh<T.BufferGeometry,T.MeshStandardMaterial>;base:T.Vector3;destination:T.Vector3;label:HTMLButtonElement;line:HTMLDivElement};
type DiagramPiece={tissue:DiagramTissue;mesh:T.Mesh<T.BufferGeometry,T.MeshStandardMaterial>;anchor:T.Vector3;label:HTMLButtonElement;line:HTMLDivElement};
export default function AnatomyScene({structures,state,onSelect,onDiagramSelect,onDiagramReady,onDiagramError,onProgress,onError,onReady}:Props){
 const host=useRef<HTMLDivElement>(null),latest=useRef(state),select=useRef(onSelect),callbacks=useRef({onProgress,onError,onReady,onDiagramSelect,onDiagramReady,onDiagramError});latest.current=state;select.current=onSelect;callbacks.current={onProgress,onError,onReady,onDiagramSelect,onDiagramReady,onDiagramError};
 useEffect(()=>{
  const el=host.current!;let alive=true,raf=0,loaded=false,lastTime=0;const abort=new AbortController();
  let renderer:T.WebGLRenderer;
  try{renderer=new T.WebGLRenderer({alpha:true,antialias:true,powerPreference:'high-performance'});}catch{callbacks.current.onError('3D 실행 불가 · WebGL 지원 브라우저 필요');return;}
  renderer.setPixelRatio(Math.min(window.devicePixelRatio,1.7));renderer.setClearColor(0xffffff,0);renderer.outputColorSpace=T.SRGBColorSpace;renderer.toneMapping=T.ACESFilmicToneMapping;renderer.toneMappingExposure=1.06;renderer.localClippingEnabled=true;renderer.autoClear=false;
  renderer.domElement.setAttribute('aria-label','3D 인체 모델 · 드래그 회전·이동 · 휠 확대 · 방향키 시점 이동 · 목록에서 기관 선택');renderer.domElement.tabIndex=0;el.appendChild(renderer.domElement);
  const scene=new T.Scene(),camera=new T.PerspectiveCamera(32,1,.005,80);camera.position.set(.13,.96,3.5);
  const controls=new OrbitControls(camera,renderer.domElement);controls.target.set(0,.86,0);controls.enableDamping=true;controls.dampingFactor=.085;controls.minDistance=.06;controls.maxDistance=8;controls.maxPolarAngle=Math.PI*.96;controls.enablePan=true;controls.screenSpacePanning=true;
  const pm=new T.PMREMGenerator(renderer),room=new RoomEnvironment(),env=pm.fromScene(room,.03);scene.environment=env.texture;room.dispose();pm.dispose();
  scene.add(new T.HemisphereLight(0xffffff,0xb0c3b7,1.8));const light=new T.DirectionalLight(0xfff4e7,2.3);light.position.set(-3,4,4);scene.add(light);const rim=new T.DirectionalLight(0xecf9ff,2);rim.position.set(2,2,-3);scene.add(rim);
  const base=new T.Mesh(new T.CylinderGeometry(.46,.47,.01,96),new T.MeshStandardMaterial({color:'#e3ebe5',roughness:.9,metalness:.1,transparent:true,opacity:.6}));base.position.y=-.025;scene.add(base);
  const ring=new T.Mesh(new T.RingGeometry(.405,.407,128),new T.MeshBasicMaterial({color:'#aabfb0',side:T.DoubleSide,transparent:true,opacity:.5}));ring.rotation.x=-Math.PI/2;ring.position.y=-.018;scene.add(ring);
  scene.traverse(object=>{if(object instanceof T.Light)object.layers.enable(1);});
  const pieces:Piece[]=[];const fullBounds=new T.Box3();const plane=new T.Plane(new T.Vector3(0,0,-1),0);const cp=[plane];const targetPos=camera.position.clone(),targetLook=controls.target.clone();let flying=true,lastSelected:string|null=null,lastFocus=-1,lastCmd=-1,lastZoom=0,lastReset=-1,lastMode='whole',lastIsolate=false,lastExplode=-1,lastAxis='',lastSex=latest.current.sex,lastNavigation='',lastPanX=0,lastPanY=0,lastContext=latest.current.context;
  const organOrders={male:new Map(structures.filter(p=>!p.parentId&&p.layer===2&&isStructureInSex(p,'male')).map((p,i)=>[p.id,i])),female:new Map(structures.filter(p=>!p.parentId&&p.layer===2&&isStructureInSex(p,'female')).map((p,i)=>[p.id,i]))};
  const refreshSex=(s:ViewerState)=>{fullBounds.makeEmpty();pieces.forEach(p=>{p.organIndex=organOrders[s.sex].get(p.s.parentId??p.s.id)??0;if(!p.s.childrenIds?.length&&isStructureInSex(p.s,s.sex))fullBounds.union(p.bounds.clone().translate(p.base));});};
  const structureById=new Map(structures.map(s=>[s.id,s]));
  let diagramData:DiagramData|null=null,diagramKey='';const diagramPieces:DiagramPiece[]=[];
  const family=(s:ViewerState)=>familyForSelection(structureById.get(s.selected??''));
  const position=(p:Piece,s:ViewerState)=>structurePosition(p.s,s,p.organIndex,family(s));
  const worldBounds=(p:Piece,s:ViewerState)=>{const bounds=new T.Box3();const members=p.s.childrenIds?.length?pieces.filter(child=>child.s.parentId===p.s.id):[p];members.forEach(child=>bounds.union(child.bounds.clone().translate(position(child,s))));return bounds;};
  const motion=window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const setFlight=(center:T.Vector3,distance:number,direction?:T.Vector3)=>{controls.enableDamping=false;controls.update();controls.enableDamping=true;targetLook.copy(center);targetPos.copy(center).addScaledVector(direction??camera.position.clone().sub(controls.target).normalize(),distance);flying=true;};
  const panScreen=(dx:number,dy:number)=>{controls.enableDamping=false;controls.update();controls.enableDamping=true;const offset=panTranslation(camera,controls.target,dx,dy,el.clientHeight);targetLook.copy(controls.target).add(offset);targetPos.copy(camera.position).add(offset);flying=true;};
  const frameBounds=(bounds:T.Box3,direction:T.Vector3,wholeBody=false)=>{
   const fit=fitAnatomyBounds(bounds,direction,Math.max(1,el.clientWidth),Math.max(1,el.clientHeight),camera.fov,wholeBody);
   setFlight(fit.center,fit.distance,direction.clone().normalize());
  };
  const fitAll=(s:ViewerState)=>{
   const bounds=new T.Box3();
   pieces.forEach(p=>{if(structureDrawState(p.s,s).visible)bounds.union(p.bounds.clone().translate(position(p,s)));});
   if(bounds.isEmpty())bounds.set(new T.Vector3(-.4,0,-.15),new T.Vector3(.4,1.76,.15));
   const direction=s.view==='back'?new T.Vector3(0,.015,-1):s.view==='side'?new T.Vector3(1,.015,0):new T.Vector3(.06,.015,1);
   frameBounds(bounds,direction,true);
  };
  const focusPiece=(id:string)=>{
   const p=pieces.find(p=>p.s.id===id);if(!p||!isStructureInSex(p.s,latest.current.sex))return;
   const bounds=worldBounds(p,latest.current);const ids=contextIdsForSelection(latest.current,p.s);pieces.filter(q=>!q.s.childrenIds?.length&&isContextStructure(q.s,ids)&&structureDrawState(q.s,latest.current).visible).forEach(q=>bounds.union(worldBounds(q,latest.current)));
   const tissue=latest.current.mode==='diagram'?diagramPieces.find(d=>d.tissue.id===latest.current.diagramTissue):null;
   if(tissue&&!latest.current.diagramHidden.includes(tissue.tissue.id))bounds.copy(tissue.mesh.geometry.boundingBox!);
   frameBounds(bounds,latest.current.mode==='diagram'?new T.Vector3(.08,-.32,1):new T.Vector3(.17,.10,1));
  };
  const labelsRoot=document.createElement('div');labelsRoot.className='model-labels';el.appendChild(labelsRoot);
  const rebuildDiagram=(s:ViewerState)=>{
   if(!diagramData||s.mode!=='diagram')return;
   const key=`${s.diagramOpening}:${s.diagramRugae}`;if(key===diagramKey)return;diagramKey=key;
   DIAGRAM_TISSUES.forEach((tissue,index)=>{
    const profile=diagramData!.profiles.find(p=>p.root===tissue.root)!;
    const geometry=buildDiagramGeometry(profile,tissue,s.diagramOpening,s.diagramRugae,diagramData!.profiles.find(p=>p.root==='uterus'));
    const targetT=tissue.root==='vagina'?[.3,.51,.72][index]:tissue.group==='자궁경부'?[.16,.24][index-6]:[.58,.72,.84][index-3];
    const row=profile.rows.reduce((best,row)=>Math.abs(row.t-targetT)<Math.abs(best.t-targetT)?row:best);
    const anchor=diagramPoint(profile,row,openingAngle(s.diagramOpening)/2,(tissue.range[0]+tissue.range[1])/2,s.diagramRugae);
    const previous=diagramPieces.find(p=>p.tissue.id===tissue.id);
    if(previous){previous.mesh.geometry.dispose();previous.mesh.geometry=geometry;previous.anchor.copy(anchor);return;}
    const material=new T.MeshStandardMaterial({color:tissue.color,side:T.DoubleSide,roughness:.62,metalness:0,transparent:true,opacity:1});
    const mesh=new T.Mesh(geometry,material);mesh.layers.set(1);mesh.userData.diagramTissue=tissue.id;mesh.renderOrder=2;scene.add(mesh);
    const label=document.createElement('button');label.className='model-label diagram-label';label.type='button';label.textContent=tissue.name;label.style.setProperty('--tissue-color',tissue.color);label.setAttribute('aria-label',`${tissue.group} ${tissue.name} 선택`);label.onclick=()=>callbacks.current.onDiagramSelect(tissue.id);label.hidden=true;labelsRoot.appendChild(label);
    const line=document.createElement('div');line.className='label-line diagram-line';line.hidden=true;labelsRoot.appendChild(line);
    diagramPieces.push({tissue,mesh,anchor,label,line});
   });
  };
  const tip=document.createElement('div');tip.className='model-tooltip';tip.hidden=true;el.appendChild(tip);
  const labelIds=new Set(['brain','heart','left-lung','liver','stomach','left-kidney','large-intestine','skull','ribcage','pelvis','left-femur','right-humerus','chest-muscles','left-thigh-muscles','left-eye','female-pelvis','female-large-intestine','uterus']);
  const load=async()=>{try{
   const manifestResponse=await fetch('/models/anatomy-v13-manifest.json',{signal:abort.signal});if(!manifestResponse.ok)throw new Error('모델 정보 로딩 실패');
   const manifest=await manifestResponse.json() as {files:string[];bytes:number};let size=0;const chunks:Uint8Array[]=[];
   for(const file of manifest.files){const response=await fetch(file,{signal:abort.signal});if(!response.ok)throw new Error('모델 로딩 실패');const reader=response.body!.getReader();while(true){const v=await reader.read();if(v.done)break;chunks.push(v.value);size+=v.value.length;if(alive)callbacks.current.onProgress(Math.min(92,Math.round(size/manifest.bytes*92)));}}
   const packed=new Uint8Array(size);let off=0;for(const c of chunks){packed.set(c,off);off+=c.length;}let buffer:ArrayBuffer;if(packed[0]===31&&packed[1]===139){if(typeof DecompressionStream==='undefined'){throw new Error('압축 해제 불가 · 최신 Chrome·Edge·Safari 필요');}else{buffer=await new Response(new Blob([packed]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer();}}else buffer=packed.buffer;
   if(!alive)return;
   structures.forEach((s,i)=>{
    const geometry=new T.BufferGeometry();geometry.setAttribute('position',new T.BufferAttribute(new Float32Array(buffer,s.positions,s.vertexCount*3),3));geometry.setAttribute('normal',new T.BufferAttribute(new Int16Array(buffer,s.normals,s.vertexCount*3),3,true));geometry.setIndex(new T.BufferAttribute(new Uint32Array(buffer,s.indices,s.indexCount),1));geometry.computeBoundingBox();geometry.computeBoundingSphere();
    if(s.colors!==undefined)geometry.setAttribute('color',new T.BufferAttribute(new Uint8Array(buffer,s.colors,s.vertexCount*3),3,true));
    const material=new T.MeshStandardMaterial({color:s.colors!==undefined?'#ffffff':s.color,vertexColors:s.colors!==undefined,roughness:s.layer===0?.49:.57,metalness:.02,side:T.DoubleSide,transparent:true,opacity:1,depthWrite:true,clippingPlanes:[]});
    const mesh=new T.Mesh(geometry,material);const basePos=new T.Vector3().fromArray(s.center);mesh.position.copy(basePos);mesh.userData.id=s.id;mesh.renderOrder=1;scene.add(mesh);
    const label=document.createElement('button');label.className='model-label';label.type='button';label.textContent=s.name;label.setAttribute('aria-label',s.name+' 선택');label.addEventListener('click',()=>select.current(s.id));labelsRoot.appendChild(label);
    const line=document.createElement('div');line.className='label-line';labelsRoot.appendChild(line);
    // Surface meshes do not encode tissue thickness or complete luminal walls.
    // Clip only supplied triangles; a filled stencil cap would invent anatomy.
    const bounds=geometry.boundingBox!.clone();fullBounds.union(bounds.clone().translate(basePos));
    pieces.push({bounds,organIndex:structures.filter(p=>p.layer===2).findIndex(p=>p.id===s.id),s,mesh,base:basePos,destination:basePos.clone(),label,line});
   });refreshSex(latest.current);loaded=true;callbacks.current.onProgress(100);callbacks.current.onReady();fitAll(latest.current);lastSelected=null;lastFocus=-1;
   try{const response=await fetch('/models/diagram-profiles-v1.json',{signal:abort.signal});if(!response.ok)throw new Error();const data=await response.json() as DiagramData;if(data.kind!=='educational-schematic-envelope'||data.profiles.length!==2)throw new Error();if(alive){diagramData=data;callbacks.current.onDiagramReady();}}
   catch{if(alive)callbacks.current.onDiagramError();}
  }catch(e){if(alive)callbacks.current.onError(e instanceof Error?e.message:'모델 로딩 실패 · 재시도 필요');}};void load();
  const resize=()=>{if(!el.clientWidth||!el.clientHeight)return;camera.aspect=el.clientWidth/el.clientHeight;camera.updateProjectionMatrix();renderer.setSize(el.clientWidth,el.clientHeight);if(latest.current.selected)focusPiece(latest.current.selected);else fitAll(latest.current);};const observer=new ResizeObserver(resize);observer.observe(el);
  controls.addEventListener('start',()=>{flying=false;tip.hidden=true;});
  const ray=new T.Raycaster(),pointer=new T.Vector2();ray.layers.enable(1);let startX=0,startY=0,maxMove=0,multi=false;const pointers=new Set<number>();
  const hit=(e:PointerEvent)=>{
   const r=el.getBoundingClientRect();pointer.set((e.clientX-r.left)/r.width*2-1,-(e.clientY-r.top)/r.height*2+1);ray.setFromCamera(pointer,camera);
   const s=latest.current;
   const diagramHits=ray.intersectObjects(diagramPieces.filter(p=>p.mesh.visible).map(p=>p.mesh),false);
   if(diagramHits.length){const id=chooseVisibleHit(diagramHits.map(h=>({id:h.object.userData.diagramTissue,opacity:(h.object as T.Mesh<T.BufferGeometry,T.MeshStandardMaterial>).material.opacity})),s.diagramTissue);return 'diagram:'+id;}
   const eligible=pieces.filter(p=>p.mesh.visible&&!p.mesh.userData.diagramGhost&&p.mesh.material.opacity>.035);
   const hits=ray.intersectObjects(eligible.map(p=>p.mesh),false).filter(h=>s.mode!=='section'||plane.distanceToPoint(h.point)>=-.0001);
   return chooseVisibleHit(hits.map(h=>({id:pickStructureId(structureById.get(h.object.userData.id)!,family(s)),opacity:(h.object as T.Mesh<T.BufferGeometry,T.MeshStandardMaterial>).material.opacity})),s.selected);
  };
  const down=(e:PointerEvent)=>{pointers.add(e.pointerId);if(pointers.size>1)multi=true;else{multi=false;startX=e.clientX;startY=e.clientY;maxMove=0;}tip.hidden=true;};
  const move=(e:PointerEvent)=>{maxMove=Math.max(maxMove,Math.hypot(e.clientX-startX,e.clientY-startY));if(e.buttons||e.pointerType==='touch'||!loaded||latest.current.navigation==='pan'){tip.hidden=true;return;}const id=hit(e);const tissue=DIAGRAM_TISSUES.find(t=>'diagram:'+t.id===id);const name=tissue?`${tissue.group} · ${tissue.name}`:pieces.find(p=>p.s.id===id)?.s.name;renderer.domElement.style.cursor=name?'pointer':'grab';tip.hidden=!name;if(name){tip.textContent=name;const r=el.getBoundingClientRect();tip.style.left=Math.min(el.clientWidth-160,Math.max(12,e.clientX-r.left+14))+'px';tip.style.top=Math.max(12,e.clientY-r.top-38)+'px';}};
  const up=(e:PointerEvent)=>{pointers.delete(e.pointerId);if(e.button!==0||latest.current.navigation==='pan'||multi||maxMove>6||!loaded)return;const id=hit(e);if(id?.startsWith('diagram:'))callbacks.current.onDiagramSelect(id.slice(8));else if(id)select.current(id);};const cancel=(e:PointerEvent)=>{pointers.delete(e.pointerId);multi=true;tip.hidden=true;};
  const key=(e:KeyboardEvent)=>{if(e.key==='+'||e.key==='='){e.preventDefault();setFlight(controls.target.clone(),camera.position.distanceTo(controls.target)*.8);}else if(e.key==='-'){e.preventDefault();setFlight(controls.target.clone(),camera.position.distanceTo(controls.target)*1.2);}else if(e.key==='Home'){e.preventDefault();fitAll(latest.current);}else if(['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(e.key)){e.preventDefault();const step=e.shiftKey?88:44;panScreen(e.key==='ArrowLeft'?-step:e.key==='ArrowRight'?step:0,e.key==='ArrowUp'?-step:e.key==='ArrowDown'?step:0);}};
  renderer.domElement.addEventListener('contextmenu',e=>e.preventDefault());
  renderer.domElement.addEventListener('pointerdown',down);renderer.domElement.addEventListener('pointermove',move);renderer.domElement.addEventListener('pointerup',up);renderer.domElement.addEventListener('pointercancel',cancel);renderer.domElement.addEventListener('pointerleave',()=>{tip.hidden=true;});renderer.domElement.addEventListener('keydown',key);
  const projected=new T.Vector3();let lastLabel=0;
  const orientR=document.createElement('div'),orientL=document.createElement('div');for(const [node,text] of [[orientR,'R'],[orientL,'L']] as const){node.className='anatomic-side';node.textContent=text;el.appendChild(node);}
  const animate=(now:number)=>{
   if(!alive)return;raf=requestAnimationFrame(animate);const dt=Math.min((now-lastTime)/1000,.05)||.016;lastTime=now;const s=latest.current;const cut=s.mode==='section';
   if(s.sex!==lastSex){refreshSex(s);lastSex=s.sex;if(loaded)fitAll(s);}
   if(s.navigation!==lastNavigation){const mapping=navigationMapping(s.navigation);controls.mouseButtons=mapping.mouse;controls.touches=mapping.touch;renderer.domElement.style.cursor='grab';lastNavigation=s.navigation;}
   const selectedPiece=pieces.find(p=>p.s.id===s.selected&&isStructureInSex(p.s,s.sex));
   const contextIds=contextIdsForSelection(s,selectedPiece?.s);
   const diagramRoots=activeDiagramRoots(s);rebuildDiagram(s);
   diagramPieces.forEach(p=>{p.mesh.visible=diagramRoots.includes(p.tissue.root)&&!s.diagramHidden.includes(p.tissue.id);const highlighted=s.diagramTissue===p.tissue.id;const opacity=s.opacity[2]/100*(s.diagramTissue&&!highlighted?.38:1);p.mesh.material.opacity=T.MathUtils.damp(p.mesh.material.opacity,opacity,14,dt);p.mesh.material.depthWrite=!s.diagramTissue||highlighted;p.mesh.material.emissive.set(highlighted?'#7d3e3e':'#000000');p.mesh.material.emissiveIntensity=highlighted?.18+(motion?0:.08*(Math.sin(now*.003)+1)):0;if(!p.mesh.visible||!s.labels){p.label.hidden=true;p.line.hidden=true;}});
   const sliceBounds=selectedPiece?worldBounds(selectedPiece,s):fullBounds;
   if(!sliceBounds.isEmpty())plane.copy(sectionPlane(s,sliceBounds));
   pieces.forEach(p=>{
    p.destination.copy(position(p,s));
    p.mesh.position.lerp(p.destination,motion?1:1-Math.exp(-10*dt));
    const {visible,selected}=structureDrawState(p.s,s);const root=diagramRoot(p.s.id);const ghost=!!root&&diagramRoots.includes(root)&&p.s.id!=='uterus--cornua';p.mesh.visible=visible&&(!ghost||s.diagramOutline);p.mesh.userData.diagramGhost=ghost;
    if(p.s.parentId){const parent=structureById.get(p.s.parentId)!;p.mesh.material.color.set(family(s)===p.s.parentId||p.s.parentId.endsWith('-eye')?p.s.color:parent.color);}
    const context=isContextStructure(p.s,contextIds);let opacity=s.opacity[p.s.layer]/100;if(s.selected&&!selected)opacity*=context?.65:s.isolate?0:.065;
    if(ghost)opacity=s.opacity[2]/100*.10;
    const drawLayer=!ghost&&(selected||context)?1:0;p.mesh.layers.set(drawLayer);
    p.mesh.material.opacity=T.MathUtils.damp(p.mesh.material.opacity,opacity,14,dt);p.mesh.material.depthWrite=!ghost&&(selected||opacity>.95);p.mesh.material.clippingPlanes=cut?cp:[];
    p.mesh.material.emissive.set(selected&&!ghost?'#287c63':'#000000');p.mesh.material.emissiveIntensity=selected&&!ghost?.17+(motion?0:.065*(Math.sin(now*.003)+1)):0;

   });
   if(loaded){
    if(s.reset!==lastReset||s.command!==lastCmd){lastReset=s.reset;lastCmd=s.command;lastPanX=s.panX;lastPanY=s.panY;lastZoom=s.zoom;fitAll(s);}
    if(s.mode!==lastMode||s.isolate!==lastIsolate||s.explode!==lastExplode||s.axis!==lastAxis||s.context!==lastContext){if(s.selected)focusPiece(s.selected);else if(s.mode!==lastMode||s.explode!==lastExplode)fitAll(s);lastMode=s.mode;lastIsolate=s.isolate;lastExplode=s.explode;lastAxis=s.axis;lastContext=s.context;}
    if(s.selected!==lastSelected||s.focus!==lastFocus){if(s.selected)focusPiece(s.selected);else if(lastSelected)fitAll(s);lastSelected=s.selected;lastFocus=s.focus;}
    if(s.panX!==lastPanX||s.panY!==lastPanY){panScreen((s.panX-lastPanX)*44,(s.panY-lastPanY)*44);lastPanX=s.panX;lastPanY=s.panY;}
    if(s.zoom!==lastZoom){const factor=Math.pow(.82,s.zoom-lastZoom);setFlight(controls.target.clone(),T.MathUtils.clamp(camera.position.distanceTo(controls.target)*factor,.06,8));lastZoom=s.zoom;}
   }
   if(flying){const t=motion?1:1-Math.exp(-6*dt);camera.position.lerp(targetPos,t);controls.target.lerp(targetLook,t);if(camera.position.distanceTo(targetPos)<.001&&controls.target.distanceTo(targetLook)<.001)flying=false;}
   controls.update();
   // Context never masks the selected organ. Keep depth testing inside the organ itself.
   base.visible=ring.visible=!s.selected;
   camera.layers.set(0);renderer.clear();renderer.render(scene,camera);
   if(selectedPiece&&(pieces.some(p=>p.mesh.visible&&p.mesh.layers.isEnabled(1))||diagramPieces.some(p=>p.mesh.visible))){renderer.clearDepth();camera.layers.set(1);renderer.render(scene,camera);camera.layers.set(0);}
   if(now-lastLabel>45){lastLabel=now;[orientR,orientL].forEach((node,i)=>{projected.set(i===0?-.32:.32,1.05,0).project(camera);node.hidden=!!s.selected||s.mode!=='whole'||projected.z>1;node.style.transform=`translate(${(projected.x+1)*el.clientWidth/2}px,${(1-projected.y)*el.clientHeight/2}px)`;});const active=pieces.filter(p=>s.labels&&(s.selected?((p.mesh.visible&&(p.s.id===s.selected||p.s.parentId===s.selected))||(contextIds.includes(p.s.id)&&(p.mesh.visible||p.s.childrenIds?.some(id=>pieces.some(q=>q.s.id===id&&q.mesh.visible))))):labelIds.has(p.s.id)&&(p.mesh.visible||p.s.childrenIds?.some(id=>{const child=structureById.get(id);return child&&structureDrawState(child,s).visible;}))));const occupied:{x:number;y:number}[]=[];
    pieces.forEach(p=>{p.label.hidden=true;p.line.hidden=true;});active.filter(p=>!diagramRoots.includes(diagramRoot(p.s.id)!)).sort((a,b)=>b.s.center[1]-a.s.center[1]).forEach((p,index)=>{
     const anchor=p.mesh.position.clone();
     const positions=p.mesh.geometry.getAttribute('position');let closest=Infinity;const localTarget=camera.position.clone().sub(p.mesh.position).normalize().multiplyScalar(p.mesh.geometry.boundingSphere!.radius*.6);const candidate=new T.Vector3();
     for(let vi=0;vi<positions.count;vi+=Math.max(1,Math.floor(positions.count/100))){candidate.fromBufferAttribute(positions,vi).add(p.mesh.position);if(cut&&plane.distanceToPoint(candidate)<0)continue;const score=candidate.clone().sub(p.mesh.position).distanceToSquared(localTarget);if(score<closest){closest=score;anchor.copy(candidate);}}
     if(closest===Infinity)return;projected.copy(anchor).project(camera);if(projected.z>1||projected.z< -1)return;const x=(projected.x+1)*el.clientWidth/2,y=(1-projected.y)*el.clientHeight/2;if(y<125||y>el.clientHeight-85||x<35||x>el.clientWidth-35)return;
     const right=p.base.x>0;const destX=T.MathUtils.clamp(x+(right?76:-100),12,el.clientWidth-160);let destY=y-10;for(const o of occupied)if(Math.abs(o.x-destX)<135&&Math.abs(o.y-destY)<31)destY=o.y+32;if(destY>el.clientHeight-85)return;occupied.push({x:destX,y:destY});p.label.hidden=false;p.label.classList.toggle('selected',s.selected===p.s.id);p.label.style.transform=`translate(${destX}px,${destY}px)`;
     const endX=right?destX:destX+p.label.offsetWidth;const endY=destY+14;const dx=endX-x,dy=endY-y;p.line.hidden=false;p.line.style.width=Math.hypot(dx,dy)+'px';p.line.style.transform=`translate(${x}px,${y}px) rotate(${Math.atan2(dy,dx)}rad)`;
    });
    diagramPieces.forEach(p=>{p.label.hidden=true;p.line.hidden=true;});
    diagramPieces.filter(p=>s.labels&&p.mesh.visible&&(p.tissue.root===diagramRoot(s.selected)||p.tissue.id===s.diagramTissue)).forEach((p,index)=>{
     projected.copy(p.anchor).project(camera);if(projected.z>1||projected.z< -1)return;
     const x=(projected.x+1)*el.clientWidth/2,y=(1-projected.y)*el.clientHeight/2;if(x<0||x>el.clientWidth||y<115||y>el.clientHeight-185)return;
     const destX=T.MathUtils.clamp(x+55,12,el.clientWidth-145);let destY=y-12;
     for(const o of occupied)if(Math.abs(o.x-destX)<145&&Math.abs(o.y-destY)<30)destY=o.y+31;
     if(destY>el.clientHeight-185)return;occupied.push({x:destX,y:destY});p.label.hidden=false;p.label.classList.toggle('selected',s.diagramTissue===p.tissue.id);p.label.style.transform=`translate(${destX}px,${destY}px)`;
     const dx=destX-x,dy=destY+13-y;p.line.hidden=false;p.line.style.width=Math.hypot(dx,dy)+'px';p.line.style.transform=`translate(${x}px,${y}px) rotate(${Math.atan2(dy,dx)}rad)`;
    });
   }
  };raf=requestAnimationFrame(animate);resize();
  const lost=(e:Event)=>{e.preventDefault();callbacks.current.onError('3D 연결 중단 · 새로고침 필요');};renderer.domElement.addEventListener('webglcontextlost',lost);
  return()=>{alive=false;abort.abort();cancelAnimationFrame(raf);observer.disconnect();controls.dispose();pieces.forEach(p=>{p.mesh.geometry.dispose();p.mesh.material.dispose();});diagramPieces.forEach(p=>{p.mesh.geometry.dispose();p.mesh.material.dispose();});base.geometry.dispose();(base.material as T.Material).dispose();ring.geometry.dispose();(ring.material as T.Material).dispose();env.dispose();renderer.dispose();renderer.domElement.remove();labelsRoot.remove();tip.remove();orientR.remove();orientL.remove();};
 },[structures]);
 return <div className="scene-host" ref={host}/>;
}
