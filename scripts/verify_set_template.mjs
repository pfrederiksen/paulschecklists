import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {explorer} from '../templates/set-page.mjs';
const catalog=JSON.parse(await readFile('data/set-catalog.json','utf8'));
const controls=['SUBSET','TEAM','PACK FORMAT','Rookies only','Reset filters','Checklist order','Name A–Z','Rarest published odds','Export CSV','Parallels & pack odds'];
for(const set of catalog.sets){
 const html=await readFile(set.page,'utf8');
 assert(html.includes('data-template="allen-ginter-v1"'),set.page);
 for(const label of ['Release and data availability','On this checklist','PARALLELS & NUMBERING','PACK ODDS'])assert(html.includes(label),`${set.page}: missing shared overview ${label}`);
 if(set.releaseStatus==='Upcoming')assert(html.includes('Upcoming')&&!html.includes('Release date has not been verified.'),`${set.page}: upcoming release must not be described as unverified`);
 for(const shared of ['brand-icon','THE COLLECTOR’S REFERENCE','class="hero"','class="stats"','INSIDE THE SET','id="insights"','id="sources"','Official data.<br>Clear expectations.'])assert(html.includes(shared),`${set.page}: ${shared}`);
 if(set.tableData||set.status==='Searchable')for(const control of controls)assert(html.includes(control),`${set.page}: ${control}`);
}
const featured=explorer({odds:97});const imported=explorer({imported:true,odds:97});
for(const token of ['class="search-wrap"','class="filters"','class="results-top"','class="notice"','class="pagination"'])assert.equal(featured.split(token).length,imported.split(token).length);
console.log(`Verified ${catalog.sets.length} sets use the Allen & Ginter template and common explorer controls.`);
