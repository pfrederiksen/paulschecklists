const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export const hasCards=s=>s.status==='Searchable'||(!!s.tableData&&s.rosterPublished!==false);
export const hasOdds=s=>!!s.odds||!!s.publishedOdds;
export const categoryLabel=s=>String(s).split('-').map(word=>({ufc:'UFC',wwe:'WWE',dc:'DC'})[word.toLowerCase()]||word.charAt(0).toUpperCase()+word.slice(1)).join(' ');
export const normalizeSearch=value=>String(value??'').normalize('NFKD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/[^a-z0-9]+/g,' ').trim();
export const matchesSet=(set,query)=>{const text=normalizeSearch(`${set.title} ${set.manufacturer} ${set.sport} ${set.year}`);return normalizeSearch(query).split(/\s+/).every(term=>text.includes(term));};
const releaseDate=s=>{
 const date=s.releaseDate??'',time=Date.parse(date);
 return /^\d{4}-\d{2}-\d{2}$/.test(date)&&Number.isFinite(time)&&new Date(time).toISOString().slice(0,10)===date?date:'';
};
export function compareSets(a,b,mode='released'){
 if(mode==='name')return a.title.localeCompare(b.title);
 if(mode==='sport')return a.sport.localeCompare(b.sport)||a.title.localeCompare(b.title);
 if(mode==='data'){
  const rank=s=>s.status==='Searchable'?5:hasCards(s)?hasOdds(s)?4:s.parallelData?3:2:s.tableData?1:0;
  return rank(b)-rank(a)||a.title.localeCompare(b.title);
 }
 const rank=s=>s.releaseStatus==='Released'?(releaseDate(s)?0:1):s.releaseStatus==='Upcoming'?3:2;
 return rank(a)-rank(b)||(rank(a)===0?releaseDate(b).localeCompare(releaseDate(a)):0)||a.title.localeCompare(b.title);
}
export function renderCatalogRow(s){
 const entries=s.presentation?.rows??s.rowCount;
 const unit=s.presentation?.unit??'source rows';
 const sections=s.presentation?.sections??s.sections;
 const formats=s.presentation?.formats??s.formats;
 const availability=s.ongoingSeries?'Partial archive':s.coverageComplete===false?'Partial checklist':hasCards(s)&&hasOdds(s)?'Cards + published odds':s.rosterPublished===false?'Specifications only':hasCards(s)?'Searchable cards':'Official link only';
 const release=s.ongoingSeries?'Ongoing series':s.releaseStatus==='Released'?`Released · ${releaseDate(s)||'date unverified'}`:s.releaseStatus==='Upcoming'?`Upcoming${s.releaseDate?' · '+s.releaseDate:''}`:'Release date unverified';
 const detail=hasOdds(s)?s.odds?`${s.odds} categories · ${formats>0?`${formats} ${formats===1?'format':'formats'}`:'format not named'}`:'Odds in card table':s.ongoingSeries?'Made to order · no pack odds':s.parallelData?'Parallel specifications':'Pack odds unavailable';
 return `<article class="catalog-row"><div class="catalog-set"><div><h3><a href="${esc(s.page)}">${esc(s.title)}</a></h3><p>${esc(s.manufacturer)} · ${esc(release)}</p></div></div><div class="catalog-meta"><span>${esc(categoryLabel(s.sport))}</span><small title="Product year / season">${esc(s.year)}</small></div><div class="catalog-metric"><strong>${entries?.toLocaleString()??'—'}</strong><small>${entries==null?'Import pending':esc(unit)}${sections?` · ${sections} sections`:''}</small></div><div class="catalog-metric"><span class="data-badge ${hasCards(s)&&hasOdds(s)?'with-odds':''}">${esc(availability)}</span><small>${esc(detail)}</small></div><a class="catalog-open" href="${esc(s.page)}" aria-label="Open ${esc(s.title)}">Open ↗</a></article>`;
}
