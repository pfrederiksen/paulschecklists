import {readFile,writeFile} from 'node:fs/promises';
import {reconcileParallels,categoryNumbering} from '../parallel-specs.mjs';
const catalog=JSON.parse(await readFile('data/set-catalog.json','utf8'));
const registry=JSON.parse(await readFile('data/parallel-specifications.json','utf8'));
const audit=[];
for(const set of catalog.sets){let data;try{data=JSON.parse(await readFile(set.tableData??`data/${set.page.replace('.html','.json')}`,'utf8'));}catch{}
 const odds=data?reconcileParallels(data):[];
 const known=odds.filter(o=>!['Not published','Not stated in imported sources'].includes(categoryNumbering({...data,odds},o.name))).length;
 const structured=!!(data?.serialColumn!=null||data?.publishedSpecifications?.length||data?.officialStructure||data?.parallelSpecifications?.length);
 audit.push({slug:set.slug,title:set.title,manufacturer:set.manufacturer,source:set.sourcePage,oddsCategories:(data?.odds??[]).length,numberedOddsCategories:known,supplementalSpecifications:data?.parallelSpecifications?.length??0,structuredNumbering:structured,ongoingSeries:!!set.ongoingSeries,status:!data?'Source import pending':structured?'Numbering evidence imported; exhaustive parallel reconciliation not confirmed':'Supplementary parallel and numbering review pending',conflicts:(registry.conflicts??[]).filter(c=>c.slug===set.slug)});
}
await writeFile('data/parallel-audit.json',JSON.stringify({checked:registry.checked,note:'A source link, search result, or odds PDF does not establish an exhaustive parallel inventory. Pending reviews remain explicit.',sets:audit},null,2)+'\n');
console.log(`Audited ${audit.length} sets; ${audit.filter(s=>s.structuredNumbering).length} have imported numbering/specification evidence. Remaining reviews are recorded.`);
