import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {explorer,setFacts,setStats} from '../templates/set-page.mjs';
const catalog=JSON.parse(await readFile('data/set-catalog.json','utf8'));
const controls=['SUBSET','TEAM','PACK FORMAT','Rookies only','Reset filters','Checklist order','Name A–Z','Rarest published odds','Export CSV','Parallels & pack odds'];
for(const set of catalog.sets){
 const html=await readFile(set.page,'utf8');
 assert(html.includes('data-template="allen-ginter-v1"'),set.page);
 for(const label of ['Release and data availability','On this checklist','PARALLELS & NUMBERING','PACK ODDS'])assert(html.includes(label),`${set.page}: missing shared overview ${label}`);
 if(set.releaseStatus==='Upcoming')assert(html.includes('Upcoming')&&!html.includes('Release date has not been verified.'),`${set.page}: upcoming release must not be described as unverified`);
 for(const label of ['CHECKLIST ENTRIES','CHECKLIST SECTIONS','PACK ODDS','PACK FORMATS'])assert(html.includes(label),`${set.page}: missing common statistic ${label}`);
 assert(html.indexOf('id="explore"')<html.indexOf('id="insights"'),`${set.page}: cards must precede secondary highlights`);
 assert(html.indexOf('id="explore"')<html.indexOf('id="set-breakdown"'),`${set.page}: checklist must precede the optional chart`);
 assert(html.includes('class="reference-details composition-details"'),`${set.page}: breakdown must be a shared disclosure`);
 if(!set.tableData&&set.status!=='Searchable')assert(html.includes('<input disabled id='),`${set.page}: pending data controls must be disabled`);
 for(const shared of ['brand-icon','THE COLLECTOR’S REFERENCE','class="hero"','class="stats"','INSIDE THE SET','id="insights"','id="sources"','Official data.<br>Clear expectations.'])assert(html.includes(shared),`${set.page}: ${shared}`);
 for(const control of controls)assert(html.includes(control),`${set.page}: ${control}`);
}
const featured=explorer({odds:97});const imported=explorer({imported:true,odds:97});
for(const token of ['class="search-wrap"','class="filters"','class="results-top"','class="notice"','class="pagination"'])assert.equal(featured.split(token).length,imported.split(token).length);
console.log(`Verified ${catalog.sets.length} sets use the Allen & Ginter template and common explorer controls.`);

// Counts use the same source semantics in set summaries and the directory.
const deployed=JSON.parse(await readFile('docs/data/set-catalog.json','utf8'));
for(const set of catalog.sets){
 const path=set.tableData||(set.status==='Searchable'?`data/${set.page.replace('.html','.json')}`:null);
 const data=path?JSON.parse(await readFile(path,'utf8')):null;
 const facts=setFacts(set,data);
 assert.deepEqual(deployed.sets.find(s=>s.slug===set.slug).presentation,facts,`${set.slug}: directory and summary facts must match`);
 if(!data)assert.equal(facts.rows,null,`${set.slug}: pending import is not zero rows`);
 if(set.ongoingSeries)assert(!facts.hasOdds,`${set.slug}: made-to-order runs are not pack odds`);
}
const ag=JSON.parse(await readFile('data/allen-ginter-2026.json','utf8'));
assert.equal(setFacts(catalog.sets.find(s=>s.page==='allen-ginter-2026.html'),ag).rows,2915);
assert(setStats({},ag).includes('grouped entries'));
const nbl=JSON.parse(await readFile('data/imports/topps-bowman-2025-26-topps-nbl-basketball.json','utf8'));
assert.equal(setFacts({},nbl).specifications,false,'Box configuration and store dates must not announce parallel limits');
assert.equal(setFacts({},ag).specifications,true,'Published family numbering must remain available');
assert.equal(setFacts({},{publishedSpecifications:[{headers:['Published parallel'],rows:[['Rainbow foil — card-specific terms']]}]}).specifications,true,'Card-specific parallel terms remain available');
assert((await readFile('sets/topps-bowman-2025-26-topps-nbl-basketball.html','utf8')).includes('Parallel names; limits pending'));
console.log('Verified consistent source counts, pending imports and made-to-order semantics across set summaries and directory rows.');
