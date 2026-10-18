import {displayQualification} from '../parallel-specs.mjs';
import assert from 'node:assert/strict';import {readFile} from 'node:fs/promises';import vm from 'node:vm';
const catalog=JSON.parse(await readFile('data/set-catalog.json','utf8'));const history=JSON.parse(await readFile('data/revision-history.json','utf8'));const index=JSON.parse(await readFile('data/player-index.json','utf8'));
assert(index.some(s=>s.names.some(n=>n.includes('Aaron Judge'))));assert(!index.some(s=>s.names.includes('Not published')));
for(const set of catalog.sets){const d=JSON.parse(await readFile(`data/research/${set.slug}.json`,'utf8'));assert.equal(d.title,set.title);assert.deepEqual(d.history,history[set.slug].events);assert(d.entries.every(e=>e.family&&e.name&&typeof e.values==='object'));const html=await readFile(set.page,'utf8');assert(html.includes('set-research')&&html.includes('Official source revision history'));}
for(const set of catalog.sets.filter(s=>s.tableData)){
 const source=JSON.parse(await readFile(set.tableData,'utf8'));
 const output=JSON.parse(await readFile(`data/research/${set.slug}.json`,'utf8'));
 assert.equal(history[set.slug].state.rows,source.rows.length,`Research must preserve imported row counts: ${set.title}`);
 assert.equal(history[set.slug].state.checklistHash,source.checklistFingerprint??source.sha256??null,`A read failure must not become a removed-source revision: ${set.title}`);
 if(source.odds?.length)assert(output.entries.length>=source.odds.length,`Imported odds must remain available in research: ${set.title}`);
}
const data=JSON.parse(await readFile('data/research/panini-2026-panini-national-silver-packs.json','utf8'));assert.equal(data.specs.reduce((n,s)=>n+s.rows.length,0),16);assert.equal(data.entries.filter(e=>!e.specificationOnly).length,0);assert(data.entries.every(e=>e.numbering));
const a=JSON.parse(await readFile('data/research/'+catalog.sets.find(s=>s.page==='allen-ginter-2026.html').slug+'.json','utf8'));assert.equal(a.formats.length,3);assert.equal(a.entries.length,97);
const elements=new Map();const element=id=>{if(!elements.has(id))elements.set(id,{value:'',dataset:{research:'test'},innerHTML:'',textContent:'',addEventListener:(event,fn)=>{element(id)[event]=fn;}});return elements.get(id);};const context=vm.createContext({displayQualification,document:{getElementById:id=>element(id)},fetch:async()=>({ok:true,json:async()=>a}),console});await new vm.Script('(async()=>{'+(await readFile('research.js','utf8')).replace(/^import .*;\n/,'')+'})()').runInContext(context);await new Promise(r=>setTimeout(r,0));assert(element('format-comparison').innerHTML.includes('hobby'));element('research-family').value='BASE CARDS';element('research-family').onchange();assert(!element('format-comparison').innerHTML.includes('DYNASTY'));element('global-player-search').value='Aaron Judge';context.fetch=async()=>({ok:true,json:async()=>index});await element('global-player-search').input();assert(element('global-player-results').innerHTML.includes('Aaron Judge'));element('global-player-search').value="Nico O'Reilly";await element('global-player-search').input();assert(element('global-player-results').innerHTML.includes('topps-bowman-2026-premier-league-topps-now-team-of-the-season-set.html'));assert(element('global-player-results').innerHTML.includes('Nico O’Reilly'));
console.log('Verified shared research views, published odds, numbering, history and global name search.');

const {recordRevision}=await import('../templates/revisions.mjs');const snapshot={checklistHash:'a',oddsHash:'b',rows:10,odds:2,specificationRows:3};const first=recordRevision(null,snapshot,'https://example.com/official.pdf','2026-10-11T00:00:00Z');assert.equal(recordRevision(first,snapshot,'https://example.com/official.pdf','later'),first);const changed=recordRevision(first,{...snapshot,checklistHash:'c',rows:11},'https://example.com/official.pdf','2026-10-12T00:00:00Z');assert.equal(changed.events.length,2);assert(changed.events[0].changes.includes('Checklist entries: 10 → 11'));assert.equal(changed.events[0].previousSnapshot.checklistHash,'a');console.log('Verified revision changes are recorded once and retain source snapshots.');
const corrected=recordRevision(first,{...snapshot,rows:11},'https://example.com/official.pdf','later');assert.equal(corrected.state.rows,11);assert.deepEqual(corrected.events,first.events,'Parser corrections with unchanged source hashes must not claim a manufacturer revision');assert.equal(recordRevision(corrected,{...snapshot,rows:11},'https://example.com/official.pdf','later again'),corrected);
const supplemented=recordRevision(first,{...snapshot,rows:11,specificationRows:4,specificationHash:'new-guide'},'https://example.com/official.pdf','later');assert.equal(supplemented.state.rows,11);assert(!supplemented.events[0].changes.some(c=>c.startsWith('Checklist entries:')),'New guide evidence must not turn an unrelated parser correction into a checklist revision');assert(supplemented.events[0].changes.includes('Supplementary specification evidence imported.'));

const absentOdds=recordRevision(null,{...snapshot,oddsHash:null,odds:0},'https://example.com/checklist.pdf','first');const importedOdds=recordRevision(absentOdds,{...snapshot,rows:9,oddsHash:'new-pdf'},'https://example.com/checklist.pdf','later');assert(importedOdds.events[0].changes.includes('Official odds document imported.'));assert(!importedOdds.events[0].changes.some(c=>c.startsWith('Checklist entries:')));

const sapphire=JSON.parse(await readFile('data/research/topps-bowman-2026-topps-chrome-marvel-comics-sapphire-edition.json','utf8'));
context.fetch=async()=>({ok:true,json:async()=>sapphire});
await new vm.Script('(async()=>{'+(await readFile('research.js','utf8')).replace(/^import .*;\n/,'')+'})()').runInContext(context);await new Promise(r=>setTimeout(r,0));
assert(element('research-family').innerHTML.includes('CHARACTERS II'));
element('research-family').value='CHARACTERS II';element('research-family').onchange();
assert.equal((element('format-comparison').innerHTML.match(/<tbody>(.*?)<\/tbody>/s)[1].match(/<tr>/g)||[]).length,8);
assert(element('format-comparison').innerHTML.includes('Base - Characters Green Sapphire')&&element('format-comparison').innerHTML.includes('1:6'));
assert(!element('format-comparison').innerHTML.includes('Marvel Facsimile'));
for(const set of catalog.sets.filter(s=>s.tableData)){
 const source=JSON.parse(await readFile(set.tableData,'utf8')),output=JSON.parse(await readFile(`data/research/${set.slug}.json`,'utf8'));
 for(const odd of source.odds??[])if(odd.familyAliases?.length)assert(output.entries.some(e=>e.name===odd.name&&JSON.stringify(e.familyAliases)===JSON.stringify(odd.familyAliases)),`Exact family aliases retained in research: ${set.title}`);
}
console.log('Verified exact shared-family aliases in research comparisons, including both Marvel Sapphire base sections.');
