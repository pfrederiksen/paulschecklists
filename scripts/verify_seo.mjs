import assert from 'node:assert/strict';
import {readFile,stat} from 'node:fs/promises';
const base='https://paulfrederiksen.com/checklists/';
const catalog=JSON.parse(await readFile('data/set-catalog.json','utf8'));
const directory=await readFile('docs/index.html','utf8');
const sitemap=await readFile('docs/sitemap.xml','utf8');
const titles=new Set(),descriptions=new Set();let bytes=0;
for(const page of ['index.html',...catalog.sets.map(s=>s.page)]){
 const html=await readFile('docs/'+page,'utf8');const url=base+(page==='index.html'?'':page);
 assert(!html.includes('\0'),'Generated HTML contains NUL bytes: '+page);
 assert.equal((html.match(/rel="canonical"/g)||[]).length,1);assert(html.includes(`rel="canonical" href="${url}"`));
 const title=html.match(/<title>(.*?)<\/title>/s)?.[1];assert(title&&!titles.has(title),page+' title');titles.add(title);
 const description=html.match(/<meta name="description" content="([^"]+)"/s)?.[1];assert(description&&!descriptions.has(description),page+' description');descriptions.add(description);
 assert.equal((html.match(/<meta name="description"/g)||[]).length,1);
 assert(html.includes(`property="og:url" content="${url}"`));assert(html.includes('name="twitter:card"'));assert(!/noindex/.test(html));assert.equal((html.match(/<h1[ >]/g)||[]).length,1);
 const schema=JSON.parse(html.match(/<script type="application\/ld\+json">(.*?)<\/script>/s)[1]);assert.equal(schema['@context'],'https://schema.org');
 assert(sitemap.includes(`<loc>${url}</loc>`));
 if(page!=='index.html'){
  assert(directory.includes(`href="${page}"`),'Missing crawlable link '+page);assert(schema['@graph'].some(s=>s['@type']==='BreadcrumbList'));
  const set=catalog.sets.find(s=>s.page===page);if(set.tableData||set.status==='Searchable')assert(html.includes('Browse the official checklist')&&html.includes('<details><summary>'),'Missing static checklist '+page);
  if(set.tableData){const data=JSON.parse(await readFile(set.tableData,'utf8'));const nameColumn=data.headers?.findIndex(h=>/^name$/i.test(h))??-1;if(nameColumn>=0){const names=data.rows.map(r=>r[nameColumn]).filter(Boolean);const staticHTML=html.slice(html.indexOf('<section class="static-checklist"'));const escape=v=>String(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));for(const name of [...names.slice(0,3),...names.slice(-3)])assert(staticHTML.includes(escape(name)),'Missing crawlable published name '+page+': '+name);}}
 }
 bytes+=(await stat('docs/'+page)).size;
}
assert.equal((sitemap.match(/<loc>/g)||[]).length,catalog.sets.length+1);
assert((await readFile('docs/robots.txt','utf8')).includes(base+'sitemap.xml'));
console.log(`Verified ${catalog.sets.length+1} unique titles/descriptions, canonicals, social metadata, JSON-LD, sitemap URLs and crawlable checklist content (${(bytes/1e6).toFixed(1)} MB total HTML).`);
