import * as T from 'three';
import type {Structure, ViewerState, Sex} from './anatomy-types';
import {diagramRoot} from './anatomy-diagram.ts';

/** All assembled positions stay in the source model's common coordinate frame. */
export function structurePosition(s:Structure, state:ViewerState, organIndex:number,activeFamily:string|null=null){
 const position=new T.Vector3().fromArray(s.center);
 if(state.mode!=='explode') return position;
 const amount=state.explode/100;
 if(s.layer===2){
  position.x+=(organIndex%2===0?-.64:.64)*amount;
  position.y+=(Math.floor(organIndex/2)-3.5)*-.12*amount;
  position.z+=.20*amount;
 }else if(s.layer===1){
  position.x+=(s.center[0]>=0?1:-1)*(.35+Math.abs(s.center[0]))*amount;
  position.y+=(s.center[1]-.85)*.22*amount;
  position.z-=.26*amount;
 }else{
  position.x+=s.center[0]*.5*amount;
  position.y+=(s.center[1]-.85)*.12*amount;
  position.z-=.10*amount;
 }
 if(s.parentId===activeFamily&&s.detailOffset)position.addScaledVector(new T.Vector3().fromArray(s.detailOffset),amount);
 return position;
}

export function sectionPlane(state:ViewerState, bounds:T.Box3){
 const axis=state.axis;
 const size=bounds.max[axis]-bounds.min[axis];
 // A selected organ has its own slicing range; global percentages would erase small organs.
 const margin=Math.max(size*.015,.0001);
 const position=T.MathUtils.lerp(bounds.min[axis]-margin,bounds.max[axis]+margin,state.cut/100);
 const normal=new T.Vector3(axis==='x'?-1:0,axis==='y'?-1:0,axis==='z'?-1:0);
 return new T.Plane(normal,position);
}

export function fitAnatomyBounds(bounds:T.Box3,direction:T.Vector3,width:number,height:number,fov=32,wholeBody=false){
 const center=bounds.getCenter(new T.Vector3());
 const forward=direction.clone().normalize();
 const right=new T.Vector3().crossVectors(new T.Vector3(0,1,0),forward).normalize();
 const up=new T.Vector3().crossVectors(forward,right).normalize();
 const aspect=Math.max(1,width)/Math.max(1,height);
 const verticalPadding=wholeBody?Math.min(48,height*.08):Math.min(135,height*.23);
 const horizontalPadding=wholeBody?Math.min(32,width*.08):Math.min(48,width*.12);
 const tanY=Math.tan(T.MathUtils.degToRad(fov/2))*(1-2*verticalPadding/height);
 const tanX=Math.tan(T.MathUtils.degToRad(fov/2))*aspect*(1-2*horizontalPadding/width);
 let distance=.035;
 for(let i=0;i<8;i++){
  const relative=new T.Vector3(i&1?bounds.max.x:bounds.min.x,i&2?bounds.max.y:bounds.min.y,i&4?bounds.max.z:bounds.min.z).sub(center);
  const depth=relative.dot(forward);
  distance=Math.max(distance,Math.abs(relative.dot(right))/tanX+depth,Math.abs(relative.dot(up))/tanY+depth);
 }
 distance*=1.12;
 return {center,position:center.clone().addScaledVector(forward,distance),distance};
}

export function selectionState(state:ViewerState,structure:Structure):ViewerState{
 if(!isStructureInSex(structure,state.sex))return state;
 const root=diagramRoot(structure.id);
 return {...state,selected:state.mode==='diagram'&&root?root:structure.id,mode:state.mode==='diagram'&&!root?'whole':state.mode,diagramTissue:null,visible:state.visible.map((v,i)=>i===structure.layer?true:v),opacity:state.opacity.map((v,i)=>i===structure.layer?100:v),cut:state.mode==='section'?50:state.cut,focus:state.focus+1};
}

export function chooseVisibleHit(hits: {id:string;opacity:number}[], selected:string|null){
 // Selection is rendered in a separate depth pass, so picking must follow the same visible order.
 return (hits.find(hit=>hit.id===selected)??hits.find(hit=>hit.opacity>=.55)??hits[0])?.id??null;
}

export function isStructureInSex(structure:Structure,sex:Sex){
 return !structure.sex||structure.sex==='both'||structure.sex===sex;
}
export function sexState(state:ViewerState,sex:Sex):ViewerState{
 return {...state,sex,selected:null,isolate:false,mode:state.mode==='diagram'?'whole':state.mode,diagramTissue:null,cut:50,command:state.command+1};
}
/** Translate parallel to the camera plane. Positive x/y moves the viewpoint right/down. Drag gestures remain object-relative. */
export function panTranslation(camera:T.PerspectiveCamera,target:T.Vector3,dx:number,dy:number,height:number){
 camera.updateMatrixWorld();
 const units=2*camera.position.distanceTo(target)*Math.tan(T.MathUtils.degToRad(camera.fov/2))/Math.max(1,height);
 const right=new T.Vector3().setFromMatrixColumn(camera.matrixWorld,0);
 const up=new T.Vector3().setFromMatrixColumn(camera.matrixWorld,1);
 return right.multiplyScalar(dx*units).addScaledVector(up,-dy*units);
}
export function navigationMapping(navigation:ViewerState['navigation']){
 return {mouse:{LEFT:navigation==='pan'?T.MOUSE.PAN:T.MOUSE.ROTATE,MIDDLE:T.MOUSE.DOLLY,RIGHT:T.MOUSE.PAN},touch:{ONE:navigation==='pan'?T.TOUCH.PAN:T.TOUCH.ROTATE,TWO:T.TOUCH.DOLLY_PAN}};
}

export function familyForSelection(selected?:Structure){
 return selected?.parentId??(selected?.childrenIds?.length?selected.id:null);
}
export function contextIdsForSelection(state:ViewerState,selected?:Structure){
 return state.context&&!state.isolate&&(state.mode==='whole'||state.mode==='diagram')?selected?.contextIds??[]:[];
}
export function isContextStructure(structure:Structure,ids:string[]){
 return ids.includes(structure.id)||!!structure.parentId&&ids.includes(structure.parentId);
}
export function structureDrawState(structure:Structure,state:ViewerState){
 const selected=structure.id===state.selected||structure.parentId===state.selected;
 const visible=!structure.childrenIds?.length&&isStructureInSex(structure,state.sex)&&state.visible[structure.layer]&&state.opacity[structure.layer]>0&&(!state.isolate||selected);
 return {selected,visible};
}
export function pickStructureId(structure:Structure,activeFamily:string|null){
 return structure.parentId&&structure.parentId!==activeFamily?structure.parentId:structure.id;
}
