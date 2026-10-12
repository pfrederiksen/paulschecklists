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
  catalog_year=re.findall(r'class="ds-form-label">(20\d\d)</div>',meta)
  if not catalog_year or catalog_year[0]!='2026':return None
  if not category or category[0].lower() not in {'baseball','football','basketball','hockey','soccer','tennis','multi-sport','boxing','mma','golf','wrestling'}:return None
  docs=[html.unescape(u) for u in re.findall(r'href="([^"]+\.(?:xlsx|xls|pdf|csv)(?:\?[^"]*)?)"',s,re.I)]
  if not docs:return None
  slug='leaf-'+re.sub('[^a-z0-9]+','-',title.lower()).strip('-');badge=re.search(r'class="ds-badge"><div>([^<]+)',s[heading.start():heading.start()+1000]);status=badge[1] if badge else ''
  return {'title':title,'manufacturer':'Leaf','sport':category[0].lower(),'year':re.search(r'20\d\d(?:[-/]\d{2,4})?',title).group(),'sourcePage':url,'checklistUrl':docs[0],'documentUrls':list(dict.fromkeys(docs)),'releaseStatus':'Released' if status=='RELEASED' else 'Upcoming' if status in ['COMING SOON','PRE-ORDER','UPCOMING'] else 'Unverified','releaseDate':None,'catalogEvidence':f'Official product page labels the product {status or "without a release status"}. Listed under the manufacturer’s 2026 product-page category; product year and exact calendar release date are separate. Exact release date is not verified.'+(' The official linked workbook filename is marked Working; published contents may be revised.' if 'working' in docs[0].lower() else ''),'sourcePageSha256':hashlib.sha256(blob).hexdigest(),'slug':slug,'page':'sets/'+slug+'.html','verified':'2026-10-11','status':'Official source'}
 except Exception as e:print('Discovery failed',url,str(e));return None
if __name__=='__main__':
 previous=json.loads((ROOT/'data/leaf-official-catalog.json').read_text());urls=[e[0].text for e in E.fromstring(get('https://www.leaftradingcards.com/sitemap.xml')) if '/products/' in e[0].text]
 with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:fresh=[r for r in pool.map(discover,urls) if r]
 records={r['slug']:r for r in previous};records.update({r['slug']:r for r in fresh});(ROOT/'data/leaf-official-catalog.json').write_text(json.dumps(list(records.values()),ensure_ascii=False,indent=2)+'\n');print('Leaf verified sports checklist sources:',len(records))
