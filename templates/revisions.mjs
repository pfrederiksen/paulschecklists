import {createHash} from 'node:crypto';
export function recordRevision(previous,state,source,at){
 const fingerprint=createHash('sha256').update(JSON.stringify(state)).digest('hex');
 if(previous?.fingerprint===fingerprint)return previous;
 // Corrected parsing can change row counts without revising a manufacturer
 // document. Update the current snapshot without inventing a source revision.
 if(previous&&['checklistHash','oddsHash','specificationHash'].every(key=>(previous.state[key]??null)===(state[key]??null)))return {...previous,state,fingerprint};
 const labels={rows:'Checklist entries',odds:'Published odds entries',specificationRows:'Numbering specification rows'};
 const changes=previous?Object.keys(state).filter(k=>state[k]!==previous.state[k]).map(k=>labels[k]?`${labels[k]}: ${previous.state[k]??0} → ${state[k]??0}`:k==='specificationHash'?'Official supplementary numbering specification changed.':k==='checklistHash'?'Official checklist or supplementary specification source changed.':'Official odds document changed.'):['Initial recorded snapshot; earlier revisions are not reconstructed.'];
 return {state,fingerprint,events:[{at,changes,source,snapshot:state,previousSnapshot:previous?.state??null},...(previous?.events??[])]};
}
