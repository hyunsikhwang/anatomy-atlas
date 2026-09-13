"use client";
import {ArrowUpRight,Focus,RotateCcw} from 'lucide-react';
import {Slider} from '@/components/ui/slider';
import {Switch} from '@/components/ui/switch';
import {DIAGRAM_TISSUES,activeDiagramRoots,diagramRoot,type DiagramRoot} from './anatomy-diagram';
import type {ViewerState} from './anatomy-types';

type Props={state:ViewerState;patch:(v:Partial<ViewerState>)=>void;onRoot:(root:DiagramRoot)=>void;onTissue:(id:string)=>void};
export function DiagramControls({state,patch,onRoot}:Omit<Props,'onTissue'>){
 return <div className="diagram-controls">
  <span className="diagram-scope">여성 생식기관</span>
  <div className="diagram-organ-tabs" role="group" aria-label="도해 기관">
   {(['vagina','uterus'] as const).map((root,i)=><button key={root} aria-pressed={diagramRoot(state.selected)===root} onClick={()=>onRoot(root)}>{['질','자궁·경부'][i]}</button>)}
  </div>
  <div className="range-caption"><span>절개 폭</span><b>{state.diagramOpening}%</b></div>
  <Slider aria-label="도해 절개 폭" value={[state.diagramOpening]} min={0} max={100} step={1} onValueChange={v=>patch({diagramOpening:v[0]})}/>
  <div className="setting-row"><span>질 주름</span><Switch checked={state.diagramRugae} onCheckedChange={v=>patch({diagramRugae:v})} aria-label="도해 질 점막 주름"/></div>
  <div className="setting-row"><span>원본 외곽</span><Switch checked={state.diagramOutline} onCheckedChange={v=>patch({diagramOutline:v})} aria-label="원본 외곽 겹쳐 보기"/></div>
  <div className="diagram-note">교육용 개략도<br/>내강·층 두께 확대</div>
  <button className="diagram-return" onClick={()=>patch({mode:'whole',diagramTissue:null,focus:state.focus+1})}><RotateCcw size={14}/>원본 보기</button>
 </div>;
}

export function DiagramDetails({state,patch,onRoot,onTissue}:Props){
 const roots=activeDiagramRoots(state),tissues=DIAGRAM_TISSUES.filter(t=>roots.includes(t.root));
 const selected=tissues.find(t=>t.id===state.diagramTissue);
 const groups=[...new Set(tissues.map(t=>t.group))];
 return <section className="diagram-details" aria-label="도해 조직층">
  <div className="diagram-detail-heading"><h3>내부 구조</h3><span>도해</span></div>
  <p className="diagram-path">질 내강 · 경관 · 자궁강</p>
  {groups.map(group=><div className="tissue-group" key={group}><h4>{group}</h4>{tissues.filter(t=>t.group===group).map(t=><div className="tissue-row" key={t.id}>
   <button className={selected?.id===t.id?'active':''} aria-pressed={selected?.id===t.id} onClick={()=>onTissue(t.id)}><span style={{background:t.color}}/>{t.name}</button>
   <Switch checked={!state.diagramHidden.includes(t.id)} aria-label={`${group} ${t.name} 표시`} onCheckedChange={v=>patch({diagramHidden:v?state.diagramHidden.filter(id=>id!==t.id):[...state.diagramHidden,t.id],diagramTissue:!v&&state.diagramTissue===t.id?null:state.diagramTissue})}/>
  </div>)}</div>)}
  {selected&&<div className="tissue-description" aria-live="polite"><strong>{selected.group} · {selected.name}</strong><p>{selected.function}</p><a href={selected.source} target="_blank" rel="noreferrer">조직학 근거 <ArrowUpRight size={12}/></a></div>}
  {tissues.length>0&&tissues.every(t=>state.diagramHidden.includes(t.id))&&<button className="diagram-return" onClick={()=>patch({diagramHidden:[]})}>조직층 모두 표시</button>}
  <button className="diagram-return" onClick={()=>onRoot(diagramRoot(state.selected)??'vagina')}><Focus size={14}/>도해 전체</button>
 </section>;
}
