// Run after build_site.mjs. Destination is a checkout of paulfrederiksen.com.
import {cp,mkdir,readFile,writeFile} from 'node:fs/promises';
import {resolve,join} from 'node:path';
const target=process.argv[2];if(!target)throw Error('Usage: node scripts/sync_domain_site.mjs /path/to/domain-repository');
const root=resolve(target);await readFile(join(root,'astro.config.mjs'));
const dest=join(root,'public/checklists');await mkdir(dest,{recursive:true});
await cp('docs',dest,{recursive:true});
// ads.txt must be at the domain root, and preserve any existing seller records.
const record=(await readFile('docs/ads.txt','utf8')).trim();
let existing='';try{existing=await readFile(join(root,'public/ads.txt'),'utf8');}catch(e){if(e.code!=='ENOENT')throw e;}
if(!existing.split(/\r?\n/).includes(record))await writeFile(join(root,'public/ads.txt'),existing.trimEnd()+(existing.trim()?'\n':'')+record+'\n');
console.log('Synced checklist assets and domain-root ads.txt.');
