import assert from 'node:assert/strict';
import {readFile,access} from 'node:fs/promises';
import vm from 'node:vm';
const catalog=JSON.parse(await readFile('data/set-catalog.json','utf8'));
const pages=new Set();let tables=0;
for(const set of catalog.sets){
 assert(!pages.has(set.page),`Duplicate page ${set.page}`);pages.add(set.page);
 assert(new URL(set.checklistUrl).protocol==='https:');
 await access(set.page);await access('docs/'+set.page);
 const html=await readFile('docs/'+set.page,'utf8');
 assert(html.includes('paulfrederiksen.goatcounter.com/count'));assert(html.includes('ads.js?v='));
 if(set.tableData){const data=JSON.parse(await readFile(set.tableData,'utf8'));assert.equal(data.rows.length,set.rowCount);assert(data.headers.length>=3);assert(data.rows.every(row=>row.length===data.headers.length));assert.equal(data.source,set.checklistUrl);tables++;}
}
const elements=new Map();const get=id=>{if(!elements.has(id))elements.set(id,{value:'',textContent:'',options:[{}],add(v){this.options.push(v);},remove(i){this.options.splice(i,1);},addEventListener(event,fn){this[event]=fn;}});return elements.get(id);};
let output='';const document={getElementById:get,querySelectorAll:()=>[{remove(){output='';}}],querySelector:()=>({insertAdjacentHTML(_,s){output+=s;}})};
const context=vm.createContext({document,console,Option:function(text,value){return {text,value};},fetch:async()=>({ok:true,json:async()=>structuredClone(catalog)})});
await new vm.Script('(async()=>{'+await readFile('directory.js','utf8')+'})()').runInContext(context);
assert.equal(get('catalog-total').textContent,catalog.sets.length);assert.equal((output.match(/class="catalog-row"/g)||[]).length,40);
get('coverage-filter').value='released';get('coverage-filter').change();assert.equal(get('catalog-count').textContent,'2 sets');assert(output.includes('bowman-football-2026.html'));assert(output.includes('allen-ginter-2026.html'));
get('catalog-reset').onclick();get('catalog-next').onclick();assert.equal(get('catalog-page').textContent,'Page 2 of 5');
get('set-search').value='this-does-not-exist';get('set-search').input();assert.equal(get('catalog-count').textContent,'0 sets');assert(get('catalog-empty').hidden===false);
console.log(`Verified ${catalog.sets.length} unique official-source pages, ${tables} preserved tables, shared tracking/ads, and directory filters/pagination.`);
