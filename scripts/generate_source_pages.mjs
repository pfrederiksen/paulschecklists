import {readFile,mkdir,writeFile} from 'node:fs/promises';
import {setPage,esc} from '../templates/set-page.mjs';
const catalog=JSON.parse(await readFile('data/set-catalog.json','utf8'));
await mkdir('sets',{recursive:true});
for(const config of JSON.parse(await readFile('templates/featured-sets.json','utf8')))await writeFile(config.page,setPage(config));
for(const set of catalog.sets){
 if(!set.page.startsWith('sets/'))continue;
 const data=set.tableData?JSON.parse(await readFile(set.tableData,'utf8')):null;
 const sections=data?[...new Set(data.rows.map(r=>r[data.sectionColumn??0]))]:[];
 const title=esc(set.title),maker=esc(set.manufacturer),year=esc(set.year),sport=esc(set.sport);
 const artTitle=title.replace(/^\d{4}(?:-\d{2})?\s*/, '');
 const stats=`<div><strong>${set.rowCount?.toLocaleString()??'Pending'}</strong><span>CHECKLIST SOURCE ROWS</span></div><div><strong>${sections.length||'—'}</strong><span>CHECKLIST SECTIONS</span></div><div><strong>${set.odds??(set.publishedOdds?'Listed':'—')}</strong><span>PUBLISHED ODDS ENTRIES</span></div><div class="verified"><span class="dot"></span><div><strong>Direct from ${maker}</strong><span>CHECKED ${esc(catalog.verified)}</span></div></div>`;
 const hero=`<div><p class="eyebrow"><span class="dot"></span> OFFICIAL CHECKLIST · ${year} EDITION</p><h1>${title}<span>Every card. Every chase.</span></h1><p class="intro">Explore the official ${maker} checklist.<br>Find cards, parallels and published pack odds.</p><div class="hero-links"><a href="#explore">Explore the checklist ↓</a><a href="${esc(set.sourcePage)}" target="_blank" rel="noopener">Official ${maker} sources ↗</a></div></div><div class="set-art" aria-hidden="true"><div class="paper-card back-card"></div><div class="paper-card front-card"><div class="ornament">✦</div><div class="card-top">${maker} · ${year}</div><div class="card-word">${artTitle}</div><div class="card-rule"></div><div class="card-bottom">${sport}</div><div class="art-ball">✦</div><div class="card-bottom">THE COLLECTION</div></div><span class="art-caption">THE ${year} COLLECTION</span></div>`;
 const links=`<div class="source-links"><a href="${esc(set.checklistUrl)}" target="_blank" rel="noopener">Official checklist ↗</a>${set.oddsUrl?`<a href="${esc(set.oddsUrl)}" target="_blank" rel="noopener">Official odds ↗</a>`:''}</div>`;
 const sources=`<div><p class="eyebrow">THE DETAILS MATTER</p><h2>Official data.<br>Clear expectations.</h2></div><div><p>“1 in 24 packs” means a card from that category, across all eligible subjects. It is not the chance of pulling a particular player. Serial numbering is a print run, not a pack hit rate.</p><p>Missing values are not estimates. Original manufacturer columns and notes remain available in card details. A listed subject is not guaranteed in every parallel.</p><p>${esc(set.catalogEvidence||'Product year and checklist availability are separate from release date.')}</p>${links}</div>`;
 const warning=set.releaseStatus==='Released'?'': '<p class="source-warning">Release date has not been verified. Checklist availability does not mean the product has released.</p>';
 const empty=`<section id="explore"><h2>The checklist</h2><p>${set.sourceUnavailable?'The manufacturer’s checklist link is currently unavailable.':'A verified searchable card import is pending.'} Published data will appear here when verified.</p>${links}</section>`;
 await writeFile(set.page,setPage({page:set.page,title:set.title+" · Paul's Checklists",body:data?`data-table="../${esc(set.tableData)}"`:'',nav:'<a href="../">← All checklists</a>',breadcrumb:`${sport.toUpperCase()} <span>/</span> ${maker.toUpperCase()} <span>/</span> ${year}`,hero,stats,odds:set.odds??'',sources,warning,imported:true,hasData:!!data,empty}));
}
console.log(`Generated ${catalog.sets.length} pages from the shared Allen & Ginter template.`);
