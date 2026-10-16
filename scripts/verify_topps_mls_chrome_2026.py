"""Independently compare MLS text objects, paired ID boxes and all odds cells."""
import collections,hashlib,json,re,unicodedata
from pathlib import Path
from pypdf import PdfReader
import pdfplumber
ROOT=Path(__file__).resolve().parents[1];SLUG='topps-bowman-topps-chrome-major-league-soccer-2026'
d=json.loads((ROOT/'data/imports'/(SLUG+'.json')).read_text());path=ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf')
norm=lambda s:re.sub(r'\s+','',unicodedata.normalize('NFKC',s))
assert hashlib.sha256(path.read_bytes()).hexdigest()==d['sha256']
assert d['dedicatedParser']=='scripts/import_topps_mls_chrome_2026.py'
heads={norm(r[0]) for r in d['rows']}|{'BASE','INSERT','AUTOGRAPH','AUTOGRAPH-RELIC'}
with pdfplumber.open(path) as physical:
 for pn,page in enumerate(PdfReader(path).pages,1):
  actual=collections.Counter()
  for line in page.extract_text().splitlines():
   v=norm(line)
   if not v or v in heads or v.startswith(('Checklistsprovided','productatthetime','EXCLUSIVETO')):continue
   # PDF text streams place centered ID/country objects after subject text.
   # Split only literal IDs, then verify their physical cells separately.
   match=re.search(r'(?:NPDA|DA)-[A-Z]+',line)
   if match:
    actual.update([match[0]]);v=norm(line[:match.start()]+line[match.end():])
   if v:actual.update([v])
  expected=collections.Counter(norm(r[7]+r[2]+r[4]+r[5]) for r in d['rows'] if r[3]==str(pn))
  for pair in [p for p in d['pairedSourceCards'] if p['page']==pn]:
   expected.update([pair['cardNumber']])
   if pair['country']:expected.update([norm(pair['country'])])
   pg=physical.pages[pn-1];y=pair['baseline'];top=pg.height-y-12;bottom=pg.height-y+3
   code=norm(pg.crop((52,top,131,bottom)).extract_text() or '')
   country=norm(pg.crop((421,top,600,bottom)).extract_text() or '')
   assert code==pair['cardNumber'] and country==norm(pair['country']),(pn,pair,code,country)
  assert actual==expected,(pn,actual-expected,expected-actual)
assert len(d['rows'])==593 and len({tuple(r[:2]) for r in d['rows']})==576
assert d['originalSubjectRows']==[[r[0],r[7],r[2],r[3],r[4],r[5]] for r in d['rows']]
count=collections.Counter(r[0] for r in d['rows']);assert len(count)==21 and len(d['sourceConfigurations'])==14
assert count['BASE CARDS']==200 and {int(r[1]) for r in d['rows'] if r[0]=='BASE CARDS'}==set(range(1,201))
assert count['CHROME DUAL AUTOGRAPHS']==22 and count['NATIONAL PAIRINGS DUAL AUTOGRAPHS']==12
assert len(d['pairedSourceCards'])==17 and sum(not r[7] for r in d['rows'])==34
for p in d['pairedSourceCards']:
 rs=[d['rows'][i] for i in p['subjectRows']];assert len(rs)==2 and all(r[0]==p['family'] and r[1]==p['cardNumber'] and r[6]==p['country'] and not r[7] for r in rs)
assert [(r[2],r[4],r[6]) for r in d['rows'] if r[1]=='NPDA-MF']==[('Lionel Messi','Inter Miami CF','Argentina'),('Enzo Fernández','Chelsea FC','Argentina')]
assert [(r[2],r[4]) for r in d['rows'] if r[1]=='DA-MB']==[('Lionel Messi','Inter Miami CF'),('David Beckham','LA Galaxy')]
assert [(r[2],r[4]) for r in d['rows'] if r[1]=='DA-ME']==[('Cristian Espinoza','Nashville SC'),('Hany Mukhtar','Nashville SC')]
assert count['MLS ALL-TIMERS AUTOGRAPHS']==19 and count['SUMMER CLASH AUTOGRAPHS']==17 and count['MANIA AUTOGRAPHS']==4
assert count['MLS DEBUT PATCH AUTOGRAPHS']==39 and count['MLS COUNTRY PATCH AUTOGRAPHED RELIC CARDS']==18
assert sum(r[5]=='Rookie' for r in d['rows'])==149 and sum(not r[4] for r in d['rows'])==6
assert next(r for r in d['rows'] if r[1]=='RA-BS2')[4]=='Chicago Fire'
assert next(r for r in d['rows'] if r[1]=='G-8')[2]=='Zlatan Ibrahimović'
op=path.with_name(SLUG+'-odds.pdf');assert hashlib.sha256(op.read_bytes()).hexdigest()==d['oddsSha256']
expected=[];token=re.compile(r'(?<!\S)(?:[\d,.]+(?::[\d,.]+)+|-)(?!\S)')
with pdfplumber.open(op) as pdf:
 for pn,page in enumerate(pdf.pages,1):
  tables=page.find_tables();assert len(tables)==1
  for row in tables[0].extract()[1:]:
   full=' '.join(' '.join((v or '').split()) for v in row);m=list(token.finditer(full));assert len(m)==3,(pn,full)
   values=[v[0] for v in m];name=full
   for v in reversed(m):name=name[:v.start()]+name[v.end():]
   expected.append((pn,norm(name),[None if v=='-' else v for v in values]))
assert expected==[(o['page'],norm(o['name']),list(o['values'].values())) for o in d['odds']]
assert len(expected)==139 and d['formats']==['Hobby','Value','Mania'] and not d['oddsUnitsPublished']
by={o['name']:o for o in d['odds']}
assert by['Base Cards Mania']['values']['Mania']=='6:1' and by['Base Cards Refractor']['values']['Mania']=='3:1'
assert {o['family'] for o in d['odds']}==set(count)
specs=d['parallelSpecifications'];assert len(specs)==1 and specs[0]['family']=='MLS TROPHY' and specs[0]['numbering']=='1/1'
assert hashlib.sha256((ROOT/specs[0]['evidenceFile']).read_bytes()).hexdigest()==specs[0]['evidenceSha256']
assert next(r for r in d['rows'] if r[0]=='BASE CARDS' and r[1]=='173')[9].startswith('Superfractor 1/1')
assert all('limited to 10 copies; serial numbering is not stated' in r[9] for r in d['rows'] if r[1]=='DA-MH')
assert sum(bool(r[9]) for r in d['rows'])==3
registry=json.loads((ROOT/'data/parallel-specifications.json').read_text());assert registry['sets'][SLUG]==specs
record=next(r for r in json.loads((ROOT/'data/set-catalog.json').read_text())['sets'] if r['slug']==SLUG)
assert record['releaseDate']=='2026-09-10' and record['rowCount']==593
print('Verified 593 physical MLS subjects / 576 identities, all 17 centered code pairs and six country cells, 149 Rookie marks, 21 families / 14 source configurations, all 139 odds / three columns, exact Trophy 1/1 and September 10 street date. Card-specific examples and box-count discrepancies remain qualified.')
