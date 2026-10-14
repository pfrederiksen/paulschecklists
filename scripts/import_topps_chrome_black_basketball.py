"""Retain original physical columns in Topps' Chrome Black Basketball PDF."""
import collections, hashlib, json, re, subprocess
from pathlib import Path
import pdfplumber
ROOT=Path(__file__).resolve().parents[1]
SLUG='topps-bowman-2026-topps-chrome-black-basketball'
PARSER='scripts/import_topps_chrome_black_basketball.py'
def build():
 catalog_path=ROOT/'data/set-catalog.json';catalog=json.loads(catalog_path.read_text())
 record=next(s for s in catalog['sets'] if s['slug']==SLUG)
 path=ROOT/'data/catalog-sources/downloads'/f'{SLUG}.pdf'
 subprocess.run(['curl','-sLf','--retry','2','--max-time','30',record['checklistUrl'],'-o',str(path)],check=True)
 data_path=ROOT/record['tableData'];data=json.loads(data_path.read_text());rows=[];raw=[];section=None
 with pdfplumber.open(path) as pdf:
  assert len(pdf.pages)==6
  for pn,page in enumerate(pdf.pages,1):
   raw.append({'page':pn,'text':page.extract_text()});lines=collections.defaultdict(list)
   for c in page.chars:lines[round(c['top'],1)].append(c)
   for y,chars in sorted(lines.items()):
    if pn==1 and y<95:continue # Printed disclaimer, above the source table.
    cols=[''.join(c['text'] for c in chars if lo<=c['x0']<hi).strip() for lo,hi in [(0,98),(98,244),(244,328),(328,page.width)]]
    if re.fullmatch(r'\d+|[A-Z0-9]+-[A-Z0-9]+',cols[0]):
     assert section and cols[1] and cols[2] and cols[3] in ['', 'Rookie'],cols
     rows.append([section,*cols,str(pn)])
    else:
     text=''.join(c['text'] for c in chars).strip()
     assert text==text.upper() and re.search('[A-Z]',text),(pn,y,text)
     if text not in ['BASE','AUTOGRAPHS','INSERTS']:section=text
 assert len(rows)==556 and len({r[0] for r in rows})==16
 base=[r for r in rows if r[0]=='BASE CARDS'];rookies=[r for r in rows if r[0]=='ROOKIES']
 assert [int(r[1]) for r in base]==list(range(1,101))
 assert [int(r[1]) for r in rookies]==list(range(101,151))
 assert sum(r[4]=='Rookie' for r in base)==5 and all(r[4]=='Rookie' for r in rookies)
 data.update(headers=['Checklist section','Card number','Name','Team','Rookie','Source page'],rows=rows,rawPages=raw,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),importKind='topps-grid-pdf',dedicatedParser=PARSER,sectionColumn=0,unclassifiedLines=[])
 # Explicit source heading aliases, without changing printed category names.
 aliases={'Base Rookies':'ROOKIES','Base':'BASE CARDS','Rookie Design Variation':'ROOKIE DESIGN VARIATION','Autographs':'AUTOGRAPH CARDS'}
 for odd in data['odds']:
  for prefix,family in aliases.items():
   if odd['name']==prefix or odd['name'].startswith(prefix+' '):
    odd.update(family=family,familyBase=odd['name']==prefix+' Base');break
 data_path.write_text(json.dumps(data,ensure_ascii=False)+'\n')
 record.update(rowCount=len(rows),sections=16,sha256=data['sha256'],importKind=data['importKind'],dedicatedParser=PARSER,dataAudit='All 556 printed card rows reconciled to physical number/name/team/rookie columns; 100 base and 50 rookie numbers, five rookie flags in the first 100 and all 30 printed Rookie Design Variation rows retained. No missing variation numbers are invented.')
 for name in ['set-catalog.json','topps-product-official-catalog.json']:
  p=ROOT/'data'/name;c=json.loads(p.read_text());items=c['sets'] if isinstance(c,dict) else c
  found=False
  for i,r in enumerate(items):
   if r['slug']==SLUG:items[i]=record;found=True
  if name=='topps-product-official-catalog.json' and not found:items.append(record)
  p.write_text(json.dumps(c,ensure_ascii=False,indent=2)+'\n')
 print('Imported 556 physical-column cards, 16 sections and all 150 base/rookie numbers; existing odds retained.')
if __name__=='__main__':build()
