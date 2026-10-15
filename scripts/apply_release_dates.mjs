import {readFile,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import assert from 'node:assert/strict';

// Apply independently verified release evidence after dedicated import refreshes.
// These observations never change card rows, source hashes, or product-year labels.
const path='data/release-dates.json';
const registry=JSON.parse(await readFile(path,'utf8'));
const catalog=JSON.parse(await readFile('data/set-catalog.json','utf8'));
const bySlug=new Map(catalog.sets.map(s=>[s.slug,s]));
const stable=value=>JSON.stringify(value,Object.keys(value).sort());
const seen=new Set();
for(const entry of registry.dates){
 assert(!seen.has(entry.slug),'Duplicate release-date mapping');seen.add(entry.slug);
 const set=bySlug.get(entry.slug),source=registry.sources[entry.source];
 assert(set&&source,'Release evidence must identify an existing exact set');
 assert(!set.ongoingSeries,'NOW sale dates remain card-specific');
 assert(/^\d{4}-\d{2}-\d{2}$/.test(entry.releaseDate)&&new Date(entry.releaseDate).toISOString().slice(0,10)===entry.releaseDate);
 assert(['Released','Upcoming'].includes(entry.releaseStatus));
 const {sha256,...snapshot}=source;
 assert.equal(createHash('sha256').update(stable(snapshot)).digest('hex'),sha256,'Release snapshot hash mismatch');
 assert(new URL(source.url).protocol==='https:');
 set.releaseDate=entry.releaseDate;set.releaseStatus=entry.releaseStatus;
 set.verifiedRelease={...source,snapshotFile:path};
 delete set.releaseDateGap;
}
for(const pending of registry.unresolved){
 const set=bySlug.get(pending.slug);assert(set);
 assert(!seen.has(pending.slug),'Conflicting dates must not be imported');
 set.releaseDateGap={gap:pending.gap,sources:pending.sources,observed:registry.observed};
}
await writeFile('data/set-catalog.json',JSON.stringify(catalog,null,2)+'\n');
const audit={observed:registry.observed,note:'Official release dates only. Product year, checklist publication, preorder starts, regional availability and e-Pack launches are separate. Unreviewed sets remain pending.',
 sets:catalog.sets.map(set=>({slug:set.slug,title:set.title,manufacturer:set.manufacturer,releaseDate:set.releaseDate??null,
  status:set.ongoingSeries?'Card-specific sale dates':set.verifiedRelease?'Explicit official release statement verified':set.releaseDate?'Existing dated release; original source retained':'Exact release-date research pending',
  ...(set.verifiedRelease?{source:set.verifiedRelease.url}:{}),...(set.releaseDateGap?{gap:set.releaseDateGap.gap}:{})}))};
await writeFile('data/release-date-audit.json',JSON.stringify(audit,null,2)+'\n');
console.log(`Applied ${seen.size} hash-checked official release dates; unresolved date research remains explicit.`);
