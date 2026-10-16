import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {reconcileParallels,categoryNumbering,displayQualification} from '../parallel-specs.mjs';
const ag=JSON.parse(await readFile('data/allen-ginter-2026.json'));
assert.equal(categoryNumbering(ag,'BASE CARDS ORANGE FOIL FILAGREE PARALLEL'),'/25');
assert.equal(categoryNumbering(ag,'ALLEN & GINTER AUTOGRAPHED RELIC CARDS ORANGE FOIL FILAGREE PARALLEL'),'Not published');
assert.equal(categoryNumbering(ag,'MINI NON BASEBALL AUTOGRAPH CARDS FRAMED MINI SIZE BLACK FRAME PARALLEL'),'/25');
const data={rows:[['Base'],['Autographs']],odds:[{name:'Base Orange',values:{Hobby:'1:100'}},{name:'Autographs Orange',values:{Hobby:'1:200'}}],publishedSpecifications:[{name:'Base',headers:['Parallel / variation','Published numbering'],rows:[['Orange','/25'],['Rainbow Foil','Not stated']]}]};
data.odds=reconcileParallels(data);
assert.equal(data.odds.length,3);assert.equal(categoryNumbering(data,'Base Orange'),'/25');assert.equal(categoryNumbering(data,'Autographs Orange'),'Not published');assert.equal(data.odds[2].specificationOnly,true);assert.deepEqual(data.odds[2].values,{});
assert.equal(reconcileParallels(data).length,3,'Repeated reconciliation must not duplicate specification-only parallels');
const panini={serialColumn:2,rows:[['Auto','A','10'],['Auto','B','25']]};assert.equal(categoryNumbering(panini,'Auto'),'Varies by card; see official card details');
const repeated={odds:[{name:'Repeated Superfractor',family:'Main program',numbering:'1/1'},{name:'Repeated Superfractor',family:'Unjoined program'}]};assert.equal(categoryNumbering(repeated,'Repeated Superfractor','Main program'),'1/1');assert.equal(categoryNumbering(repeated,'Repeated Superfractor','Unjoined program'),'Not published','Repeated captions must not copy limits between source families');
console.log('Verified official numbering, exact family scopes and specification-only parallels.');

const csv={publishedSpecifications:[{name:'Base Orange',headers:['Card number','Athlete','Published SEQUENCE'],rows:[['1','A','25'],['2','B','25']]}]};assert.equal(categoryNumbering(csv,'Base Orange'),'/25');

