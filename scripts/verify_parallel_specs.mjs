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
