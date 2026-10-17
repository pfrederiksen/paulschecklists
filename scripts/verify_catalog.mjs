import assert from 'node:assert/strict';
import {readFile,access} from 'node:fs/promises';
import vm from 'node:vm';
import {hasCards,hasOdds,categoryLabel,renderCatalogRow,matchesSet,compareSets} from '../catalog-model.mjs';
const catalog=JSON.parse(await readFile('data/set-catalog.json','utf8'));
const unnamed=renderCatalogRow({title:'Unnamed odds source',manufacturer:'Topps',sport:'basketball',year:'2026',page:'test.html',odds:60,formats:1,presentation:{formats:0}});assert(unnamed.includes('60 categories · format not named')&&!unnamed.includes('0 formats'),'Unavailable source formats must not be presented as zero');
assert(renderCatalogRow({title:'Named odds source',manufacturer:'Topps',sport:'basketball',year:'2026',page:'test.html',odds:60,formats:1}).includes('60 categories · 1 format'));
const pages=new Set();let tables=0;
for(const set of catalog.sets){
 assert(!pages.has(set.page),`Duplicate page ${set.page}`);pages.add(set.page);
 assert(new URL(set.checklistUrl).protocol==='https:');
 await access(set.page);await access('docs/'+set.page);
 const html=await readFile('docs/'+set.page,'utf8');
 assert(html.includes('paulfrederiksen.goatcounter.com/count'));assert(html.includes('ads.js?v='));
 if(set.tableData){const data=JSON.parse(await readFile(set.tableData,'utf8'));assert.equal(data.rows.length,set.rowCount);assert(data.headers.length>=3);assert(data.rows.every(row=>row.length===data.headers.length));assert.equal(data.source,set.checklistUrl);tables++;}
}
const directorySets=catalog.sets.filter(s=>!s.ongoingSeries||s.slug==='topps-now-2026');
const elements=new Map();const get=id=>{if(!elements.has(id))elements.set(id,{value:'',textContent:'',options:[{}],add(v){this.options.push(v);},remove(i){this.options.splice(i,1);},addEventListener(event,fn){this[event]=fn;}});return elements.get(id);};
let output='';const document={getElementById:get,querySelectorAll:()=>[{remove(){output='';}}],querySelector:()=>({insertAdjacentHTML(_,s){output+=s;}})};
const context=vm.createContext({document,console,hasCards,hasOdds,categoryLabel,renderCatalogRow,matchesSet,compareSets,Option:function(text,value){return {text,value};},fetch:async()=>({ok:true,json:async()=>structuredClone(catalog)})});
await new vm.Script('(async()=>{'+(await readFile('directory.js','utf8')).replace(/^import .*;\n/,'')+'})()').runInContext(context);
assert.equal(get('catalog-total').textContent,directorySets.length);assert.equal((output.match(/class="catalog-row"/g)||[]).length,40);
get('coverage-filter').value='released';get('coverage-filter').change();assert.equal(get('catalog-count').textContent,`${directorySets.filter(s=>s.releaseStatus==='Released').length} sets`);
// Dated backfills can move older releases beyond the first 40 results.
get('set-search').value='Bowman Football';get('set-search').input();assert(output.includes('bowman-football-2026.html'));
get('set-search').value='2026 Tribute Baseball';get('set-search').input();assert(output.includes('2026-topps-tribute-baseball.html'));
get('catalog-reset').onclick();get('catalog-next').onclick();assert.equal(get('catalog-page').textContent,`Page 2 of ${Math.ceil(directorySets.filter(s=>s.status==='Searchable'||(s.tableData&&s.rosterPublished!==false)).length/40)}`);
get('set-search').value='this-does-not-exist';get('set-search').input();assert.equal(get('catalog-count').textContent,'0 sets');assert(get('catalog-empty').hidden===false);
console.log(`Verified ${catalog.sets.length} unique official-source pages, ${tables} preserved tables, shared tracking/ads, and directory filters/pagination.`);