const registry=JSON.parse(await readFile('data/parallel-specifications.json'));
const signatureAudit=JSON.parse(await readFile('data/parallel-audit.json')).sets.find(s=>s.slug==='topps-bowman-2025-26-topps-signature-class-basketball');assert.equal(signatureAudit.supplementalSpecifications,79);assert.equal(signatureAudit.numberedOddsCategories,62,'Explicitly non-numbered parallels must not count as numbered categories');assert(signatureAudit.status.includes('not confirmed'));
const holidayAudit=JSON.parse(await readFile('data/parallel-audit.json')).sets.find(s=>s.slug==='topps-bowman-2026-topps-holiday-baseball');assert.equal(holidayAudit.numberedOddsCategories,0,'Guide parallel names with unstated numbering must not count as verified numbering');
const nblAudit=JSON.parse(await readFile('data/parallel-audit.json')).sets.find(s=>s.slug==='topps-bowman-2025-26-topps-nbl-basketball');assert.equal(nblAudit.structuredNumbering,false,'Box contents and store availability do not establish parallel numbering');assert.equal(nblAudit.publishedSpecifications,true);assert(nblAudit.status.includes('incomplete'));
const olympicsAudit=JSON.parse(await readFile('data/parallel-audit.json')).sets.find(s=>s.slug==='topps-bowman-2026-topps-chrome-u-s-winter-olympics-paralympic-team-hopefuls');assert.equal(olympicsAudit.numberedOddsCategories,0,'An unjoined guide limit is not a numbered odds category');assert.equal(olympicsAudit.supplementalSpecifications,1);assert.equal(olympicsAudit.structuredNumbering,true);
const heritage=JSON.parse(await readFile('data/imports/topps-bowman-2026-topps-heritage-football.json'));heritage.odds=reconcileParallels(heritage);assert.equal(categoryNumbering(heritage,'HERITAGE ROOKIE AUTOGRAPHS Gold'),'/50');assert.equal(categoryNumbering(heritage,'REAL ONE ROOKIE AUTOGRAPHS Gold'),'Not published');assert.equal(categoryNumbering(heritage,'CUT SIGNATURES'),'Not published','An unresolved guide example must not number all five cut codes');
for(const conflict of registry.conflicts??[])if(conflict.evidenceFile)assert.equal(createHash('sha256').update(await readFile(conflict.evidenceFile)).digest('hex'),conflict.evidenceSha256,'Conflicting guide evidence must retain its verified hash');
assert(registry.conflicts.some(c=>c.slug==='topps-bowman-2026-topps-chrome-baseball'&&c.family==='GOLD LOGOMAN RELICS'));
assert(!(registry.sets['topps-bowman-2026-topps-chrome-baseball']??[]).some(s=>s.family==='GOLD LOGOMAN RELICS'),'Conflicting Gold Logoman limits must not be selected');
for(const [slug,rows] of Object.entries(registry.sets)){const source=JSON.parse(await readFile(`data/imports/${slug}.json`));const reconciled=reconcileParallels(source);for(const row of rows){const o=reconciled.find(o=>row.oddsName?o.name===row.oddsName:o.specificationKey===row.family+'|'+row.name);assert(o,'Every official specification must appear in its shared parallel view');assert.equal(o.numbering,row.numbering);assert.equal(o.family,row.family);}}
const {specificationRows}=await import('../parallel-specs.mjs');
const leaf={headers:['Card number','Foil','Orange','Quantity','Additions'],rows:[['25','Prismatic',3,25,7]]};assert.deepEqual(specificationRows(leaf),[['25','Prismatic','/3',25,7]]);
assert(registry.conflicts.some(c=>c.slug.includes('exalted')));assert(!registry.sets['topps-bowman-2025-topps-exalted-wwe'].some(s=>s.family==='BASE CARDS'),'Conflicting base limits must not be selected automatically');
console.log('Verified all supplemental mappings, source-scoped limits, original quantities and recorded source conflicts.');

const vault=JSON.parse(await readFile('data/imports/topps-bowman-2026-topps-vault-marvel.json'));vault.odds=reconcileParallels(vault);
assert.equal(categoryNumbering(vault,'True Greatness Black Parallel'),'/10');
assert.equal(categoryNumbering(vault,'True Greatness Autograph Edition Black Parallel'),'Not published','A guide example must not assign numbering to a different autograph family');
assert.equal(categoryNumbering(vault,'Marvel Duos Autographs Base'),'Not published','Unspecified guide parallel numbering must not be assigned to an inferred Base category');
assert.equal(categoryNumbering(vault,'Marvel Diamonds Base'),'/50','Preserve the prior authoritative hobby-guide Silver/base join');
assert.equal(categoryNumbering(vault,'Vault Relics Base'),'/50');
assert.equal(categoryNumbering(vault,'The Vault Autograph Relic Book'),'1/1');

assert.equal(displayQualification('Published for this family; individual-card eligibility is not inferred.'),'');
assert.equal(displayQualification('Published for the named family only; individual-card parallel eligibility is not inferred. Serial numbering is not stated.'),'Serial numbering is not stated.');
assert.equal(displayQualification('Published for this family; individual-card eligibility is not inferred. Guide-only roster; /25 or less.'),'Guide-only roster; /25 or less.');
assert.equal(displayQualification('Only selected subjects; see the official guide.'),'Only selected subjects; see the official guide.');

const helperHash=createHash('sha256').update(await readFile('parallel-specs.mjs')).digest('hex').slice(0,12);for(const asset of ['source-page.js','research.js'])assert((await readFile('docs/'+asset,'utf8')).includes('./parallel-specs.mjs?v='+helperHash),'Both shared views must load the current numbering helper');
