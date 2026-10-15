"""Refresh the official current checklist directory; preserve existing imports.
The directory is a discovery window, not proof of an exhaustive release calendar.
"""
import hashlib,html,json,re,urllib.parse,subprocess
from datetime import date
from pathlib import Path
from import_official_catalog import run
ROOT=Path(__file__).resolve().parents[1]
URL='https://upperdeck.com/checklists/'
def read(url):
 return subprocess.run(['curl','-sLf','--retry','2','--max-time','45',url],capture_output=True,check=True).stdout
def refresh():
 blob=read(URL);text=blob.decode()
 inventory_path=ROOT/'data/upperdeck-official-catalog.json'
 inventory=json.loads(inventory_path.read_text())
 known={r['sourcePage'] for r in inventory}
 urls=list(dict.fromkeys(urllib.parse.urljoin(URL,html.unescape(u)) for u in re.findall(r'href=["\']([^"\']+/checklist/[^"\']+)["\']',text)))
 catalog_path=ROOT/'data/set-catalog.json';catalog=json.loads(catalog_path.read_text());added=[]
 for url in urls:
  if url in known:continue
  source=read(url);page=source.decode();heading=re.search(r'<h1[^>]*>(.*?)</h1>',page,re.S)
  if not heading:raise ValueError('Missing official checklist heading: '+url)
  title=html.unescape(re.sub('<[^>]+>',' ',heading[1])).strip().removesuffix(' Checklist')
  year=re.search(r'20\d\d(?:[-/]\d{2,4})?',title)
  if not year:continue
  published=re.search(r'"datePublished":"([^"]+)"',page)
  if not published or not published[1].startswith('2026-'):continue
  # Categories are the manufacturer's published post classes, never inferred teams.
  categories=re.findall(r'checklist-category-([a-z-]+)',page)
  sport=next((s for s in categories if s!='entertainment'),'entertainment')
  slug='upper-deck-'+re.sub('[^a-z0-9]+','-',title.lower()).strip('-')
  record={'title':title,'manufacturer':'Upper Deck','sport':sport,'year':year[0],
   'sourcePage':url,'checklistUrl':url,'checklistPublished':published[1][:10],'releaseStatus':'Unverified','releaseDate':None,
   'slug':slug,'page':'sets/'+slug+'.html','verified':date.today().isoformat(),'status':'Official source',
   'catalogEvidence':'Listed in the manufacturer’s current checklist directory. Product year is printed in the checklist title; an exact calendar release date is not verified.',
   'discoverySource':URL,'discoverySha256':hashlib.sha256(blob).hexdigest()}
  cache=ROOT/'data/catalog-sources/downloads'/f'{slug}.html';cache.parent.mkdir(exist_ok=True,parents=True);cache.write_bytes(source);cache.with_suffix('.html.url').write_text(url)
  imported=run(dict(record))
  if imported.get('tableData'):
   archive=ROOT/'data/official-upperdeck'/f'{slug}.html';archive.parent.mkdir(exist_ok=True,parents=True);archive.write_bytes(source)
   data_path=ROOT/imported['tableData'];data=json.loads(data_path.read_text());data['sourceExport']=str(archive.relative_to(ROOT));data_path.write_text(json.dumps(data,ensure_ascii=False)+'\n')
  inventory.append(record);catalog['sets'].append(imported);added.append(imported)
 inventory_path.write_text(json.dumps(inventory,ensure_ascii=False,indent=2)+'\n')
 catalog_path.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
 (ROOT/'data/catalog-sources/upperdeck-current-directory.html').write_bytes(blob)
 print('New official current-directory checklists:',len(added))
if __name__=='__main__':refresh()
