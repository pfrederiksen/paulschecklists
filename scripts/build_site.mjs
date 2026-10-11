import {mkdir,copyFile,writeFile,cp,readdir} from 'node:fs/promises';
import config from '../ads-config.js';
import {createHash} from 'node:crypto';
await mkdir('docs/data',{recursive:true});
for(const file of ['index.html','allen-ginter-2026.html','bowman-football-2026.html','directory.js','source-page.js','styles.css','app.js','privacy.html','ads.js','ads-config.js'])await copyFile(file,`docs/${file}`);
for(const slug of ['allen-ginter-2026','bowman-football-2026'])await copyFile(`data/${slug}.json`,`docs/data/${slug}.json`);
await cp('sets','docs/sets',{recursive:true});
await cp('data/imports','docs/data/imports',{recursive:true});
await copyFile('data/set-catalog.json','docs/data/set-catalog.json');
await writeFile('docs/.nojekyll','');
// Generate an authorized-seller record only from an actual account identifier.
if(config.publisherId){
 if(!/^ca-pub-\d{16}$/.test(config.publisherId))throw Error('Invalid AdSense publisher ID');
 await writeFile('docs/ads.txt',`google.com, ${config.publisherId.replace('ca-','')}, DIRECT, f08c47fec0942fa0\n`);
}else{
 const {rm}=await import('node:fs/promises');await rm('docs/ads.txt',{force:true});
}
// Bust browser/CDN asset caches whenever shared application code changes.
for(const html of ['index.html','allen-ginter-2026.html','bowman-football-2026.html','privacy.html',...(await readdir('sets')).filter(f=>f.endsWith('.html')).map(f=>'sets/'+f)]){
 const {readFile}=await import('node:fs/promises');let text=await readFile(`docs/${html}`,'utf8');
 for(const asset of ['app.js','directory.js','source-page.js','styles.css','ads.js']){const hash=createHash('sha256').update(await readFile(asset)).digest('hex').slice(0,12);text=text.replaceAll(`"${asset}"`,`"${asset}?v=${hash}"`).replaceAll(`"../${asset}"`,`"../${asset}?v=${hash}"`);}
 await writeFile(`docs/${html}`,text);
}
console.log('Static site packaged in docs/ for GitHub Pages.');
