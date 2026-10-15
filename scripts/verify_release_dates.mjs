import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {compareSets,hasCards} from '../catalog-model.mjs';
const registry=JSON.parse(await readFile('data/release-dates.json','utf8'));
const catalog=JSON.parse(await readFile('data/set-catalog.json','utf8'));
const deployed=JSON.parse(await readFile('docs/data/set-catalog.json','utf8'));
const audit=JSON.parse(await readFile('data/release-date-audit.json','utf8'));
assert.equal(audit.sets.length,catalog.sets.length);
for(const set of catalog.sets){
 const html=await readFile('docs/'+set.page,'utf8');
 assert(!html.includes('<a href=""'),set.slug+': empty provenance link');
 assert(!html.includes(' · . Verified ;'),set.slug+': missing provenance fields');
}
for(const entry of registry.dates){
 const set=catalog.sets.find(s=>s.slug===entry.slug),live=deployed.sets.find(s=>s.slug===entry.slug),source=registry.sources[entry.source];
 const {sha256,...snapshot}=source;
 assert.equal(createHash('sha256').update(JSON.stringify(snapshot,Object.keys(snapshot).sort())).digest('hex'),sha256);
 assert(['ripped.topps.com','www.topps.com','upperdeck.com'].includes(new URL(source.url).hostname));
 assert.equal(set.releaseDate,entry.releaseDate);assert.equal(set.releaseStatus,entry.releaseStatus);
 assert.deepEqual(set.verifiedRelease,{...source,snapshotFile:'data/release-dates.json'});
 assert.equal(live.releaseDate,set.releaseDate);assert.deepEqual(live.verifiedRelease,set.verifiedRelease);
 assert.equal(audit.sets.find(s=>s.slug===set.slug).source,source.url);
 const html=await readFile('docs/'+set.page,'utf8');
 assert(html.includes(set.releaseDate)&&html.includes('Official release date ↗')&&html.includes(source.url));
 assert(!html.includes('Release date has not been verified. Checklist availability does not mean the product has released.'));
 if(set.releaseStatus==='Upcoming')assert(html.includes('Upcoming')&&html.includes('scheduled release'));
}
const by=slug=>catalog.sets.find(s=>s.slug===slug);
assert.equal(by('topps-bowman-2025-star-wars-masterwork').releaseDate,'2026-06-03','Product year 2025 remains separate from the official 2026 release');
const masterworkHtml=await readFile('docs/'+by('topps-bowman-2025-star-wars-masterwork').page,'utf8');
assert(masterworkHtml.includes('Exhaustive parallel-numbering coverage has not been established.'));
assert(!masterworkHtml.includes('and a calendar release date have not been established'),'Release evidence must not erase the separate parallel audit gap');
assert.equal(by('topps-bowman-2026-topps-stadium-club-wwe').releaseDate,'2026-10-23');
assert.equal(by('topps-bowman-2026-topps-stadium-club-wwe').releaseStatus,'Upcoming');
assert.equal(by('topps-bowman-2026-topps-chrome-disney').releaseDate,'2026-06-17');
assert.equal(by('topps-bowman-2026-topps-chrome-ufc').releaseDate,'2026-05-08');
for(const slug of ['topps-bowman-2026-topps-chrome-disney-sapphire-edition','topps-bowman-2026-topps-chrome-ufc-sapphire-edition'])assert.equal(by(slug).releaseDate,null,'Regular Chrome dates do not establish Sapphire dates');
assert.equal(by('topps-bowman-2026-topps-chrome-tennis').releaseDate,'2026-09-30','Presale September 1 is not release day');
assert.equal(by('topps-bowman-2026-topps-museum-collection-baseball').releaseDate,'2026-11-11');
assert.equal(by('topps-bowman-2026-topps-museum-collection-baseball').releaseStatus,'Upcoming');
assert.equal(by('topps-bowman-2026-bowman-baseball').releaseDate,null,'Conflicting official dates remain unresolved');
assert(by('topps-bowman-2026-bowman-baseball').releaseDateGap.gap.includes('May 6 versus May 13'));
for(const slug of ['topps-bowman-2026-bowman-chrome-baseball-mega-box','topps-bowman-2026-bowman-chrome-baseball-sapphire-edition','topps-bowman-2026-topps-chrome-marvel-comics-sapphire-edition'])assert.equal(by(slug).releaseDate,null,'Dates must not propagate to other variants');
for(const set of catalog.sets.filter(s=>s.ongoingSeries))assert.equal(set.releaseDate,null,'NOW dates belong to individual cards');
const sorted=catalog.sets.filter(s=>(!s.ongoingSeries||s.slug==='topps-now-2026')&&hasCards(s)).toSorted(compareSets);
const latest=sorted[0];assert.equal(latest.releaseStatus,'Released');assert(sorted.every(s=>s.releaseStatus!=='Released'||!s.releaseDate||s.releaseDate<=latest.releaseDate));
const html=await readFile('docs/index.html','utf8');assert.equal([...html.matchAll(/<h3><a href="([^"]+)"/g)][0][1],latest.page);
console.log(`Verified ${registry.dates.length} exact-set official release statements, snapshot hashes, shared source links, scheduled dates, conflicts and newest-release directory order.`);
