import {createHash} from 'node:crypto';
import {reconcileParallels,categoryNumbering,specificationRows} from '../parallel-specs.mjs';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {recordRevision} from '../templates/revisions.mjs';
const catalog=JSON.parse(await readFile('data/set-catalog.json','utf8'));
let history={};try{history=JSON.parse(await readFile('data/revision-history.json','utf8'));}catch{}
export const research=new Map();const index=[];
await mkdir('data/research',{recursive:true});
for(const set of catalog.sets){
 let data=null;try{data=JSON.parse(await readFile(set.tableData||`data/${set.page.replace('.html','.json')}`,'utf8'));}catch(error){if(set.tableData||set.status==='Searchable')throw error;}
 if(data&&!data.sections)data.odds=reconcileParallels(data);
 const featured=!!data?.sections;const sections=featured?data.sections:[];let formats=data?.formats??[];let entries=[];
 if(featured){formats=[...new Set(data.odds.flatMap(o=>Object.keys(o.odds)))];entries=data.odds.map(o=>({family:sections.find(s=>s.oddsIds?.includes(data.odds.indexOf(o)))?.name??'Other published categories',name:o.name,values:Object.fromEntries(formats.map(f=>[f,o.odds[f]?`1:${o.odds[f]}`:'Not listed']))}));}
 else entries=(data?.odds??[]).map(o=>({family:o.family??(data?.rows??[]).map(r=>r[0]).filter(n=>o.name.toLowerCase().startsWith(String(n).toLowerCase())).sort((a,b)=>b.length-a.length)[0]??'Other published categories',name:o.name,specificationOnly:!!o.specificationOnly,qualification:[o.numberingSource?.qualification,o.qualification].filter(Boolean).join('; '),numberingSource:o.numberingSource?.url??'',values:o.values}));
 const specs=(data?.publishedSpecifications??[]).map(s=>({...s,rows:specificationRows(s)}));
 for(const family of new Set((data?.parallelSpecifications??[]).map(s=>s.family)))specs.push({name:family,headers:['Parallel / variation','Published numbering','Manufacturer qualification','Official source'],rows:data.parallelSpecifications.filter(s=>s.family===family).map(s=>[s.name,s.numbering,s.qualification??'',s.source])});
 if(data?.oddsColumn!=null){formats=['Official published odds'];entries=[...new Map(data.rows.map(row=>[JSON.stringify([row[0],row[data.oddsColumn]]),{family:row[0],name:row[0],values:{'Official published odds':row[data.oddsColumn]||'Not published'}}])).values()];}
 if(data?.serialColumn!=null){specs.push({name:'Official card numbering',headers:[data.headers[0],data.headers[1],data.headers[data.serialColumn]],rows:data.rows.filter(r=>r[data.serialColumn]).map(r=>[r[0],r[1],r[data.serialColumn]])});}
 for(const subset of data?.officialStructure?.subsets??[])for(const group of subset.groups??[])specs.push({name:subset.name,headers:['Board','Parallel','Unsigned numbering','Autograph numbering'],rows:(group.rows??[]).map(r=>[group.board,r.p??'',r.base??'Not published',r.au??'Not published'])});
 entries=entries.map(e=>({...e,numbering:categoryNumbering(data??{},e.name),family:e.family||'Unlabeled source section',name:e.name||'Unlabeled published category'}));
 const rows=featured?sections.flatMap(s=>s.cards.flatMap(c=>c.subjects.map(p=>[p.name,c.number,s.name]))):data?.rows??[];
 let ni=featured?0:(data?.headers??[]).findIndex(h=>/name|player|subject|description|decription/i.test(h));if(ni<0)ni=1;
 const names=[...new Set(rows.map(r=>String(r[ni]??'')).filter(Boolean))];if(names.length&&set.rosterPublished!==false)index.push({title:set.title,page:set.page,sport:set.sport,names});
 const state={checklistHash:data?.checklistFingerprint??data?.sha256??null,oddsHash:data?.oddsSha256??null,rows:featured?sections.reduce((n,s)=>n+s.cards.length,0):data?.rows?.length??0,odds:entries.filter(e=>!e.specificationOnly).length,specificationRows:specs.reduce((n,s)=>n+s.rows.length,0)};
 if(data?.parallelSpecifications?.length)state.specificationHash=createHash('sha256').update(JSON.stringify(data.parallelSpecifications)).digest('hex');
 history[set.slug]=recordRevision(history[set.slug],state,set.checklistUrl,new Date().toISOString());
 const value={title:set.title,formats,entries,specs,history:history[set.slug].events};research.set(set.slug,value);await writeFile(`data/research/${set.slug}.json`,JSON.stringify(value));
}
await writeFile('data/player-index.json',JSON.stringify(index));await writeFile('data/revision-history.json',JSON.stringify(history,null,2)+'\n');
console.log(`Built research views and global name index for ${index.length} sets.`);
