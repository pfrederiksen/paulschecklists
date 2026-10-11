import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import vm from 'node:vm';
const catalog=JSON.parse(await readFile('data/set-catalog.json','utf8'));
const code=await readFile('source-page.js','utf8');
for(const kind of ['pdf','html','wildcard','xlsx']){
 const set=catalog.sets.find(s=>s.importKind===kind&&s.tableData&&s.rosterPublished!==false&&(kind!=='pdf'||s.odds));
 const data=JSON.parse(await readFile(set.tableData,'utf8'));
 const map=new Map(),get=id=>{if(!map.has(id))map.set(id,{value:'',options:[{}],setAttribute(k,v){this[k]=v;},focus(){},add(option){this.options.push(option);}});return map.get(id);};
 const context=vm.createContext({document:{body:{dataset:{table:set.tableData}},getElementById:get,addEventListener(){}},console,Option:function(text,value){return {text,value};},fetch:async()=>({ok:true,json:async()=>data})});
 await new vm.Script('(async()=>{'+code+'})()').runInContext(context);
 assert(get('source-results').innerHTML.includes('<table>'));
 assert(get('source-results').innerHTML.includes('PLAYER / SUBJECT'));assert(get('source-results').innerHTML.includes('View family details'));
 get('source-results').onclick({target:{closest:()=>({dataset:{row:'0'}})}});assert(get('source-results').innerHTML.includes('OFFICIAL '+data.headers[0]));assert(get('source-results').innerHTML.includes('Hide family details'));
 get('source-sort').value='name';get('source-sort').onchange();assert(get('source-results').innerHTML.includes('<table>'));
 get('source-reset').onclick();assert.equal(get('source-sort').value,'checklist');assert.equal(get('source-section').value,'');
 assert(get('insights').innerHTML.includes('insight-grid'));
 get('source-odds-tab').onclick();assert.equal(get('source-cards-panel').hidden,true);assert.equal(get('source-specifications').hidden,false);get('source-cards-tab').onclick();assert.equal(get('source-specifications').hidden,true);
 assert(get('source-specifications').innerHTML.includes('odds-group'));
 get('source-search').value='no-matching-source-row-ever';get('source-search').oninput();assert(get('source-results').innerHTML.includes('No matching'));
 get('source-search').value='';get('source-section').value=data.rows[0][data.sectionColumn??0];get('source-section').onchange();assert.equal(get('source-count').textContent,`${data.rows.filter(r=>r[data.sectionColumn??0]===data.rows[0][data.sectionColumn??0]).length.toLocaleString()} official source rows`);
 if(data.odds?.length){assert(get('source-transcript').innerHTML.includes('Odds document text'));const second=data.formats[1];if(second){get('source-format').value=second;get('source-format').onchange();assert(get('source-specifications').innerHTML.includes(second.replaceAll('&','&amp;')));}}
}
for(const set of catalog.sets.filter(s=>s.oddsUrl)){
 const data=JSON.parse(await readFile(set.tableData,'utf8'));
 assert.equal(data.odds.length,set.odds);assert.equal(data.formats.length,set.formats);
 assert.equal(data.oddsIssues.length,0,`Unresolved odds alignment: ${set.title}`);
 assert(data.odds.every(o=>o.name&&o.page&&Object.keys(o.values).every(f=>data.formats.includes(f))));
}
const football=catalog.sets.find(s=>s.title==='2025 Topps Chrome® Football');const d=JSON.parse(await readFile(football.tableData,'utf8'));const base=d.odds.find(o=>o.name==='BASE REFRACTOR');const hobby=d.formats.find(f=>f.includes('6390'));assert.equal(base.values[hobby],'1:4');assert.equal(d.formats.length,14);
const finest=catalog.sets.find(s=>s.title==='2025-26 Topps Finest Basketball');const f=JSON.parse(await readFile(finest.tableData,'utf8'));assert.deepEqual(f.formats,['Hobby','Breaker']);assert.equal(f.odds.find(o=>o.name==='Base Common').values.Hobby,'5:1');assert.equal(f.odds.find(o=>o.name==='Base Common').values.Breaker,null);
console.log('Verified PDF/HTML/Wild Card search, group filters, specifications, format selection, published odds alignment and cards-per-pack ratios.');
