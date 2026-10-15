import {readFile,mkdir,writeFile} from 'node:fs/promises';
import {setPage,setOverview,setDataStory,researchView,setFacts,setStats,setHero,esc} from '../templates/set-page.mjs';
import {setSEO} from '../templates/seo.mjs';
// These modules mutate/read the same imports. Static imports with top-level
// await can interleave their writes and reads, so complete each phase first.
await import('./apply_parallel_specs.mjs');
await import('./apply_release_dates.mjs');
await import('./audit_parallel_coverage.mjs');
const {research}=await import('./build_research.mjs');
const catalog=JSON.parse(await readFile('data/set-catalog.json','utf8'));
await mkdir('sets',{recursive:true});
for(const config of JSON.parse(await readFile('templates/featured-sets.json','utf8'))){
 const set={...catalog.sets.find(s=>s.page===config.page),description:config.description};
 const data=JSON.parse(await readFile('data/'+config.page.replace('.html','.json'),'utf8'));
 const facts=setFacts(set,data),narrative=setDataStory(set,data);
 await writeFile(config.page,setPage({...config,hero:setHero(set,{featured:true}),stats:setStats(set,data),story:narrative.summary,breakdown:narrative.breakdown,tools:researchView(set,research.get(set.slug)),overview:setOverview(set,{hasCards:facts.hasCards,hasOdds:facts.hasOdds,hasSpecifications:facts.specifications}),seo:setSEO(set,data)}));
}
for(const set of catalog.sets){
 if(!set.page.startsWith('sets/'))continue;
 const data=set.tableData?JSON.parse(await readFile(set.tableData,'utf8')):null;
 const sections=data?[...new Set(data.rows.map(r=>r[data.sectionColumn??0]))]:[];
 const title=esc(set.title),maker=esc(set.manufacturer),year=esc(set.year),sport=esc(set.sport);
 const facts=setFacts(set,data),narrative=setDataStory(set,data);
 const stats=setStats(set,data),hero=setHero(set);

 const links=`<div class="source-links"><a href="${esc(set.checklistUrl)}" target="_blank" rel="noopener">Official checklist ↗</a>${set.oddsUrl?`<a href="${esc(set.oddsUrl)}" target="_blank" rel="noopener">Official odds ↗</a>`:''}${set.verifiedRelease?`<a href="${esc(set.verifiedRelease.url)}" target="_blank" rel="noopener">Official release date ↗</a>`:''}</div>`;
 const originalEvidence=set.catalogEvidence||'Product year and checklist availability are separate from release date.';
 const checklistEvidence=set.verifiedRelease?originalEvidence.replace(/; this is not a verified release date/g,'').replace(/(?:An exact|Exact) (?:calendar )?release date (?:has not been independently verified|is (?:not |un)verified)\./g,'').replace('Exhaustive parallel-numbering coverage and a calendar release date have not been established.','Exhaustive parallel-numbering coverage has not been established.'):originalEvidence;
 const dateEvidence=set.verifiedRelease?`<p>Manufacturer ${set.releaseStatus==='Upcoming'?'scheduled release':'release'}: ${esc(set.releaseDate)} · ${esc(set.verifiedRelease.scope)}. Verified ${esc(set.verifiedRelease.observed)}; scheduled dates may change.</p>`:set.releaseDateGap?`<p>Release-date review: ${esc(set.releaseDateGap.gap)}</p>`:'';
 const sources=`<div><p class="eyebrow">THE DETAILS MATTER</p><h2>Official data.<br>Clear expectations.</h2></div><div><p>“1 in 24 packs” means a card from that category, across all eligible subjects. It is not the chance of pulling a particular player. Serial numbering is a print run, not a pack hit rate.</p><p>Missing values are not estimates. Original manufacturer columns and notes remain available in card details. A listed subject is not guaranteed in every parallel. Imported odds categories alone do not establish an exhaustive parallel inventory.</p><p>${esc(checklistEvidence)}</p>${dateEvidence}${links}</div>`;
 const warning=set.ongoingSeries?'<p class="source-warning"><strong>Partial archive · ongoing series.</strong> The backfill starts January 1, 2026, using verified official sale dates. Entries with unverified dates and unresolved product details remain pending. Product year and season labels are preserved separately. Print runs appear only when Topps publishes them.</p>':set.coverageComplete===false?`<p class="source-warning"><strong>Partial import.</strong> ${esc(set.catalogEvidence)}</p>`:set.releaseStatus==='Upcoming'?'<p class="source-warning">This set is upcoming. Published contents and scheduled release dates may change.</p>':set.releaseStatus==='Released'?'':'<p class="source-warning">Release date has not been verified. Checklist availability does not mean the product has released.</p>';
 const empty=`<div class="empty"><p>${set.sourceUnavailable?'The manufacturer’s checklist link is currently unavailable.':'A verified searchable card import is pending.'} Published data will appear here when verified.</p>${links}</div>`;
 await writeFile(set.page,setPage({story:narrative.summary,breakdown:narrative.breakdown,tools:researchView(set,research.get(set.slug)),oddsUnitsPublished:data?.oddsUnitsPublished!==false,overview:setOverview(set,{oddsUnitsPublished:data?.oddsUnitsPublished!==false,hasCards:facts.hasCards,hasOdds:facts.hasOdds,hasSpecifications:facts.specifications}),page:set.page,title:set.title+" · Paul's Checklists",body:data?`data-table="../${esc(set.tableData)}"`:'',nav:'<a href="../">← All checklists</a>',breadcrumb:`${sport.toUpperCase()} <span>/</span> ${maker.toUpperCase()} <span>/</span> ${year}`,hero,stats,odds:set.odds??'',sources,warning,imported:true,hasData:!!data,empty,seo:setSEO(set,data)}));
}
console.log(`Generated ${catalog.sets.length} pages from the shared Allen & Ginter template.`);
