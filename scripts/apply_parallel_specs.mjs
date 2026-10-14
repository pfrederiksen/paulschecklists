import {readFile,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
const catalog=JSON.parse(await readFile('data/set-catalog.json','utf8'));
let registry={sets:{}};try{registry=JSON.parse(await readFile('data/parallel-specifications.json','utf8'));}catch{}
for(const set of catalog.sets){const additions=registry.sets[set.slug];if(!additions)continue;
 const path=set.tableData??`data/${set.page.replace('.html','.json')}`;const data=JSON.parse(await readFile(path,'utf8'));
 for(const entry of additions){const blob=await readFile(entry.evidenceFile);if(createHash('sha256').update(blob).digest('hex')!==entry.evidenceSha256)throw Error('Changed specification evidence: '+entry.evidenceFile);if(entry.oddsName&&!data.odds?.some(o=>o.name===entry.oddsName))throw Error('Missing exact odds mapping: '+entry.oddsName);}
 data.parallelSpecifications=additions;
 // Featured datasets retain their original group IDs and PDF odds counts.
 if(data.sections)for(const entry of additions){if(entry.oddsName){const odd=data.odds.find(o=>o.name===entry.oddsName);odd.numbering=entry.numbering;odd.numberingSource={url:entry.source,qualification:entry.qualification};}}
 await writeFile(path,JSON.stringify(data,null,data.sections?2:undefined)+'\n');
}
