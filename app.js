const setSlug=document.body?.dataset?.set||'allen-ginter-2026';
const $=id=>document.getElementById(id);
const esc=v=>String(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const pretty=v=>v.toLowerCase().replace(/\b\w/g,c=>c.toUpperCase()).replace(/\bIi\b/g,'II').replace(/\bI\b/g,'I').replace(/\bN(34|43)\b/g,'N$1');
const normalize=v=>v.normalize('NFD').replace(/\p{Diacritic}/gu,'').toLowerCase();
let data,oddsGroups=[],view='cards',page=1,filtered=[],expanded=new Set();const pageSize=40;
const oddsText=n=>n==null?'Not listed for this format':`1 in ${n.toLocaleString()} packs`;
const familyOdds=s=>s.oddsIds.map(i=>data.odds[i]);
const baseOdds=s=>data.formats?familyOdds(s).find(o=>['BASE','REFRACTOR','Standard / original'].includes(o.label)):familyOdds(s).find(o=>!o.name.includes('PARALLEL'));
function parallelLabel(group,o){
 if(o.label)return pretty(o.label);
 const family=group.entries.find(e=>!e.name.includes('PARALLEL'))?.name;
 let label=o.name;
 if(family&&label===family)return 'Standard / original';
 const prefixes=['BASE CARDS ', 'BASE CARD MINI SIZED ', 'BASE CARD CHROME VARIATION ', 'BASE MINI CARD CHROME VARIATION '];
 if(family&&label.startsWith(family+' '))label=label.slice(family.length+1);
 else for(const prefix of prefixes){if(label.startsWith(prefix)){label=label.slice(prefix.length);break;}}
 return pretty(label.replace(/ PARALLEL$/, '').replace(/FILAGREE/g,'FILIGREE'));
}
function buildOddsGroups(){
 const groups=[];
 for(const section of data.sections){
  const shared=section.name.startsWith('ALLEN AND GINTER FRAMED RELICS MINI SIZE');
  let group=shared?groups.find(g=>g.name==='Framed Mini Relics'):null;
  if(group){group.sectionIds.push(section.id);group.cardCount+=section.cards.length;continue;}
  groups.push({name:shared?'Framed Mini Relics':pretty(section.name),sectionIds:[section.id],cardCount:section.cards.length,entries:familyOdds(section)});
 }
 const mapped=new Set(data.sections.flatMap(s=>s.oddsIds));
 const remaining=data.odds.filter((o,i)=>!mapped.has(i));
 if(remaining.length)groups.push({name:'Other Published Categories',sectionIds:[],cardCount:0,entries:remaining});
 return groups;
}
function renderBowmanInsights(){
 const rookie=data.sections.find(s=>s.name==='BASE ROOKIE'),prospects=data.sections.find(s=>s.name==='PAPER PROSPECTS');
 const rare=data.odds.filter(o=>o.odds.hobby).sort((a,b)=>b.odds.hobby-a.odds.hobby)[0];
 $('insights').innerHTML=`<div class="insight-grid"><article class="insight-card"><p class="eyebrow">THE NFL ROOKIE CLASS</p><strong>${rookie.cards.length}</strong><h3>NFL rookies on paper</h3><p>The rookie checklist spans card numbers 101–200, alongside the NFL veteran base section.</p><button data-insight="rookies">Explore NFL rookies →</button></article><article class="insight-card"><p class="eyebrow">THE NEXT GENERATION</p><strong>${prospects.cards.length}</strong><h3>College paper prospects</h3><p>College talent has its own paper and Chrome checklists, with separately published parallel odds.</p><button data-insight="prospects">Explore the prospects →</button></article><article class="insight-card"><p class="eyebrow">THE LONGEST HOBBY ODDS</p><strong class="long-number">1:${rare.odds.hobby.toLocaleString()}</strong><h3>RetroFractor autograph SuperFractor</h3><p>The rarest category by published hobby pack odds. This is not the chance of a specific player.</p><button data-insight="rarest">Explore the chase →</button></article></div>`;
 $('insights').onclick=e=>{const b=e.target.closest('[data-insight]');if(!b)return;$('reset').onclick();$('format').value='hobby';if(b.dataset.insight==='rarest'){$('search').value=rare.name;switchView('odds');}else{$('subset').value=String(b.dataset.insight==='rookies'?rookie.id:prospects.id);switchView('cards');}$('explore').scrollIntoView({behavior:'smooth'});};
}
function renderInsights(){
 if(setSlug==='bowman-football-2026'){renderBowmanInsights();return;}
 const base=data.sections.find(s=>s.name==='BASE CARDS');
 const total=base.cards.length;
 const rookies=base.cards.filter(c=>c.subjects.some(s=>s.rookie)).length;
 const unassigned=base.cards.filter(c=>c.subjects.every(s=>!s.team)).length;
 const other=total-rookies-unassigned;
 const hello=data.sections.find(s=>s.name==='MINI 50 WAYS TO SAY HELLO');
 const rarest=data.odds.filter(o=>o.odds.hobby).sort((a,b)=>b.odds.hobby-a.odds.hobby)[0];
 $('insights').innerHTML=`<div class="insight-grid"><article class="insight-card"><p class="eyebrow">THE ROOKIE CLASS</p><strong>${rookies}</strong><h3>Rookies in the base set</h3><p>${(rookies/total*100).toFixed(1)}% of the ${total}-card base checklist carries Topps’ rookie designation.</p><button data-insight="rookies">Explore the rookies →</button></article><article class="insight-card"><p class="eyebrow">THE GINTER CURIOSITIES</p><strong>${hello.cards.length}</strong><h3>Ways to say hello</h3><p>A whole mini insert checklist devoted to greetings. Published hobby odds: ${oddsText(baseOdds(hello).odds.hobby)}.</p><button data-insight="hello">See the greetings →</button></article><article class="insight-card"><p class="eyebrow">THE LONGEST PUBLISHED ODDS</p><strong class="long-number">1:${rarest.odds.hobby.toLocaleString()}</strong><h3>Dynasty Gold redemption</h3><p>The rarest category by published hobby pack odds. This is a category pull rate, not odds for an individual subject.</p><button data-insight="rarest">Explore the chase →</button></article></div><div class="base-composition"><div><h3>What’s in the base checklist?</h3><p>${total} cards, grouped by the official rookie and team labels.</p></div><div class="composition-chart"><div class="composition-bar" role="img" aria-label="${rookies} rookies, ${other} other cards with a team listed, ${unassigned} cards without a team listed"><span style="width:${rookies/total*100}%"></span><span style="width:${other/total*100}%"></span><span style="width:${unassigned/total*100}%"></span></div><div class="composition-legend"><span><i></i>${rookies} rookies</span><span><i></i>${other} other team-listed cards</span><span><i></i>${unassigned} no team listed</span></div><p>“No team listed” reflects the source document; it does not imply a sport or occupation.</p></div></div>`;
 $('insights').onclick=e=>{
  const button=e.target.closest('[data-insight]');if(!button)return;
  $('reset').onclick();$('format').value='hobby';
  if(button.dataset.insight==='rookies'){$('subset').value=String(base.id);$('rookie').checked=true;switchView('cards');}
  if(button.dataset.insight==='hello'){$('subset').value=String(hello.id);switchView('cards');}
  if(button.dataset.insight==='rarest'){$('search').value=rarest.name;switchView('odds');}
  $('explore').scrollIntoView({behavior:'smooth',block:'start'});
 };
}
function readFilters(){return {q:normalize($('search').value.trim()),subset:$('subset').value,team:$('team').value,format:$('format').value,rookie:$('rookie').checked,sort:$('sort').value};}
function render(){
 const f=readFilters();
 if(view==='cards'){
 filtered=data.sections.flatMap(s=>s.cards.map(c=>({...c,section:s}))).filter(c=>(!f.subset||String(c.section.id)===f.subset)&&(!f.team||c.subjects.some(s=>(s.team||'No team listed')===f.team))&&(!f.rookie||c.subjects.some(s=>s.rookie))&&(!f.q||normalize([c.number,c.section.name,...c.subjects.map(s=>s.sourceText)].join(' ')).includes(f.q)));
 if(f.sort==='name')filtered.sort((a,b)=>a.subjects[0].name.localeCompare(b.subjects[0].name));
 if(f.sort==='rare')filtered.sort((a,b)=>(baseOdds(b.section)?.odds[f.format]||0)-(baseOdds(a.section)?.odds[f.format]||0));
 }else{
 filtered=oddsGroups.filter(g=>!f.subset||g.sectionIds.includes(Number(f.subset))).map(g=>({...g,entries:g.entries.filter(o=>!f.q||normalize(g.name+' '+o.name).includes(f.q))})).filter(g=>!f.q||g.entries.length||normalize(g.name).includes(f.q));
 if(f.sort==='name')filtered.sort((a,b)=>a.name.localeCompare(b.name));
 if(f.sort==='rare')filtered.sort((a,b)=>Math.max(0,...b.entries.map(o=>o.odds[f.format]||0))-Math.max(0,...a.entries.map(o=>o.odds[f.format]||0)));
 }
 const pages=Math.max(1,Math.ceil(filtered.length/pageSize));page=Math.min(page,pages);
 $('result-count').textContent=`${filtered.length.toLocaleString()} ${view==='cards'?(filtered.length===1?'card':'cards'):(filtered.length===1?'checklist family':'checklist families')}${f.q?' matching your search':''}`;
 $('page-label').textContent=`Page ${page} of ${pages}`;$('previous').disabled=page===1;$('next').disabled=page===pages;
 $('team').disabled=view==='odds';$('rookie').disabled=view==='odds';
 const rows=filtered.slice((page-1)*pageSize,page*pageSize);
 if(!rows.length){$('results').innerHTML='<div class="empty">No results found. Try a broader search or reset your filters.</div>';return;}
 if(view==='odds'){
 $('results').innerHTML=rows.map(g=>`<section class="odds-group"><div class="odds-group-heading"><div><h3>${esc(g.name)}</h3><p>${g.cardCount.toLocaleString()} checklist cards · ${g.entries.length} published odds ${g.entries.length===1?'entry':'entries'}</p></div><span class="format-label">${esc($('format').selectedOptions[0].text)} packs</span></div>${g.entries.length?`<div class="table-scroll"><table><thead><tr><th>PARALLEL / VARIATION</th><th>PACK ODDS</th><th>PER-PACK RATE</th></tr></thead><tbody>${g.entries.map(o=>`<tr><td><span class="card-name">${esc(parallelLabel(g,o))}</span><span class="team">Official odds sheet · page ${o.page}</span></td><td>${oddsText(o.odds[f.format])}</td><td>${o.odds[f.format]?`${(100/o.odds[f.format]).toLocaleString(undefined,{maximumSignificantDigits:3})}%`:'—'}</td></tr>`).join('')}</tbody></table></div>`:'<p class="unpublished">Pack odds are not published for this checklist family.</p>'}</section>`).join('');
 }else{
 $('results').innerHTML=`<div class="table-scroll"><table><thead><tr><th>CARD #</th><th>PLAYER / SUBJECT</th><th>SUBSET</th><th>CATEGORY ODDS & PARALLELS</th></tr></thead><tbody>${rows.map(c=>{
 const key=`${c.section.id}:${c.number}`,odds=baseOdds(c.section),details=familyOdds(c.section);
 return `<tr><td>${esc(c.number)}</td><td>${c.subjects.map(s=>`<span class="card-name">${esc(s.name)}${s.rookie?'<span class="pill">RC</span>':''}</span><span class="team">${esc(s.team||'No team listed')}</span>`).join('')}</td><td><span class="family">${esc(pretty(c.section.name))}</span></td><td><span class="family">${odds?oddsText(odds.odds[f.format]):'Not published'}</span><button class="row-detail" data-key="${esc(key)}" aria-expanded="${expanded.has(key)}">${expanded.has(key)?'Hide':'View'} family details ${expanded.has(key)?'−':'+'}</button></td></tr>${expanded.has(key)?`<tr><td colspan="4" class="detail-cell"><strong>${esc(pretty(c.section.name))} · published family odds</strong><p>These categories apply to the subset. Inclusion of ${esc(c.subjects.map(s=>s.name).join(' / '))} in every parallel is not guaranteed. No individual-card odds or print runs are inferred.</p>${details.length?`<table><thead><tr><th>CATEGORY / PARALLEL</th><th>${esc($('format').selectedOptions[0].text)} PACK ODDS</th></tr></thead><tbody>${details.map(o=>`<tr><td>${esc(o.label?pretty(o.label):pretty(o.name))}</td><td>${oddsText(o.odds[f.format])}</td></tr>`).join('')}</tbody></table>`:'<p>Topps has not published a corresponding odds entry for this section.</p>'}<p>Checklist PDF page ${c.subjects[0].page}. Serial numbering is not provided in these source documents.</p></td></tr>`:''}`;
 }).join('')}</tbody></table></div>`;
 }
}
function change(){page=1;expanded.clear();render();}
function switchView(next){view=next;page=1;expanded.clear();$('cards-tab').setAttribute('aria-selected',next==='cards');$('odds-tab').setAttribute('aria-selected',next==='odds');$('search').placeholder=next==='cards'?'Search a player, card number, team, or subset…':'Search a checklist family or parallel…';render();}
function exportCsv(){const f=readFilters();const rows=view==='cards'?[['Number','Subjects','Teams','Subset','Rookie','Pack format','Category odds','Source page'],...filtered.map(c=>[c.number,c.subjects.map(s=>s.name).join(' / '),c.subjects.map(s=>s.team).join(' / '),c.section.name,c.subjects.some(s=>s.rookie),f.format,baseOdds(c.section)?oddsText(baseOdds(c.section).odds[f.format]):'Not published',c.subjects.map(s=>s.page).join(' / ')])]:[['Checklist family','Category','Pack format','Category odds','Source page'],...filtered.flatMap(g=>g.entries.map(o=>[g.name,o.name,f.format,oddsText(o.odds[f.format]),o.page]))];
 // Neutralize spreadsheet formula prefixes in downloaded text fields.
 const csv=rows.map(r=>r.map(v=>`"${String(v).replace(/^[=+@-]/,"'$&").replace(/"/g,'""')}"`).join(',')).join('\r\n');const url=URL.createObjectURL(new Blob(['\uFEFF'+csv],{type:'text/csv;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download=`${setSlug}-${view}.csv`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
try{
 const res=await fetch(`./data/${setSlug}.json`);if(!res.ok)throw Error(`HTTP ${res.status}`);data=await res.json();
 if(setSlug==='bowman-football-2026'&&!data.title.includes('Bowman Football'))throw Error('Checklist dataset does not match this page');
 oddsGroups=buildOddsGroups();
 if(data.formats){$('format').innerHTML='';data.formats.forEach(f=>$('format').add(new Option(f.name,f.id)));$('format').value='hobby';}
 $('official').href=data.source.product;$('checklist-source').href=data.source.checklist;$('odds-source').href=data.source.odds;
 $('card-total').textContent=data.sections.reduce((n,s)=>n+s.cards.length,0).toLocaleString();
 data.sections.forEach(s=>$('subset').add(new Option(`${pretty(s.name)} (${s.cards.length})`,s.id)));
 const teams=new Set(data.sections.flatMap(s=>s.cards.flatMap(c=>c.subjects.map(s=>s.team||'No team listed'))));[...teams].sort().forEach(t=>$('team').add(new Option(t,t)));
 ['search','subset','team','format','rookie','sort'].forEach(id=>$(id).addEventListener(id==='search'?'input':'change',change));
 $('reset').onclick=()=>{['search','subset','team'].forEach(id=>$(id).value='');$('rookie').checked=false;$('sort').value='checklist';change();};
 $('cards-tab').onclick=()=>switchView('cards');$('odds-tab').onclick=()=>switchView('odds');
 $('previous').onclick=()=>{page--;render();};$('next').onclick=()=>{page++;render();};$('export').onclick=exportCsv;
 $('results').onclick=e=>{const b=e.target.closest('[data-key]');if(!b)return;expanded.has(b.dataset.key)?expanded.delete(b.dataset.key):expanded.add(b.dataset.key);render();};
 document.addEventListener('keydown',e=>{if(e.key==='/'&&!['INPUT','SELECT','TEXTAREA'].includes(document.activeElement.tagName)){e.preventDefault();$('search').focus();}if(e.target.matches('[role=tab]')&&['ArrowLeft','ArrowRight'].includes(e.key)){e.preventDefault();switchView(view==='cards'?'odds':'cards');$(view==='cards'?'cards-tab':'odds-tab').focus();}});
 renderInsights();render();
}catch(e){$('result-count').textContent='Could not load the checklist.';$('results').innerHTML='<div class="error">Serve this folder through an HTTP server to load the data. Reload to retry.</div>';console.error(e);}