get('catalog-reset').onclick();assert.equal(get('coverage-filter').value,'searchable');assert.equal(get('sort-filter').value,'released');assert.equal([...output.matchAll(/<h3><a href="([^"]+)"/g)][0][1],directorySets.filter(hasCards).toSorted(compareSets)[0].page);get('coverage-filter').value='full';get('coverage-filter').change();assert.equal(get('catalog-count').textContent,`${directorySets.filter(s=>(s.odds||s.publishedOdds)&&(s.status==='Searchable'||(s.tableData&&s.rosterPublished!==false))).length} sets`);get('coverage-filter').value='source';get('coverage-filter').change();assert.equal(get('catalog-count').textContent,`${directorySets.filter(s=>s.status==='Official source').length} sets`);get('sort-filter').value='name';get('sort-filter').change();console.log('Verified latest-release default and full/table/source availability filters.');
get('show-full').onclick();assert.equal(get('coverage-filter').value,'full');assert.equal(get('complete-total').textContent,directorySets.filter(s=>(s.odds||s.publishedOdds)&&(s.status==='Searchable'||(s.tableData&&s.rosterPublished!==false))).length);
get('coverage-filter').value='upcoming';get('coverage-filter').change();assert.equal(get('catalog-count').textContent,`${directorySets.filter(s=>s.releaseStatus==='Upcoming').length} ${directorySets.filter(s=>s.releaseStatus==='Upcoming').length===1?'set':'sets'}`);assert(output.includes('Upcoming'));
console.log('Verified one-click cards + odds filter, availability counts and upcoming release filter.');

const ongoingInventory=JSON.parse(await readFile('data/topps-now-official-catalog.json','utf8'));
for(const series of ongoingInventory){const published=catalog.sets.find(set=>set.slug===series.slug);assert(published,'Published NOW slug must survive discovery: '+series.slug);assert.equal(published.page,series.page);}
console.log('Verified published NOW series slugs and page URLs remain stable.');

assert(matchesSet({title:'2026 Topps Chrome® Baseball',manufacturer:'Topps / Bowman',sport:'baseball',year:'2026'},'Chrome Baseball'));
assert(matchesSet({title:'2026 Chrome® Baseball',manufacturer:'Topps',sport:'baseball',year:'2026'},'baseball chrome 2026'));
get('catalog-reset').onclick();get('set-search').value='Chrome Baseball';get('set-search').input();assert(output.includes('2026-topps-chrome-baseball.html'));
console.log('Verified punctuation-tolerant and multi-word set search.');

const fixture=[
 {title:'Future set',releaseStatus:'Upcoming',releaseDate:'2026-12-01'},
 {title:'Unknown with product year',year:'2027',releaseStatus:'Unverified',releaseDate:'2026-11-01'},
 {title:'Undated released',releaseStatus:'Released'},
 {title:'Invalid date released',releaseStatus:'Released',releaseDate:'2026-99-99'},
 {title:'Older release',releaseStatus:'Released',releaseDate:'2026-01-20'},
 {title:'B newest release',releaseStatus:'Released',releaseDate:'2026-10-14'},
 {title:'A newest release',releaseStatus:'Released',releaseDate:'2026-10-14'}
];
assert.deepEqual(fixture.toSorted(compareSets).map(s=>s.title),['A newest release','B newest release','Older release','Invalid date released','Undated released','Unknown with product year','Future set']);
assert(renderCatalogRow({...fixture[5],manufacturer:'Topps',sport:'baseball',page:'test.html'}).includes('Released · 2026-10-14'));
get('catalog-reset').onclick();
const expected=directorySets.filter(hasCards).toSorted(compareSets);
assert.deepEqual([...output.matchAll(/<h3><a href="([^"]+)"/g)].map(m=>m[1]),expected.slice(0,40).map(s=>s.page));
get('catalog-next').onclick();assert.deepEqual([...output.matchAll(/<h3><a href="([^"]+)"/g)].map(m=>m[1]),expected.slice(40,80).map(s=>s.page));
get('sort-filter').value='data';get('sort-filter').change();assert(output.indexOf('allen-ginter-2026.html')<output.indexOf('upper-deck-'));
get('catalog-reset').onclick();assert.equal(get('sort-filter').value,'released');
const built=await readFile('docs/index.html','utf8');
assert(built.includes('<option value="released" selected>Latest releases</option>'));
assert.deepEqual([...built.matchAll(/<h3><a href="([^"]+)"/g)].map(m=>m[1]),expected.slice(0,40).map(s=>s.page));
console.log('Verified descending verified release dates, stable ties, undated/upcoming placement, reset, pagination and matching static directory order.');
