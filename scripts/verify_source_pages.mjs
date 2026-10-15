import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import vm from 'node:vm';
import {reconcileParallels,categoryNumbering,specificationRows} from '../parallel-specs.mjs';
const catalog=JSON.parse(await readFile('data/set-catalog.json','utf8'));
const code=(await readFile('source-page.js','utf8')).replace(/^import .*;\n/, '');
const cases=['pdf','html','wildcard','xlsx','panini-pdf'].map(kind=>catalog.sets.find(s=>s.importKind===kind&&s.tableData&&s.rosterPublished!==false&&(kind!=='pdf'||s.odds))).concat(catalog.sets.filter(s=>s.importKind==='topps-grid-pdf'||s.dedicatedParser||['upper-deck-2025-26-stature','wild-card-2026-wild-card-alumination-just-the-hits-baseball-250th','wild-card-2026-wild-card-slimgem-variety-pack'].includes(s.slug)));
for(const set of catalog.sets.filter(s=>s.oddsParser))if(!cases.some(c=>c.slug===set.slug))cases.push(set);
for(const set of cases){
 const kind=set.importKind;
 const data=JSON.parse(await readFile(set.tableData,'utf8'));
 if(set.slug==='wild-card-2026-wild-card-slimgem-variety-pack'){
  assert.deepEqual(data.rows,Object.entries(data.officialStructure.rosters).flatMap(([key,names])=>names.map(name=>[key,name,''])));
  assert.equal(data.rows.length,95);assert.notEqual(set.rosterPublished,false);
 }
 const map=new Map(),get=id=>{if(!map.has(id))map.set(id,{value:'',options:id==='source-sort'?[{value:'checklist'},{value:'name'},{value:'rare'}]:[{}],setAttribute(k,v){this[k]=v;},focus(){},add(option){this.options.push(option);}});return map.get(id);};
 const context=vm.createContext({reconcileParallels,categoryNumbering,specificationRows,document:{body:{dataset:{table:set.tableData}},getElementById:get,addEventListener(){}},console,Option:function(text,value){return {text,value};},fetch:async()=>({ok:true,json:async()=>JSON.parse(JSON.stringify(data))})});
 await new vm.Script('(async()=>{'+code+'})()').runInContext(context);
 if(!data.rows.length){assert(get('source-results').innerHTML.includes('No matching'));assert.equal(set.rosterPublished,false);continue;}
 assert(get('source-results').innerHTML.includes('<table>'));
 if(set.slug==='upper-deck-2025-26-stature'){get('source-rookie').checked=true;get('source-rookie').onchange();assert.equal(get('source-count').textContent,'882 official source rows');get('source-reset').onclick();}
 if(set.dedicatedParser==='scripts/import_leaf_csv.py'){assert.equal(get('source-team').disabled,true);assert.equal(get('source-rookie').disabled,true);assert.equal(get('source-format').disabled,true);assert(get('source-sort').options.find(o=>o.value==='rare').disabled);let exported;context.Blob=class{constructor(parts){exported=parts.join('');}};context.URL={createObjectURL:()=>'',revokeObjectURL(){}};context.setTimeout=()=>{};context.document.createElement=()=>({click(){}});get('source-export').onclick();assert(exported.includes('Source worksheet')&&exported.includes('Source row'));for(const h of data.headers)assert(exported.includes(h.replaceAll('\"','\"\"')));const named=data.rows.find(r=>r[1]);assert(exported.includes(named[1]));}
 if(kind==='topps-now'){assert(get('source-results').innerHTML.includes('PRINT RUN'));const printed=data.rows.find(r=>r[3]);if(printed){get('source-section').value=printed[0];get('source-section').onchange();get('source-search').value=printed[2];get('source-search').oninput();assert(get('source-results').innerHTML.includes(printed[3]),'Published print run must remain searchable and visible');get('source-reset').onclick();}assert.equal(get('source-team').disabled,true);assert.equal(get('source-rookie').disabled,true);assert.equal(data.oddsColumn,undefined);assert.equal(set.coverageComplete,false);}
 if(kind==='topps-grid-pdf'||(set.dedicatedParser&&data.headers.includes('Name')&&data.headers.includes('Rookie'))){const nameColumn=data.headers.indexOf('Player / subjects')>=0?data.headers.indexOf('Player / subjects'):data.headers.indexOf('Name');assert(get('source-results').innerHTML.includes(data.rows[0][nameColumn].replaceAll('&','&amp;').replaceAll("'",'&#39;')));assert.equal(get('source-team').disabled,!data.headers.some(h=>/^team$/i.test(h)));assert.equal(get('source-rookie').disabled,!data.headers.includes('Rookie'));if(data.headers.includes('Rookie')){get('source-rookie').checked=true;get('source-rookie').onchange();assert.equal(get('source-count').textContent,`${data.rows.filter(r=>r[data.headers.indexOf('Rookie')]==='Rookie').length.toLocaleString()} official source rows`);get('source-reset').onclick();}}
 assert(get('source-results').innerHTML.includes('PLAYER / SUBJECT'));assert(get('source-results').innerHTML.includes('View family details'));
 get('source-results').onclick({target:{closest:()=>({dataset:{row:'0'}})}});assert(get('source-results').innerHTML.includes('OFFICIAL '+data.headers[0]));assert(get('source-results').innerHTML.includes('Hide family details'));
 get('source-sort').value='name';get('source-sort').onchange();assert(get('source-results').innerHTML.includes('<table>'));
 get('source-reset').onclick();assert.equal(get('source-sort').value,'checklist');assert.equal(get('source-section').value,'');
 assert(get('insights').innerHTML.includes('insight-grid'));
 get('source-odds-tab').onclick();assert.equal(get('source-cards-panel').hidden,true);assert.equal(get('source-specifications').hidden,false);get('source-cards-tab').onclick();assert.equal(get('source-specifications').hidden,true);
 if(set.slug==='topps-bowman-2025-topps-transcendent-collection-baseball'){
  assert.equal(get('source-format').disabled,true);
  assert(get('source-sort').options.find(o=>o.value==='rare').disabled);
  get('source-section').value='GEMSTONES';get('source-section').onchange();
  assert.equal(get('source-count').textContent,'6 official source rows');
  get('source-search').value='CRCS';get('source-search').oninput();assert.equal(get('source-count').textContent,'2 official source rows');
  assert(get('source-results').innerHTML.includes('Lou Gehrig')&&get('source-results').innerHTML.includes('Cal Ripken Jr.'));
  get('source-results').onclick({target:{closest:()=>({dataset:{row:String(data.rows.findIndex(r=>r[1]==='CRCS'))}})}});
  assert(get('source-results').innerHTML.includes('One-of-one'));assert(!get('source-results').innerHTML.includes('1 in '));
  get('source-reset').onclick();get('source-section').value='TRANSCENDENT ICONS CHROME BASE CARDS';get('source-section').onchange();
  get('source-results').onclick({target:{closest:()=>({dataset:{row:'0'}})}});
  assert(get('source-results').innerHTML.includes('/25')&&get('source-results').innerHTML.includes('/10'));
  assert(!get('source-results').innerHTML.includes('VIP'));
  let csv='';context.Blob=class{constructor(parts){csv=parts.join('');}};context.URL={createObjectURL:()=> 'blob:test',revokeObjectURL(){}};context.setTimeout=()=>{};context.document.createElement=()=>({click(){}});
  get('source-export').onclick();assert(csv.includes('"Name","Team","Rookie"'));assert(csv.includes('Shohei Ohtani'));
  get('source-reset').onclick();get('source-odds-tab').onclick();assert(get('source-specifications').innerHTML.includes('/25 or less'));assert(get('source-specifications').innerHTML.includes('Limited to 25 copies'));
  get('source-export').onclick();assert(csv.includes('/25 or less')&&csv.includes('Limited to 25 copies'));assert(csv.includes('One-of-one'));assert(csv.includes('serial marking is not'));
  get('source-cards-tab').onclick();get('source-reset').onclick();
 }
 if(set.slug==='topps-bowman-2026-topps-chrome-baseball'){
  get('source-rookie').checked=true;get('source-rookie').onchange();assert.equal(get('source-count').textContent,'412 official source rows');get('source-reset').onclick();
  get('source-section').value='BASE CARDS';get('source-section').onchange();assert.equal(get('source-count').textContent,'300 official source rows');
  get('source-search').value='Samuel Basallo';get('source-search').oninput();assert(get('source-results').innerHTML.includes('Baltimore Orioles®'));get('source-reset').onclick();
  get('source-section').value='1991 TOPPS BASEBALL';get('source-section').onchange();assert.equal(get('source-count').textContent,'30 official source rows');get('source-reset').onclick();
  get('source-section').value='FANATICS AUTHENTICS REDEMPTION CARDS';get('source-section').onchange();assert.equal(get('source-count').textContent,'30 official source rows');
  let csv='';context.Blob=class{constructor(parts){csv=parts.join('');}};context.URL={createObjectURL:()=> 'blob:test',revokeObjectURL(){}};context.setTimeout=()=>{};context.document.createElement=()=>({click(){}});
  get('source-export').onclick();assert(csv.includes('"Name","Team","Rookie"'));assert(csv.includes('"FANATICS AUTHENTICS REDEMPTION CARDS","","Chase Utley","Philadelphia Phillies®"'));get('source-reset').onclick();
  get('source-section').value='2025 MLB COMMISSIONERS TROPHY';get('source-section').onchange();assert(get('source-results').innerHTML.includes('Name not published'));assert(get('source-results').innerHTML.includes('Los Angeles Dodgers®'));get('source-reset').onclick();
  get('source-section').value='2025 WORLD CHAMPIONS AUTOGRAPH REFRACTOR';get('source-section').onchange();get('source-format').value=data.formats[4];get('source-format').onchange();get('source-odds-tab').onclick();
  assert(get('source-specifications').innerHTML.includes('0.39374999999999999'));assert(get('source-specifications').innerHTML.includes('without a ratio separator'));assert(!get('source-specifications').innerHTML.includes('39.375%'));
  get('source-export').onclick();assert(csv.includes('0.39374999999999999')&&csv.includes('not inferred'));get('source-reset').onclick();get('source-cards-tab').onclick();
 }
 if(set.slug==='topps-bowman-2025-26-topps-hopps-basketball'){
  assert.equal(get('source-team').disabled,false);assert.equal(get('source-rookie').disabled,false);
  get('source-rookie').checked=true;get('source-rookie').onchange();assert.equal(get('source-count').textContent,'384 official source rows');get('source-reset').onclick();
  get('source-search').value='Cooper Flagg';get('source-search').oninput();assert(get('source-results').innerHTML.includes('Dallas Mavericks'));get('source-reset').onclick();
  get('source-section').value='BASE CARDS II';get('source-section').onchange();assert.equal(get('source-count').textContent,'100 official source rows');get('source-results').onclick({target:{closest:()=>({dataset:{row:'100'}})}});assert(get('source-results').innerHTML.includes('Base Rainbow'));assert(!get('source-results').innerHTML.includes('Hoops Rookie Signatures Pixel Burst'));
  get('source-reset').onclick();get('source-section').value='ALL STARS';get('source-section').onchange();get('source-odds-tab').onclick();assert(get('source-specifications').innerHTML.includes('Base Rainbow'));get('source-reset').onclick();get('source-cards-tab').onclick();
  get('source-search').value='HW-19';get('source-search').oninput();assert.equal(get('source-count').textContent,'1 official source rows');assert(get('source-results').innerHTML.includes('De&#39;Aaron Fox'));assert(get('source-results').innerHTML.includes('San Antonio Spurs'));
  let csv='';context.Blob=class{constructor(parts){csv=parts.join('');}};context.URL={createObjectURL:()=> 'blob:test',revokeObjectURL(){}};context.setTimeout=()=>{};context.document.createElement=()=>({click(){}});get('source-export').onclick();assert(csv.includes('"Name","Team","Rookie"'));assert(csv.includes('"HW-19","De\'Aaron Fox","San Antonio Spurs"'));get('source-reset').onclick();
  get('source-section').value='HOOPS ROOKIE FIRST SIGNS';get('source-section').onchange();get('source-odds-tab').onclick();assert(get('source-specifications').innerHTML.includes('Hoops Rookies First Signs'));get('source-reset').onclick();get('source-cards-tab').onclick();
 }
 if(set.slug==='topps-bowman-2025-topps-chrome-formula-1-sapphire-edition'){
  assert.equal(get('source-team').disabled,false);assert.equal(get('source-rookie').disabled,false);
  assert.deepEqual(data.formats,['Sapphire Pack Rate']);
  get('source-section').value='BASE CARDS';get('source-section').onchange();assert.equal(get('source-count').textContent,'210 official source rows');get('source-results').onclick({target:{closest:()=>({dataset:{row:'0'}})}});
  assert(get('source-results').innerHTML.includes('Base Orange Sapphire Parallel'));assert(get('source-results').innerHTML.includes('1 in 17 packs'));assert(!get('source-results').innerHTML.includes('Base Refractor Parallel'),'Ordinary Chrome configurations must not appear in Sapphire family details');
  get('source-reset').onclick();get('source-team').value='Oracle Red Bull Racing';get('source-team').onchange();assert.equal(get('source-count').textContent,`${data.rows.filter(r=>r[4]==='Oracle Red Bull Racing').length} official source rows`);
  get('source-reset').onclick();get('source-rookie').checked=true;get('source-rookie').onchange();assert.equal(get('source-count').textContent,'35 official source rows');get('source-reset').onclick();
  get('source-section').value='Chrome Autographs';get('source-section').onchange();get('source-search').value='CAC-COL';get('source-search').oninput();assert(get('source-results').innerHTML.includes('Franco Colapinto'));const actor=data.rows.findIndex(r=>r[1]==='CAC-COL');get('source-results').onclick({target:{closest:()=>({dataset:{row:String(actor)}})}});assert(get('source-results').innerHTML.includes('OFFICIAL Subset'));assert(get('source-results').innerHTML.includes('BWT Alpine Formula One™ Team'));
  let csv='';context.Blob=class{constructor(parts){csv=parts.join('');}};context.URL={createObjectURL:()=> 'blob:test',revokeObjectURL(){}};context.setTimeout=()=>{};context.document.createElement=()=>({click(){}});get('source-export').onclick();assert(csv.includes('"Team","Subset","Rookie"'));assert(csv.includes('Franco Colapinto'));get('source-reset').onclick();
  get('source-section').value='Infinite Sapphire';get('source-section').onchange();get('source-odds-tab').onclick();assert(get('source-specifications').innerHTML.includes('1 in 80 packs'));assert(get('source-specifications').innerHTML.includes('1 in 8,080 packs'));get('source-reset').onclick();get('source-cards-tab').onclick();
 }
 if(set.slug==='topps-bowman-2025-star-wars-masterwork'){
  get('source-section').value='CHARACTERS';get('source-section').onchange();assert.equal(get('source-count').textContent,'100 official source rows');
  get('source-results').onclick({target:{closest:()=>({dataset:{row:'0'}})}});assert(get('source-results').innerHTML.includes('Base Cards Blue'));assert(get('source-results').innerHTML.includes('1 in 6 packs'));assert(!get('source-results').innerHTML.includes('Under Disguise Rainbow Foil'));
  get('source-reset').onclick();get('source-search').value='ARC-LUNA';get('source-search').oninput();assert(get('source-results').innerHTML.includes('Diego Luna'));
  const actor=data.rows.findIndex(r=>r[1]==='ARC-LUNA');get('source-results').onclick({target:{closest:()=>({dataset:{row:String(actor)}})}});assert(get('source-results').innerHTML.includes('Cassian Andor'));assert(get('source-results').innerHTML.includes('Missle: Andor'));
  get('source-reset').onclick();get('source-section').value='SKELETON CREW AUTOGRAPH RELIC';get('source-section').onchange();get('source-odds-tab').onclick();assert(get('source-specifications').innerHTML.includes('1,249'));assert(get('source-specifications').innerHTML.includes('without a ratio separator'));assert(!get('source-specifications').innerHTML.includes('1 in 1,249 packs'));
  get('source-reset').onclick();get('source-cards-tab').onclick();get('source-section').value='SKETCH ARTISTS';get('source-section').onchange();assert.equal(get('source-count').textContent,'208 official source rows');get('source-search').value='ジェイソン';get('source-search').oninput();assert(get('source-results').innerHTML.includes('ジェイソン (Jason)'));get('source-reset').onclick();
 }
 if(set.slug==='topps-bowman-2025-topps-star-wars-smugglers-outpost'){
  get('source-section').value='Finest Base Set';get('source-section').onchange();assert.equal(get('source-count').textContent,'75 official source rows');get('source-results').onclick({target:{closest:()=>({dataset:{row:'0'}})}});assert(get('source-results').innerHTML.includes('Finest Base Set Green Refractor Parallel'));assert(!get('source-results').innerHTML.includes('Chrome Black Base Set Gold Refractor Parallel'));
  get('source-reset').onclick();get('source-section').value='Galactic Funk';get('source-section').onchange();get('source-odds-tab').onclick();assert(get('source-specifications').innerHTML.includes('Galactic Funk Gold Refractor Parallel'));assert(get('source-specifications').innerHTML.includes('/50'));assert(!get('source-specifications').innerHTML.includes('Galactic Funk Galactic Funk'));
  get('source-reset').onclick();get('source-section').value='Stellar Signatures Autograph';get('source-section').onchange();get('source-odds-tab').onclick();assert(get('source-specifications').innerHTML.includes('/99'));assert(get('source-specifications').innerHTML.includes('Stellar Signatures Autograph Green Parallel'));
  get('source-reset').onclick();get('source-cards-tab').onclick();get('source-section').value='Sketch Artist List';get('source-section').onchange();assert.equal(get('source-count').textContent,'216 official source rows');get('source-search').value='ジェイソン';get('source-search').oninput();assert(get('source-results').innerHTML.includes('ジェイソン (Jason)'));
  let csv='';context.Blob=class{constructor(parts){csv=parts.join('');}};context.URL={createObjectURL:()=> 'blob:test',revokeObjectURL(){}};context.setTimeout=()=>{};context.document.createElement=()=>({click(){}});get('source-export').onclick();assert(csv.includes('Artist roster name'));assert(csv.includes('ジェイソン (Jason)'));get('source-reset').onclick();
 }
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
 if(set.slug==='topps-bowman-2025-topps-disneyland-70th-anniversary'){
  assert.equal(get('source-team').disabled,true);assert.equal(get('source-rookie').disabled,true);
  get('source-section').value='THEN AND NOW';get('source-section').onchange();assert.equal(get('source-count').textContent,'82 official source rows');
  get('source-results').onclick({target:{closest:()=>({dataset:{row:'0'}})}});assert(get('source-results').innerHTML.includes('Base Set Rainbow Foil'));assert(get('source-results').innerHTML.includes('OFFICIAL Land'));assert(get('source-results').innerHTML.includes('Main Street, U.S.A.'));
  get('source-reset').onclick();get('source-section').value='THEN AND NOW HIDDEN MICKEY VARIATION';get('source-section').onchange();get('source-odds-tab').onclick();assert(get('source-specifications').innerHTML.includes('Base Set Variation Hidden Mickey'));assert(!get('source-specifications').innerHTML.includes('Base Set Rainbow Foil'),'Variation lists must not inherit ordinary base parallels');
  get('source-reset').onclick();get('source-cards-tab').onclick();get('source-search').value='T55A-ANR';get('source-search').oninput();assert.equal(get('source-count').textContent,'1 official source rows');assert(get('source-results').innerHTML.includes('Anika Noni Rose'));
  get('source-results').onclick({target:{closest:()=>({dataset:{row:String(data.rows.findIndex(r=>r[1]==='T55A-ANR'))}})}});assert(get('source-results').innerHTML.includes('OFFICIAL First Name'));assert(get('source-results').innerHTML.includes('OFFICIAL Attraction'));
  let csv='';context.Blob=class{constructor(parts){csv=parts.join('');}};context.URL={createObjectURL:()=> 'blob:test',revokeObjectURL(){}};context.setTimeout=()=>{};context.document.createElement=()=>({click(){}});get('source-export').onclick();assert(csv.includes('"First Name","Last Name","Character","Attraction"'));assert(csv.includes('Anika Noni')&&csv.includes('Tiana'));
  get('source-reset').onclick();get('source-section').value='SKETCH ARTISTS';get('source-section').onchange();assert.equal(get('source-count').textContent,'77 official source rows');get('source-search').value='ジェイソン';get('source-search').oninput();assert(get('source-results').innerHTML.includes('ジェイソン (Jason)'));get('source-reset').onclick();
 }
 if(set.slug==='topps-bowman-2026-topps-star-wars-chrome-galaxy'){
  assert.equal(get('source-team').disabled,true);assert.equal(get('source-rookie').disabled,true);
  get('source-section').value='BASE CARDS';get('source-section').onchange();assert.equal(get('source-count').textContent,'100 official source rows');get('source-search').value='Claudio Aboy';get('source-search').oninput();assert(get('source-results').innerHTML.includes('The Mandalorian&#39;s Escape'));
  get('source-results').onclick({target:{closest:()=>({dataset:{row:'0'}})}});assert(get('source-results').innerHTML.includes('OFFICIAL Additional published text'));assert(get('source-results').innerHTML.includes('Claudio Aboy'));
  get('source-reset').onclick();get('source-section').value='ART OF KNIGHTS OF THE REPUBLIC';get('source-section').onchange();get('source-odds-tab').onclick();assert(get('source-specifications').innerHTML.includes('Art of Knights of the Old Republic Superfractor Parallel'));assert(!get('source-specifications').innerHTML.includes('Base Cards Superfractor Parallel'),'KOTOR family must not receive ordinary base parallels');get('source-cards-tab').onclick();
  get('source-reset').onclick();get('source-search').value='GA-BDH';get('source-search').oninput();assert.equal(get('source-count').textContent,'1 official source rows');assert(get('source-results').innerHTML.includes('Bryce Dallas Howard'));
  get('source-reset').onclick();get('source-section').value='QUAD AUTOGRAPHS';get('source-section').onchange();get('source-search').value='Q-ANDOR';get('source-search').oninput();assert.equal(get('source-count').textContent,'4 official source rows');
  let csv='';context.Blob=class{constructor(parts){csv=parts.join('');}};context.URL={createObjectURL:()=> 'blob:test',revokeObjectURL(){}};context.setTimeout=()=>{};context.document.createElement=()=>({click(){}});get('source-export').onclick();assert(csv.includes('Additional published text'));for(const name of ['Diego Luna',"Genevieve O'Reilly",'Stellan Skarsgård','Benjamin Bratt'])assert(csv.includes(name));
  get('source-reset').onclick();get('source-section').value='SKETCH CARD ARTISTS';get('source-section').onchange();assert.equal(get('source-count').textContent,'218 official source rows');get('source-search').value='ジェイソン';get('source-search').oninput();assert(get('source-results').innerHTML.includes('ジェイソン (Jason)'));
  get('source-reset').onclick();get('source-odds-tab').onclick();assert(get('source-specifications').innerHTML.includes('4 cards per pack; 18 packs per box; 4 Chrome parallels per box'));assert(get('source-specifications').innerHTML.includes('not calculated pack odds'));get('source-cards-tab').onclick();
 }
 if(kind==='topps-now'&&data.rows.some(r=>/^https:\/\/(?:uk|uk-next)\.topps\.com\//.test(r[8]))){get('source-odds-tab').onclick();assert(/href="https:\/\/(?:uk|uk-next)\.topps\.com\/products\//.test(get('source-specifications').innerHTML),'Regional official product evidence must remain linked in shared parallel tables');get('source-cards-tab').onclick();}
 if(kind==='topps-now'&&data.rows.some(r=>r[8].startsWith('https://fr.topps.com/'))){get('source-odds-tab').onclick();assert(get('source-specifications').innerHTML.includes('Official French product'));assert(get('source-specifications').innerHTML.includes('Foil orange'));get('source-cards-tab').onclick();}
 if(set.slug==='topps-now-2026'){
  get('source-section').value='2025-26 NHL Topps NOW®';get('source-section').onchange();get('source-search').value='Tomas Hertl';get('source-search').oninput();
  const index=data.rows.findIndex(r=>r[0]==='2025-26 NHL Topps NOW®'&&r[1]==='188');get('source-results').onclick({target:{closest:()=>({dataset:{row:String(index)}})}});assert(get('source-results').innerHTML.includes('Black Ice Parallels'));assert(get('source-results').innerHTML.includes('non-base sticker'));
  let csv='';context.Blob=class{constructor(parts){csv=parts.join('');}};context.URL={createObjectURL:()=> 'blob:test',revokeObjectURL(){}};context.setTimeout=()=>{};context.document.createElement=()=>({click(){}});get('source-export').onclick();assert(csv.includes('Jun 5, 2026'));assert(csv.includes('Gold Ice Parallel'));
  get('source-reset').onclick();get('source-section').value='2026-27 NFL Topps NOW®';get('source-section').onchange();get('source-search').value='David Bailey';get('source-search').oninput();assert(get('source-results').innerHTML.includes('12 oct. 2026'));assert(get('source-results').innerHTML.includes('Not published'),'Active print run must remain unpublished');get('source-reset').onclick();
 }
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
