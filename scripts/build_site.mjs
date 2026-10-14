import {mkdir,copyFile,writeFile,cp,readdir} from 'node:fs/promises';
import {readFile} from 'node:fs/promises';
import {base,directorySEO,directoryLinks} from '../templates/seo.mjs';
import config from '../ads-config.js';
import {createHash} from 'node:crypto';
await mkdir('docs/data',{recursive:true});
for(const file of ['index.html','allen-ginter-2026.html','bowman-football-2026.html','directory.js','research.js','source-page.js','parallel-specs.mjs','styles.css','app.js','privacy.html','ads.js','ads-config.js'])await copyFile(file,`docs/${file}`);
for(const slug of ['allen-ginter-2026','bowman-football-2026'])await copyFile(`data/${slug}.json`,`docs/data/${slug}.json`);
await cp('sets','docs/sets',{recursive:true});
await cp('data/imports','docs/data/imports',{recursive:true});
await cp('data/research','docs/data/research',{recursive:true});
await copyFile('data/player-index.json','docs/data/player-index.json');
await copyFile('data/set-catalog.json','docs/data/set-catalog.json');
const parallelHash=createHash('sha256').update(await readFile('parallel-specs.mjs')).digest('hex').slice(0,12);
await writeFile('docs/source-page.js',(await readFile('source-page.js','utf8')).replace('./parallel-specs.mjs',`./parallel-specs.mjs?v=${parallelHash}`));
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
 for(const asset of ['app.js','directory.js','research.js','source-page.js','parallel-specs.mjs','styles.css','ads.js']){const hash=createHash('sha256').update(await readFile(asset)).update(asset==='source-page.js'?parallelHash:'').digest('hex').slice(0,12);text=text.replaceAll(`"${asset}"`,`"${asset}?v=${hash}"`).replaceAll(`"../${asset}"`,`"../${asset}?v=${hash}"`);}
 await writeFile(`docs/${html}`,text);
}
console.log('Static site packaged in docs/ for GitHub Pages.');

const catalog=JSON.parse(await readFile('data/set-catalog.json','utf8'));
let directory=await readFile('docs/index.html','utf8');
directory=directory.replace('<title>Paul’s Checklists · Sports Card Checklists</title>','<title>Sports Card Checklists, Parallels &amp; Pack Odds | Paul’s Checklists</title>').replace(/<meta name="description"[^>]*>/,'').replace('</head>',directorySEO(catalog.sets)+'</head>').replace('</main>',directoryLinks(catalog.sets)+'</main>');
const directorySets=catalog.sets.filter(s=>!s.ongoingSeries||s.slug==='topps-now-2026');
directory=directory.replace('id="catalog-total">2<',`id="catalog-total">${directorySets.length}<`).replace('id="catalog-searchable">2<',`id="catalog-searchable">${directorySets.filter(s=>s.status==='Searchable'||(s.tableData&&s.rosterPublished!==false)).length}<`);
await writeFile('docs/index.html',directory);
const urls=[base,...catalog.sets.map(s=>base+s.page)];
await writeFile('docs/sitemap.xml','<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+urls.map(url=>'<url><loc>'+url+'</loc></url>').join('')+'</urlset>');
await writeFile('docs/robots.txt',`User-agent: *\nAllow: /\nSitemap: ${base}sitemap.xml\n`);
