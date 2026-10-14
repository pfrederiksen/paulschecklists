import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import vm from 'node:vm';
import {reconcileParallels,categoryNumbering,specificationRows} from '../parallel-specs.mjs';
const catalog=JSON.parse(await readFile('data/set-catalog.json','utf8'));
const code=(await readFile('source-page.js','utf8')).replace(/^import .*;\n/, '');
const cases=['pdf','html','wildcard','xlsx','panini-pdf'].map(kind=>catalog.sets.find(s=>s.importKind===kind&&s.tableData&&s.rosterPublished!==false&&(kind!=='pdf'||s.odds))).concat(catalog.sets.filter(s=>s.importKind==='topps-grid-pdf'||s.dedicatedParser||['wild-card-2026-wild-card-alumination-just-the-hits-baseball-250th','wild-card-2026-wild-card-slimgem-variety-pack'].includes(s.slug)));
for(const set of catalog.sets.filter(s=>s.oddsParser))if(!cases.some(c=>c.slug===set.slug))cases.push(set);
for(const set of cases){
 const kind=set.importKind;
 const data=JSON.parse(await readFile(set.tableData,'utf8'));
 if(set.slug==='wild-card-2026-wild-card-slimgem-variety-pack'){
  assert.deepEqual(data.rows,Object.entries(data.officialStructure.rosters).flatMap(([key,names])=>names.map(name=>[key,name,''])));
  assert.equal(data.rows.length,95);assert.notEqual(set.rosterPublished,false);
 }
 const map=new Map(),get=id=>{if(!map.has(id))map.set(id,{value:'',options:[{}],setAttribute(k,v){this[k]=v;},focus(){},add(option){this.options.push(option);}});return map.get(id);};
 const context=vm.createContext({reconcileParallels,categoryNumbering,specificationRows,document:{body:{dataset:{table:set.tableData}},getElementById:get,addEventListener(){}},console,Option:function(text,value){return {text,value};},fetch:async()=>({ok:true,json:async()=>JSON.parse(JSON.stringify(data))})});
 await new vm.Script('(async()=>{'+code+'})()').runInContext(context);
 if(!data.rows.length){assert(get('source-results').innerHTML.includes('No matching'));assert.equal(set.rosterPublished,false);continue;}
 assert(get('source-results').innerHTML.includes('<table>'));
 if(kind==='topps-now'){assert(get('source-results').innerHTML.includes('PRINT RUN'));const printed=data.rows.find(r=>r[3]);if(printed){get('source-section').value=printed[0];get('source-section').onchange();get('source-search').value=printed[2];get('source-search').oninput();assert(get('source-results').innerHTML.includes(printed[3]),'Published print run must remain searchable and visible');get('source-reset').onclick();}assert.equal(get('source-team').disabled,true);assert.equal(get('source-rookie').disabled,true);assert.equal(data.oddsColumn,undefined);assert.equal(set.coverageComplete,false);}
 if(kind==='topps-grid-pdf'||(set.dedicatedParser&&data.headers.includes('Name')&&data.headers.includes('Rookie'))){assert(get('source-results').innerHTML.includes(data.rows[0][data.headers.indexOf('Name')].replaceAll('&','&amp;').replaceAll("'",'&#39;')));assert.equal(get('source-team').disabled,!data.headers.some(h=>/^team$/i.test(h)));assert.equal(get('source-rookie').disabled,false);get('source-rookie').checked=true;get('source-rookie').onchange();assert.equal(get('source-count').textContent,`${data.rows.filter(r=>r[data.headers.indexOf('Rookie')]==='Rookie').length.toLocaleString()} official source rows`);get('source-reset').onclick();}
 assert(get('source-results').innerHTML.includes('PLAYER / SUBJECT'));assert(get('source-results').innerHTML.includes('View family details'));
 get('source-results').onclick({target:{closest:()=>({dataset:{row:'0'}})}});assert(get('source-results').innerHTML.includes('OFFICIAL '+data.headers[0]));assert(get('source-results').innerHTML.includes('Hide family details'));
 get('source-sort').value='name';get('source-sort').onchange();assert(get('source-results').innerHTML.includes('<table>'));
 get('source-reset').onclick();assert.equal(get('source-sort').value,'checklist');assert.equal(get('source-section').value,'');
 assert(get('insights').innerHTML.includes('insight-grid'));
 get('source-odds-tab').onclick();assert.equal(get('source-cards-panel').hidden,true);assert.equal(get('source-specifications').hidden,false);get('source-cards-tab').onclick();assert.equal(get('source-specifications').hidden,true);
 if(set.slug==='topps-bowman-2026-topps-chrome-ufc'){
  get('source-cards-tab').onclick();get('source-section').value='BASE CARDS II';get('source-section').onchange();
  get('source-results').onclick({target:{closest:()=>({dataset:{row:'100'}})}});
  assert(get('source-results').innerHTML.includes('/399'),'The second printed base section must retain the shared base parallel limits');
  get('source-odds-tab').onclick();assert(get('source-specifications').innerHTML.includes('/399'));get('source-reset').onclick();get('source-cards-tab').onclick();
 }
 if(set.slug==='topps-bowman-2026-topps-chrome-baseball-team-samurai-japan-collection'){
  assert.equal(get('source-team').disabled,false);assert.equal(get('source-rookie').disabled,true);
  get('source-section').value='Base Card Short Prints';get('source-section').onchange();assert.equal(get('source-count').textContent,'6 official source rows');
  get('source-search').value='75SP';get('source-search').oninput();assert(get('source-results').innerHTML.includes('Shohei Ohtani'));assert(get('source-results').innerHTML.includes('1 in 15 packs'));
  const row=data.rows.findIndex(r=>r[1]==='75SP');get('source-results').onclick({target:{closest:()=>({dataset:{row:String(row)}})}});
  assert(get('source-results').innerHTML.includes('OFFICIAL Published position'));assert(get('source-results').innerHTML.includes('P/DH'));
  assert(get('source-results').innerHTML.includes('BASE CARDS SHORTPRINTS DARK GOLD PARALLEL'));assert(!get('source-results').innerHTML.includes('BASE CARDS GREEN PARALLEL'),'SP details must not receive ordinary base parallels');
  get('source-reset').onclick();get('source-odds-tab').onclick();assert(get('source-specifications').innerHTML.includes('Odds (Per Pack)'));get('source-cards-tab').onclick();
 }
 if(set.slug==='topps-bowman-2026-topps-dynamic-duals-baseball'){
  assert.equal(get('source-team').disabled,false);assert.equal(get('source-rookie').disabled,true);
  get('source-team').value='Milwaukee Brewers™';get('source-team').onchange();
  assert.equal(get('source-count').textContent,`${data.rowTeams.filter(teams=>teams.includes('Milwaukee Brewers™')).length} official source rows`);
  assert(get('source-results').innerHTML.includes('Paul Skenes / Jacob Misiorowski'),'Either printed team must match a dual card');get('source-reset').onclick();
  get('source-section').value='Dynamic "Dozen" Autograph Booklet';get('source-section').onchange();get('source-search').value='Derek Jeter';get('source-search').oninput();
  assert.equal(get('source-count').textContent,'1 official source rows');assert(get('source-results').innerHTML.includes('Mookie Betts'));assert(get('source-results').innerHTML.includes('1 in 18,845 packs'));
  let csv='';context.Blob=class{constructor(parts){csv=parts.join('');}};context.URL={createObjectURL:()=> 'blob:test',revokeObjectURL(){}};context.setTimeout=()=>{};context.document.createElement=()=>({click(){}});
  get('source-export').onclick();assert(csv.includes('"Team 1","Team 2"'));assert(csv.includes('Cal Ripken Jr.')&&csv.includes('Mookie Betts'),'CSV must retain every booklet signer');
  get('source-reset').onclick();get('source-section').value='Base Card Dual Autographs';get('source-section').onchange();
  get('source-results').onclick({target:{closest:()=>({dataset:{row:String(data.rows.findIndex(r=>r[1]==='1-A'))}})}});
  assert(get('source-results').innerHTML.includes('BASE CARD DUAL AUTO VARIATION PURPLE PARALLEL'));assert(!get('source-results').innerHTML.includes('26TDDB - BASE CARD BLACK PARALLEL'),'Autographs must not receive ordinary base parallels');
  get('source-reset').onclick();get('source-odds-tab').onclick();assert(get('source-specifications').innerHTML.includes('26TDDB - FENCE BUSTERS'));assert(!get('source-specifications').innerHTML.includes('DescriptionPacks'));get('source-cards-tab').onclick();
 }
 if(data.formatNamesPublished===false){
  assert.equal(get('source-format').disabled,true);assert(get('insights').innerHTML.includes('does not name a format or ratio unit'));
  get('source-odds-tab').onclick();assert(get('source-specifications').innerHTML.includes('Published odds (format not named)'));assert(get('source-specifications').innerHTML.includes('3:1'));assert(!get('source-specifications').innerHTML.includes('3 cards per pack'),'Unspecified units must remain literal');get('source-cards-tab').onclick();
 }
 if(set.slug==='topps-bowman-2026-topps-chrome-black-basketball'){
  get('source-section').value='BASE CARDS';get('source-section').onchange();assert.equal(get('source-count').textContent,'100 official source rows');
  get('source-results').onclick({target:{closest:()=>({dataset:{row:'0'}})}});assert(get('source-results').innerHTML.includes('/299'));assert(get('source-results').innerHTML.includes('/150'));
  get('source-section').value='ROOKIES';get('source-section').onchange();assert.equal(get('source-count').textContent,'50 official source rows');
  get('source-results').onclick({target:{closest:()=>({dataset:{row:'100'}})}});assert(get('source-results').innerHTML.includes('Base Rookies Green Refractor'));assert(get('source-results').innerHTML.includes('/99'));
  get('source-reset').onclick();get('source-section').value='ROOKIE DESIGN VARIATION';get('source-section').onchange();get('source-odds-tab').onclick();assert(get('source-specifications').innerHTML.includes('/50'));assert(!get('source-specifications').innerHTML.includes('/299'),'Variation families must not receive ordinary base numbering');get('source-reset').onclick();get('source-cards-tab').onclick();
 }
 if(set.slug==='topps-bowman-2026-topps-flagship-football'){
  get('source-search').value='NFLTA-ABM';get('source-search').oninput();assert.equal(get('source-count').textContent,'1 official source rows');assert(get('source-results').innerHTML.includes('Drake Maye / Josh Allen / Joe Burrow'));
  get('source-team').value='Cincinnati Bengals';get('source-team').onchange();assert.equal(get('source-count').textContent,'1 official source rows','Any printed signer team must match');
  get('source-results').onclick({target:{closest:()=>({dataset:{row:String(data.rows.findIndex(r=>r[1]==='NFLTA-ABM'))}})}});assert(get('source-results').innerHTML.includes('OFFICIAL Published subjects'));
  let csv='';context.Blob=class{constructor(parts){csv=parts.join('');}};context.URL={createObjectURL:()=> 'blob:test',revokeObjectURL(){}};context.setTimeout=()=>{};context.document.createElement=()=>({click(){}});get('source-export').onclick();assert(csv.includes('Josh Allen')&&csv.includes('Joe Burrow')&&csv.includes('Published subjects'));
  get('source-reset').onclick();get('source-section').value='ROOKIES';get('source-section').onchange();assert.equal(get('source-count').textContent,'100 official source rows');get('source-format').value='Hobby Pack Rate';get('source-format').onchange();
  get('source-results').onclick({target:{closest:()=>({dataset:{row:String(data.rows.findIndex(r=>r[0]==='ROOKIES'))}})}});assert(get('source-results').innerHTML.includes('Base Cards Rainbow Foil'));assert(get('source-results').innerHTML.includes('1 in 1 packs'));get('source-reset').onclick();
 }
 if(set.slug==='topps-bowman-2026-topps-midnight-ufc'){
  assert.equal(get('source-team').disabled,true);get('source-section').value='BASE CARDS';get('source-section').onchange();assert.equal(get('source-count').textContent,'100 official source rows');
  get('source-search').value='Ilia Topuria';get('source-search').oninput();assert(get('source-results').innerHTML.includes('1 in 1 packs'));get('source-results').onclick({target:{closest:()=>({dataset:{row:'0'}})}});assert(get('source-results').innerHTML.includes('Base Moonrise'));assert(get('source-results').innerHTML.includes('1 in 8 packs'));assert(!get('source-results').innerHTML.includes('Base Autograph Variations Black Light'));
  get('source-reset').onclick();get('source-section').value='BASE CARDS AUTOGRAPH VARIATION';get('source-section').onchange();get('source-results').onclick({target:{closest:()=>({dataset:{row:String(data.rows.findIndex(r=>r[0]==='BASE CARDS AUTOGRAPH VARIATION'))}})}});assert(get('source-results').innerHTML.includes('Base Autograph Variations Black Light'));assert(!get('source-results').innerHTML.includes('Base Zodiac'));
  get('source-reset').onclick();get('source-section').value='FIGHT GLOVE RELIC AUTOGRAPHS';get('source-section').onchange();get('source-odds-tab').onclick();assert(get('source-specifications').innerHTML.includes('Limited to 8 and 1'));assert(!get('source-specifications').innerHTML.includes('/8'),'A family print limit must not become inferred serial numbering');get('source-reset').onclick();get('source-cards-tab').onclick();
 }
 if(set.slug==='topps-bowman-2025-topps-royalty-wwe'){
  assert.equal(get('source-team').disabled,true);get('source-section').value='BASE CARDS';get('source-section').onchange();assert.equal(get('source-count').textContent,'100 official source rows');get('source-search').value='Cody Rhodes';get('source-search').oninput();assert(get('source-results').innerHTML.includes('Cody Rhodes'));get('source-results').onclick({target:{closest:()=>({dataset:{row:'13'}})}});assert(get('source-results').innerHTML.includes('OFFICIAL Published designation'));assert(get('source-results').innerHTML.includes('Smackdown'));
  get('source-reset').onclick();get('source-section').value='100 PERCENT STRATUSFACTION RELICS';get('source-section').onchange();assert.equal(get('source-count').textContent,'5 official source rows');get('source-reset').onclick();
 }
 if(kind==='topps-now'&&data.rows.some(r=>/^https:\/\/(?:uk|uk-next)\.topps\.com\//.test(r[8]))){get('source-odds-tab').onclick();assert(/href="https:\/\/(?:uk|uk-next)\.topps\.com\/products\//.test(get('source-specifications').innerHTML),'Regional official product evidence must remain linked in shared parallel tables');get('source-cards-tab').onclick();}
 if(kind==='topps-now'&&data.supplementarySourceProducts?.length){
  const proof=data.supplementarySourceProducts[0],index=data.rows.findIndex(r=>r[0]===proof.series&&r[1]===proof.number);
  get('source-results').onclick({target:{closest:()=>({dataset:{row:String(index)}})}});
  get('source-search').value=data.rows[index][2];get('source-search').oninput();
  get('source-results').onclick({target:{closest:()=>({dataset:{row:String(index)}})}});
  assert(get('source-results').innerHTML.includes('Official sources for retained fields'));
  assert(get('source-results').innerHTML.includes(proof.evidence.url.replaceAll('&','&amp;')),'Retained print runs and dates must keep their original official evidence link');get('source-reset').onclick();
 }
 if(data.importKind==='pdf'||data.odds?.length||data.publishedSpecifications?.length||data.officialStructure||data.oddsColumn!=null||data.serialColumn!=null)assert(get('source-specifications').innerHTML.includes('odds-group'));else assert(get('source-specifications').innerHTML.includes('No parallel or odds specification'));
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
