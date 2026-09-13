import * as T from 'three';
import type {ViewerState} from './anatomy-types';

export type DiagramRoot='vagina'|'uterus';
export type DiagramRow={t:number;center:number[];radii:number[]};
export type DiagramProfile={root:DiagramRoot;sourceIds:string[];right:number[];front:number[];axis:number[];split:number|null;rows:DiagramRow[]};
export type DiagramData={kind:string;sourceSha256:string;units:string;profiles:DiagramProfile[]};
export type DiagramTissue={id:string;root:DiagramRoot;group:string;name:string;color:string;function:string;source:string;range:[number,number]};
const VAGINA_SOURCE='https://histologyguide.com/slideview/MH-173-vagina/18-slide-1.html';
const UTERUS_SOURCE='https://histology.leeds.ac.uk/home/female/uterus/';
const CERVIX_SOURCE='https://histologyguide.com/slideview/MHS-207-cervix/18-slide-1.html';
export const DIAGRAM_TISSUES:DiagramTissue[]=[
 {id:'vaginal-mucosa',root:'vagina',group:'질',name:'점막·주름',color:'#df8e99',function:'비각질 중층편평상피 · 가로 주름 · 신장성',source:VAGINA_SOURCE,range:[0,.27]},
 {id:'vaginal-muscle',root:'vagina',group:'질',name:'근육층',color:'#b95460',function:'평활근 · 벽의 수축·이완',source:VAGINA_SOURCE,range:[.27,.8]},
 {id:'vaginal-adventitia',root:'vagina',group:'질',name:'외막',color:'#e1bc97',function:'결합조직 · 주변 구조와 연결',source:VAGINA_SOURCE,range:[.8,1]},
 {id:'endometrium',root:'uterus',group:'자궁체부',name:'자궁내막',color:'#ee9ca4',function:'착상 부위 · 기능층의 주기적 탈락',source:UTERUS_SOURCE,range:[0,.14]},
 {id:'myometrium',root:'uterus',group:'자궁체부',name:'자궁근층',color:'#b65363',function:'두꺼운 평활근 · 월경·분만 시 수축',source:UTERUS_SOURCE,range:[.14,.92]},
 {id:'perimetrium',root:'uterus',group:'자궁체부',name:'장막·자궁외막',color:'#e6c19c',function:'복막으로 덮인 자궁 표면',source:UTERUS_SOURCE,range:[.92,1]},
 {id:'cervical-mucosa',root:'uterus',group:'자궁경부',name:'경부 점막',color:'#daafa7',function:'경관 내벽 · 점액 분비',source:CERVIX_SOURCE,range:[0,.14]},
 {id:'cervical-stroma',root:'uterus',group:'자궁경부',name:'경부 기질',color:'#ad829e',function:'콜라겐 중심의 결합조직 · 경부 지지',source:CERVIX_SOURCE,range:[.14,1]},
];

export function diagramRoot(id:string|null|undefined):DiagramRoot|null{
 if(id==='vagina'||id?.startsWith('vagina--'))return 'vagina';
 if(id==='uterus'||id?.startsWith('uterus--'))return 'uterus';
 return null;
}
export function activeDiagramRoots(state:ViewerState):DiagramRoot[]{
 const root=diagramRoot(state.selected);
 if(state.mode!=='diagram'||state.sex!=='female'||!root||!state.visible[2]||state.opacity[2]<=0)return [];
 return state.context&&!state.isolate?['vagina','uterus']:[root];
}
export function diagramState(state:ViewerState,root:DiagramRoot):ViewerState{
 return {...state,sex:'female',mode:'diagram',selected:root,diagramTissue:null,context:true,isolate:false,
  visible:state.visible.map((v,i)=>i===2?true:v),opacity:state.opacity.map((v,i)=>i===2?100:v),focus:state.focus+1};
}
export function openingAngle(value:number){return T.MathUtils.degToRad(60+T.MathUtils.clamp(value,0,100)*1.8);}

function envelopeRadius(row:DiagramRow,angle:number){
 const u=((angle/(Math.PI*2)%1)+1)%1*row.radii.length;
 const i=Math.floor(u);return T.MathUtils.lerp(row.radii[i],row.radii[(i+1)%row.radii.length],u-i);
}

/** Inner contours are illustrative, NOT recovered histology or measured luminal geometry. */
export function diagramRadius(profile:DiagramProfile,row:DiagramRow,angle:number,fraction:number,rugae=true){
 const outer=envelopeRadius(row,angle);
 let inner:number;
 if(profile.root==='vagina'){
  // A flattened potential space, opened for teaching. No glands or extra muscularis mucosae.
  inner=Math.max(outer*.42,outer-.0028);
  if(rugae){const fade=Math.sin(Math.PI*row.t)**2;const fold=(.5+.5*Math.cos(row.t*Math.PI*28+.65*Math.sin(angle*3)))**3;
   inner-=Math.min(.00065,inner*.2)*fade*fold;}
 }else{
  const split=profile.split!;const body=T.MathUtils.clamp((row.t-split)/(1-split),0,1);
  // Cervical canal continues into a transversely widening, flattened uterine cavity.
  const rx=row.t<=split?.0018:T.MathUtils.lerp(.0018,.015,Math.min(body/.83,1));
  const rz=row.t<=split?.0013:.0019;
  const ellipse=1/Math.sqrt((Math.sin(angle)/rx)**2+(Math.cos(angle)/rz)**2);
  const fundalClosure=body<.87?1:Math.max(0,(1-body)/.13);
  inner=Math.min(ellipse*fundalClosure,outer*.73);
 }
 return T.MathUtils.lerp(inner,outer,T.MathUtils.clamp(fraction,0,1));
}

