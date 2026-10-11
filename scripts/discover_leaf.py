"""Discover official Leaf sports product checklist links from its public sitemap."""
import concurrent.futures,json,re,html,urllib.request,xml.etree.ElementTree as E,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def get(url):return urllib.request.urlopen(url,timeout=30).read()
def discover(url):
 try:
  blob=get(url);s=blob.decode();heading=re.search(r'<h1[^>]*>(.*?)</h1>',s,re.S)
  if not heading:return None
  title=html.unescape(re.sub('<[^>]*>','',heading[1]));meta=s[max(0,heading.start()-650):heading.start()];category=re.findall(r'class="ds-form-label uppercase">([^<]+)',meta)
  if not category or category[0].lower() not in {'baseball','football','basketball','hockey','soccer','tennis','multi-sport','boxing','mma','golf','wrestling'}:return None
  docs=[html.unescape(u) for u in re.findall(r'href="([^"]+\.(?:xlsx|xls|pdf|csv)(?:\?[^"]*)?)"',s,re.I)]
  if not docs:return None
  slug='leaf-'+re.sub('[^a-z0-9]+','-',title.lower()).strip('-');badge=re.search(r'class="ds-badge"><div>([^<]+)',s[heading.start():heading.start()+1000]);status=badge[1] if badge else ''
  return {'title':title,'manufacturer':'Leaf','sport':category[0].lower(),'year':re.search('20\d\d',title).group(),'sourcePage':url,'checklistUrl':docs[0],'documentUrls':list(dict.fromkeys(docs)),'releaseStatus':'Released' if status=='RELEASED' else 'Upcoming' if status in ['COMING SOON','PRE-ORDER','UPCOMING'] else 'Unverified','releaseDate':None,'catalogEvidence':f'Official product page labels the product {status or "without a release status"}. Exact calendar release date is not verified.','sourcePageSha256':hashlib.sha256(blob).hexdigest(),'slug':slug,'page':'sets/'+slug+'.html','verified':'2026-10-11','status':'Official source'}
 except Exception as e:print('Discovery failed',url,str(e));return None
if __name__=='__main__':
 previous=json.loads((ROOT/'data/leaf-official-catalog.json').read_text());urls=[e[0].text for e in E.fromstring(get('https://www.leaftradingcards.com/sitemap.xml')) if '/products/' in e[0].text and '2026' in e[0].text]
 with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:fresh=[r for r in pool.map(discover,urls) if r]
 records={r['slug']:r for r in previous};records.update({r['slug']:r for r in fresh});(ROOT/'data/leaf-official-catalog.json').write_text(json.dumps(list(records.values()),ensure_ascii=False,indent=2)+'\n');print('Leaf verified sports checklist sources:',len(records))
