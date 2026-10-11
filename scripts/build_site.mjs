import {mkdir,copyFile,writeFile} from 'node:fs/promises';
import config from '../ads-config.js';
await mkdir('docs/data',{recursive:true});
for(const file of ['index.html','allen-ginter-2026.html','bowman-football-2026.html','directory.js','styles.css','app.js','privacy.html','ads.js','ads-config.js'])await copyFile(file,`docs/${file}`);
for(const slug of ['allen-ginter-2026','bowman-football-2026'])await copyFile(`data/${slug}.json`,`docs/data/${slug}.json`);
await writeFile('docs/.nojekyll','');
// Generate an authorized-seller record only from an actual account identifier.
if(config.publisherId){
 if(!/^ca-pub-\d{16}$/.test(config.publisherId))throw Error('Invalid AdSense publisher ID');
 await writeFile('docs/ads.txt',`google.com, ${config.publisherId.replace('ca-','')}, DIRECT, f08c47fec0942fa0\n`);
}else{
 const {rm}=await import('node:fs/promises');await rm('docs/ads.txt',{force:true});
}
console.log('Static site packaged in docs/ for GitHub Pages.');
