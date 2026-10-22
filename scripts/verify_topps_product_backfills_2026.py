"""Independently compare every imported original cell and odds literal with PDFs."""
import collections,hashlib,json,re
from pathlib import Path
import pdfplumber
from pypdf import PdfReader
ROOT=Path(__file__).resolve().parents[1]
proof=json.loads((ROOT/'data/parallel-audit-sources/product-only-baseball-sapphire-ucc-20261022.json').read_text())
norm=lambda x:re.sub(r'\s+','',x)
for spec in proof['products']:
 key=spec['key'];data=json.loads((ROOT/'data/imports'/(spec['slug']+'.json')).read_text());src=proof[key+'-checklist'];op=proof[key+'-odds'];path=ROOT/src['file'];oddpath=ROOT/op['file']
 assert hashlib.sha256(path.read_bytes()).hexdigest()==data['sha256']==src['sha256']
 assert hashlib.sha256(oddpath.read_bytes()).hexdigest()==data['oddsSha256']==op['sha256']
 assert data['dedicatedParser']=='scripts/import_topps_product_backfills_2026.py' and not data['oddsUnitsPublished']
 rows=data['rows'];families={r[0] for r in rows};notes={r[1] for r in data['sourceDocumentNotes']};ignored={norm(s) for s in families|notes}
 for pn,page in enumerate(PdfReader(path).pages,1):
  actual=collections.Counter(norm(s) for s in page.extract_text().splitlines() if s.strip() and norm(s) not in ignored)
  expected=collections.Counter(norm(''.join(r[1:5])) for r in rows if r[5]==str(pn))
  assert actual==expected,('Independent full pypdf flow',key,pn,actual-expected,expected-actual)
 with pdfplumber.open(path) as pdf:
  for pn,page in enumerate(pdf.pages,1):
   if key=='bowman-sapphire':starts=[133.34,270.89,422.71]
   elif pn<=2:starts=[89.66,162.74,249.41]
   elif pn<=4:starts=[71.18,103.82,137.78]
   elif pn<=6:starts=[83.78,138.74,206.45]
   elif pn<=8:starts=[106.46,230.45,355.75]
   else:starts=[128.54,280.25,428.47]
   # Independent fixed physical rectangles; unlike the importer this does
   # not assign fields from drawing-order column resets.
   bands=[]
   for c in sorted(page.chars,key=lambda c:c['top']):
    if not bands or abs(c['top']-bands[-1][0])>.8:bands.append((c['top'],[]))
    bands[-1][1].append(c)
   found=[]
   for top,chars in bands:
    if not all(any(abs(c['x0']-x)<.04 for c in chars) for x in starts[:2]):continue
    bounds=[0,*[s-.05 for s in starts],page.width];values=[]
    for a,b in zip(bounds,bounds[1:]):
     values.append(' '.join(''.join(c['text'] for c in sorted(chars,key=lambda c:c['x0']) if a<=c['x0']<b).split()))
    found.append(tuple(values))
   assert collections.Counter(found)==collections.Counter(tuple(r[1:5]) for r in rows if r[5]==str(pn)),('Physical field rectangles',key,pn)
 # Independently read every original odds text line, preserving null dashes.
 pdf=PdfReader(oddpath);actual=[]
 for pn,page in enumerate(pdf.pages,1):
  lines=[line.strip() for line in page.extract_text().splitlines() if line.strip()]
  if key=='bowman-sapphire':
   start=lines.index('MLB-BOWMAN 2026 SAPPHIRE')+1;body=lines[start:];assert len(body)==38
   actual.extend((body[i],[body[i+1]],pn) for i in range(0,len(body),2));continue
  for line in lines:
   m=re.match(r'^(.+?)\s+((?:\d[\d,]*(?::[\d,]+)+|-)(?:\s+(?:\d[\d,]*(?::[\d,]+)+|-))*)\s*$',line.strip())
   if m:actual.append((m[1],m[2].split(),pn))
 expected=[(o['name'],[o['values'][f] or '-' for f in data['officialOddsFormats']],o['page']) for o in data['officialOddsTable']]
 assert [list(o['values'].values()) for o in data['odds']]==[list(o['values'].values()) for o in data['officialOddsTable']]
 assert actual==expected,('Every original odds row and cell',key,len(actual),len(expected))
 assert not data.get('parallelSpecifications') and not data.get('categoryNumbering')
 record=next(r for r in json.loads((ROOT/'data/set-catalog.json').read_text())['sets'] if r['slug']==spec['slug'])
 assert record['releaseDate'] is None and record['releaseStatus']=='Unverified'
 if key=='bowman-sapphire':
  assert len(rows)==195 and len(families)==4 and sum(r[4]=='Rookie' for r in rows)==5
  assert {r[1] for r in rows if r[0]=='CHROME PROSPECTS'}=={f'BCP-{i}' for i in range(1,151)}
  assert rows[-1][1:5]==['SSA-WA','Wehiwa Aloy','Baltimore Orioles®','']
  assert len(data['odds'])==19 and data['formats']==['Published odds (format not named)'] and data['officialOddsFormats']==['MLB-BOWMAN 2026 SAPPHIRE'] and not data['formatNamesPublished']
  assert any(o['name']=='CHROME PROSPECTS PADPRADASCHA' for o in data['odds'])
  assert any('PAPRADASCHA' in o['name'] for o in data['odds'])
 else:
  assert len(rows)==950 and len(families)==37 and sum(r[4]=='Rookie' for r in rows)==106
  assert sum(not r[1] for r in rows)==64
  base={'VETERANS AND ROOKIES','FUTURE STARS','UCL TEAM OF THE SEASON','2024 25 TITLE WINNERS'}
  assert len([r for r in rows if r[0] in base])==200 and {r[1] for r in rows if r[0] in base}=={str(i) for i in range(1,201)}
  assert rows[-1][1:5]==['GM-GM','Antoine Griezmann','Atlético de Madrid','']
  assert len(data['odds'])==270 and data['formats']==['Hobby','Value','Hanger','London Store','Carnaval','Japan Hobby','Japan Retail','Spring Tin']
  assert data['odds'][0]['values']['Hanger']=='2:1'
 print('Verified',spec['title'],len(rows),'physical subjects, original field alignment, literal Rookie flags, full odds matrix, hashes and explicit release/numbering gaps.')
