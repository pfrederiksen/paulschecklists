import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {reconcileParallels,categoryNumbering} from '../parallel-specs.mjs';
const ag=JSON.parse(await readFile('data/allen-ginter-2026.json'));
assert.equal(categoryNumbering(ag,'BASE CARDS ORANGE FOIL FILAGREE PARALLEL'),'/25');
assert.equal(categoryNumbering(ag,'ALLEN & GINTER AUTOGRAPHED RELIC CARDS ORANGE FOIL FILAGREE PARALLEL'),'Not published');
assert.equal(categoryNumbering(ag,'MINI NON BASEBALL AUTOGRAPH CARDS FRAMED MINI SIZE BLACK FRAME PARALLEL'),'/25');
const data={rows:[['Base'],['Autographs']],odds:[{name:'Base Orange',values:{Hobby:'1:100'}},{name:'Autographs Orange',values:{Hobby:'1:200'}}],publishedSpecifications:[{name:'Base',headers:['Parallel / variation','Published numbering'],rows:[['Orange','/25'],['Rainbow Foil','Not stated']]}]};
data.odds=reconcileParallels(data);
assert.equal(data.odds.length,3);assert.equal(categoryNumbering(data,'Base Orange'),'/25');assert.equal(categoryNumbering(data,'Autographs Orange'),'Not published');assert.equal(data.odds[2].specificationOnly,true);assert.deepEqual(data.odds[2].values,{});
assert.equal(reconcileParallels(data).length,3,'Repeated reconciliation must not duplicate specification-only parallels');
const panini={serialColumn:2,rows:[['Auto','A','10'],['Auto','B','25']]};assert.equal(categoryNumbering(panini,'Auto'),'Varies by card; see official card details');
console.log('Verified official numbering, exact family scopes and specification-only parallels.');

const csv={publishedSpecifications:[{name:'Base Orange',headers:['Card number','Athlete','Published SEQUENCE'],rows:[['1','A','25'],['2','B','25']]}]};assert.equal(categoryNumbering(csv,'Base Orange'),'/25');

const registry=JSON.parse(await readFile('data/parallel-specifications.json'));
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