export function diagramPoint(profile:DiagramProfile,row:DiagramRow,angle:number,fraction:number,rugae=true){
 const r=diagramRadius(profile,row,angle,fraction,rugae);
 return new T.Vector3().fromArray(row.center)
  .addScaledVector(new T.Vector3().fromArray(profile.right),Math.sin(angle)*r)
  .addScaledVector(new T.Vector3().fromArray(profile.front),Math.cos(angle)*r);
}

/** Closed tissue bands around an EMPTY channel; cut faces only bridge each wall band. */
export function buildDiagramGeometry(profile:DiagramProfile,tissue:DiagramTissue,opening:number,rugae=true,connectedProfile?:DiagramProfile){
 const cervical=tissue.group==='자궁경부';
 const rows=profile.rows.filter(r=>profile.root==='vagina'||(cervical?r.t<=profile.split!+1e-8:r.t>=profile.split!-1e-8));
 const segments=48,half=openingAngle(opening)/2,span=Math.PI*2-half*2;
 const positions:number[]=[],indices:number[]=[];
 const vertex=(row:DiagramRow,angle:number,fraction:number)=>{const r=diagramRadius(profile,row,angle,fraction,rugae),x=Math.sin(angle)*r,z=Math.cos(angle)*r;for(let k=0;k<3;k++)positions.push(row.center[k]+profile.right[k]*x+profile.front[k]*z);return positions.length/3-1;};
 const quad=(a:number,b:number,c:number,d:number,flip=false)=>{if(flip)indices.push(a,c,b,a,d,c);else indices.push(a,b,c,a,c,d);};
 for(let side=0;side<2;side++){
  const start=positions.length/3;
  for(const row of rows)for(let j=0;j<=segments;j++)vertex(row,half+span*j/segments,tissue.range[side]);
  for(let i=0;i<rows.length-1;i++)for(let j=0;j<segments;j++){
   const a=start+i*(segments+1)+j;quad(a,a+1,a+segments+2,a+segments+1,side===0);
  }
 }
 // Separate vertices keep the two cut edges and wall ends crisp.
 for(const j of [0,segments])for(let i=0;i<rows.length-1;i++){
  const a=vertex(rows[i],half+span*j/segments,tissue.range[0]);
  const b=vertex(rows[i],half+span*j/segments,tissue.range[1]);
  const c=vertex(rows[i+1],half+span*j/segments,tissue.range[1]);
  const d=vertex(rows[i+1],half+span*j/segments,tissue.range[0]);quad(a,b,c,d,j===0);
 }
 for(const i of [0,rows.length-1])for(let j=0;j<segments;j++){
  const a=vertex(rows[i],half+span*j/segments,tissue.range[0]);
  const b=vertex(rows[i],half+span*(j+1)/segments,tissue.range[0]);
  const c=vertex(rows[i],half+span*(j+1)/segments,tissue.range[1]);
  const d=vertex(rows[i],half+span*j/segments,tissue.range[1]);quad(a,b,c,d,i===0);
 }
 // Schematic mucosal transition at the native external os. Join the two oblique
 // channel mouths without putting a disk across either lumen. Fornices and the
 // squamocolumnar transition are not histologically reconstructed by this collar.
 if(tissue.id==='vaginal-mucosa'&&connectedProfile){
  const last=rows[rows.length-1],first=connectedProfile.rows[0],bands=6;
  const joined=(j:number,k:number,side:number)=>{
   const angle=half+span*j/segments;
   const a=diagramPoint(profile,last,angle,tissue.range[side],rugae);
   const b=diagramPoint(connectedProfile,first,angle,side===0?0:.14,rugae);
   const point=a.lerp(b,k/bands);positions.push(point.x,point.y,point.z);return positions.length/3-1;
  };
  for(let side=0;side<2;side++){
   const start=positions.length/3;
   for(let k=0;k<=bands;k++)for(let j=0;j<=segments;j++)joined(j,k,side);
   for(let k=0;k<bands;k++)for(let j=0;j<segments;j++){const a=start+k*(segments+1)+j;quad(a,a+1,a+segments+2,a+segments+1,side===0);}
  }
  for(const j of [0,segments])for(let k=0;k<bands;k++)quad(joined(j,k,0),joined(j,k,1),joined(j,k+1,1),joined(j,k+1,0),j===0);
 }
 const geometry=new T.BufferGeometry();geometry.setAttribute('position',new T.Float32BufferAttribute(positions,3));geometry.setIndex(indices);geometry.computeVertexNormals();geometry.computeBoundingBox();geometry.computeBoundingSphere();
 return geometry;
}
